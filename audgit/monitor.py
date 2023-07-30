from queue import Empty
from typing import cast

from pynostr.event import Event
from pynostr.relay_manager import RelayManager
from pynostr.filters import FiltersList, Filters
import time
import json
import uuid
import logging

log = logging.getLogger("audgit")


class Monitor:
    def __init__(self, debug: bool):
        self.debug = debug
        self.handlers = {}

    def add_handler(self, name, func):
        self.handlers[name] = func

    def start(self, once=False):
        relay_manager = self._subscribe(close_on_eose=False)

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

                    try:
                        result = self.handlers[name](event)
                        if result:
                            log.debug("publishing result...")
                            time.sleep(1)
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

        relay_manager.close_all_relay_connections()

    def _subscribe(self, close_on_eose):
        relay_manager = RelayManager(timeout=2)
        relay_manager.add_relay("wss://relay.arcade.city", close_on_eose=close_on_eose)
        relay_manager.add_relay("wss://nostr-pub.wellorder.net", close_on_eose=close_on_eose)
        relay_manager.add_relay("wss://relay.damus.io", close_on_eose=close_on_eose)
        now = time.time()
        log.debug("now: %s", now)
        f = Filters(kinds=[65123], limit=100)  # , since=time.time()
        tags = list(self.handlers)
        f.add_arbitrary_tag("j", tags)
        filters = FiltersList([f])
        subscription_id = uuid.uuid1().hex
        relay_manager.add_subscription_on_all_relays(subscription_id, filters)
        relay_manager.run_sync()
        return relay_manager

    def one(self):
        self.start(once=True)

    def list(self):
        relay_manager = self._subscribe(close_on_eose=True)

        # wait for eose
        relay_manager.message_pool.eose_notices.get(timeout=10)

        for event_msg in relay_manager.message_pool.get_all_events():
            event: Event = event_msg.event
            print(event.content)

    def publish_result(self, result):
        # publishes the event to nostr
        log.debug("publish result %s", json.dumps(json.loads(str(result)), indent=4))

    def publish_exception(self, ex):
        log.debug("publish exception %s", ex)
