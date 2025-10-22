"""
Thin I²C device base class and helpers
"""

# from __future__ import annotations
from typing import Iterable, Dict, Any, List

DEFAULT_BUS_FREQ_HZ: float = 100_000.0  # 100kHz

class I2CConfig:
    
    bus: int
    address: int
    freq_hz: float = DEFAULT_BUS_FREQ_HZ  # Default to 100kHz

    def __init__(self, bus: int, address: int, freq_hz: float = DEFAULT_BUS_FREQ_HZ):
        self.bus = bus
        self.address = address
        self.freq_hz = freq_hz


class I2CAdapter:
    """
    Thin base for I²C register devices. Methods are intentionally small & explicit
    to make a later C++ port straightforward.
    """

    cfg: I2CConfig

    # ---- Device lifecycle ------------------------------------------------------
    def __init__(self, cfg: I2CConfig):
        self.cfg = cfg

    def open(self) -> None:
        """
        Virtual: override in subclasses to open bus/device.
        """
        pass

    def reopen(self, cfg: I2CConfig) -> None:
        self.close()
        self.cfg = cfg
        self.open()

    def configure(self, **kwargs) -> None:
        """
        Virtual: override in subclasses to apply mode/averaging/rates.
        """
        pass

    def close(self) -> None:
        raise NotImplementedError()

    # ---- 8-bit register helpers ------------------------------------------------
    def write_u8(self, reg: int, val: int) -> None:
        raise NotImplementedError()

    def read_u8(self, reg: int) -> int:
        raise NotImplementedError()

    # ---- 16-bit register helpers (big-endian is common on TI parts) -----------
    def write_u16_le(self, reg: int, val: int) -> None:
        raise NotImplementedError()

    def write_u16_be(self, reg: int, val: int) -> None:
        raise NotImplementedError()

    def read_u16_le(self, reg: int) -> int:
        raise NotImplementedError()

    def read_u16_be(self, reg: int) -> int:
        raise NotImplementedError()

    # ---- Sequential/burst ------------------------------------------------------
    def write_block(self, reg: int, data: Iterable[int]) -> None:
        raise NotImplementedError()

    def read_block(self, reg: int, length: int) -> List[int]:
        raise NotImplementedError()

    # # Many I²C devices keep an internal pointer; this allows raw burst reads
    # def read_no_cmd(self, length: int) -> bytes:
    #     raise NotImplementedError()

    # ---- Simple file writer ----------------------------------------------------
    def write_dict_to_file(self, path: str, data: Dict[str, Any]) -> None:
        from .export import write_auto

        write_auto(path, data)
