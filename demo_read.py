from i2c_sensors.base import I2CConfig
from i2c_sensors.ina260 import INA260
from i2c_sensors.adc128d818 import ADC128D818, ADC128D818Config

# Example addresses – adjust to your wiring
INA_ADDR = 0x40  # A0/A1 strapping selects one of 16 addresses per datasheet
ADC_ADDR = 0x1D  # A0/A1 tri-level allow 9 addresses

# ina = INA260(I2CConfig(1, INA_ADDR))
# ina.configure(avg=0, vbus_ct=0, ishunt_ct=0, mode=0b111)
# print("INA260:", ina.to_dict())
# ina.close()

adc = ADC128D818(I2CConfig(1, ADC_ADDR))
conf = ADC128D818Config( 
            start = True,
            continuous = True,
            disable_mask = 0x00,
            extResistorMultipliers = [2.7, 2.7, 2.7, 5.0, 5.0, 5.0, 2.0, 2.0] )
adc.configure(conf)
print("ADC128D818:", adc.read_channels())
adc.close()
