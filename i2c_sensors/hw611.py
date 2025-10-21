from i2c_sensors.i2c_device import I2CDevice
import time

# BMP280 temperature + pressure sensor driver based on the BMP280 datasheet.
# Uses i2c_sensors.I2CDevice for bus access.


class HW611:
    """
    BMP280-compatible driver (keeps the original class name for compatibility).
    Implements calibration readout and compensation per the BMP280 datasheet.
    Provides temperature (°C) and pressure (Pa) properties.
    """

    _device: I2CDevice = None

    DEFAULT_ADDRESS = 0x76  # common BMP280 address (0x76 or 0x77)

    # BMP280 registers
    REG_CALIB_START = 0x88  # calibration registers start (26 bytes)
    REG_ID = 0xD0
    REG_RESET = 0xE0
    REG_STATUS = 0xF3
    REG_CTRL_MEAS = 0xF4
    REG_CONFIG = 0xF5
    REG_PRESS_MSB = 0xF7  # read 6 bytes: press(3) then temp(3)

    def __init__(self, device: I2CDevice):
        """
        Initialize BMP280 driver, read calibration data and set a sane default config.
        """
        self._device = device
        self._device.open()

        # calibration parameters (will be filled from the device)
        self._dig_T1 = 0
        self._dig_T2 = 0
        self._dig_T3 = 0
        self._dig_P1 = 0
        self._dig_P2 = 0
        self._dig_P3 = 0
        self._dig_P4 = 0
        self._dig_P5 = 0
        self._dig_P6 = 0
        self._dig_P7 = 0
        self._dig_P8 = 0
        self._dig_P9 = 0

        # t_fine computed during temperature compensation and used for pressure
        self._t_fine = 0

        # read calibration data from sensor
        self._read_calibration()

        # configure sensor: osrs_t = 1, osrs_p = 1, mode = normal (0b001_001_11 => 0x27)
        # This is a safe default; adjust oversampling and filter in REG_CONFIG if needed.
        self._write_register(self.REG_CTRL_MEAS, bytes([0x27]))

    # --- low-level register access ------------------------------------------------
    def _read_register(self, register: int, length: int) -> bytearray:
        return self._device.read_block(register, length)

    def _write_register(self, register: int, data: bytes) -> None:
        self._device.write_block(register, data)

    def _u16_le(self, lo: int, hi: int) -> int:
        return (hi << 8) | lo

    def _s16_le(self, lo: int, hi: int) -> int:
        val = self._u16_le(lo, hi)
        if val & 0x8000:
            val -= 1 << 16
        return val

    def _wait_until_ready(self, timeout: float = 1.0) -> bool:
        """Wait until BUSY_STATUS indicates ready, or timeout (seconds)"""
        t0 = time.time()
        while not self._device.read_u8(self.REG_STATUS) & 0x07:
            if (time.time() - t0) > timeout:
                return False
            time.sleep(0.01)
        return True

    def _read_calibration(self) -> None:
        # Read 26 bytes of calibration data starting at 0x88
        calib = self._read_register(self.REG_CALIB_START, 26)
        # calib is little-endian per datasheet
        self._dig_T1 = self._u16_le(calib[0], calib[1])
        self._dig_T2 = self._s16_le(calib[2], calib[3])
        self._dig_T3 = self._s16_le(calib[4], calib[5])
        self._dig_P1 = self._u16_le(calib[6], calib[7])
        self._dig_P2 = self._s16_le(calib[8], calib[9])
        self._dig_P3 = self._s16_le(calib[10], calib[11])
        self._dig_P4 = self._s16_le(calib[12], calib[13])
        self._dig_P5 = self._s16_le(calib[14], calib[15])
        self._dig_P6 = self._s16_le(calib[16], calib[17])
        self._dig_P7 = self._s16_le(calib[18], calib[19])
        self._dig_P8 = self._s16_le(calib[20], calib[21])
        self._dig_P9 = self._s16_le(calib[22], calib[23])
        # bytes 24-25 are reserved/unused in many chips; ignore

    def _read_raw_temp_press(self):
        # Read 6 bytes starting at 0xF7: press_msb, press_lsb, press_xlsb, temp_msb, temp_lsb, temp_xlsb
        if not self._wait_until_ready(timeout=1.0):
            err_msg = "Timeout waiting for BMP280 to become ready"
            # self._config.log.error(err_msg)
            raise TimeoutError(err_msg)

        data = self._read_register(self.REG_PRESS_MSB, 6)
        press_raw = (data[0] << 12) | (data[1] << 4) | (data[2] >> 4)
        temp_raw = (data[3] << 12) | (data[4] << 4) | (data[5] >> 4)
        return temp_raw, press_raw

    # --- compensation algorithms from BMP280 datasheet ---------------------------

    def _raw_to_temp(self, raw: int) -> float:
        # Helper to convert raw temperature to °C without updating t_fine
        var1 = (((raw >> 3) - (self._dig_T1 << 1)) * self._dig_T2) >> 11
        var2 = (
            ((((raw >> 4) - self._dig_T1) * ((raw >> 4) - self._dig_T1)) >> 12)
            * self._dig_T3
        ) >> 14
        t_fine = var1 + var2
        t = (t_fine * 5 + 128) >> 8  # temperature in 0.01°C
        return t / 100.0

    @property
    def temperature(self) -> float:
        """
        Returns compensated temperature in degrees Celsius.
        """
        temp_raw, _ = self._read_raw_temp_press()
        # # Temperature compensation
        # var1 = (((temp_raw >> 3) - (self._dig_T1 << 1)) * self._dig_T2) >> 11
        # var2 = (
        #     (
        #         (((temp_raw >> 4) - self._dig_T1) * ((temp_raw >> 4) - self._dig_T1))
        #         >> 12
        #     )
        #     * self._dig_T3
        # ) >> 14
        # self._t_fine = var1 + var2
        # t = (self._t_fine * 5 + 128) >> 8  # temperature in 0.01°C
        # return t / 100.0
        return self._raw_to_temp(temp_raw)

    def _raw_to_pressure(self, raw: int) -> float:
        var1 = self._t_fine - 128000
        var2 = var1 * var1 * self._dig_P6
        var2 = var2 + ((var1 * self._dig_P5) << 17)
        var2 = var2 + (self._dig_P4 << 35)
        var1 = ((var1 * var1 * self._dig_P3) >> 8) + ((var1 * self._dig_P2) << 12)
        var1 = (((1 << 47) + var1) * self._dig_P1) >> 33

        if var1 == 0:
            return 0.0  # avoid division by zero

        p = 1048576 - raw
        p = (((p << 31) - var2) * 3125) // var1
        var1 = (self._dig_P9 * (p >> 13) * (p >> 13)) >> 25
        var2 = (self._dig_P8 * p) >> 19
        p = ((p + var1 + var2) >> 8) + (self._dig_P7 << 4)
        # p is in Q24.8 format (Pa * 256)
        return p / 256.0

    @property
    def pressure(self) -> float:
        """
        Returns compensated pressure in Pascals (Pa).
        """
        # Ensure temperature was read to populate t_fine
        # Some sensors require reading temperature prior to pressure compensation
        # _ = self.temperature

        _, press_raw = self._read_raw_temp_press()
        return self._raw_to_pressure(press_raw)

    # Optional: allow writing ctrl_meas or config registers
    def configure(self, ctrl_meas: int = 0b01101111, config: int = 0x00) -> None:
        """
        Configure the sensor: ctrl_meas is written to REG_CTRL_MEAS, config to REG_CONFIG.
        Defaults select oversampling x1 for temp/press and normal mode.
        """
        self._write_register(self.REG_CONFIG, bytes([config]))
        self._write_register(self.REG_CTRL_MEAS, bytes([ctrl_meas]))

    def read_all(self) -> dict:
        """
        Read and return all sensor data as a dictionary.
        """
        raw_temp, raw_press = self._read_raw_temp_press()
        self._t_fine = 0  # reset t_fine
        temperature = self._raw_to_temp(raw_temp)
        pressure = self._raw_to_pressure(raw_press)
        return {
            "temperature_c": temperature,
            "temperature_f": temperature * 9.0 / 5.0 + 32.0,
            "temperature_raw": raw_temp,
            "pressure_pa": pressure,
            "pressure_mmHg": int(pressure * 0.00750062),
            "pressure_raw": raw_press,
        }


if __name__ == "__main__":
    import logging
    from i2c_sensors.i2c_device_ftdi import I2CFtdi
    from i2c_sensors.i2c_device import I2CConfig

    logging.basicConfig(level=logging.DEBUG)
    log = logging.getLogger("BMP280_Test")

    # Example usage
    i2c_cfg = I2CConfig(bus=1, address=HW611.DEFAULT_ADDRESS, freq_hz=100000)
    i2c_dev = I2CFtdi(url="ftdi://ftdi:232h/1", cfg=i2c_cfg)
    i2c_dev.open()

    bmp = HW611(i2c_dev)
    bmp.configure(ctrl_meas=0b01011111, config=0x00)  # oversampling x1, normal mode

    try:
        temp = bmp.temperature
        pressure = bmp.pressure

        log.info(f"Temperature: {temp:.2f} °C")
        log.info(f"Pressure: {pressure:.2f} Pa")
        res = bmp.read_all()
        log.info(f"All Sensor Data: ")
        log.info(f"  Temperature (C): {res['temperature_c']:.2f}")
        log.info(f"  Temperature (F): {res['temperature_f']:.2f}")
        log.info(f"  Temperature (Raw): 0x{res['temperature_raw']:06X}")
        log.info(f"  Pressure (Pa): {res['pressure_pa']:.2f}")
        log.info(f"  Pressure (mmHg): {res['pressure_mmHg']}")
        log.info(f"  Pressure (Raw): 0x{res['pressure_raw']:06X}")
    finally:
        i2c_dev.close()
