import os
from i2c_sensors.export import write_prom
from i2c_sensors.export import write_csv
from i2c_sensors.export import write_json


# test_export.py

def test_write_prom_empty_list(tmp_path):
    out = tmp_path / "prom.txt"
    write_prom(str(out), [])
    assert out.read_text() == ""

def test_write_prom_list_of_dicts(tmp_path):
    out = tmp_path / "prom.txt"
    data = [{"a": 1, "b": "x"}, {"a": 2, "b": None}]
    write_prom(str(out), data)
    lines = out.read_text().splitlines()
    assert "a 1" in lines
    assert 'b "x"' in lines
    assert "a 2" in lines
    assert not any(line.startswith("b ") and "None" in line for line in lines)

def test_write_prom_dict(tmp_path):
    out = tmp_path / "prom.txt"
    data = {"foo": 42, "bar": "baz", "skip": None}
    write_prom(str(out), data)
    text = out.read_text()
    assert "foo 42" in text
    assert 'bar "baz"' in text
    assert "skip" not in text

def test_write_prom_fallback(tmp_path):
    out = tmp_path / "prom.txt"
    write_prom(str(out), 123)
    assert out.read_text() == "data 123\n"

def test_write_prom_quotes_strings(tmp_path):
    out = tmp_path / "prom.txt"
    data = {"x": "hello world"}
    write_prom(str(out), data)
    assert out.read_text() == 'x "hello world"\n'


def test_write_csv_empty(tmp_path):
    out = tmp_path / "out.csv"
    write_csv(str(out), [])
    assert out.read_text() == ""

def test_write_csv_consistent_keys(tmp_path):
    out = tmp_path / "out.csv"
    rows = [{"a": 1, "b": 2}, {"a": 3, "b": 4}]
    write_csv(str(out), rows)
    lines = out.read_text().splitlines()
    assert lines[0] == "a,b" or lines[0] == "b,a"
    assert "1,2" in lines or "2,1" in lines
    assert "3,4" in lines or "4,3" in lines

def test_write_csv_varying_keys(tmp_path):
    out = tmp_path / "out.csv"
    rows = [{"a": 1}, {"b": 2}, {"a": 3, "b": 4}]
    write_csv(str(out), rows)
    text = out.read_text()
    assert "a" in text and "b" in text
    assert ",2" in text or "2," in text  # missing 'a' or 'b' should be blank

def test_write_csv_single_row(tmp_path):
    out = tmp_path / "out.csv"
    rows = [{"x": 42, "y": "foo"}]
    write_csv(str(out), rows)
    lines = out.read_text().splitlines()
    assert "x" in lines[0] and "y" in lines[0]
    assert "42,foo" in lines[1] or "foo,42" in lines[1]

def test_write_csv_non_string_values(tmp_path):
    out = tmp_path / "out.csv"
    rows = [{"a": 1, "b": True, "c": None}]
    write_csv(str(out), rows)
    text = out.read_text()
    assert "1" in text
    assert "True" in text
    assert ",," in text or text.endswith(",\n")  # None should be blank

def test_write_csv_header_sorted(tmp_path):
    out = tmp_path / "out.csv"
    rows = [{"z": 1, "a": 2, "m": 3}]
    write_csv(str(out), rows)
    header = out.read_text().splitlines()[0]
    assert header == ",".join(sorted(["z", "a", "m"]))