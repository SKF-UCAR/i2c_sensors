import io
import json
import threading
import time
import types
import pytest
import importlib

def test_import_utils():
    importlib.import_module('i2c_sensors.utils')


def _reload_utils():
    # helper to reload module and reset state between tests
    utils = importlib.import_module('i2c_sensors.utils')
    importlib.reload(utils)
    # ensure default logger cleared
    try:
        utils._default_logger = None
    except Exception:
        pass
    return utils


def test_init_get_resolve_and_wrappers(tmp_path, caplog):
    utils = _reload_utils()

    # init logger with file output
    logfile = tmp_path / "test.log"
    logger = utils.init_logger(name="testlogger", level=10, logfile=str(logfile), fmt="%(levelname)s:%(message)s")
    assert logger.name == "testlogger"
    # get_logger should return the initialized default logger
    got = utils.get_logger()
    assert got is logger

    # _resolve_logger with None returns default
    assert utils._resolve_logger(None) is logger
    # with a logger instance returns that instance
    other = importlib.import_module('logging').getLogger("other")
    assert utils._resolve_logger(other) is other
    # with a name returns a logger with that name
    named = utils._resolve_logger("arnold")
    assert named.name == "arnold"

    # test wrapper functions produce log records
    caplog.clear()
    caplog.set_level(10)
    utils.info("info-msg")
    utils.debug("debug-msg")
    utils.warning("warn-msg")
    utils.error("err-msg")
    # ensure messages are present
    texts = [r.message for r in caplog.records]
    assert "info-msg" in texts
    assert "debug-msg" in texts
    assert "warn-msg" in texts
    assert "err-msg" in texts

    # logfile should be created and contain formatted logs
    with open(logfile, "r") as f:
        data = f.read()
    assert "INFO" in data or "info-msg" in data


def test_read_write_json(tmp_path):
    utils = _reload_utils()
    p = tmp_path / "cfg.json"
    obj = {"b": 2, "a": 1}
    utils.write_json(str(p), obj)
    assert p.exists()
    loaded = utils.read_json(str(p))
    assert loaded == obj
    # ensure file is pretty-printed (indentation)
    text = p.read_text()
    assert "\n" in text and "  " in text


def test_scan_i2c_found_and_not_found(monkeypatch, caplog):
    utils = _reload_utils()
    caplog.set_level(20)  # INFO

    # Fake SMBus that finds devices at 0x10 and 0x20
    class FakeBus:
        def __init__(self, busnum):
            self.busnum = busnum
            self.closed = False

        def write_quick(self, addr):
            if addr in (0x10, 0x20):
                return  # success
            raise OSError("no device")

        def close(self):
            self.closed = True

    monkeypatch.setattr(utils, "smbus2", types.SimpleNamespace(SMBus=FakeBus))
    found = utils.scan_i2c(busnum=1)
    assert 0x10 in found and 0x20 in found
    assert all(isinstance(a, int) for a in found)
    # logs mention found devices
    logs = "\n".join(r.getMessage() for r in caplog.records)
    assert "Found device at address 0x10" in logs or "0x10" in logs

    # simulate bus missing (FileNotFoundError)
    def raise_on_open(busnum):
        raise FileNotFoundError("no bus")
    monkeypatch.setattr(utils, "smbus2", types.SimpleNamespace(SMBus=raise_on_open))
    caplog.clear()
    found2 = utils.scan_i2c(busnum=99)
    assert found2 == []
    # should log an error about cannot open bus
    assert any("Cannot open I2C bus" in r.getMessage() for r in caplog.records)


def test_send_udp_message_success_and_failure(monkeypatch, caplog):
    utils = _reload_utils()
    # ensure logger exists and captures debug/error
    utils.init_logger(name="udp-test", level=10, fmt="%(levelname)s:%(message)s")
    caplog.set_level(10)

    # Fake socket that records sendto calls
    class FakeSocket:
        def __init__(self, af, type):
            self.sent = []

        def sendto(self, data, addr):
            self.sent.append((data, addr))

        def close(self):
            pass

    def fake_socket_factory(af, type):
        return FakeSocket(af, type)

    monkeypatch.setattr(utils, "socket", types.SimpleNamespace(socket=fake_socket_factory))
    utils.send_udp_message("hello", "127.0.0.1", 9999)
    # debug logged on success
    assert any("Sent UDP message" in r.getMessage() for r in caplog.records)

    # Now make sendto raise
    class BadSocket:
        def __init__(self, af, type):
            pass
        def sendto(self, data, addr):
            raise RuntimeError("boom")
        def close(self):
            pass

    monkeypatch.setattr(utils, "socket", types.SimpleNamespace(socket=lambda a, b: BadSocket(a, b)))
    caplog.clear()
    utils.send_udp_message("x", "127.0.0.1", 1)
    assert any("Error sending UDP message" in r.getMessage() for r in caplog.records)


def test_schedule_periodic_calls_and_stops():
    utils = _reload_utils()
    calls = []
    def fn(x=None):
        calls.append(time.time())

    stop_event = utils.schedule_periodic(fn, 0.01)
    # let it run a bit
    time.sleep(0.08)
    stop_event.set()
    # allow thread to exit
    time.sleep(0.02)
    assert len(calls) >= 2
