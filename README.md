# i2c_sensors

Small Python project to read I²C devices, store data into files, and export in common formats.  
Includes drivers for **TI ADC128D818** (8-channel 12-bit ADC) and **TI INA260** (current/voltage/power monitor).

---

## Features
- **Base class** for I²C devices (`I2CDevice`):
  - Initialize device
  - Read/write 8- and 16-bit registers
  - Sequential (block) reads/writes
  - Virtual `configure()` method for device setup
- **Drivers included:**
  - `ADC128D818` — read 8 analog channels, one-shot, continuous, shutdown modes
  - `INA260` — read bus voltage, current, and power using integrated shunt
- **Export adapters**: write results to JSON, CSV or PROM
- **CLI tool** (`i2c-sensors`) to poll devices and log results
- **Extensible**: easy to add new I²C device classes or export formats
<!-- - **Portable to C++**: register-oriented API with minimal Python-specific magic -->

---

## Installation

### From source
```bash
git clone https://github.com/yourusername/i2c_sensors.git
cd i2c_sensors
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
````

### Editable install

```bash
pip install -e .
```

---

## File structure

```bash
/
├─ i2c_sensors/
| ├─ adc128d818.py   # ADC128D818 driver
| ├─ base.py         # I2CDevice base class
| ├─ cli.py          # Command-line tool
| ├─ export.py       # JSON/CSV exporters
| ├─ ina260.py       # INA260 driver
| └─ utils.py        # log, config, scheduler, i2c dev search
├─ demo_read.py      # Simple usage demo
├─ power_monitor/    # App uses both INA260 and ADC128D818
| ├─ power_monitor.py
└─ udp_monitor/
  └─ udp_monitor.py        # Prints all the traffic for the UDP port
```

---

## Requirements

* Python 3.8+
* Linux with I²C support (`/dev/i2c-*`)
* [smbus2](https://pypi.org/project/smbus2/)

Install system packages if needed:

```bash
sudo apt install python3-smbus i2c-tools
```

---

## Development

Run tests:

```bash
pytest
```

Lint & type check:

```bash
flake8 i2c_sensors
mypy i2c_sensors
```

---

## Usage

### Command line tool

Example: read both INA260 (`0x40`) and ADC128D818 (`0x1D`) on bus 1, 5 samples, and save to CSV:

```bash
i2c-sensors --bus 1 --ina260 0x40 --adc128 0x1D --count 5 --delay 0.5 --out readings.csv
```

Options:

```bash
$ i2c-sensors -h
usage: i2c-sensors [-h] [--bus BUS] [--ina260 INA260] [--adc128 ADC128] [--out OUT] [--count COUNT] [--delay DELAY] [--debug]

Simple I2C sensor reader

options:
  -h, --help       show this help message and exit
  --bus N          I²C bus number (default 1)
  --ina260 ADDR    INA260 I²C address (e.g. 0x40)
  --adc128 ADDR    ADC128D818 I²C address (e.g. 0x1D)
  --out FILE       Output file (.prom, .json or .csv)
  --count COUNT    Samples per device
  --delay DELAY    Delay between samples (s)
  --debug          Show debug messages
```

### From Python

Using i2c_sensor library from python app:

```python
import logging
import i2c_sensors.utils as utils 

from i2c_sensors.base import I2CConfig
from i2c_sensors.ina260 import INA260
from i2c_sensors.adc128d818 import ADC128D818

log = utils.init_logger("demo", level=logging.DEBUG)

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

adc = ADC128D818(I2CConfig(1, 0x1D))
conf = ADC128D818Config( 
                start = False,
                continuous = False,
                disable_mask = 0,
                mode = 0,
                extResistorMultipliers = [2.7, 2.7, 2.7, 5.0, 5.0, 5.0, 2.0, 100.0],
                log = log )
adc.configure(conf)
print("ADC128D818:", adc.read_all())
adc.close()
```

## Other examples and apps

### power_monitor.py

```bash
usage: power_monitor.py [-h] [--config CONFIG] [--debug]

Power Monitor using INA260 and ADC128D818

options:
  -h, --help       show this help message and exit
  --config CONFIG  Configuration file (JSON)
  --debug          Show debug messages
```

`power-monitor` takes measurements and sends a UDP message in ascii format:

```bash
UNIX_timestamp, ADC128_ch0, ..., ADC128_ch7, INA260_V, INA260_A, INA260_W
```

### udp_monitor

`udp_monitor` - is a small utility app to monitor UDP messages sent by `power-monitor`.

Usage:

```bash
$ udp-monitor -h
usage: udp-monitor [-h] [--host HOST] [--port PORT]

Simple UDP monitor

options:
  -h, --help            show this help message and exit
  --host HOST, -H HOST  Bind address (default: 0.0.0.0)
  --port PORT, -p PORT  Port to listen on (default: 9999)
```

Example of the `power-monitor` UDP message as seen from the  `udp-monitor` output:

```bash
------------------------------------------------------------
[2025-09-25 23:38:10.463863] from 127.0.0.1:51575 (101 bytes)
TEXT:
1758839890, 0.0000, 6.9103, 0.0068, 10.2719, 9.8375, 0.6000, 5.1188, 37.0000, 11.9750, 0.3738, 4.4300
HEX:
31 37 35 38 38 33 39 38 39 30 2c 20 30 2e 30 30 30 30 2c 20 36 2e 39 31 30 33 2c 20 30 2e 30 30 36 38 2c 20 31 30 2e 32 37 31 39 2c 20 39 2e 38 33 37 35 2c 20 30 2e 36 30 30 30 2c 20 35 2e 31 31 38 38 2c 20 33 37 2e 30 30 30 30 2c 20 31 31 2e 39 37 35 30 2c 20 30 2e 33 37 33 38 2c 20 34 2e 34 33 30 30
------------------------------------------------------------
[2025-09-25 23:38:11.571547] from 127.0.0.1:33124 (101 bytes)
TEXT:
1758839891, 0.0000, 6.9103, 0.0068, 10.2656, 9.8500, 0.6031, 5.1188, 36.5000, 11.9750, 0.3613, 4.3200
HEX:
31 37 35 38 38 33 39 38 39 31 2c 20 30 2e 30 30 30 30 2c 20 36 2e 39 31 30 33 2c 20 30 2e 30 30 36 38 2c 20 31 30 2e 32 36 35 36 2c 20 39 2e 38 35 30 30 2c 20 30 2e 36 30 33 31 2c 20 35 2e 31 31 38 38 2c 20 33 36 2e 35 30 30 30 2c 20 31 31 2e 39 37 35 30 2c 20 30 2e 33 36 31 33 2c 20 34 2e 33 32 30 30
```

### demo_read.py

```bash
usage: demo_read.py [-h] [--mask MASK] [--mode MODE] [--cont] [--debug]

Simple I2C sensor reader

options:
  -h, --help   show this help message and exit
  --mask MASK  Disable mask for ADC128D818 (bit i disables channel i)
  --mode MODE  Mode for ADC128D818 (0-3, see datasheet)
  --cont       Continuous mode for ADC128D818
  --debug      Show debug messages
```

---

## TODO

- [x] finish README.md
- [x] add `requirements.txt`

## License

MIT License © 2025 UCAR
