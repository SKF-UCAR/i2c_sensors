from typing import Iterable, List, Mapping, Any
from i2c_sensors.i2c_adapter import I2CConfig, I2CAdapter
try:
    from pyftdi.i2c import I2cController, I2cPort
except ImportError as _e:
    raise ImportError(
        "The 'pyftdi' package is required for FTDI I2C support but is not installed in the active Python environment.\n"
        "If you're using the project's virtualenv, activate it first, for example:\n"
        "  source .venv/bin/activate\n"
        "or install into the venv directly:\n"
        "  .venv/bin/pip install pyftdi\n"
        "Alternatively install / upgrade globally or in your active env:\n"
        "  pip install pyftdi\n"
    ) from _e


class I2CFtdiAdapter(I2CAdapter):
    _controller: I2cController
    _port: I2cPort
    _url: str

    def __init__(self, url: str, cfg: I2CConfig):
        super().__init__(cfg)
        self._url = url
        self._controller = I2cController()

    def open(self) -> None:
        # self._controller.configure(url=self._url, frequency= self.cfg.freq_hz)
        # self._controller.configure(url=self._url, frequency= self.cfg.freq_hz)
        fd: Mapping[str, Any] = {"frequency": self.cfg.freq_hz}
        self._controller.configure(url=self._url, **fd)
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
    
    def write_i2c_block_data(self, addr: int, reg: int, data: Iterable[int]) -> None:
        return self._controller.write_i2c_block_data(addr, reg, data)

    def read_i2c_block_data(self, addr: int, reg: int, length: int) -> List[int]:
        return self._controller.read_i2c_block_data(addr, reg, length)

    def close(self) -> None:
        try:
            self._controller.close()
        except Exception:
            pass


if __name__ == "__main__":
    import utils as utils
    import argparse

    from pyftdi.ftdi import Ftdi

    devices = Ftdi.list_devices()
    if not devices:
        print("No FTDI devices found")
        exit(1)


    # devices is a list of tuples: (usb_device, (vid, pid, serial), iface)
    for d in devices:
        # print(f"Found FTDI device: VID=0x{d[1][0]:04x} PID=0x{d[1][1]:04x} S/N={d[1][2]}")
        print(f"Found FTDI device: {d}")

    argparser = argparse.ArgumentParser(
        description="Simple test/demo of FTDI I2C adapter"
    )
    argparser.add_argument("--ftdiURL", type=str, help="FTDI URL (e.g. ftdi://ftdi::1/1)")
    args = argparser.parse_args()

    # Simple test/demo
    cfg = I2CConfig(bus=0, address=118, freq_hz=100000)
    url = args.ftdiURL if args.ftdiURL else "ftdi://ftdi::P03UM9NA/2"
    dev = I2CFtdiAdapter(url=url, cfg=cfg)
    print("Opening FTDI I2C adapter...")
    dev.open()
    print("Looking for I2C devices:")
    for d in utils.scan_i2c(dev, bus=0):
        print(f"Found I2C device at address 0x{d:02X}")

    # dev.reopen(cfg=cfg)
    # dev.write_u8(0x00, 0x42)
    # for i in range(5):
    #     val = dev.read_u8(i)
    #     print(f"Read reg[{i}]: 0x{val:02X}")

    dev.close()
