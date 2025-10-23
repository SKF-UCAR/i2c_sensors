import logging
import argparse, time
import os
import sys

from typing import Optional, Dict, Any

# Ensure the project root is on sys.path when running this script directly so
# imports like `import i2c_sensors...` work. If this package is installed into
# the environment (for example with `pip install -e .`) this is not necessary.
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.abspath(os.path.join(_THIS_DIR, os.pardir))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

import i2c_sensors.utils as utils
import i2c_sensors.export as export
from i2c_sensors.i2c_ftdi_adapter import I2CFtdiAdapter
from i2c_sensors.adc128d818 import ADC128D818
from i2c_sensors.ina260 import INA260
from power_monitor.power_monitor_config import PowerMonitorConfig


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
            ina_adapter = I2CFtdiAdapter(url=config.FTDI_URL, cfg=config.INA260_I2C)
            self.ina = INA260(ina_adapter)
            self.ina.open()
            self.ina.configure(config.INA260_config)

        if config.ADC128D818_config is not None:
            adc_adapter = I2CFtdiAdapter(url=config.FTDI_URL, cfg=config.ADC128D818_I2C)
            self.adc = ADC128D818(adc_adapter)
            self.adc.open()
            self.adc.configure(config.ADC128D818_config)

    def read_all(self) -> Dict[str, Any]:
        d : Dict[str, Any] = {}
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
                d["dsm_pm_timestamp_"]=data.get("_timestamp_")
                d.update({f"dsm_pm_{k}": v for k, v in (data.get('adc128d818', {}) or {}).items() if not k.startswith("raw")})
                d.update({f"dsm_pm_{k}": v for k, v in (data.get('ina260', {}) or {}).items() if not k.startswith("raw")})
                export.write_prom(args.out, d)
                # export.write_prom(args.out, data)
            time.sleep(config.Read_Interval)
    except KeyboardInterrupt:
        print("Interrupted, exiting...")
    except Exception as e:
        log.exception("Error during read: %s", e)
    finally:
        pm.close()

    if not args.config:
        pm.config.write_config("power_monitor.config")

if __name__ == "__main__":
    main()