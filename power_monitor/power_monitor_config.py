import os
import json
import logging
from typing import Optional

import i2c_sensors.utils as utils
from i2c_sensors.i2c_adapter import I2CConfig
from i2c_sensors.adc128d818 import ADC128D818Config
from i2c_sensors.ina260 import INA260Config


# Default addresses – adjust to your wiring
INA_ADDR = 0x40  # A0/A1 strapping selects one of 16 addresses per datasheet
ADC_ADDR = 0x1D  # A0/A1 tri-level allow 9 addresses


class PowerMonitorConfig:
    """
    Configuration object for power monitor
    - log: logger
    """

    log: logging.Logger

    UDP_Addr: str = "localhost"
    UDP_Port: int = 9999
    Read_Interval: float = 1.0  # seconds between reads
    ADC128D818_I2C: I2CConfig
    ADC128D818_config: Optional[ADC128D818Config] = None
    INA260_I2C: I2CConfig
    INA260_config: Optional[INA260Config] = None
    FTDI_URL: str = "ftdi://ftdi:1/1"

    def __init__(self, log: Optional[logging.Logger] = None):
        self.log = log or utils.get_logger("PMon")

    def init_defaults(self) -> None:
        """
        Initialize default config values to both devices
        enabled with typical configs
        """
        #
        # ADC128D818
        self.ADC128D818_I2C = I2CConfig(1, ADC_ADDR)
        self.ADC128D818_config = ADC128D818Config(
            start=False,
            continuous=False,
            disable_mask=0x00,
            mode=0x00,
            extResistorMultipliers=[2.7, 2.7, 2.7, 5.0, 5.0, 5.0, 2.0, 100.0],
            log=self.log,
        )

        # INA260
        int_congf = (
            INA260Config.AVG_MODE.AVG_MODE_0004
            | INA260Config.VCT_MODE.VCT_MODE_1100US
            | INA260Config.ITC_MODE.ICT_MODE_1100US
            | INA260Config.OPERATING_MODE.MODE_SHUNT_BUS_CONT
        )
        self.INA260_I2C = I2CConfig(1, INA_ADDR)
        self.INA260_config = INA260Config(int_congf, log=self.log)
        self.FTDI_URL="ftdi://ftdi:1/1"

    def _normalize_filename(self, fn: str) -> str:
        if not fn:
            fn = f"{__name__}.config"
        if not os.path.isabs(fn):
            fn = os.path.join(os.path.dirname(__file__), fn)
        return fn

    def read_config(self, filename: str) -> None:
        """
        Read configuration from a file (JSON)
        Normalize filename:
        - if empty, use module-based name like "power_monitor.config"
        - if relative path, make it relative to this source file
        """

        filename = self._normalize_filename(filename)

        self.log.debug("Reading PowerMonitor config from %s", filename)
        if not os.path.exists(filename):
            self.log.error("Config file not found: %s", filename)
            raise FileNotFoundError(filename)

        with open(filename, "r") as fh:
            data = json.load(fh)

        def _make(obj, cls):
            if obj is None:
                return None
            # already an instance of desired class
            if isinstance(obj, cls):
                return obj
            # dict -> try constructor with kwargs
            if isinstance(obj, dict):
                try:
                    return cls(**obj)
                except Exception:
                    # fall back to from_dict if available
                    if hasattr(cls, "from_dict") and callable(
                        getattr(cls, "from_dict")
                    ):
                        return cls.from_dict(obj)
                    # give up and return raw dict
                    return obj
            # otherwise return as-is
            return obj

        # populate expected entries if present in JSON
        self.UDP_Addr = data.get("UDP_Addr", self.UDP_Addr)
        self.UDP_Port = data.get("UDP_Port", self.UDP_Port)
        self.Read_Interval = data.get("Read_Interval", self.Read_Interval)
        self.ADC128D818_I2C = _make(data.get("ADC128D818_I2C"), I2CConfig)
        self.ADC128D818_config = _make(data.get("ADC128D818_config"), ADC128D818Config)
        self.INA260_I2C = _make(data.get("INA260_I2C"), I2CConfig)
        self.INA260_config = _make( data.get("INA260_config"), INA260Config)
        self.FTDI_URL = data.get("FTDI_URL", self.FTDI_URL)

        self.log.info(
            "Loaded PowerMonitor config: INA260=%s ADC128D818=%s",
            "present" if self.INA260_config else "absent",
            "present" if self.ADC128D818_config else "absent",
        )

    def write_config(self, filename: str) -> None:
        """
        Write configuration to a file (JSON)
        Normalize filename:
        - if empty, use module-based name like "power_monitor.config"
        - if relative path, make it relative to this source file
        """

        filename = self._normalize_filename(filename)

        self.log.debug("Writing PowerMonitor config to %s", filename)
        dirpath = os.path.dirname(filename)
        if dirpath and not os.path.exists(dirpath):
            os.makedirs(dirpath, exist_ok=True)

        def _dump(obj):
            if obj is None:
                return None
            # primitives and simple containers
            if isinstance(obj, (str, int, float, bool)):
                return obj
            if isinstance(obj, dict):
                return {k: _dump(v) for k, v in obj.items()}
            if isinstance(obj, (list, tuple)):
                return [_dump(v) for v in obj]
            # prefer explicit serialization methods
            for method in ("to_dict", "as_dict", "to_json", "toJSON", "toJson"):
                if hasattr(obj, method) and callable(getattr(obj, method)):
                    try:
                        return _dump(getattr(obj, method)())
                    except Exception:
                        pass
            # dataclass- or object-like fallback
            if hasattr(obj, "__dict__"):
                return {
                    k: _dump(v)
                    for k, v in obj.__dict__.items()
                    if not k.startswith("_")
                }
            # last resort: string representation
            return str(obj)

        payload = {
            "UDP_Addr": self.UDP_Addr,
            "UDP_Port": self.UDP_Port,
            "Read_Interval": self.Read_Interval,
            "ADC128D818_I2C": _dump(self.ADC128D818_I2C),
            "ADC128D818_config": _dump(self.ADC128D818_config),
            "INA260_I2C": _dump(self.INA260_I2C),
            "INA260_config": _dump(self.INA260_config),
        }

        try:
            with open(filename, "w") as fh:
                json.dump(payload, fh, indent=2)
            self.log.info("Wrote PowerMonitor config to %s", filename)
        except Exception as e:
            self.log.exception("Failed to write config to %s: %s", filename, e)
            raise
