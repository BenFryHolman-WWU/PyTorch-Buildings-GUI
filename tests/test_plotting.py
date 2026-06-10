import unittest
import csv
import tempfile
from pathlib import Path

import numpy as np
import torch

from test_support import get_qapp

from PyQt6.QtCore import QPointF
from gui.plot_widget import ChartWidget, LineSeries, MultiChartWidget
from simulation.plotter import DEFAULT_PLOT_VARS, VARIABLE_META, ZONE_COLORS, auto_title, select_variables


class PlottingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = get_qapp()

    def test_auto_title_formats_time_and_duration(self):
        title = auto_title("Model", 18 * 3600, 7200, 300, "Results")

        self.assertIn("Results", title)
        self.assertIn("2.0h", title)
        self.assertIn("6 PM", title)
        self.assertNotIn("dt=", title)
        self.assertNotIn("batch=", title)

    def test_select_variables_prefers_default_priority(self):
        results = {
            "t": torch.zeros(1, 2, 1),
            DEFAULT_PLOT_VARS[1]: torch.zeros(1, 2, 1),
            "other": torch.zeros(1, 2, 1),
        }

        self.assertEqual(select_variables(results), [DEFAULT_PLOT_VARS[1]])

    def test_select_variables_falls_back_to_first_tensor_series(self):
        results = {
            "t": torch.zeros(1, 2, 1),
            "scalar": torch.zeros(1),
            "series": torch.zeros(1, 2, 3),
        }

        self.assertEqual(select_variables(results), ["series"])

    def test_chart_widget_render_to_pixmap_produces_non_null_image(self):
        chart = ChartWidget(ylabel="Temp [C]", show_x_axis=True)
        chart.set_series([
            LineSeries(
                x=__import__("numpy").array([0.0, 1.0, 2.0]),
                y=__import__("numpy").array([10.0, 12.0, 11.0]),
                label="Zone 1",
            )
        ])

        pixmap = chart.render_to_pixmap(320, 180)

        self.assertFalse(pixmap.isNull())
        self.assertEqual(pixmap.width(), 320)
        self.assertEqual(pixmap.height(), 180)

    def test_chart_hover_finds_nearest_visible_sample(self):
        chart = ChartWidget(ylabel="Temp [C]", show_x_axis=True)
        chart.resize(360, 220)
        chart.set_series([
            LineSeries(
                x=__import__("numpy").array([0.0, 300.0, 600.0]),
                y=__import__("numpy").array([10.0, 20.0, 15.0]),
                label="Zone 1",
            )
        ])
        pr = chart._plot_rect(chart.width(), chart.height())
        px, py = chart._to_px(300.0, 20.0, pr)

        sample = chart._nearest_sample(QPointF(px + 3.0, py + 2.0), pr)

        self.assertIsNotNone(sample)
        self.assertEqual(sample["sample_index"], 1)
        self.assertEqual(sample["x"], 300.0)
        self.assertEqual(sample["y"], 20.0)

    def test_chart_hover_ignores_hidden_series(self):
        chart = ChartWidget(ylabel="Temp [C]", show_x_axis=True)
        chart.resize(360, 220)
        visible = LineSeries(
            x=np.array([0.0, 300.0]),
            y=np.array([10.0, 20.0]),
            label="Zone 1",
        )
        hidden = LineSeries(
            x=np.array([0.0, 300.0]),
            y=np.array([10.0, 20.0]),
            label="Zone 2",
            opacity=0.0,
        )
        chart.set_series([visible, hidden])
        pr = chart._plot_rect(chart.width(), chart.height())
        px, py = chart._to_px(300.0, 20.0, pr)

        sample = chart._nearest_sample(QPointF(px, py), pr)

        self.assertIsNotNone(sample)
        self.assertIs(sample["series"], visible)
        self.assertEqual(sample["series_index"], 0)

    def test_hidden_series_does_not_drive_y_fit(self):
        chart = ChartWidget(ylabel="Temp [C]", show_x_axis=True)
        chart.set_series([
            LineSeries(
                x=np.array([0.0, 300.0]),
                y=np.array([10.0, 20.0]),
                label="Zone 1",
            ),
            LineSeries(
                x=np.array([0.0, 300.0]),
                y=np.array([900.0, 1000.0]),
                label="Zone 2",
                opacity=0.0,
            ),
        ])

        self.assertFalse(chart.series[1].visible)
        self.assertLess(chart._y_max, 25.0)

    def test_chart_hover_x_uses_time_formatter_when_present(self):
        chart = ChartWidget(ylabel="Power [W]", show_x_axis=True)
        chart.x_formatter = lambda x: "5:00 AM"

        self.assertEqual(chart._format_hover_x(0.0), "5:00 AM")

    def test_loaded_chart_x_formatter_includes_minutes(self):
        widget = MultiChartWidget()
        results = {
            "t": torch.tensor([[[18000.0], [18300.0]]]),
            "rtu.total_power": torch.tensor([[[100.0], [200.0]]]),
        }

        widget.load_results(results, ["rtu.total_power"], 18000, VARIABLE_META, ZONE_COLORS)

        chart = widget.charts[0]
        self.assertEqual(chart.x_formatter(0.0), "5:00 AM")
        self.assertEqual(chart.x_formatter(300.0), "5:05 AM")

    def test_multi_chart_load_results_creates_one_chart_per_variable(self):
        widget = MultiChartWidget()
        results = {
            "t": torch.tensor([[[0.0], [300.0]]]),
            "envelope.T_zones": torch.tensor([[[293.15, 294.15], [294.15, 295.15]]]),
            "rtu.total_power": torch.tensor([[[100.0], [200.0]]]),
        }

        widget.load_results(
            results,
            ["envelope.T_zones", "rtu.total_power"],
            18000,
            VARIABLE_META,
            ZONE_COLORS,
        )

        self.assertEqual(len(widget.charts), 2)
        self.assertEqual(len(widget.charts[0].series), 2)
        self.assertTrue(widget.charts[-1].show_x_axis)

    def test_multi_chart_csv_export_uses_time_index_and_variable_columns(self):
        widget = MultiChartWidget()
        results = {
            "t": torch.tensor([[[0.0], [300.0]]]),
            "envelope.T_zones": torch.tensor([[[293.15, 294.15], [294.15, 295.15]]]),
            "rtu.total_power": torch.tensor([[[100.0], [200.0]]]),
        }
        widget.load_results(
            results,
            ["envelope.T_zones", "rtu.total_power"],
            18000,
            VARIABLE_META,
            ZONE_COLORS,
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "plot.csv"
            widget.save_to_csv(path)
            with path.open(newline="", encoding="utf-8") as csv_file:
                rows = list(csv.reader(csv_file))

        self.assertEqual(
            rows[0],
            [
                "elapsed_time_seconds",
                "envelope.T_zones - Zone 1 [C]",
                "envelope.T_zones - Zone 2 [C]",
                "rtu.total_power [W]",
            ],
        )
        self.assertEqual(rows[1][0], "0.0")
        self.assertAlmostEqual(float(rows[1][1]), 20.0, places=4)
        self.assertAlmostEqual(float(rows[1][2]), 21.0, places=4)
        self.assertEqual(rows[2][0], "300.0")
        self.assertEqual(rows[2][3], "200.0")

    def test_partial_live_results_keep_full_x_axis_range(self):
        widget = MultiChartWidget()
        results = {
            "t": torch.tensor([[[18000.0], [18300.0], [18600.0], [18900.0]]]),
            "rtu.total_power": torch.tensor([[[100.0], [200.0]]]),
        }

        widget.load_results(results, ["rtu.total_power"], 18000, VARIABLE_META, ZONE_COLORS)

        chart = widget.charts[0]
        self.assertEqual(chart.series[0].x.tolist(), [0.0, 300.0])
        self.assertEqual(chart._x_min, -150.0)
        self.assertEqual(chart._x_max, 1050.0)
        self.assertEqual(chart._vx_min, -150.0)
        self.assertEqual(chart._vx_max, 1050.0)

    def test_chart_ranges_pad_edge_samples_so_points_are_visible(self):
        chart = ChartWidget(ylabel="Power [W]", show_x_axis=True)
        chart.set_series([
            LineSeries(
                x=__import__("numpy").array([0.0, 300.0, 600.0]),
                y=__import__("numpy").array([100.0, 400.0, 200.0]),
                label="Power",
            )
        ])

        self.assertLess(chart._x_min, 0.0)
        self.assertGreater(chart._x_max, 600.0)
        self.assertLess(chart._y_min, 100.0)
        self.assertGreater(chart._y_max, 400.0)

    def test_live_refresh_pads_y_range_for_current_partial_data(self):
        widget = MultiChartWidget()
        results = {
            "t": torch.tensor([[[18000.0], [18300.0], [18600.0]]]),
            "rtu.total_power": torch.tensor([[[100.0], [400.0]]]),
        }
        widget.load_results(results, ["rtu.total_power"], 18000, VARIABLE_META, ZONE_COLORS)

        widget.refresh_series_from_results(results, 18000, VARIABLE_META, ZONE_COLORS)

        chart = widget.charts[0]
        self.assertLess(chart._y_min, 100.0)
        self.assertGreater(chart._y_max, 400.0)

    def test_temperature_axis_can_switch_between_celsius_and_kelvin(self):
        chart = ChartWidget(ylabel="Zone Temp [C]", show_x_axis=True)
        chart.set_value_axis("Zone Temp", "C", temperature_units_enabled=True)
        chart.set_series([
            LineSeries(
                x=np.array([0.0, 300.0]),
                y=np.array([10.0, 20.0]),
                label="Zone 1",
            )
        ])

        chart.set_temperature_unit("K")

        self.assertEqual(chart.value_unit, "K")
        self.assertEqual(chart.ylabel, "Zone Temp [K]")
        self.assertAlmostEqual(chart.series[0].y[0], 283.15)
        self.assertAlmostEqual(chart._y_min, 9.5 + 273.15)

    def test_manual_y_axis_range_survives_live_refresh(self):
        widget = MultiChartWidget()
        results = {
            "t": torch.tensor([[[18000.0], [18300.0], [18600.0]]]),
            "rtu.total_power": torch.tensor([[[100.0], [400.0], [200.0]]]),
        }
        widget.load_results(results, ["rtu.total_power"], 18000, VARIABLE_META, ZONE_COLORS)
        chart = widget.charts[0]
        chart.set_y_axis_range(0.0, 1000.0)

        widget.refresh_series_from_results(results, 18000, VARIABLE_META, ZONE_COLORS)

        self.assertEqual(chart._y_min, 0.0)
        self.assertEqual(chart._y_max, 1000.0)
        self.assertEqual(chart._vy_min, 0.0)
        self.assertEqual(chart._vy_max, 1000.0)

    def test_live_refresh_preserves_hidden_series_and_scales_to_visible(self):
        widget = MultiChartWidget()
        results = {
            "t": torch.tensor([[[18000.0], [18300.0], [18600.0]]]),
            "envelope.T_zones": torch.tensor([[[10.0, 900.0], [20.0, 1000.0], [15.0, 950.0]]]),
        }
        widget.load_results(results, ["envelope.T_zones"], 18000, VARIABLE_META, ZONE_COLORS)
        chart = widget.charts[0]
        chart.series[1].opacity = 0.0

        widget.refresh_series_from_results(results, 18000, VARIABLE_META, ZONE_COLORS)

        self.assertEqual(chart.series[1].opacity, 0.0)
        self.assertLess(chart._y_max, 25.0)

    def test_single_series_uses_variable_specific_default_color(self):
        widget = MultiChartWidget()
        results = {
            "t": torch.tensor([[[0.0], [300.0]]]),
            "rtu.cooling_power": torch.tensor([[[100.0], [200.0]]]),
        }

        widget.load_results(results, ["rtu.cooling_power"], 18000, VARIABLE_META, ZONE_COLORS)

        self.assertEqual(widget.charts[0].series[0].color.name(), VARIABLE_META["rtu.cooling_power"]["color"].lower())


if __name__ == "__main__":
    unittest.main()
