"""Container and drag-list widgets for simulation plots."""

import csv
from typing import List

import numpy as np
from PyQt6.QtCore import Qt, QMimeData, QRectF, pyqtSignal
from PyQt6.QtGui import QColor, QDrag, QFont, QPainter, QPen
from PyQt6.QtWidgets import QAbstractItemView, QListWidget, QListWidgetItem, QSizePolicy, QVBoxLayout, QWidget

from .plot_widget import ChartWidget, LineSeries, _padded_range, _time_domain_with_margin


class MultiChartWidget(QWidget):

    variable_removed = pyqtSignal(str)
    variable_added = pyqtSignal(str)
    charts_reordered = pyqtSignal(list)

    def __init__(self, parent = None):
        """Summary: Init."""
        super().__init__(parent)
        self.charts: List[ChartWidget] = []
        self._overall_title = ""
        self._overall_title_font_size = 13
        self._grid_visible = True
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(2)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._drop_highlight = False
        self._reorder_drop_idx = -1
        self.setAcceptDrops(True)


    def set_overall_title(self, text: str, font_size: int = 13):
        self._overall_title = text
        self._overall_title_font_size = font_size
        for i, c in enumerate(self.charts):
            c.overall_title = text if i == 0 else ""
            c.title_font_size = font_size
            c.update()


    def set_font_size(self, size: int):
        for c in self.charts:
            c.font_size = size
            c.update()


    def set_grid(self, on: bool):
        self._grid_visible = bool(on)
        for c in self.charts:
            c.show_grid = self._grid_visible
            c.update()
        self._sync_grid_toggle()


    def toggle_grid(self):
        next_value = not self.charts[0].show_grid if self.charts else True
        self.set_grid(next_value)


    def _sync_grid_toggle(self):
        for chart in self.charts:
            chart.grid_toggle_callback = None
            chart.update()


    def reset_view(self):
        for c in self.charts:
            c.reset_view()


    def set_font_family(self, family: str):
        for c in self.charts:
            c.font_family = family
            c.update()


    def set_font_color(self, color: QColor):
        for c in self.charts:
            c.axis_color = color
            c.update()


    def set_chart_height_weight(self, index: int, weight: int):
        if 0 <= index < self._layout.count():
            self._layout.setStretch(index, max(1, weight))


    def clear(self):
        for c in self.charts:
            c.deleteLater()
        self.charts.clear()
        while self._layout.count():
            item = self._layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()


    def _elapsed_time_vector(self, results: dict):
        try:
            time_vec = results["t"][0, :].detach().cpu().numpy().flatten()
        except Exception:
            return np.array([], dtype=float)
        if len(time_vec) == 0:
            return np.array([], dtype=float)
        return time_vec - time_vec[0]


    def _series_color(self, meta: dict, var_key: str, feat: int, n_feat: int, zone_colors: List[str]) -> QColor:
        if n_feat > 1:
            return QColor(zone_colors[feat % len(zone_colors)])
        return QColor(meta.get("color", zone_colors[feat % len(zone_colors)]))


    def _apply_full_x_range(self, chart: ChartWidget, full_time: np.ndarray):
        if len(full_time) == 0:
            return
        lo, hi = _time_domain_with_margin(full_time)
        chart._x_min = lo
        chart._x_max = hi
        chart._vx_min = lo
        chart._vx_max = hi


    def load_results(self, results: dict, variables: List[str], t_start: float,
                     variable_meta: dict, zone_colors: List[str]):
        """
        Summary: Load results.
        Args: results, variables, variable_meta, zone_colors
        Returns: Return the computed value.
        """
        import torch
        self.clear()
        full_time = self._elapsed_time_vector(results)
        if len(full_time) == 0:
            return

        def _fmt(xv: float) -> str:
            try:
                tod = (t_start + xv) % 86400
                h = int(tod // 3600)
                m = int((tod % 3600) // 60)
                h12 = ((h - 1) % 12) + 1
                return f"{h12}:{m:02d} {'AM' if h < 12 else 'PM'}"
            except Exception:
                return ""

        for i, var in enumerate(variables):
            is_last = (i == len(variables) - 1)
            meta = variable_meta.get(var, {})
            unit = meta.get("unit", "")
            label = meta.get("label", var)
            scale = meta.get("scale", None)
            ylabel = f"{label} [{unit}]" if unit else label
            chart = ChartWidget(ylabel = ylabel, show_x_axis = is_last)
            chart.set_value_axis(label, unit, temperature_units_enabled=(unit in {"C", "K"} and scale is not None))
            chart.var_key = var
            chart.show_grid = self._grid_visible
            chart.remove_callback = (lambda k=var: self.variable_removed.emit(k))
            chart.x_formatter = _fmt
            if i == 0 and self._overall_title:
                chart.overall_title = self._overall_title
                chart.title_font_size = self._overall_title_font_size
            try:
                data = results.get(var)
                if isinstance(data, torch.Tensor) and data.ndim == 3:
                    n = min(len(full_time), data.shape[1])
                    n_feat = data.shape[2]
                    series = []
                    for feat in range(n_feat):
                        y = data[0, :n, feat].detach().cpu().numpy().copy()
                        if scale is not None:
                            y = scale(y)
                        series.append(LineSeries(
                            x = full_time[:n].copy(),
                            y = y,
                            label = f"Zone {feat + 1}" if n_feat > 1 else label,
                            color = self._series_color(meta, var, feat, n_feat, zone_colors),
                            width = 2,
                            style = "Solid",
                        ))
                    chart.set_series(series)
                    self._apply_full_x_range(chart, full_time)
            except Exception:
                pass
            self.charts.append(chart)
            self._layout.addWidget(chart, 1)
        self._sync_grid_toggle()


    def refresh_series_from_results(self, results: dict, t_start: float,
                                     variable_meta: dict, zone_colors: list):
        """
        Summary: Refresh series from results.
        Args: results, variable_meta, zone_colors
        """
        import torch
        full_time = self._elapsed_time_vector(results)
        if len(full_time) == 0:
            return

        for chart in self.charts:
            var_key = chart.var_key
            tensor = results.get(var_key)
            if not isinstance(tensor, torch.Tensor) or tensor.ndim != 3:
                continue
            meta = variable_meta.get(var_key, {})
            scale_fn = meta.get("scale")
            n_data = min(tensor.shape[1], len(full_time))
            if n_data <= 0:
                continue
            t_local = full_time[:n_data]
            n_feat = tensor.shape[2]

            while len(chart.series) < n_feat:
                zi = len(chart.series)
                label = meta.get("label", var_key)
                chart.series.append(LineSeries(
                    x=t_local,
                    y=t_local * 0,
                    label=f"Zone {zi + 1}" if n_feat > 1 else label,
                    color=self._series_color(meta, var_key, zi, n_feat, zone_colors),
                    width=2,
                    style="Solid",
                ))
            for zi in range(min(n_feat, len(chart.series))):
                y = tensor[0, :n_data, zi].detach().cpu().numpy().copy()
                if scale_fn is not None:
                    y = scale_fn(y)
                if chart.temperature_units_enabled and chart.value_unit == "K":
                    y = y + 273.15
                chart.series[zi].x = t_local
                chart.series[zi].y = y

            visible_series = [s for s in chart.series[:n_feat] if s.visible]
            y_series = visible_series if visible_series else chart.series[:n_feat]
            all_y = np.concatenate([s.y for s in y_series])
            y_min, y_max = _padded_range(all_y)
            self._apply_full_x_range(chart, full_time)
            if chart._manual_y_range:
                chart._vy_min = chart._y_min
                chart._vy_max = chart._y_max
            else:
                chart._y_min = y_min
                chart._y_max = y_max
                chart._vy_min = chart._y_min
                chart._vy_max = chart._y_max
            chart.update()


    def paintEvent(self, event):
        """Summary: Paintevent."""
        super().paintEvent(event)
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        if not self.charts:
            p.fillRect(self.rect(), QColor(240, 242, 248))
            if self._drop_highlight:
                pen = QPen(QColor(72, 120, 200), 2, Qt.PenStyle.DashLine)
                p.setPen(pen)
                p.setBrush(QColor(72, 120, 200, 18))
                p.drawRoundedRect(QRectF(self.rect().adjusted(8, 8, -8, -8)), 10, 10)
            font = QFont()
            font.setPointSize(12)
            font.setItalic(True)
            p.setFont(font)
            p.setPen(QColor(152, 164, 196))
            p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter,
                       "\u2190 Drag variables from the list to plot them")

        if self._reorder_drop_idx >= 0 and self.charts:
            if self._reorder_drop_idx == 0:
                y_line = self.charts[0].y()
            elif self._reorder_drop_idx >= len(self.charts):
                c = self.charts[-1]
                y_line = c.y() + c.height()
            else:
                y_line = self.charts[self._reorder_drop_idx].y()
            pen = QPen(QColor(72, 120, 200), 2)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            p.setPen(pen)
            p.setBrush(QColor(72, 120, 200))
            margin = 16
            p.drawLine(margin, y_line, self.width() - margin, y_line)

            p.drawEllipse(QRectF(margin - 3, y_line - 3, 6, 6))
            p.drawEllipse(QRectF(self.width() - margin - 3, y_line - 3, 6, 6))
        p.end()


    def _chart_insert_idx(self, y: int) -> int:
        for i, c in enumerate(self.charts):
            if y < c.y() + c.height() // 2:
                return i
        return len(self.charts)

    def _reorder_charts(self, src_idx: int, dst_idx: int):
        """
        Summary: Reorder charts.
        Args: src_idx, dst_idx
        """
        n = len(self.charts)
        if src_idx < 0 or src_idx >= n or dst_idx < 0:
            return
        dst_idx = min(dst_idx, n)

        effective_dst = dst_idx if dst_idx <= src_idx else dst_idx - 1
        if effective_dst == src_idx:
            return
        chart = self.charts.pop(src_idx)
        self.charts.insert(effective_dst, chart)

        while self._layout.count():
            self._layout.takeAt(0)
        for i, c in enumerate(self.charts):
            c.show_x_axis = (i == len(self.charts) - 1)
            c.overall_title = self._overall_title if i == 0 else ""
            self._layout.addWidget(c, 1)
        self._sync_grid_toggle()
        self.charts_reordered.emit([c.var_key for c in self.charts])

    def dragEnterEvent(self, event):
        """Summary: Dragenterevent."""
        text = event.mimeData().text() if event.mimeData().hasText() else ""
        if text.startswith("chartreorder:"):
            self._reorder_drop_idx = self._chart_insert_idx(event.position().toPoint().y())
            self.update()
            event.acceptProposedAction()
        elif text.startswith("plotvar:"):
            self._drop_highlight = True
            self.update()
            event.acceptProposedAction()
        else:
            event.ignore()


    def dragMoveEvent(self, event):
        """Summary: Dragmoveevent."""
        text = event.mimeData().text() if event.mimeData().hasText() else ""
        if text.startswith("chartreorder:"):
            new_idx = self._chart_insert_idx(event.position().toPoint().y())
            if new_idx != self._reorder_drop_idx:
                self._reorder_drop_idx = new_idx
                self.update()
            event.acceptProposedAction()
        elif text.startswith("plotvar:"):
            event.acceptProposedAction()
        else:
            event.ignore()


    def dragLeaveEvent(self, event):
        self._drop_highlight = False
        self._reorder_drop_idx = -1
        self.update()


    def dropEvent(self, event):
        """Summary: Dropevent."""
        self._drop_highlight = False
        self._reorder_drop_idx = -1
        self.update()
        text = event.mimeData().text() if event.mimeData().hasText() else ""
        if text.startswith("chartreorder:"):
            try:
                src_idx = int(text.split(":")[1])
            except (IndexError, ValueError):
                event.ignore()
                return
            dst_idx = self._chart_insert_idx(event.position().toPoint().y())
            self._reorder_charts(src_idx, dst_idx)
            event.acceptProposedAction()
        elif text.startswith("plotvar:"):
            key = text[8:]
            self.variable_added.emit(key)
            event.acceptProposedAction()
        else:
            event.ignore()


    def save_to_file(self, path: str, chart_width: int = 1200, chart_height: int = 300,
                     scale: float = 3.0):
        """
        Summary: Save to file.
        Args: chart_width, chart_height
        """
        if not self.charts:
            return
        phys_w = max(1, int(chart_width * scale))
        phys_total_h = max(1, int(chart_height * len(self.charts) * scale))
        canvas = QPixmap(phys_w, phys_total_h)
        canvas.setDevicePixelRatio(scale)
        canvas.fill(QColor(255, 255, 255))
        p = QPainter(canvas)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        y = 0
        for chart in self.charts:
            px = chart.render_to_pixmap(chart_width, chart_height, scale=scale)

            p.drawPixmap(0, y, chart_width, chart_height, px)
            y += chart_height
        p.end()
        if not canvas.save(path):
            raise OSError("The plot image could not be written.")


    def save_to_csv(self, path: str):
        """Export the currently displayed chart series and units as CSV rows."""
        if not self.charts:
            raise ValueError("There are no chart series to export.")
        with open(path, "w", encoding="utf-8", newline="") as csv_file:
            writer = csv.writer(csv_file)
            writer.writerow([
                "chart",
                "variable",
                "series",
                "elapsed_time_seconds",
                "value",
                "unit",
            ])
            for chart_index, chart in enumerate(self.charts, start=1):
                for series in chart.series:
                    for elapsed, value in zip(series.x, series.y):
                        writer.writerow([
                            chart_index,
                            chart.var_key,
                            series.label,
                            float(elapsed),
                            float(value),
                            chart.value_unit,
                        ])


class VarListWidget(QListWidget):

    _STYLE = """
        QListWidget {
            background: #f4f5fa;
            border: 1px solid #d4d8ea;
            border-radius: 6px;
            padding: 2px;
            outline: 0;
        }
        QListWidget::item {
            padding: 4px 4px;
            border-radius: 4px;
            color: #2c3454;
            font-size: 11px;
        }
        QListWidget::item:selected {
            background: #dce3f5;
            color: #1a2240;
        }
        QListWidget::item:hover:!selected {
            background: #dcdde3;
        }
    """

    def __init__(self, parent=None):
        """Summary: Init."""
        super().__init__(parent)
        self.setDragEnabled(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.DragOnly)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setSpacing(1)
        self.setStyleSheet(self._STYLE)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self._sync_height()

    def populate(self, group_vars: list, meta: dict):
        """
        Summary: Populate.
        Args: group_vars, meta
        """
        self.clear()
        for key in group_vars:
            label = meta.get(key, {}).get("label", key)
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, key)
            item.setFlags(
                Qt.ItemFlag.ItemIsEnabled
                | Qt.ItemFlag.ItemIsDragEnabled
                | Qt.ItemFlag.ItemIsSelectable
            )
            self.addItem(item)
        self._sync_height()

    def addItem(self, item):
        super().addItem(item)
        self._sync_height()

    def clear(self):
        super().clear()
        self._sync_height()

    def _sync_height(self):
        rows = self.count()
        if rows <= 0:
            target = 30
        else:
            row_h = max(22, self.sizeHintForRow(0))
            target = rows * row_h + max(0, rows - 1) * self.spacing() + 10
        self.setFixedHeight(max(30, target))

    def startDrag(self, supportedActions):
        """
        Summary: Startdrag.
        Args: supportedActions
        """
        item = self.currentItem()
        if item is None:
            return
        key = item.data(Qt.ItemDataRole.UserRole)
        if not key:
            return
        mime = QMimeData()
        mime.setText(f"plotvar:{key}")
        drag = QDrag(self)
        drag.setMimeData(mime)
        drag.exec(Qt.DropAction.CopyAction)
