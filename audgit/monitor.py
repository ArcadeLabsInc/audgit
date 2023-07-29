from typing import cast

from pynostr.event import Event
from pynostr.relay_manager import RelayManager
from pynostr.filters import FiltersList, Filters
import uuid


class Monitor:
    def __init__(self, debug: bool):
        self.debug = debug

    def add_handler(self, name, func):
        
    def start(self, once=False):
        relay_manager = RelayManager(timeout=2)

        relay_manager.add_relay("wss://nostr-pub.wellorder.net", close_on_eose=False)
        relay_manager.add_relay("wss://relay.damus.io", close_on_eose=False)

        f = Filters(kinds=[68005], limit=100)  # noqa
        f.add_arbitrary_tag("j", ["code-review"])
        filters = FiltersList([f])

        subscription_id = uuid.uuid1().hex

        relay_manager.add_subscription_on_all_relays(subscription_id, filters)
        relay_manager.run_sync()

        while event_msg := relay_manager.message_pool.events.get(timeout=5):
            event: Event = cast(Event, event_msg.event)

            print(event.content)

            if once:
                break

        relay_manager.close_all_relay_connections()

    def one(self):
        self.start(once=True)

    def list(self):
        relay_manager = RelayManager(timeout=2)

        relay_manager.add_relay("wss://nostr-pub.wellorder.net", close_on_eose=True)
        relay_manager.add_relay("wss://relay.damus.io", close_on_eose=True)

        f = Filters(kinds=[68005], limit=100)  # noqa
        f.add_arbitrary_tag("j", ["code-review"])
        filters = FiltersList([f])

        subscription_id = uuid.uuid1().hex

        relay_manager.add_subscription_on_all_relays(subscription_id, filters)
        relay_manager.run_sync()

        # wait for eose
        relay_manager.message_pool.eose_notices.get(timeout=10)

        for event_msg in relay_manager.message_pool.get_all_events():
            event: Event = event_msg.event
            print(event.content)