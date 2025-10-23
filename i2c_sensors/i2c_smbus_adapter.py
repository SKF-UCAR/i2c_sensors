from typing import Iterable, Dict, Any, Optional, List, Tuple
from .i2c_adapter import I2CConfig, I2CAdapter

try:
    # Linux I²C userspace helper
    from smbus2 import SMBus
except ImportError:  # fall back to smbus if needed
    from smbus import SMBus  # type: ignore


class I2CSMBusAdapter(I2CAdapter):
    bus: SMBus

    def __init__(self, cfg: I2CConfig):
        super().__init__(cfg)

    def open(self) -> None:
        self.bus = SMBus(self.cfg.bus)
        self.bus.open(self.cfg.bus)

    def close(self) -> None:
        try:
            self.bus.close()
        except Exception:
            pass

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

    def write_u16_le(self, reg: int, val: int) -> None:
        lo = (val >> 8) & 0xFF
        hi = val & 0xFF
        self.bus.write_i2c_block_data(self.cfg.address, reg & 0xFF, [hi, lo])

    def read_u16_be(self, reg: int) -> int:
        data = self.bus.read_i2c_block_data(self.cfg.address, reg & 0xFF, 2)
        return ((data[0] << 8) | data[1]) & 0xFFFF

    def read_u16_le(self, reg: int) -> int:
        data = self.bus.read_i2c_block_data(self.cfg.address, reg & 0xFF, 2)
        return ((data[1] << 8) | data[0]) & 0xFFFF

    # ---- Sequential/burst ------------------------------------------------------
    def write_block(self, reg: int, data: Iterable[int]) -> None:
        self.bus.write_i2c_block_data(
            self.cfg.address, reg & 0xFF, [d & 0xFF for d in data]
        )

    def read_block(self, reg: int, length: int) -> List[int]:
        return self.bus.read_i2c_block_data(self.cfg.address, reg & 0xFF, length)

    def write_i2c_block_data(self, addr: int, reg: int, data: Iterable[int]) -> None:
        return self.bus.write_i2c_block_data(addr, reg, data)

    def read_i2c_block_data(self, addr: int, reg: int, length: int) -> List[int]:
        return self.bus.read_i2c_block_data(addr, reg, length)
