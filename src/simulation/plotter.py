"""Simulation plotting metadata and helper utilities."""

import math
import torch


def kelvin_to_celsius(values):
    return values - 273.15


VARIABLE_META = {

    "envelope.T_zones":         {"label": "Zone Temp",           "unit": "C",    "scale": kelvin_to_celsius, "color": "#2F80C1"},
    "rtu.T_supply":             {"label": "RTU Supply Temp",      "unit": "C",    "scale": kelvin_to_celsius, "color": "#1F9E89"},
    "T_outdoor":                {"label": "Outdoor Temp",         "unit": "C",    "scale": kelvin_to_celsius, "color": "#697386"},
    "vav.T_supply":             {"label": "VAV Supply Temp",      "unit": "C",    "scale": kelvin_to_celsius, "color": "#35A7C8"},

    "rtu.total_power":          {"label": "RTU Total Power",      "unit": "W",    "scale": None, "color": "#B8325A"},
    "rtu.fan_power":            {"label": "Fan Power",            "unit": "W",    "scale": None, "color": "#7C4D9E"},
    "rtu.cooling_power":        {"label": "Cooling Power",        "unit": "W",    "scale": None, "color": "#2E86C1"},
    "rtu.heating_power":        {"label": "Heating Power",        "unit": "W",    "scale": None, "color": "#D66B2A"},
    "rtu.supply_heat_flow":     {"label": "Supply Heat Flow",     "unit": "W",    "scale": None, "color": "#C2410C"},
    "vav.Q_supply_flow":        {"label": "VAV Heat Flow",        "unit": "W",    "scale": None, "color": "#C77D23"},
    "vav.total_power":          {"label": "VAV Total Power",      "unit": "W",    "scale": None, "color": "#9F2D55"},

    "solar.Q_solar":            {"label": "Solar Gains",          "unit": "W",    "scale": None, "color": "#E2A72E"},
    "Q_internal":               {"label": "Internal Gains",       "unit": "W",    "scale": None, "color": "#8B6F47"},
    "weather_factor":           {"label": "Weather Factor",       "unit": "-",    "scale": None, "color": "#5E6AD2"},

    "rtu.supply_airflow":       {"label": "Supply Airflow",       "unit": "kg/s", "scale": None, "color": "#168A75"},
    "vav.supply_airflow":       {"label": "VAV Airflow",          "unit": "kg/s", "scale": None, "color": "#2F9E44"},
    "rtu.P_supply":             {"label": "Supply Pressure",      "unit": "Pa",   "scale": None, "color": "#5C677D"},
    "vav.P_supply":             {"label": "VAV Pressure",         "unit": "Pa",   "scale": None, "color": "#7A869A"},

    "rtu.damper_position":      {"label": "RTU Damper",           "unit": "-",    "scale": None, "color": "#4B5563"},
    "rtu.valve_position":       {"label": "RTU Valve",            "unit": "-",    "scale": None, "color": "#8B5CF6"},
    "vav.damper_position":      {"label": "VAV Damper",           "unit": "-",    "scale": None, "color": "#6B7280"},
    "vav.reheat_position":      {"label": "VAV Reheat",           "unit": "-",    "scale": None, "color": "#F97316"},
    "rtu.integral_accumulator": {"label": "RTU Integrator",       "unit": "-",    "scale": None, "color": "#6366F1"},

    "T_setpoint":               {"label": "Zone Setpoint",        "unit": "C",    "scale": kelvin_to_celsius, "color": "#0F766E"},
    "T_supply_setpoint":        {"label": "Supply Temp Setpoint", "unit": "C",    "scale": kelvin_to_celsius, "color": "#2563EB"},
    "supply_airflow_setpoint":  {"label": "Airflow Setpoint",     "unit": "kg/s", "scale": None, "color": "#16A34A"},
}

ZONE_COLORS = [
    "#2F80C1", "#37A169", "#D97706",
    "#C026D3", "#0E7490", "#DC2626",
]


PLOT_GROUPS = [
    (
        "Weather & Gains",
        ["T_outdoor", "weather_factor", "Q_internal", "solar.Q_solar"],
    ),
    (
        "Setpoints",
        ["T_setpoint", "T_supply_setpoint", "supply_airflow_setpoint"],
    ),
    (
        "Results",
        ["envelope.T_zones", "rtu.T_supply", "rtu.total_power",
         "vav.Q_supply_flow", "rtu.supply_airflow", "rtu.fan_power"],
    ),
]

DEFAULT_PLOT_VARS = [
    "envelope.T_zones",
    "rtu.T_supply",
    "rtu.total_power",
]

_PRIORITY = DEFAULT_PLOT_VARS


def auto_title(model_name: str, t_start: float, t_duration: float, dt: float, tab_name: str = "") -> str:
    hour_of_day = math.floor((t_start % 86400) / 3600)
    hour_12 = ((hour_of_day - 1) % 12) + 1
    am_pm = "AM" if hour_of_day < 12 else "PM"
    duration = f"{t_duration / 3600:.1f}h"
    base = f"{duration} from {int(hour_12)} {am_pm}"
    return f"{tab_name} - {base}" if tab_name else base


def select_variables(results: dict) -> list:
    variables = [k for k in _PRIORITY if k in results]
    if not variables:
        variables = [
            k for k in results
            if k != "t"
            and isinstance(results[k], torch.Tensor)
            and results[k].ndim == 3
        ][:6]
    return variables
