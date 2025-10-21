from __future__ import annotations
import csv, json

# , yaml

from pathlib import Path
import time
from typing import Dict, Any, Iterable, List


def write_json(path: str, obj: Dict[str, Any]) -> None:
    Path(path).write_text(json.dumps(obj, indent=2, sort_keys=True))


def write_csv(path: str, rows: Iterable[Dict[str, Any]]) -> None:
    rows = list(rows)
    if not rows:
        Path(path).write_text("")  # nothing to do
        return
    headers: List[str] = sorted({k for r in rows for k in r.keys()})
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=headers)
        w.writeheader()
        for r in rows:
            w.writerow(r)


def write_prom(path: str, data: Any, use_timestamp: bool = False) -> None:
    """Write data to prometheus text file format."""
    if not data:
        Path(path).write_text("")  # nothing to do
        return

    time_stamp_headers: List[str] = ["_timestamp_", "timestamp", "time"]
    lines: List[str] = []

    def dict_to_prom_object_str(d: Dict[str, Any]) -> str:
        items = []
        for k in sorted(d.keys()):
            v = d[k]
            if v is None:
                continue
            if isinstance(v, (list, dict)):
                continue

            items.append(f'{k}="{v}"')
        return "{" + ",".join(items) + "}" if items else ""

    def process_row(r: Dict[str, Any]) -> None:
        headers: List[str] = sorted({k for k in r.keys()})
        ts_h = None
        if not use_timestamp:
            ts_h = None
        else:
            # find first matching timestamp header
            for tsh in time_stamp_headers:
                if tsh in headers:
                    headers.remove(tsh)
                    ts_h = tsh
                    break
        ts: int | None = None
        if ts_h is not None:
            ts = int(r.get(ts_h, 0))  # use timestamp from the current row
        elif use_timestamp:
            ts = int(time.time())  # use current time
        ts = ts * 1000 if ts is not None else None  # prometheus wants ms

        for k in headers:
            v = r.get(k)
            if v is None:
                continue
            if isinstance(v, str):
                v = f'"{v}"'  # quote strings
            if isinstance(v, bool):
                v = "1" if v else "0"  # convert bool to int
            if isinstance(v, (dict)):
                stringified = dict_to_prom_object_str(v)

                # stringified = yaml.safe_dump(v, default_style='\"', default_flow_style=True, sort_keys=True).strip().replace(": ", "=")
                lines.append(f"{k}{stringified} {ts if ts is not None else ''}".strip())
            else:
                lines.append(f"{k} {v} {ts if ts is not None else ''}".strip())

    if isinstance(data, list) and all(isinstance(r, dict) for r in data):
        # table → prometheus
        for r in data:
            process_row(r)

    elif isinstance(data, dict):
        # mapping → prometheus
        process_row(data)
    else:
        # fallback prometheus
        lines.append(f"data {data} {int(time.time())}")

    Path(path).write_text("\n".join(lines) + "\n")


def write_auto(path: str, data: Any) -> None:
    """
    Minimal adapter: dict -> json; list[dict] -> csv; otherwise -> json.
    """
    path = str(path).lower()
    if path.endswith(".prom") or path.endswith(".txt"):
        write_prom(path, data)  # table/dict/other → prometheus
    elif path.endswith(".csv"):
        # if isinstance(data, list) and all(isinstance(r, dict) for r in data):
        write_csv(path, data)  # table → CSV
    elif isinstance(data, dict):
        write_json(path, data)  # mapping → JSON
    else:
        # fallback JSON
        write_json(path, {"data": data})
