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
    log = utils.init_logger("demo", level=logging.DEBUG)
    ap = argparse.ArgumentParser(description="Simple I2C sensor reader")
    ap.add_argument("--cont", type=bool, help="Continuous mode for ADC128D818")
    ap.add_argument("--mask", type=int, default=0, help="Disable mask for ADC128D818 (bit i disables channel i)")
    ap.add_argument("--mode", type=int, default=0, help="Mode for ADC128D818 (0-3, see datasheet)")
    args = ap.parse_args()

    log.info(f"Args: {args}")

    print("INA260:")
    ina = INA260(I2CConfig(1, INA_ADDR))
    ina_config = INA260Config(
        avg=0, 
        vbus_ct=0, 
        ishunt_ct=0, 
        mode=0b111, 
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
    print("ADC128D818:", adc.read_channels())
    # conf.mode = 0
    # conf.extResistorMultipliers = [2.7, 2.7, 2.7, 5.0, 5.0, 5.0, 2.0, 1.0]
    # adc.configure(conf)
    # time.sleep(0.05)
    # print("ADC128D818: Temp mode:", adc.read_channel(7))
    adc.close()


if __name__ == "__main__":
    main()