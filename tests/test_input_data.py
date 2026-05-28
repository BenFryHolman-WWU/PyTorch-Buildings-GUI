import tempfile
import unittest
import sqlite3
from pathlib import Path

import test_support  # noqa: F401
from simulation.input_data import inspect_input_csv, load_input_csv


class InputDataTests(unittest.TestCase):
    def test_load_input_csv_maps_supported_columns_and_units(self):
        csv_text = "\n".join([
            "Time [s],Outdoor Dry-Bulb Temperature [°C],Global Horizontal Irradiance [W/m²],"
            "Zone 1 Cooling Setpoint [°C],Zone 2 Cooling Setpoint [°C],"
            "AHU Supply Air Temperature [°C],AHU Supply Fan Air Flow [m³/s]",
            "0,20,0,24,25,12,1.0",
            "60,22,800,26,27,14,2.0",
        ])
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "inputs.csv"
            path.write_text(csv_text, encoding="utf-8")

            tensors, summary = load_input_csv(path, [18000, 18060], 2, 18000)

        self.assertEqual(summary["zone_count"], 2)
        self.assertIn("T_setpoint", summary["mapped_keys"])
        self.assertAlmostEqual(float(tensors["T_outdoor"][0, 0, 0]), 293.15, places=3)
        self.assertAlmostEqual(float(tensors["T_outdoor"][0, 1, 0]), 295.15, places=3)
        self.assertAlmostEqual(float(tensors["weather_factor"][0, 1, 0]), 1.0, places=3)
        self.assertAlmostEqual(float(tensors["T_supply_setpoint"][0, 0, 0]), 285.15, places=3)
        self.assertAlmostEqual(float(tensors["supply_airflow_setpoint"][0, 1, 0]), 2.4, places=3)
        self.assertEqual(tuple(tensors["T_setpoint"].shape), (1, 2, 2))
        self.assertAlmostEqual(float(tensors["T_setpoint"][0, 0, 1]), 298.15, places=3)

    def test_inspect_input_csv_reports_supported_metadata(self):
        csv_text = "\n".join([
            "Time [s],Outdoor Dry-Bulb Temperature [°C],Zone 1 Cooling Setpoint [°C]",
            "0,20,24",
        ])
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "inputs.csv"
            path.write_text(csv_text, encoding="utf-8")

            summary = inspect_input_csv(path)

        self.assertEqual(summary["row_count"], 1)
        self.assertEqual(summary["zone_count"], 1)
        self.assertEqual(summary["mapped_keys"], ["T_outdoor", "T_setpoint"])

    def test_load_input_database_maps_supported_columns(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "inputs.sqlite"
            with sqlite3.connect(path) as connection:
                connection.execute(
                    'CREATE TABLE input_data ("Time [s]" REAL, "Outdoor Dry-Bulb Temperature [°C]" REAL, '
                    '"Zone 1 Cooling Setpoint [°C]" REAL)'
                )
                connection.executemany(
                    'INSERT INTO input_data VALUES (?, ?, ?)',
                    [(0, 20, 24), (60, 22, 26)],
                )

            tensors, summary = load_input_csv(path, [18000, 18060], 1, 18000)

        self.assertEqual(summary["row_count"], 2)
        self.assertEqual(summary["zone_count"], 1)
        self.assertIn("T_outdoor", summary["mapped_keys"])
        self.assertAlmostEqual(float(tensors["T_outdoor"][0, 1, 0]), 295.15, places=3)


if __name__ == "__main__":
    unittest.main()
