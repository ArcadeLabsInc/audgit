import os
from queue import Empty
from typing import cast, Callable

from nostr.event import Event
from nostr.key import PrivateKey
from nostr.relay_manager import RelayManager
from nostr.filter import Filters, Filter

import time
import uuid
import logging

log = logging.getLogger("audgit")


def get_tag(event, param):
    for tag in event.tags:
        if tag[0] == param:
            return tag[1]


class Monitor:
    def __init__(self, debug: bool):
        self.debug = debug
        self.handlers: dict[str, Callable] = {}
        self.private_key = PrivateKey.from_hex(os.environ["NOSTR_PRIVKEY"])
        self.since = int(time.time() - 7200)

    def add_handler(self, name, func):
        self.handlers[name] = func

    def start(self, once=False):
        done = set()

        for event in self.enum(filter=[self.get_reply_filter()]):
            status = get_tag(event, "status")
            ref_event = get_tag(event, "e")
            if status and ref_event:
                log.debug("done: %s (%s)", event.id, status)
                done.add(ref_event)

        relay_manager, _sub_id = self._subscribe(filter=self.get_job_filter())

        while True:
            try:
                while event_msg := relay_manager.message_pool.events.get(timeout=5):
                    event: Event = cast(Event, event_msg.event)
                    name = ""
                    for tag in event.tags:
                        if tag[0] == "j":
                            name = tag[1]

                    if name not in self.handlers:
                        continue

                    if event.id in done:
                        continue

                    if event.created_at < self.since:
                        continue

                    log.info("processing event: %s", event.id)
                    try:
                        result: Event
                        for result in self.handlers[name](event):
                            result.kind = 65001
                            result.public_key = self.private_key.public_key.hex()
                            self.private_key.sign_event(result)
                            if result:
                                log.info("publishing result {%s}, for event: %s", result.tags, event.id)
                                relay_manager.publish_event(result)
                    except Exception as ex:
                        log.exception("Exception in handler")
                        result = Event(kind=65001, content=f"Exception: {repr(ex)}", tags=[["e", event.id], ["status", "failure"]])
                        result.pubkey = self.private_key.public_key.hex(),
                        self.private_key.sign_event(result)
                        relay_manager.publish_event(result)

                    if once:
                        break
            except Empty:
                if once:
                    break
                pass
            except Exception as ex:
                log.debug("Exception in main loop: %s", ex)

    #        relay_manager.close_all_relay_connections()

    def _subscribe(self, filter: Filter | list[Filter]):
        relay_manager = RelayManager()
        relay_manager.add_relay("wss://relay.arcade.city")
        relay_manager.add_relay("wss://nostr-pub.wellorder.net")
        relay_manager.add_relay("wss://relay.damus.io")
        now = time.time()
        log.debug("now: %s", now)
        if not isinstance(filter, list):
            filter = [filter]
        filters = Filters(filter)
        subscription_id = uuid.uuid1().hex
        relay_manager.add_subscription_on_all_relays(subscription_id, filters)
        return relay_manager, subscription_id

    def get_job_filter(self):
        fil = Filter(kinds=[65123])  # , since=int(time.time() - 3600)
        tags = list(self.handlers)
        fil.add_arbitrary_tag("j", tags)
        return fil

    def get_reply_filter(self):
        fil = Filter(kinds=[65001], since=self.since)  # , since=int(time.time() - 3600)
        return fil

    def one(self):
        self.start(once=True)

    def cli_review(self, issue: str):
        name = "code-review"
        event = Event(content=issue, tags=[["j", "code-review"]])
        for result in self.handlers[name](event):
            print(result)

    def enum(self, filter):
        fil = filter
        relay_manager, sub_id = self._subscribe(filter=fil)

        # wait for eose
        relay_manager.message_pool.eose_notices.get(timeout=60)

        try:
            while event_msg := relay_manager.message_pool.events.get(False):
                event = event_msg.event
                yield event
        except Empty:
            pass
        relay_manager.close_subscription_on_all_relays(sub_id)
        relay_manager.close_all_relay_connections()

    def list(self):
        for event in self.enum(self.get_job_filter()):
            print(event.id, event.created_at, event.content)
