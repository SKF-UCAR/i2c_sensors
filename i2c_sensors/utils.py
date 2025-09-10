"""
Utility functions for i2c_sensors package 
    - logging, 
    - config files, 
    - I2C scan, 
    - UDP send, 
    - periodic scheduling
"""
import logging
from typing import Optional, Union

### Simple logging utility for i2c_sensors package ###

_default_logger: Optional[logging.Logger] = None


def init_logger(
    name: Optional[str] = None,
    level: int = logging.INFO,
    logfile: Optional[str] = None,
    fmt: Optional[str] = None,
) -> logging.Logger:
    """
    Initialize and return a logger.

    - name: logger name (defaults to 'i2c_sensors' if None)
    - level: logging level (e.g. logging.DEBUG)
    - logfile: optional path to a file to also log to
    - fmt: optional format string for log messages
    """
    global _default_logger
    name = name or "i2c_sensors"
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # remove existing handlers to allow re-init
    for h in list(logger.handlers):
        logger.removeHandler(h)

    fmt = fmt or "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    formatter = logging.Formatter(fmt)

    sh = logging.StreamHandler()
    sh.setFormatter(formatter)
    logger.addHandler(sh)

    if logfile:
        fh = logging.FileHandler(logfile)
        fh.setFormatter(formatter)
        logger.addHandler(fh)

    _default_logger = logger
    return logger


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """
    Return the default logger if initialized, otherwise return a named logger.
    """
    if _default_logger is not None:
        return _default_logger
    return logging.getLogger(name or "i2c_sensors")


def _resolve_logger(logger: Optional[Union[str, logging.Logger]]) -> logging.Logger:
    if logger is None:
        return get_logger()
    if isinstance(logger, logging.Logger):
        return logger
    return logging.getLogger(str(logger))


def info(msg: str, *args, logger: Optional[Union[str, logging.Logger]] = None, **kwargs) -> None:
    _resolve_logger(logger).info(msg, *args, **kwargs)


def debug(msg: str, *args, logger: Optional[Union[str, logging.Logger]] = None, **kwargs) -> None:
    _resolve_logger(logger).debug(msg, *args, **kwargs)


def error(msg: str, *args, logger: Optional[Union[str, logging.Logger]] = None, **kwargs) -> None:
    _resolve_logger(logger).error(msg, *args, **kwargs)


def warning(msg: str, *args, logger: Optional[Union[str, logging.Logger]] = None, **kwargs) -> None:
    _resolve_logger(logger).warning(msg, *args, **kwargs)


### Simple config file reader/writer ###
import json

def read_json(path: str) -> dict:
    with open(path, "r") as f:
        return json.load(f)     
    
def write_json(path: str, obj: dict) -> None:
    with open(path, "w") as f:
        json.dump(obj, f, indent=2, sort_keys=True) 

### Simple I2C address scanner ###
import smbus2

def scan_i2c(busnum: int = 1, logger: Optional[Union[str, logging.Logger]] = None) -> list[int]:
    """
    Scan I2C bus for devices; return list of found addresses.
    """
    logger = _resolve_logger(logger)
    found : list[int] = []
    try:
        bus = smbus2.SMBus(busnum)
    except FileNotFoundError as e:
        logger.error(f"Cannot open I2C bus {busnum}: {e}")
        return found
    logger.info(f"Scanning I2C bus {busnum}...")
    for addr in range(0x03, 0x78):
        try:
            bus.write_quick(addr)
            found.append(addr)
            logger.info(f"  Found device at address 0x{addr:02X}")
        except OSError:
            pass
    bus.close()
    if not found:
        logger.info("  No I2C devices found.")
    return found

### senf UDP message ###
import socket

def send_udp_message(message: str, host: str, port: int, logger: Optional[Union[str, logging.Logger]] = None) -> None:
    """
    Send a UDP message to the specified host and port.
    """
    logger = _resolve_logger(logger)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.sendto(message.encode('utf-8'), (host, port))
        logger.debug(f"Sent UDP message to {host}:{port}")
    except Exception as e:
        logger.error(f"Error sending UDP message: {e}")
    finally:
        sock.close()

### Schedule periodic function call ###
import threading

def schedule_periodic(func, interval: float, *args, **kwargs) -> threading.Event:
    """
    Schedule a function to be called periodically every 'interval' seconds.
    Returns an Event that can be set to stop the periodic calls.
    """
    stop_event = threading.Event()

    def wrapper():
        while not stop_event.is_set():
            func(*args, **kwargs)
            stop_event.wait(interval)

    thread = threading.Thread(target=wrapper)
    thread.daemon = True
    thread.start()
    return stop_event

### End of i2c_sensors/utils.py ###
