from __future__ import annotations
from dataclasses import dataclass
import logging
from typing import Dict, Any, Optional
from enum import IntFlag, IntEnum

import i2c_sensors.utils as utils
from .i2c_device import I2CDevice, I2CConfig


# Register addresses (datasheet Table / summary)
class INA260_CONFIG_REG(IntEnum):
    REG_CONFIG = 0x00
    REG_CURRENT = 0x01
    REG_BUS_VOLT = 0x02
    REG_POWER = 0x03
    REG_MASK_ENABLE = 0x06
    REG_ALERT_LIMIT = 0x07
    REG_MFG_ID = 0xFE
    REG_DIE_ID = 0xFF


# LSBs (Electrical Characteristics): current=1.25mA, voltage=1.25mV, power=10mW
LSB_CURRENT_A = 1.25e-3
LSB_VOLT_V = 1.25e-3
LSB_POWER_W = 10e-3
DEFAULT_CONFIG_REG = 0x6127  # default reset value 0b0110000100100111


@dataclass
class INA260Reading:
    """Simple container for INA260 readings"""

    bus_voltage_v: float
    current_a: float
    power_w: float
    raw_bus: int
    raw_current: int
    raw_power: int


# Define the mode enums at module level to avoid depending on the enclosing class
# during class creation (some static analyzers or runtimes can report a self-dependency).
class INA260_AVG_MODE(IntFlag):
    AVG_MODE_0001 = 0x0000
    AVG_MODE_0004 = 0x0200
    AVG_MODE_0016 = 0x0400
    AVG_MODE_0064 = 0x0600
    AVG_MODE_0128 = 0x0800
    AVG_MODE_0256 = 0x0A00
    AVG_MODE_0512 = 0x0C00
    AVG_MODE_1024 = 0x0E00


# Bus Voltage conversion time settings (in microseconds)
class INA260_VCT_MODE(IntFlag):
    VCT_MODE_140US = 0x0000
    VCT_MODE_204US = 0x0040
    VCT_MODE_332US = 0x0080
    VCT_MODE_588US = 0x00C0
    VCT_MODE_1100US = 0x0100
    VCT_MODE_2116US = 0x0140
    VCT_MODE_4156US = 0x0180
    VCT_MODE_8244US = 0x01C0


# Shunt current conversion time settings (in microseconds)
class INA260_ITC_MODE(IntFlag):
    ICT_MODE_140US = 0x0000
    ICT_MODE_204US = 0x0008
    ICT_MODE_332US = 0x0010
    ICT_MODE_588US = 0x0018
    ICT_MODE_1100US = 0x0020
    ICT_MODE_2116US = 0x0028
    ICT_MODE_4156US = 0x0030
    ICT_MODE_8244US = 0x0038


# Operating modes
class INA260_OPERATING_MODE(IntFlag):
    MODE_POWERDOWN = 0x0000
    MODE_SHUNT_TRIG = 0x0001
    MODE_BUS_TRIG = 0x0002
    MODE_SHUNT_BUS_TRIG = 0x0003
    MODE_SHUNT_CONT = 0x0005
    MODE_BUS_CONT = 0x0006
    MODE_SHUNT_BUS_CONT = 0x0007


class INA260Config:
    """
    Configuration object for INA260
    - config_reg:
        reset [15],
        reserved [14:12],
        avg: 0..7 as per datasheet AVG bits [11:9]
        vbus_ct: 0..7 conversion time code [8:6]
        ishunt_ct: uses same CT field [5:3]
        mode: 0..7, see datasheet MODE bits [2:0]
    - log: logger
    """

    ### Predefined modes for convenience (exposed as class attributes)

    # Expose the module-level enums under the INA260Config namespace for backward compatibility
    AVG_MODE = INA260_AVG_MODE
    VCT_MODE = INA260_VCT_MODE
    ITC_MODE = INA260_ITC_MODE
    OPERATING_MODE = INA260_OPERATING_MODE

    config_reg: int = DEFAULT_CONFIG_REG
    log: logging.Logger = utils.get_logger("INA260")

    # def __init__(self,
    #              avg: int = 0,           # 0..7 as per datasheet AVG bits
    #              vbus_ct: int = 0,       # 0..7 conversion time code
    #              ishunt_ct: int = 0,     # uses same CT field
    #              mode: int = 0b111,
    #              log: Optional[logging.Logger] = None):     # continuous shunt+bus by default
    #     self.config_reg = avg << 9 | vbus_ct << 6 | ishunt_ct << 3 | mode
    #     if log is not None:
    #         self.log = log

    def __init__(
        self, config_reg: int = DEFAULT_CONFIG_REG, log: Optional[logging.Logger] = None
    ):
        """Initialize from raw config register value"""
        self.config_reg = config_reg & 0xFFFF
        if log is not None:
            self.log = log

    def to_dict(self) -> Dict[str, Any]:
        return {
            "config_reg": self.config_reg,
        }


class INA260:
    """
    TI INA260 – precision current/voltage/power monitor with integrated shunt.
    """

    _device: I2CDevice = None
    _config: INA260Config = None

    def __init__(self, base_device: I2CDevice, cfg: I2CConfig = None):
        self._device = base_device
        if cfg is not None:
            self._device.reopen(cfg)

    def configure(
        self, config: INA260Config = INA260Config()
    ) -> None:  # continuous shunt+bus by default
        """
        avg: AVG2:0, vbus_ct: VBUSCT2:0, ishunt_ct: ISHCT2:0, mode: MODE2:0
        """
        # Configuration register bit layout (see Fig. 30 in datasheet):
        # [15]RST, [14:12]-reserved [11:9]AVG2 [8:6]VBUSCT [5:3]ISHCT [2:0]MODE
        self._config = config
        self._config.log.debug(
            f"configure: REG_CONFIG: 0b{self._config.config_reg:016b}"
        )
        self._device.write_u16_be(INA260_CONFIG_REG.REG_CONFIG, self._config.config_reg)

    def read_all(self) -> INA260Reading:
        raw_v = self._device.read_u16_be(INA260_CONFIG_REG.REG_BUS_VOLT)
        raw_i = self._device.read_u16_be(INA260_CONFIG_REG.REG_CURRENT)
        raw_p = self._device.read_u16_be(INA260_CONFIG_REG.REG_POWER)

        self._config.log.debug(
            f"bus_voltage_v: {(raw_v * LSB_VOLT_V):9.4f} (raw 0x{raw_v:04X})"
        )
        self._config.log.debug(
            f"current_a    : {(raw_i * LSB_CURRENT_A):9.4f} (raw 0x{raw_i:04X})"
        )
        self._config.log.debug(
            f"power_w      : {(raw_p * LSB_POWER_W):9.4f} (raw 0x{raw_p:04X})"
        )
        return INA260Reading(
            bus_voltage_v=raw_v * LSB_VOLT_V,
            current_a=raw_i * LSB_CURRENT_A,
            power_w=raw_p * LSB_POWER_W,
            raw_bus=raw_v,
            raw_current=raw_i,
            raw_power=raw_p,
        )

    def to_dict(self) -> Dict[str, Any]:
        r = self.read_all()
        return {
            "bus_voltage_v": r.bus_voltage_v,
            "current_a": r.current_a,
            "power_w": r.power_w,
            "raw_bus": r.raw_bus,
            "raw_current": r.raw_current,
            "raw_power": r.raw_power,
        }
