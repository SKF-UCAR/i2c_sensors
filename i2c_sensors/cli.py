from __future__ import annotations
import argparse, time, logging
from .utils import init_logger
from .i2c_device import I2CConfig
from .ina260 import INA260, INA260Config
from .adc128d818 import ADC128D818, ADC128D818Config
from .export import write_auto


def main():
    ap = argparse.ArgumentParser(description="Simple I2C sensor reader")
    ap.add_argument("--bus", type=int, default=1, help="I2C bus number (default 1)")
    ap.add_argument(
        "--ina260", type=lambda x: int(x, 0), help="INA260 address (e.g. 0x40)"
    )
    ap.add_argument(
        "--adc128", type=lambda x: int(x, 0), help="ADC128D818 address (e.g. 0x1D)"
    )
    ap.add_argument("--out", type=str, help="Output file (.prom, .json or .csv)")
    ap.add_argument("--count", type=int, default=1, help="Samples per device")
    ap.add_argument(
        "--delay", type=float, default=0.2, help="Delay between samples (s)"
    )
    ap.add_argument(
        "--debug",
        default=False,
        help="Show debug messages",
        action="store_const",
        const=True,
    )

    ap.add_argument(
        "--ftdiURL", type=str, help="FTDI URL (e.g. ftdi://ftdi:1/1)
    )
    args = ap.parse_args()

    log = init_logger("demo", level=logging.DEBUG if args.debug else logging.INFO)
    log.info(f"Args: {args}")

    rows = []
    dev_ina260 = None
    dev_adc128 = None

    t0 = time.time()
    if args.ina260 is not None:
        dev_ina260 = INA260(I2CConfig(args.bus, args.ina260))
        int_conf = (
            INA260Config.AVG_MODE.AVG_MODE_0004
            | INA260Config.VCT_MODE.VCT_MODE_1100US
            | INA260Config.ITC_MODE.ICT_MODE_1100US
            | INA260Config.OPERATING_MODE.MODE_SHUNT_BUS_CONT
        )
        dev_ina260.configure(INA260Config(int_conf, log=log))

    if args.adc128 is not None:
        dev_adc128 = ADC128D818(I2CConfig(args.bus, args.adc128))
        conf = ADC128D818Config(
            start=True,
            continuous=True,
            disable_mask=0x00,
            extResistorMultipliers=[1.0] * 8,
        )
        dev_adc128.configure(conf)

    for _ in range(args.count):
        d = {}
        d["_timestamp_"] = time.time()  # - t0
        if args.ina260 is not None:
            d.update(dev_ina260.to_dict())
        if args.adc128 is not None:
            d.update(dev_adc128.read_all())
        rows.append({f"{k}": v for k, v in d.items() if not k.startswith("raw")})
        time.sleep(args.delay)

    if args.ina260 is not None:
        dev_ina260.close()

    if args.adc128 is not None:
        dev_adc128.close()

    if args.out:
        write_auto(args.out, rows if len(rows) > 1 else (rows[0] if rows else {}))
    else:
        from pprint import pprint

        pprint(rows)


if __name__ == "__main__":
    main()
