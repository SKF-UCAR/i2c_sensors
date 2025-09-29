import logging
import argparse, time, json, os

from typing import Optional
import i2c_sensors.utils as utils 
import i2c_sensors.export as export
from i2c_sensors.base import I2CConfig
from i2c_sensors.adc128d818 import ADC128D818, ADC128D818Config
from i2c_sensors.ina260 import INA260, INA260Config

# Example addresses – adjust to your wiring
INA_ADDR = 0x40  # A0/A1 strapping selects one of 16 addresses per datasheet
ADC_ADDR = 0x1D  # A0/A1 tri-level allow 9 addresses


class PowerMonitorConfig:
    """
    Configuration object for power monitor
    - log: logger
    """
    log : logging.Logger

    UDP_Addr: str = "localhost"
    UDP_Port: int = 9999
    Read_Interval: float = 1.0  # seconds between reads
    ADC128D818_I2C: I2CConfig
    ADC128D818_config: Optional[ADC128D818Config] = None
    INA260_I2C: I2CConfig
    INA260_config: Optional[INA260Config] = None

    def __init__(self,  
                 log: Optional[logging.Logger] = None):
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
                start = False,
                continuous = False,
                disable_mask = 0x00,
                mode = 0x00,
                extResistorMultipliers = [2.7, 2.7, 2.7, 5.0, 5.0, 5.0, 2.0, 100.0],
                log = self.log )

        # INA260
        int_congf = INA260Config.AVG_MODE.AVG_MODE_0004 | \
                    INA260Config.VCT_MODE.VCT_MODE_1100US | \
                    INA260Config.ITC_MODE.ICT_MODE_1100US | \
                    INA260Config.OPERATING_MODE.MODE_SHUNT_BUS_CONT
        self.INA260_I2C = I2CConfig(1, INA_ADDR)
        self.INA260_config = INA260Config(
                int_congf,
                log=self.log)

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
                    if hasattr(cls, "from_dict") and callable(getattr(cls, "from_dict")):
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
        self.INA260_config = _make(data.get("INA260_config"), INA260Config)

        self.log.info("Loaded PowerMonitor config: INA260=%s ADC128D818=%s",
                  "present" if self.INA260_config else "absent",
                  "present" if self.ADC128D818_config else "absent")
    
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
                return {k: _dump(v) for k, v in obj.__dict__.items() if not k.startswith("_")}
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

class PowerMonitor:
    """
    Combined power monitor using INA260 and ADC128D818
    """
    config: PowerMonitorConfig
    ina: Optional[INA260] = None
    adc: Optional[ADC128D818] = None

    def __init__(self,
                 config: PowerMonitorConfig):
        self.config = config
        if config.INA260_config is not None:
            self.ina = INA260(config.INA260_I2C)
            self.ina.configure(config.INA260_config)
        if config.ADC128D818_config is not None:
            self.adc = ADC128D818(config.ADC128D818_I2C)
            self.adc.configure(config.ADC128D818_config)

    def read_all(self) -> dict:
        d = {}
        d["_timestamp_"] = int(time.time())
        if self.ina is not None:
            d["ina260"] = self.ina.to_dict()
        if self.adc is not None:
            d["adc128d818"] = self.adc.read_all()
        return d

    def close(self) -> None:
        if self.ina is not None:
            self.ina.close()
        if self.adc is not None:
            self.adc.close()


def main():
    ap = argparse.ArgumentParser(description="Power Monitor using INA260 and ADC128D818")
    ap.add_argument("--config", type=str, default="", help="Configuration file (JSON)")
    ap.add_argument("--debug", default=False, help="Show debug messages", action="store_const", const=True)
    ap.add_argument("--out", type=str, help="Output file for prometheus (.prom)")
    args = ap.parse_args()

    log = utils.init_logger("PMon", level=logging.DEBUG if args.debug else logging.INFO)

    config = PowerMonitorConfig(log=log)
    if args.config:
        config.read_config(args.config)
    else:
        log.warning("No config file specified, using defaults")
        config.init_defaults()

    pm = PowerMonitor(config)

    try:
        while True:
            data = pm.read_all()
            # udp_msg = json.dumps(data)
            udp_msg =f"{data.get('_timestamp_')}"
            for k, v in (data.get('adc128d818', {}) or {}).items():
                if not k.startswith("raw"):
                    udp_msg += f", {v:.4f}"
            for k, v in (data.get('ina260', {}) or {}).items():
                if not k.startswith("raw"):
                    udp_msg += f", {v:.4f}"
            log.debug("Read data: %s", udp_msg)
            utils.send_udp_message(udp_msg, config.UDP_Addr, config.UDP_Port, logger=log)   
            # log.debug(json.dumps(data, indent=2))
            if args.out:
                d = {}
                d["_timestamp_"]=data.get("_timestamp_")
                d.update({f"{k}": v for k, v in (data.get('adc128d818', {}) or {}).items() if not k.startswith("raw")})
                d.update({f"{k}": v for k, v in (data.get('ina260', {}) or {}).items() if not k.startswith("raw")})
                export.write_prom(args.out, d)
            time.sleep(config.Read_Interval)
    except KeyboardInterrupt:
        print("Interrupted, exiting...")
    except Exception as e:
        log.exception("Error during read: %s", e)
    finally:
        pm.close()

    pm.config.write_config(args.config or "power_monitor.config")

if __name__ == "__main__":
    main()