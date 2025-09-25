import logging
import argparse,time
import i2c_sensors.utils as utils 

from i2c_sensors.base import I2CConfig
from i2c_sensors.ina260 import INA260, INA260Config
from i2c_sensors.adc128d818 import ADC128D818, ADC128D818Config

# Example addresses – adjust to your wiring
INA_ADDR = 0x40  # A0/A1 strapping selects one of 16 addresses per datasheet
ADC_ADDR = 0x1D  # A0/A1 tri-level allow 9 addresses

def main():
    
    ap = argparse.ArgumentParser(description="Simple I2C sensor reader")
    ap.add_argument("--mask", type=int, default=0, help="Disable mask for ADC128D818 (bit i disables channel i)")
    ap.add_argument("--mode", type=int, default=0, help="Mode for ADC128D818 (0-3, see datasheet)")
    ap.add_argument("--cont", default=False, help="Continuous mode for ADC128D818", action="store_const", const=True)
    ap.add_argument("--debug", default=False, help="Show debug messages", action="store_const", const=True)
    args = ap.parse_args()
    
    log = utils.init_logger("demo", level=logging.DEBUG if args.debug else logging.INFO)
    log.info(f"Args: {args}")

    print("INA260:")
    ina = INA260(I2CConfig(1, INA_ADDR))
    int_conf = INA260Config.AVG_MODE.AVG_MODE_0004 | \
                INA260Config.VCT_MODE.VCT_MODE_1100US | \
                INA260Config.ITC_MODE.ICT_MODE_1100US | \
                INA260Config.OPERATING_MODE.MODE_SHUNT_BUS_CONT
    
    log.info(f"INA260 config: 0x{int_conf:04X}")
    ina_config = INA260Config(
                    int_conf, # default reset value
                log=log)
    ina.configure(ina_config)
    print("INA260:", ina.to_dict())
    ina.close()

    print("ADC128D818:")
    adc = ADC128D818(I2CConfig(1, ADC_ADDR))
    conf = ADC128D818Config( 
                start = False if args.cont is None else True,
                continuous = False if args.cont is None else True,
                disable_mask = args.mask & 0x0F,
                mode = args.mode & 0x03,
                extResistorMultipliers = [2.7, 2.7, 2.7, 5.0, 5.0, 5.0, 2.0, 100.0],
                log = log )
    adc.configure(conf)
    adc.deep_shutdown(True if args.cont is None else False)
    time.sleep(0.05)
    print("ADC128D818:", adc.read_all())
    # conf.mode = 0
    # conf.extResistorMultipliers = [2.7, 2.7, 2.7, 5.0, 5.0, 5.0, 2.0, 1.0]
    # adc.configure(conf)
    # time.sleep(0.05)
    # print("ADC128D818: Temp mode:", adc.read_channel(7))
    adc.close()


if __name__ == "__main__":
    main()