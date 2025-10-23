import datetime
from i2c_sensors.i2c_adapter import I2CAdapter, I2CConfig

# DS3231 register addresses
_REG_SECONDS = 0x00
_REG_MINUTES = 0x01
_REG_HOURS = 0x02
_REG_DAY = 0x03
_REG_DATE = 0x04
_REG_MONTH = 0x05
_REG_YEAR = 0x06
_REG_TEMP_MSB = 0x11
_REG_TEMP_LSB = 0x12

def _bcd_to_int(b):
    return (b >> 4) * 10 + (b & 0x0F)

def _int_to_bcd(i):
    return ((i // 10) << 4) | (i % 10)

class DS3231:
    """
    Minimal DS3231 driver.

    Usage:
        # adapter must provide:
        #   read_i2c_block_data(addr, reg, length) -> list[int]
        #   write_i2c_block_data(addr, reg, data)
        #   close() optional
        rtc = DS3231(adapter=my_adapter, address=0x68)
        now = rtc.read_time()
        rtc.set_time(datetime.datetime.now())
        temp = rtc.read_temperature()
        rtc.close()
    """
    def __init__(self, adapter: I2CAdapter):
        # adapter: an I2CAdapter instance (see docstring)
        self._adapter = adapter

    def open(self):
        self._adapter.open()

    def close(self):
        # try:
        #     close_fn = getattr(self._adapter, "close", None)
        #     if callable(close_fn):
        #         close_fn()
        # except Exception:
        #     pass
        self._adapter.close()

    def _read_regs(self, reg, length):
        return self._adapter.read_block(reg, length)

    def _write_regs(self, reg, data):
        self._adapter.write_block(reg, data)

    def read_time(self):
        """
        Read current time from RTC and return a timezone-naive datetime.
        """
        raw = self._read_regs(_REG_SECONDS, 7)
        sec = _bcd_to_int(raw[0] & 0x7F)
        minute = _bcd_to_int(raw[1] & 0x7F)

        hour_reg = raw[2]
        # Handle 12/24 hour mode. If bit 6 is set, 12-hour mode.
        if hour_reg & 0x40:
            # 12-hour mode: bit 5 is AM/PM, bottom 5 bits BCD hour (1-12)
            hour = _bcd_to_int(hour_reg & 0x1F)
            if hour_reg & 0x20:  # PM flag
                if hour != 12:
                    hour = (hour + 12) % 24
            else:  # AM
                if hour == 12:
                    hour = 0
        else:
            hour = _bcd_to_int(hour_reg & 0x3F)

        day = _bcd_to_int(raw[4] & 0x3F)
        month_reg = raw[5]
        month = _bcd_to_int(month_reg & 0x1F)
        year = _bcd_to_int(raw[6]) + 2000

        return datetime.datetime(year, month, day, hour, minute, sec)

    def set_time(self, dt):
        """
        Set RTC time. Accepts datetime.datetime (uses dt.year 2000-2099).
        """
        year = dt.year
        if year < 2000 or year > 2099:
            raise ValueError("Year must be in range 2000-2099 for DS3231")
        data = [
            _int_to_bcd(dt.second),
            _int_to_bcd(dt.minute),
            _int_to_bcd(dt.hour),  # write 24-hour mode
            _int_to_bcd(dt.isoweekday() % 7 or 7),  # day of week (1-7). keep simple
            _int_to_bcd(dt.day),
            _int_to_bcd(dt.month),
            _int_to_bcd(dt.year - 2000),
        ]
        self._write_regs(_REG_SECONDS, data)

    def read_temperature(self):
        """
        Read temperature in degrees Celsius as float with 0.25°C resolution.
        """
        msb = self._read_regs(_REG_TEMP_MSB, 1)[0]
        lsb = self._read_regs(_REG_TEMP_LSB, 1)[0]
        # msb is signed 8-bit, lsb's top two bits are the fraction (0.25 increments)
        if msb & 0x80:  # negative
            msb = msb - 256
        frac = (lsb >> 6) * 0.25
        return msb + frac


    def read_all(self):
        """
        Read all time and temperature data from the RTC.
        """
        return {
            "time": self.read_time(),
            "temperature": self.read_temperature(),
        }

if __name__ == "__main__":
    import i2c_sensors.utils as utils
    from i2c_sensors.i2c_ftdi_adapter import I2CFtdiAdapter
    log = utils.get_logger("DS3231")
    adapter = I2CFtdiAdapter(url="ftdi://ftdi::P03UM9NA/2", cfg=I2CConfig(2, 0x68))
    rtc = DS3231(adapter)
    rtc.open()
    rtc.set_time(datetime.datetime.now())
    print(rtc.read_all())
    rtc.close()