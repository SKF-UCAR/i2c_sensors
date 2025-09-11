"""
Thin I²C device base class and helpers
"""
from __future__ import annotations
from typing import Iterable, Dict, Any, Optional, List, Tuple
import time

try:
    # Linux I²C userspace helper
    from smbus2 import SMBus, i2c_msg
except ImportError:  # fall back to smbus if needed
    from smbus import SMBus  # type: ignore


class I2CConfig:
    bus: int
    address: int
    freq_hz: Optional[int] = None  # informational; not configured here

    def __init__(self, bus: int, address: int, freq_hz: Optional[int] = None):
        self.bus = bus
        self.address = address
        self.freq_hz = freq_hz

class I2CDevice:
    """
    Thin base for I²C register devices. Methods are intentionally small & explicit
    to make a later C++ port straightforward.
    """
    cfg: I2CConfig
    bus: SMBus

    def __init__(self, cfg: I2CConfig):
        self.cfg = cfg
        self.bus = SMBus(cfg.bus)

    # ---- 8-bit register helpers ------------------------------------------------
    def write_u8(self, reg: int, val: int) -> None:
        self.bus.write_byte_data(self.cfg.address, reg & 0xFF, val & 0xFF)

    def read_u8(self, reg: int) -> int:
        return self.bus.read_byte_data(self.cfg.address, reg & 0xFF) & 0xFF

    # ---- 16-bit register helpers (big-endian is common on TI parts) -----------
    def write_u16_be(self, reg: int, val: int) -> None:
        hi = (val >> 8) & 0xFF
        lo = val & 0xFF
        self.bus.write_i2c_block_data(self.cfg.address, reg & 0xFF, [hi, lo])

    def read_u16_be(self, reg: int) -> int:
        data = self.bus.read_i2c_block_data(self.cfg.address, reg & 0xFF, 2)
        return ((data[0] << 8) | data[1]) & 0xFFFF

    # ---- Sequential/burst ------------------------------------------------------
    def write_block(self, reg: int, data: Iterable[int]) -> None:
        self.bus.write_i2c_block_data(self.cfg.address, reg & 0xFF, [d & 0xFF for d in data])

    def read_block(self, reg: int, length: int) -> List[int]:
        return self.bus.read_i2c_block_data(self.cfg.address, reg & 0xFF, length)

    # Many I²C devices keep an internal pointer; this allows raw burst reads
    def read_no_cmd(self, length: int) -> bytes:
        read = i2c_msg.read(self.cfg.address, length)
        self.bus.i2c_rdwr(read)
        return bytes(list(read))

    # ---- Device lifecycle ------------------------------------------------------
    def configure(self, **kwargs) -> None:
        """
        Virtual: override in subclasses to apply mode/averaging/rates.
        """
        pass

    def close(self) -> None:
        try:
            self.bus.close()
        except Exception:
            pass

    # ---- Simple file writer ----------------------------------------------------
    def write_dict_to_file(self, path: str, data: Dict[str, Any]) -> None:
        from .export import write_auto
        write_auto(path, data)
