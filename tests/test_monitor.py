import threading
import time
from unittest.mock import patch, MagicMock

import pytest
from dotenv import load_dotenv
from nostr.event import Event

from audgit.monitor import Monitor, Executor, get_tag

# Load environment variables from .env file in the tests directory
load_dotenv()

# Import the module to be tested


class MonitorEx(Monitor):
    get_events: list[Event]
    enum_events: list[Event]

# Helper function to mock the 'enum' method of Monitor
def mock_enum(events):
    def generator():
        yield from events

    return [generator()]


# Helper function to mock the '_subscribe' method of Monitor
def mock_subscribe(filter):
    return MagicMock(), "subscription_id"


# Helper function to mock the 'from_hex' method of PrivateKey
def mock_from_hex(hex: str):
    return MagicMock()


# Helper function to mock the 'submit' method of Executor
def mock_submit(self, fn, *args, **kwargs):
    return fn(*args, **kwargs)


# Test cases

def test_get_tag():
    event = MagicMock()
    event.tags = [("param1", "value1"), ("param2", "value2")]

    assert get_tag(event, "param1") == "value1"
    assert get_tag(event, "param2") == "value2"
    assert get_tag(event, "param3") is None


def test_monitor_init():
    with patch("audgit.monitor.PrivateKey.from_hex", side_effect=mock_from_hex):
        monitor = Monitor(debug=True)
        assert monitor.debug is True
        assert isinstance(monitor.private_key, MagicMock)


def test_monitor_add_handler():
    monitor = Monitor(debug=True)
    monitor.add_handler("handler_name", lambda x: x)

    assert "handler_name" in monitor.handlers


@pytest.fixture
def monitor(request):
    def mock_msg(ev):
        msg = MagicMock()
        msg.event = ev
        return msg

    enum_events = request.param[0]
    get_events = request.param[1]
    msg_events = [mock_msg(ev) for ev in get_events]

    manager = MagicMock()
    manager.message_pool.events.get = MagicMock(side_effect=msg_events)

    def mock_subscribe(filter):
        return manager, "sub-id"

    with patch("audgit.monitor.PrivateKey.from_hex", mock_from_hex), \
            patch("audgit.monitor.Monitor.enum", side_effect=mock_enum(enum_events)), \
            patch("audgit.monitor.Monitor._subscribe", side_effect=mock_subscribe):
        monitor = Monitor(debug=True)
        monitor.enum_events = enum_events
        monitor.get_events = get_events
        yield monitor


event1 = Event(created_at=int(time.time()), tags=[["status", "done"], ["e", "event0"], ["j", "handler_name"]])


@pytest.mark.parametrize("monitor", [[
    [
        Event(created_at=int(time.time()),
              tags=[["status", "done"], ["e", event1.id], ["R", "result"], ["status", "success"]])
    ],
    [event1,
     Event(created_at=int(time.time()), tags=[["status", "in_progress"], ["e", "event2"], ["j", "handler_name"]]),
     ]
]], indirect=True)
def test_monitor_start(monitor: MonitorEx):
    processed_events = set()
    got_event = threading.Event()

    def mock_handle_event(event: Event):
        # Call the actual handler and keep track of processed events
        processed_events.add(event.id)
        got_event.set()
        return []

    monitor.add_handler("handler_name", mock_handle_event)

    monitor.start(once=True)

    got_event.wait(10)

    assert monitor.get_events[1].id in processed_events
    assert monitor.get_events[0].id not in processed_events
    assert monitor.enum_events[0].id not in processed_events
    assert len(processed_events) == 1


@pytest.mark.parametrize("monitor", [[
    [],
    [
        Event(created_at=int(time.time()), tags=[["status", "in_progress"], ["e", str(i)], ["j", "handler_name"]])
        for i in range(100)
    ]
]], indirect=True)
def test_monitor_start_parallel(monitor: MonitorEx):
    processed_events = set()

    def mock_handle_event(event: Event):
        # Call the actual handler and keep track of processed events
        processed_events.add(event.id)
        if len(processed_events) == len(monitor.get_events):
            monitor.stop = True
        return []

    monitor.add_handler("handler_name", mock_handle_event)

    monitor.start(once=False)


def test_monitor_add_handler_and_start():
    events = [
        MagicMock(tags=[("status", "done"), ("e", "ref_event1")]),
        MagicMock(tags=[("status", "done"), ("e", "ref_event2")]),
    ]

    with patch("audgit.monitor.PrivateKey.from_hex", mock_from_hex), \
            patch("audgit.monitor.Monitor.enum", side_effect=mock_enum(events)), \
            patch("audgit.monitor.Monitor._subscribe", side_effect=mock_subscribe):
        monitor = Monitor(debug=True)
        monitor.add_handler("handler_name", lambda x: x)

        # Check that 'start' method triggers the handler
        with patch.object(monitor, "handlers", {"handler_name": MagicMock()}):
            monitor.start(once=True)

            # Assert that the handler is called with the correct event
            monitor.handlers["handler_name"].assert_called_with(events[0])


def test_executor_submit():
    # Create an Executor instance
    executor = Executor(max_workers=2)

    # Create a test function to be submitted to the executor
    def test_function(value):
        return value * 2

    # Submit the test function to the executor
    future = executor.submit(test_function, 10)

    # Get the result from the future
    result = future.result()

    # Assert that the result is correct
    assert result == 20

# Add more test cases as needed to cover other functions in the Monitor class.
