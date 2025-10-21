import json
from i2c_sensors.i2c_device import I2CConfig
from i2c_sensors.adc128d818 import ADC128D818Config
from i2c_sensors.ina260 import INA260Config
from power_monitor.power_monitor_config import PowerMonitorConfig


def test_power_monitor_config_init_defaults():
    pmc = PowerMonitorConfig()
    pmc.init_defaults()
    assert pmc.ADC128D818_config is not None
    assert pmc.INA260_config is not None
    assert isinstance(pmc.ADC128D818_I2C, I2CConfig)
    assert isinstance(pmc.INA260_I2C, I2CConfig)
    assert pmc.ADC128D818_I2C.address == 0x1D
    assert pmc.INA260_I2C.address == 0x40
    assert isinstance(pmc.ADC128D818_config, ADC128D818Config)
    assert isinstance(pmc.INA260_config, INA260Config)
    # check some config values
    assert pmc.ADC128D818_config.start is False
    assert pmc.ADC128D818_config.continuous is False
    assert len(pmc.ADC128D818_config.extResistorMultipliers) == 8
    assert pmc.INA260_config.log is pmc.log
    assert pmc.INA260_config.config_reg == (
        INA260Config.AVG_MODE.AVG_MODE_0004
        | INA260Config.VCT_MODE.VCT_MODE_1100US
        | INA260Config.ITC_MODE.ICT_MODE_1100US
        | INA260Config.OPERATING_MODE.MODE_SHUNT_BUS_CONT
    )


def test_power_monitor_config_read_config(tmp_path):
    pmc = PowerMonitorConfig()
    config_data = {
        "UDP_Addr": "localhost",
        "UDP_Port": 8888,
        "Read_Interval": 2.5,
        "ADC128D818_I2C": {"bus": 1, "address": 0x1D},
        "ADC128D818_config": {
            "start": True,
            "continuous": True,
            "disable_mask": 0xFF,
            "mode": 0x01,
            "extResistorMultipliers": [2.0, 2.0, 2.0, 5.0, 5.0, 5.0, 2.0, 100.0],
        },
        "INA260_I2C": {"bus": 1, "address": 0x40},
        "INA260_config": {"config_reg": 0x1234},
    }
    config_file = tmp_path / "pmon_config.json"
    config_file.write_text(json.dumps(config_data))
    pmc.read_config(str(config_file))
    assert pmc.UDP_Addr == "localhost"
    assert pmc.UDP_Port == 8888
    assert pmc.Read_Interval == 2.5
    assert pmc.ADC128D818_I2C.bus == 1
    assert pmc.ADC128D818_I2C.address == 0x1D
    assert pmc.ADC128D818_config is not None
    assert pmc.ADC128D818_config.start is True
    assert pmc.ADC128D818_config.continuous is True
    assert pmc.ADC128D818_config.disable_mask == 0xFF
    assert pmc.ADC128D818_config.mode == 0x01
    assert pmc.ADC128D818_config.extResistorMultipliers == [
        2.0,
        2.0,
        2.0,
        5.0,
        5.0,
        5.0,
        2.0,
        100.0,
    ]
    assert pmc.INA260_I2C.bus == 1
    assert pmc.INA260_I2C.address == 0x40
    assert pmc.INA260_config is not None
    assert pmc.INA260_config.config_reg == 0x1234
