import math
import torch


VARIABLE_META = {
    "envelope.T_zones":         {"label": "Zone Temp",        "unit": "°C",   "scale": lambda x: x - 273.15},
    "rtu.T_supply":             {"label": "Supply Temp",       "unit": "°C",   "scale": lambda x: x - 273.15},
    "T_outdoor":                {"label": "Outdoor Temp",      "unit": "°C",   "scale": lambda x: x - 273.15},
    "vav.T_supply":             {"label": "VAV Supply Temp",   "unit": "°C",   "scale": lambda x: x - 273.15},
    "rtu.total_power":          {"label": "RTU Total Power",   "unit": "W",    "scale": None},
    "rtu.fan_power":            {"label": "Fan Power",         "unit": "W",    "scale": None},
    "rtu.cooling_power":        {"label": "Cooling Power",     "unit": "W",    "scale": None},
    "rtu.heating_power":        {"label": "Heating Power",     "unit": "W",    "scale": None},
    "rtu.supply_heat_flow":     {"label": "Supply Heat Flow",  "unit": "W",    "scale": None},
    "solar.Q_solar":            {"label": "Solar Gains",       "unit": "W",    "scale": None},
    "vav.Q_supply_flow":        {"label": "VAV Heat Flow",     "unit": "W",    "scale": None},
    "vav.total_power":          {"label": "VAV Total Power",   "unit": "W",    "scale": None},
    "Q_internal":               {"label": "Internal Gains",    "unit": "W",    "scale": None},
    "rtu.supply_airflow":       {"label": "Supply Airflow",    "unit": "kg/s", "scale": None},
    "vav.supply_airflow":       {"label": "VAV Airflow",       "unit": "kg/s", "scale": None},
    "rtu.P_supply":             {"label": "Supply Pressure",   "unit": "Pa",   "scale": None},
    "vav.P_supply":             {"label": "VAV Pressure",      "unit": "Pa",   "scale": None},
    "rtu.damper_position":      {"label": "RTU Damper",        "unit": "-",    "scale": None},
    "rtu.valve_position":       {"label": "RTU Valve",         "unit": "-",    "scale": None},
    "vav.damper_position":      {"label": "VAV Damper",        "unit": "-",    "scale": None},
    "vav.reheat_position":      {"label": "VAV Reheat",        "unit": "-",    "scale": None},
    "T_supply_setpoint":        {"label": "Supply Setpoint",   "unit": "°C",   "scale": lambda x: x - 273.15},
    "supply_airflow_setpoint":  {"label": "Airflow Setpoint",  "unit": "kg/s", "scale": None},
    "T_setpoint":               {"label": "Zone Setpoint",     "unit": "°C",   "scale": lambda x: x - 273.15},
    "weather_factor":           {"label": "Weather Factor",    "unit": "-",    "scale": None},
    "rtu.integral_accumulator": {"label": "RTU Integrator",    "unit": "-",    "scale": None},
}

ZONE_COLORS = [
    "#1f77b4", "#ff7f0e", "#2ca02c",
    "#d62728", "#9467bd", "#8c564b",
]

PLOT_GROUPS = [
    (
        "24hr Data",
        ["T_outdoor", "weather_factor", "Q_internal", "solar.Q_solar"],
    ),
    (
        "Initial Values",
        ["T_setpoint", "T_supply_setpoint", "supply_airflow_setpoint", "rtu.integral_accumulator"],
    ),
    (
        "Simulation Results",
        ["envelope.T_zones", "rtu.T_supply", "rtu.total_power", "vav.Q_supply_flow", "rtu.fan_power", "rtu.supply_airflow"],
    ),
]

DEFAULT_PLOT_VARS = [
    "envelope.T_zones",
    "rtu.T_supply",
    "rtu.total_power",
    "solar.Q_solar",
    "vav.Q_supply_flow",
]

_PRIORITY = DEFAULT_PLOT_VARS


def auto_title(model_name: str, t_start: float, t_duration: float, dt: float, tab_name: str = "") -> str:
    """Generate a simulation title matching the neuromancer simplot format. Args: model_name (str), t_start (float), t_duration (float), dt (float), tab_name (str). Returns: str."""
    hour_of_day = math.floor((t_start % 86400) / 3600)
    hour_12 = ((hour_of_day - 1) % 12) + 1
    am_pm = "AM" if hour_of_day < 12 else "PM"
    base = (
        f"{model_name} Simulation: {t_duration / 3600:.1f} hours "
        f"from {int(hour_12)} {am_pm} "
        f"(dt={dt:.1f}sec, batch=0)"
    )
    return f"{tab_name} — {base}" if tab_name else base


def select_variables(results: dict) -> list:
    """Return ordered list of variable keys to plot from results. Args: results (dict). Returns: list."""
    variables = [k for k in _PRIORITY if k in results]
    if not variables:
        variables = [
            k for k in results
            if k != "t"
            and isinstance(results[k], torch.Tensor)
            and results[k].ndim == 3
        ][:6]
    return variables
