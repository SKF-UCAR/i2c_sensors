from typing import Iterable, Dict, Any, Optional, List, Tuple
from i2c_device import I2CConfig, I2CDevice

from pyftdi.i2c import I2cController, I2cPort


class I2CFtdi(I2CDevice):
    _controller: I2cController
    _port: I2cPort
    _url: str

    def __init__(self, url: str, cfg: I2CConfig):
        super().__init__(cfg)
        self._url = url
        self._controller = I2cController()

    def open(self) -> None:
        self._controller.configure(url=self._url, frequency=self.cfg.freq_hz)
        self._port = self._controller.get_port(self.cfg.address)

    # ---- 8-bit register helpers ------------------------------------------------
    def write_u8(self, reg: int, val: int) -> None:
        self._port.write_to(reg & 0xFF, [val & 0xFF])

    def read_u8(self, reg: int) -> int:
        return self._port.read_from(reg & 0xFF, 1)[0] & 0xFF

    # ---- 16-bit register helpers (big-endian is common on TI parts) -----------
    def write_u16_be(self, reg: int, val: int) -> None:
        hi = (val >> 8) & 0xFF
        lo = val & 0xFF
        self._port.write_to(reg & 0xFF, [hi, lo])

    def write_u16_le(self, reg: int, val: int) -> None:
        lo = (val >> 8) & 0xFF
        hi = val & 0xFF
        self._port.write_to(reg & 0xFF, [hi, lo])

    def read_u16_be(self, reg: int) -> int:
        data = self._port.read_from(reg & 0xFF, 2)
        return ((data[0] << 8) | data[1]) & 0xFFFF

    def read_u16_le(self, reg: int) -> int:
        data = self._port.read_from(reg & 0xFF, 2)
        return ((data[1] << 8) | data[0]) & 0xFFFF

    # ---- Sequential/burst ------------------------------------------------------
    def write_block(self, reg: int, data: Iterable[int]) -> None:
        self._port.write_to(reg & 0xFF, [d & 0xFF for d in data])

    def read_block(self, reg: int, length: int) -> List[int]:
        _bytes = self._port.read_from(reg & 0xFF, length)
        return [_b & 0xFF for _b in _bytes]

    def close(self) -> None:
        try:
            self._controller.close()
        except Exception:
            pass


if __name__ == "__main__":
    import i2c_sensors.utils as utils

    # Simple test/demo
    cfg = I2CConfig(bus=0, address=118, freq_hz=100000)
    dev = I2CFtdi(url="ftdi://ftdi:232h/1", cfg=cfg)
    dev.open()
    # print(utils.scan_i2c(dev, bus=0))
    # dev.reopen(cfg=cfg)

    # dev.write_u8(0x00, 0x42)
    for i in range(5):
        val = dev.read_u8(i)
        print(f"Read reg[{i}]: 0x{val:02X}")

    dev.close()
