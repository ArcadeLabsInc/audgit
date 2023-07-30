import os
from queue import Empty
from typing import cast, Callable

from pynostr.event import Event
from pynostr.key import PrivateKey
from pynostr.relay_manager import RelayManager
from pynostr.filters import FiltersList, Filters
import time
import json
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
        self.private_key = PrivateKey.from_hex(os.getenv("NOSTR_PRIVKEY"))
        self.since = time.time() - 3600

    def add_handler(self, name, func):
        self.handlers[name] = func

    def start(self, once=False):
        done = set()

        for event in self.enum(filter=[self.get_reply_filter()]):
            status = get_tag(event, "status")
            ref_event = get_tag(event, "e")
            if status and ref_event:
                done.add(event.id)

        relay_manager = self._subscribe(close_on_eose=False, filter=self.get_job_filter())
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

                    try:
                        for result in self.handlers[name](event):
                            result.pubkey = self.private_key.public_key.hex(),
                            result.sign(self.private_key.hex())
                            if result:
                                log.debug("publishing result...")
                                relay_manager.publish_event(result)
                                self.publish_result(result)
                    except Exception as ex:
                        log.debug("Exception in handler: %s", ex)

                    if once:
                        break
            except Empty:
                pass
            except Exception as ex:
                log.debug("Exception in main loop: %s", ex)

#        relay_manager.close_all_relay_connections()

    def _subscribe(self, close_on_eose, filter: Filters | list[Filters]):
        relay_manager = RelayManager(timeout=2)
        relay_manager.add_relay("wss://relay.arcade.city", close_on_eose=close_on_eose)
        # relay_manager.add_relay("wss://nostr-pub.wellorder.net", close_on_eose=close_on_eose)
        # relay_manager.add_relay("wss://relay.damus.io", close_on_eose=close_on_eose)
        now = time.time()
        log.debug("now: %s", now)
        if not isinstance(filter, list):
            filter = [filter]
        filters = FiltersList(filter)
        subscription_id = uuid.uuid1().hex
        relay_manager.add_subscription_on_all_relays(subscription_id, filters)
        relay_manager.run_sync()
        return relay_manager

    def get_job_filter(self):
        fil = Filters(kinds=[65123], limit=100)  # , since=int(time.time() - 3600)
        tags = list(self.handlers)
        fil.add_arbitrary_tag("j", tags)
        return fil

    def get_reply_filter(self):
        fil = Filters(kinds=[65001], limit=200)  # , since=int(time.time() - 3600)
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
        relay_manager = self._subscribe(close_on_eose=True, filter=fil)

        # wait for eose
        relay_manager.message_pool.eose_notices.get(timeout=60)

        for event_msg in relay_manager.message_pool.get_all_events():
            event: Event = event_msg.event
            yield event

    def list(self):
        for event in self.enum(self.get_job_filter()):
            print(event.content)

    def publish_result(self, result):
        # publishes the event to nostr
        log.debug("publish result %s", json.dumps(json.loads(str(result)), indent=4))

    def publish_exception(self, ex):
        log.debug("publish exception %s", ex)
