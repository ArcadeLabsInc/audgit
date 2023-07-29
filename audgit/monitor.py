from typing import cast

from pynostr.event import Event
from pynostr.relay_manager import RelayManager
from pynostr.filters import FiltersList, Filters
import time
import json
import uuid


class Monitor:
    def __init__(self, debug: bool):
        self.debug = debug
        self.handlers = {}

    def add_handler(self, name, func):
        self.handlers[name] = func

    def start(self, once=False):
        relay_manager = RelayManager(timeout=2)

        relay_manager.add_relay("wss://relay.arcade.city", close_on_eose=False)
        relay_manager.add_relay("wss://nostr-pub.wellorder.net", close_on_eose=False)
        relay_manager.add_relay("wss://relay.damus.io", close_on_eose=False)

        now = time.time()
        print("now: ", now)
        f = Filters(kinds=[65123], limit=100)  # , since=time.time()

        tags = list(self.handlers)

        f.add_arbitrary_tag("j", tags)

        filters = FiltersList([f])

        subscription_id = uuid.uuid1().hex

        relay_manager.add_subscription_on_all_relays(subscription_id, filters)
        relay_manager.run_sync()

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
                            print("publishing result...")
                            time.sleep(1)
                            relay_manager.publish_event(result)
                            self.publish_result(result)
                    except Exception as ex:
                        print("Exception in handler: ", ex)

                    if once:
                        break
            except Exception as ex:
                print("Exception in main loop", ex)

        relay_manager.close_all_relay_connections()

    def one(self):
        self.start(once=True)

    # def list(self):
    #     relay_manager = RelayManager(timeout=2)

    #     relay_manager.add_relay("wss://nostr-pub.wellorder.net", close_on_eose=True)
    #     relay_manager.add_relay("wss://relay.damus.io", close_on_eose=True)

    #     f = Filters(kinds=[65006], limit=100)  # noqa
    #     f.add_arbitrary_tag("j", ["code-review"])
    #     filters = FiltersList([f])

    #     subscription_id = uuid.uuid1().hex

    #     relay_manager.add_subscription_on_all_relays(subscription_id, filters)
    #     relay_manager.run_sync()

    #     # wait for eose
    #     relay_manager.message_pool.eose_notices.get(timeout=10)

    #     for event_msg in relay_manager.message_pool.get_all_events():
    #         event: Event = event_msg.event
    #         print(event.content)

    def publish_result(self, result):
        # publishes the event to nostr
        print("publish result", json.dumps(json.loads(str(result)), indent=4))

    def publish_exception(self, ex):
        print("publish exception", ex)
