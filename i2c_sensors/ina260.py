from __future__ import annotations
from dataclasses import dataclass
import logging
from typing import Dict, Any, Optional

import i2c_sensors.utils as utils
from .base import I2CDevice, I2CConfig

# Register addresses (datasheet Table / summary)
REG_CONFIG       = 0x00
REG_CURRENT      = 0x01
REG_BUS_VOLT     = 0x02
REG_POWER        = 0x03
REG_MASK_ENABLE  = 0x06
REG_ALERT_LIMIT  = 0x07
REG_MFG_ID       = 0xFE
REG_DIE_ID       = 0xFF

# LSBs (Electrical Characteristics): current=1.25mA, voltage=1.25mV, power=10mW
LSB_CURRENT_A = 1.25e-3
LSB_VOLT_V    = 1.25e-3
LSB_POWER_W   = 10e-3

@dataclass
class INA260Reading:
    bus_voltage_v: float
    current_a: float
    power_w: float
    raw_bus: int
    raw_current: int
    raw_power: int

class INA260Config:
    """
    Configuration object for INA260
    - avg: 0..7 as per datasheet AVG bits
    - vbus_ct: 0..7 conversion time code
    - ishunt_ct: uses same CT field
    - mode: 0..7, see datasheet
    """
    avg: int = 0
    vbus_ct: int = 0
    ishunt_ct: int = 0
    mode: int = 0b111 # continuous shunt+bus by default
    log : logging.Logger = utils.get_logger("INA260")

    def __init__(self,
                 avg: int = 0,           # 0..7 as per datasheet AVG bits
                 vbus_ct: int = 0,       # 0..7 conversion time code
                 ishunt_ct: int = 0,     # uses same CT field
                 mode: int = 0b111,
                 log: Optional[logging.Logger] = None):     # continuous shunt+bus by default        
        self.avg = avg
        self.vbus_ct = vbus_ct
        self.ishunt_ct = ishunt_ct
        self.mode = mode
        if log is not None:
            self.log = log


class INA260(I2CDevice):
    """
    TI INA260 – precision current/voltage/power monitor with integrated shunt.
    """
    def configure(self,
                  config: INA260Config = INA260Config()) -> None:  # continuous shunt+bus by default
        """
        avg: AVG2:0, vbus_ct: VBUSCT2:0, ishunt_ct: ISHCT2:0, mode: MODE2:0
        """
        # Configuration register bit layout (see Fig. 30 in datasheet):
        # [15]RST [14:11]-reserved [10:9]AVG2:1 [8]AVG0 [7:6]VBUSCT2:1 [5]VBUSCT0
        # [4:3]ISHCT2:1 [2]ISHCT0 [1:0]MODE2:1:0 (packed as 16 bits)
        self.config = config
        self.config.avg &= 0x7
        self.config.vbus_ct &= 0x7
        self.config.ishunt_ct &= 0x7
        self.config.mode &= 0x7
        value = (
            (0 << 15) |
            (self.config.avg << 9) |
            (self.config.vbus_ct << 6) |
            (self.config.ishunt_ct << 3) |
            (self.config.mode)
        )
        self.config.log.debug(f"configure: avg={self.config.avg}, vbus_ct={self.config.vbus_ct}, ishunt_ct={self.config.ishunt_ct}, mode={self.config.mode}")
        self.config.log.debug(f"configure: REG_CONFIG: 0b{value:016b}")
        self.write_u16_be(REG_CONFIG, value)

    def read_all(self) -> INA260Reading:
        raw_v = self.read_u16_be(REG_BUS_VOLT)
        raw_i = self.read_u16_be(REG_CURRENT)
        raw_p = self.read_u16_be(REG_POWER)

        self.config.log.debug(f"bus_voltage_v: {(raw_v * LSB_VOLT_V):9.4f} (raw 0x{raw_v:04X})")
        self.config.log.debug(f"current_a    : {(raw_i * LSB_CURRENT_A):9.4f} (raw 0x{raw_i:04X})") 
        self.config.log.debug(f"power_w      : {(raw_p * LSB_POWER_W):9.4f} (raw 0x{raw_p:04X})") 
        return INA260Reading(
            bus_voltage_v = raw_v * LSB_VOLT_V,
            current_a     = raw_i * LSB_CURRENT_A,
            power_w       = raw_p * LSB_POWER_W,
            raw_bus       = raw_v,
            raw_current   = raw_i,
            raw_power     = raw_p,
        )

    def to_dict(self) -> Dict[str, Any]:
        r = self.read_all()
        return {
            "bus_voltage_v": r.bus_voltage_v,
            "current_a": r.current_a,
            "power_w": r.power_w,
            "raw": {"bus": r.raw_bus, "current": r.raw_current, "power": r.raw_power},
        }
