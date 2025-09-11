from __future__ import annotations
import csv, json
from pathlib import Path
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

def write_prom(path: str, data: Any) -> None:
    """ Write data to prometheus text file format. """
    lines: List[str] = []
    if isinstance(data, list) and all(isinstance(r, dict) for r in data):
        # table → prometheus
        if not data:
            Path(path).write_text("")  # nothing to do
            return
        headers: List[str] = sorted({k for r in data for k in r.keys()})
        for r in data:
            for k in headers:
                v = r.get(k)
                if v is None:
                    continue
                if isinstance(v, str):
                    v = f'"{v}"'  # quote strings
                lines.append(f"{k} {v}")
    elif isinstance(data, dict):
        # mapping → prometheus
        for k, v in data.items():
            if v is None:
                continue
            if isinstance(v, str):
                v = f'"{v}"'  # quote strings
            lines.append(f"{k} {v}")
    else:
        # fallback prometheus
        lines.append(f"data {data}")
    Path(path).write_text("\n".join(lines) + "\n")

def write_auto(path: str, data: Any) -> None:
    """
    Minimal adapter: dict -> json; list[dict] -> csv; otherwise -> json.
    """
    if isinstance(data, list) and all(isinstance(r, dict) for r in data):
        write_csv(path, data)           # table → CSV
    elif isinstance(data, dict):
        write_json(path, data)          # mapping → JSON
    else:
        # fallback JSON
        write_json(path, {"data": data})
