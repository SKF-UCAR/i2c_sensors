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
- **Export adapters**: write results to JSON or CSV
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

## Usage

### Command line

Example: read both INA260 (`0x40`) and ADC128D818 (`0x1D`) on bus 1, 5 samples, and save to CSV:

```bash
i2c-sensors --bus 1 --ina260 0x40 --adc128 0x1D --count 5 --delay 0.5 --out readings.csv
```

Options:

```
--bus N            I²C bus number (default 1)
--ina260 ADDR      INA260 I²C address (e.g. 0x40)
--adc128 ADDR      ADC128D818 I²C address (e.g. 0x1D)
--out FILE         Output file (.json or .csv)
--count N          Number of samples (default 1)
--delay SEC        Delay between samples (default 0.2s)
```

### From Python

```python
from i2c_sensors.base import I2CConfig
from i2c_sensors.ina260 import INA260
from i2c_sensors.adc128d818 import ADC128D818

cfg = I2CConfig(bus=1, address=0x40)
ina = INA260(cfg)
ina.configure()
print("INA260:", ina.to_dict())
ina.close()

adc = ADC128D818(I2CConfig(1, 0x1D))
adc.configure(start=True, continuous=True)
print("ADC128D818:", adc.read_channels())
adc.close()
```

---

## File structure

```
/
├─ i2c_sensors/
| ├─ base.py         # I2CDevice base class
| ├─ export.py       # JSON/CSV exporters
| ├─ ina260.py       # INA260 driver
| ├─ adc128d818.py   # ADC128D818 driver
| └─ cli.py          # Command-line tool
├─ demo_read.py      # Simple usage demo
├─ power_monitor.py  # App uses both INA260 and ADC128D818
└─ udp_mon.py        # Prints all the traffic for the UDP port
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

## License

MIT License © 2025 UCAR
