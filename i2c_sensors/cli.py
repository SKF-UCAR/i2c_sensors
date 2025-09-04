from __future__ import annotations
import argparse, time
from pathlib import Path
from typing import Optional
from .base import I2CConfig
from .ina260 import INA260
from .adc128d818 import ADC128D818, ADC128D818Config
from .export import write_auto

def main():
    ap = argparse.ArgumentParser(description="Simple I2C sensor reader")
    ap.add_argument("--bus", type=int, default=1, help="I2C bus number (default 1)")
    ap.add_argument("--ina260", type=lambda x:int(x,0), help="INA260 address (e.g. 0x40)")
    ap.add_argument("--adc128", type=lambda x:int(x,0), help="ADC128D818 address (e.g. 0x1D)")
    ap.add_argument("--out", type=str, help="Output file (.json or .csv)")
    ap.add_argument("--count", type=int, default=1, help="Samples per device")
    ap.add_argument("--delay", type=float, default=0.2, help="Delay between samples (s)")
    args = ap.parse_args()

    rows = []
    t0 = time.time()

    if args.ina260 is not None:
        dev = INA260(I2CConfig(args.bus, args.ina260))
        dev.configure(avg=0, vbus_ct=0, ishunt_ct=0, mode=0b111)
        for _ in range(args.count):
            d = dev.to_dict()
            d["t"] = time.time() - t0
            rows.append({f"ina260_{k}": v for k, v in d.items() if k != "raw"})
            time.sleep(args.delay)
        dev.close()

    if args.adc128 is not None:
        dev = ADC128D818(I2CConfig(args.bus, args.adc128))
        conf = ADC128D818Config( 
            start = True,
            continuous = True,
            disable_mask = 0x00,
            extResistorMultipliers = [1.0] * 8 )
        dev.configure(conf)
        
        for _ in range(args.count):
            d = dev.read_channels()
            d["t"] = time.time() - t0
            rows.append({f"adc_{k}": v for k, v in d.items()})
            time.sleep(args.delay)
        dev.close()

    if args.out:
        write_auto(args.out, rows if len(rows) > 1 else (rows[0] if rows else {}))
    else:
        from pprint import pprint
        pprint(rows)

if __name__ == "__main__":
    main()
