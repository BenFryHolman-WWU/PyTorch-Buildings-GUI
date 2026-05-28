"""External simulation input-data loading and mapping."""

import csv
import sqlite3
from pathlib import Path

import torch


CSV_INPUT_MAPPINGS = {
    "T_outdoor": "Outdoor Dry-Bulb Temperature [°C]",
    "weather_factor": "Global Horizontal Irradiance [W/m²]",
    "T_supply_setpoint": "AHU Supply Air Temperature [°C]",
    "supply_airflow_setpoint": "AHU Supply Fan Air Flow [m³/s]",
}

TIME_COLUMN = "Time [s]"
ZONE_SETPOINT_TEMPLATE = "Zone {zone} Cooling Setpoint [°C]"
AIR_DENSITY_KG_PER_M3 = 1.2
MAX_IRRADIANCE_W_PER_M2 = 800.0
DATABASE_SUFFIXES = {".db", ".sqlite", ".sqlite3"}


def _to_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _linear_interpolate(times, values, target):
    """
    Summary: Linear interpolate.
    Args: times
    Returns: Return the computed value.
    """
    if not times:
        return 0.0
    if target <= times[0]:
        return values[0]
    if target >= times[-1]:
        return values[-1]
    low = 0
    high = len(times) - 1
    while low + 1 < high:
        mid = (low + high) // 2
        if times[mid] <= target:
            low = mid
        else:
            high = mid
    span = times[high] - times[low]
    if span == 0:
        return values[low]
    alpha = (target - times[low]) / span
    return values[low] + alpha * (values[high] - values[low])


def _series_tensor(times, rows, column, target_times, transform=lambda value: value):
    values = [transform(_to_float(row.get(column))) for row in rows]
    series = [_linear_interpolate(times, values, target) for target in target_times]
    return torch.tensor(series, dtype=torch.float32).reshape(1, -1, 1)


def _zone_tensor(times, rows, columns, target_times, n_zones, transform=lambda value: value):
    if not columns:
        return None
    zone_series = []
    for zone_index in range(n_zones):
        column = columns[min(zone_index, len(columns) - 1)]
        values = [transform(_to_float(row.get(column))) for row in rows]
        zone_series.append([_linear_interpolate(times, values, target) for target in target_times])
    by_time = list(zip(*zone_series))
    return torch.tensor(by_time, dtype=torch.float32).reshape(1, -1, n_zones)


def _read_csv_rows(path):
    with path.open("r", encoding="utf-8-sig", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        return list(reader), reader.fieldnames or []


def _quote_sql_identifier(identifier):
    return '"' + str(identifier).replace('"', '""') + '"'


def _read_database_rows(path):
    """
    Summary: Read database rows.
    Returns: Return the computed value.
    """
    with sqlite3.connect(path) as connection:
        connection.row_factory = sqlite3.Row
        tables = connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()
        for table_row in tables:
            table_name = table_row["name"]
            columns = [
                column["name"]
                for column in connection.execute(
                    f"PRAGMA table_info({_quote_sql_identifier(table_name)})"
                ).fetchall()
            ]
            if not columns:
                continue
            if TIME_COLUMN in columns:
                order_clause = f" ORDER BY {_quote_sql_identifier(TIME_COLUMN)}"
            else:
                order_clause = ""
            if TIME_COLUMN in columns or any(column in columns for column in CSV_INPUT_MAPPINGS.values()):
                rows = connection.execute(
                    f"SELECT * FROM {_quote_sql_identifier(table_name)}{order_clause}"
                ).fetchall()
                return [dict(row) for row in rows], columns
    raise ValueError(f"No supported input data table found in {path}")


def _read_input_rows(path):
    path = Path(path)
    if path.suffix.lower() in DATABASE_SUFFIXES:
        return _read_database_rows(path)
    return _read_csv_rows(path)


def inspect_input_csv(path):
    """
    Summary: Inspect input csv.
    Returns: Return the computed value.
    """
    path = Path(path)
    rows, fieldnames = _read_input_rows(path)
    row_count = len(rows)
    zone_count = 0
    for index in range(1, 100):
        if ZONE_SETPOINT_TEMPLATE.format(zone=index) in fieldnames:
            zone_count = index
    mapped_keys = [
        key for key, column in CSV_INPUT_MAPPINGS.items()
        if column in fieldnames
    ]
    if any(ZONE_SETPOINT_TEMPLATE.format(zone=index) in fieldnames for index in range(1, 100)):
        mapped_keys.append("T_setpoint")
    return {
        "path": str(path),
        "row_count": row_count,
        "zone_count": zone_count,
        "mapped_keys": mapped_keys,
    }


def load_input_csv(path, t_rng, n_zones, t_start):
    """
    Summary: Load input csv.
    Args: n_zones
    Returns: Return the computed value.
    """
    path = Path(path)
    rows, fieldnames = _read_input_rows(path)
    if not rows:
        return {}, inspect_input_csv(path)
    times = [_to_float(row.get(TIME_COLUMN)) for row in rows]
    target_times = [float(t) - float(t_start) for t in t_rng]
    tensors = {}
    if CSV_INPUT_MAPPINGS["T_outdoor"] in fieldnames:
        tensors["T_outdoor"] = _series_tensor(
            times,
            rows,
            CSV_INPUT_MAPPINGS["T_outdoor"],
            target_times,
            transform=lambda value: value + 273.15,
        )
    if CSV_INPUT_MAPPINGS["weather_factor"] in fieldnames:
        tensors["weather_factor"] = _series_tensor(
            times,
            rows,
            CSV_INPUT_MAPPINGS["weather_factor"],
            target_times,
            transform=lambda value: max(0.0, min(1.0, value / MAX_IRRADIANCE_W_PER_M2)),
        )
    if CSV_INPUT_MAPPINGS["T_supply_setpoint"] in fieldnames:
        tensors["T_supply_setpoint"] = _series_tensor(
            times,
            rows,
            CSV_INPUT_MAPPINGS["T_supply_setpoint"],
            target_times,
            transform=lambda value: value + 273.15,
        )
    if CSV_INPUT_MAPPINGS["supply_airflow_setpoint"] in fieldnames:
        tensors["supply_airflow_setpoint"] = _series_tensor(
            times,
            rows,
            CSV_INPUT_MAPPINGS["supply_airflow_setpoint"],
            target_times,
            transform=lambda value: value * AIR_DENSITY_KG_PER_M3,
        )
    zone_columns = [
        ZONE_SETPOINT_TEMPLATE.format(zone=index)
        for index in range(1, 100)
        if ZONE_SETPOINT_TEMPLATE.format(zone=index) in fieldnames
    ]
    zone_tensor = _zone_tensor(
        times,
        rows,
        zone_columns,
        target_times,
        int(n_zones),
        transform=lambda value: value + 273.15,
    )
    if zone_tensor is not None:
        tensors["T_setpoint"] = zone_tensor
    return tensors, inspect_input_csv(path)
