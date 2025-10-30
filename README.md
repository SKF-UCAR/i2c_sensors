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
./
├── docs
│   ├── ADC128d818_Modes.png
│   ├── BMP280-Datasheet.pdf
│   ├── DSM_PWR_i2C_registers.xlsx
│   ├── DSP_Power_revB_I2C.pptx
│   ├── FTDI_i2c_wiring.png
│   ├── GPIO-Pinout-Diagram-2.png
│   ├── I2C_Basic_Address_and_Data_Frames.jpg
│   ├── image.png
│   ├── TI_ADC_adc128d818.pdf
│   └── TI_Power_Monitor_ina260.pdf
├── i2c_sensors
│   ├── adc128d818.py           # ADC128D818 driver
│   ├── bmp280.py               # BMP280 driver
│   ├── cli.py                  # Command-line tool
│   ├── ds3231.py               # DS3231 RTC driver
│   ├── export.py               # Exporters (CSV, JSON, PROM)
│   ├── i2c_adapter.py          # Base I2C adapter
│   ├── i2c_ftdi_adapter.py     # FTDI I2C adapter
│   ├── i2c_smbus_adapter.py    # SMBus I2C adapter
│   ├── ina260.py               # INA260 driver
│   ├── __init__.py
│   └── utils.py                # logging, config, scheduler, i2c device search
├── power_monitor               # App uses both INA260 and ADC128D818
│   ├── __init__.py
│   ├── power_monitor.config
│   ├── power_monitor_config.py
│   └── power_monitor.py
├── tests                       # Unit tests for the library
│   ├── test_export.py
│   ├── test_power_monitor_config.py
│   └── test_utils.py
├── udp_monitor
│   └── udp_monitor.py          # Prints all the traffic for the UDP port
├── demo_read.py                # Simple usage demo
├── install_i2c_pm.yml          # Ansible playbook to install power-monitor as a service
├── LICENSE
├── pyproject.toml              # Project metadata and build system requirements
├── README.md                   # This file
└── requirements.txt


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

---

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

#### power-monitor.config

Config file contains settings for both chips and parameters for power-monitor itself:

```json
{
  "ADC128D818_I2C": {
    "bus": 2,
    "address": 29,
    "freq_hz": 100000.0
  },
  "ADC128D818_config": {
    "start": false,
    "continuous": false,
    "disable_mask": 0,
    "mode": 0,
    "extResistorMultipliers": [
      2.7,
      2.7,
      2.7,
      5.0,
      5.0,
      5.0,
      2.0,
      100.0
    ]
  },
  "INA260_I2C": {
    "bus": 2,
    "address": 64,
    "freq_hz": 100000.0
  },
  "INA260_config": {
    "config_reg": 807
  },
  "FTDI_URL":"ftdi://ftdi::P03UM9NA/2",
  "Read_Interval": 15.0,
  "UDP_Addr": "127.0.0.1",
  "UDP_Port": 9999
}
```

##### xx_I2C

Those sections are self-explanatory.

##### ADC128D818_config

This section contains arguments to configure the **ADC128D818** chip.

- **start**: set START bit - i.e. start measures immediately
- **continuous**: if `False`, set low-power conversion (convert all enabled, then shutdown), if `True` - continues measures and conversions.
- **disable_mask**: bit _i_ disables channel _i_ when set. Must be done in shutdown mode.
- **mode**: modes of operation (more info see below and in [TI_ADC_adc128d818.pdf](./docs/TI_ADC_adc128d818.pdf))

- **extResistorMultipliers**: List of 8 floats, one per channel, to scale readings if using external `Vref` divider. E.g. for a 10k/30k divider, multiplier is 4.0 _**(Vout=Vin*10k/40k)**_.

|Ch.| Mode 0 | Mode 1 | Mode 2 | Mode 3 |
|---|---|---|---|---|
|1| IN0 | IN0 | IN0(+)/IN1(-) | IN0 |
|2| IN1 | IN1 | IN2(+)/IN3(-) | IN1 |
|3| IN2 | IN2 | IN4(+)/IN5(-) | IN2 |
|4| IN3 | IN3 | IN6(+)/IN7(-) | IN3 |
|5| IN4 | IN4 | | IN4(+)/IN5(-) |
|6| IN5 | IN5 | | IN6(+)/IN7(-) |
|7| IN6 | IN6 | | |
|8| N/C | IN7 | | |
|Local Temp |Yes|No|Yes|Yes|

##### INA260_config

This section contains arguments to configure the **INA260** chip.

- **config_reg**: sets **INA260**'s configuration register. (see more info: [TI_Power_Monitor_ina260.pdf](./docs/TI_Power_Monitor_ina260.pdf))

##### Table 5. Configuration Register Field Descriptions

|Bit |Field |Type |Reset |Description|
|---|---|---|---|---|
|15 | RST|  R/W | 0 | Reset BitSetting this bit to '1' generates a system reset that is the same as power-on reset. Resets all registers to default values; this bit self-clears.|
|14..12| — | R | 110 ||
|11..9| AVG | R/W | 000 | Averaging Mode (see below)|
|8..6| VBUSCT| R/W | 100 | Bus Voltage Conversion Time (see below)|
|5..3| ISHCT |R/W |100 | Shunt Current Conversion Time (see below)|
|2..0| MODE |R/W| 111| Operating Mode (see below)|

##### Averaging Mode

Determines the number of samples that are collected and averaged. The following shows all the `AVG` bit settings and related number of averages for each bit setting.

|AVG2 | AVG1 |AVG0 | # of averages|
|---|---|---|---|
| 0| 0| 0| 1 (1)|
| 0| 0| 1| 4|
| 0| 1| 0| 16|
| 0| 1| 1| 64|
| 1| 0| 0| 128|
| 1| 0| 1| 256|
| 1| 1| 0| 512|
| 1| 1| 1| 1024|

##### Bus Voltage Conversion Time

Sets the conversion time for the bus voltage measurement. The following shows the `VBUSCT` bit options and related conversion times for each bit setting.

|VBUSCT2|VBUSCT1|VBUSCT0|conversion time|
|---|---|---|---|
|0| 0| 0| 140 μs|
|0| 0| 1| 204 μs|
|0| 1| 0| 332 μs|
|0| 1| 1| 588 μs|
|1| 0| 0| 1.1 (1) ms|
|1| 0| 1| 2.116 ms|
|1| 1| 0| 4.156 ms|
|1| 1| 1| 8.244 ms|

##### Shunt Current Conversion Time

The following shows the `ISHCT` bit options and related conversion times for each bit
setting.

|ISHCT2|ISHCT1|ISHCT0| conversion time|
|---|---|---|---|
|0| 0| 0| 140 μs|
|0| 0| 1| 204 μs|
|0| 1| 0| 332 μs|
|0| 1| 1| 588 μs|
|1| 0| 0| 1.1 (1) ms|
|1| 0| 1| 2.116 ms|
|1| 1| 0| 4.156 ms|
|1| 1| 1| 8.244 ms|

##### Operating Mode

Selects continuous, triggered, or power-down mode of operation. These bits default to
continuous shunt and bus measurement mode. The following shows mode settings.

|MODE2|MODE1|MODE0|mode|
|---|---|---|---|
|0|0|0| Power-Down (or Shutdown) |
|0|0|1| Shunt Current, Triggered|
|0|1|0| Bus Voltage, Triggered|
|0|1|1| Shunt Current and Bus Voltage, Triggered|
|1|0|0| Power-Down (or Shutdown)|
|1|0|1| Shunt Current, Continuous|
|1|1|0| Bus Voltage, Continuous|
|1|1|1| Shunt Current and Bus Voltage, Continuous(1)|

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

## Using metrics via Prometheus

### 1. Exporters Available as Debian Packages

#### Node Exporter

```bash
sudo apt update
sudo apt install prometheus-node-exporter
```

- Runs automatically as a systemd service (prometheus-node-exporter.service)

- Default scrape URL: http://localhost:9100/metrics

- __Note__: Debian package does not enable the textfile collector by default.

Enable it by editing /etc/default/prometheus-node-exporter:

```bash
ARGS="--collector.textfile.directory=/var/lib/node_exporter"
```

Then:

```bash
sudo mkdir -p /var/lib/node_exporter
sudo systemctl restart prometheus-node-exporter
```

To check if text file collector is working you can open `http://<your-node>:9100/metrics` and if you can - check node's prometheus-node-exporter status:

```bash
systemctl status prometheus-node-exporter.service
```

__Note__: you might need to change permissions to the `/var/lib/node_exporter` folder. 


## License

MIT License © 2025 UCAR
