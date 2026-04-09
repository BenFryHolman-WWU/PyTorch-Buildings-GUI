import math
from dataclasses import dataclass, field
from typing import Callable, List, Optional

import numpy as np

from PyQt6.QtCore import Qt, QRectF, QRect, QPointF
from PyQt6.QtGui import (
    QColor, QFont, QFontMetrics, QPainter, QPainterPath, QPen, QPixmap,
)
from PyQt6.QtWidgets import QLabel, QSizePolicy, QVBoxLayout, QWidget


STYLE_OPTIONS = ["Solid", "Dashed", "Dotted", "Dash-dot"]

_PEN_STYLE: dict = {
    "Solid":    Qt.PenStyle.SolidLine,
    "Dashed":   Qt.PenStyle.DashLine,
    "Dotted":   Qt.PenStyle.DotLine,
    "Dash-dot": Qt.PenStyle.DashDotLine,
}


@dataclass
class LineSeries:
    x: np.ndarray
    y: np.ndarray
    label: str = ""
    color: QColor = field(default_factory=lambda: QColor("#1f77b4"))
    width: int = 2
    style: str = "Solid"


class ChartWidget(QWidget):
    """One subplot drawn with QPainter. Drag to rubber-band-zoom, double-click to reset."""

    _ML = 72
    _MR = 14
    _TITLE_H = 30
    _SUB_H = 22
    _MT_BASE = 6
    _MB_X = 40
    _MB_NOX = 6

    def __init__(self, ylabel: str = "", show_x_axis: bool = False, parent = None):
        """Initialize a chart widget. Args: ylabel (str), show_x_axis (bool), parent (QWidget, optional)."""
        super().__init__(parent)
        self.series: List[LineSeries] = []
        self.ylabel = ylabel
        self.subplot_title = ""
        self.overall_title = ""
        self.title_font_size = 13
        self.show_x_axis = show_x_axis
        self.show_grid = True
        self.font_size = 9
        self.font_family: str = ""
        self.axis_color: QColor = QColor(50, 50, 50)
        self.bg_color = QColor(255, 255, 255)
        self.x_formatter: Optional[Callable[[float], str]] = None
        self._x_min = self._x_max = 0.0
        self._y_min = self._y_max = 1.0
        self._vx_min = self._vx_max = 0.0
        self._vy_min = self._vy_max = 1.0
        self._rb_origin: Optional[QPointF] = None
        self._rb_current: Optional[QPointF] = None
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumHeight(100)
        self.setCursor(Qt.CursorShape.CrossCursor)
        self.setMouseTracking(True)


    def _mt(self) -> int:
        """Calculate top margin based on active titles. Returns: int."""
        h = self._MT_BASE
        if self.overall_title:
            h += self._TITLE_H
        if self.subplot_title:
            h += self._SUB_H
        return h


    def _mb(self) -> int:
        """Calculate bottom margin based on x-axis visibility. Returns: int."""
        return self._MB_X if self.show_x_axis else self._MB_NOX


    def _plot_rect(self, w: int, h: int) -> QRectF:
        """Calculate the drawable plot rectangle. Args: w (int), h (int). Returns: QRectF."""
        return QRectF(
            self._ML, self._mt(),
            max(10.0, w - self._ML - self._MR),
            max(10.0, h - self._mt() - self._mb()),
        )


    def set_series(self, series: List[LineSeries]):
        """Set the data series and refresh the view. Args: series (List[LineSeries])."""
        self.series = series
        self._fit_all()
        self.update()


    def _fit_all(self):
        """Fit the view to the full data range of all series."""
        valid = [s for s in self.series if len(s.x) > 0 and len(s.y) > 0]
        if not valid:
            return
        try:
            xs = np.concatenate([s.x for s in valid])
            ys = np.concatenate([s.y for s in valid])
            xs = xs[np.isfinite(xs)]
            ys = ys[np.isfinite(ys)]
            if len(xs) == 0 or len(ys) == 0:
                return
            self._x_min, self._x_max = float(xs.min()), float(xs.max())
            self._y_min, self._y_max = float(ys.min()), float(ys.max())
            yr = self._y_max - self._y_min or 1.0
            self._y_min -= yr * 0.05
            self._y_max += yr * 0.05
        except Exception:
            return
        self._vx_min, self._vx_max = self._x_min, self._x_max
        self._vy_min, self._vy_max = self._y_min, self._y_max


    def reset_view(self):
        """Reset zoom to the full data range."""
        self._vx_min, self._vx_max = self._x_min, self._x_max
        self._vy_min, self._vy_max = self._y_min, self._y_max
        self.update()


    def _to_px(self, xv: float, yv: float, pr: QRectF):
        """Convert data coordinates to pixel coordinates. Args: xv (float), yv (float), pr (QRectF). Returns: tuple."""
        xr = self._vx_max - self._vx_min or 1.0
        yr = self._vy_max - self._vy_min or 1.0
        px = pr.left() + (xv - self._vx_min) / xr * pr.width()
        py = pr.bottom() - (yv - self._vy_min) / yr * pr.height()
        return px, py


    @staticmethod
    def _nice_ticks(lo: float, hi: float, n: int = 5) -> List[float]:
        """Calculate human-friendly tick positions. Args: lo (float), hi (float), n (int). Returns: List[float]."""
        if not (math.isfinite(lo) and math.isfinite(hi)):
            return [0.0]
        span = hi - lo
        if span <= 0 or not math.isfinite(span):
            return [round(lo, 6)] if math.isfinite(lo) else [0.0]
        raw = span / max(1, n)
        if raw <= 0:
            return [lo]
        try:
            mag = 10 ** math.floor(math.log10(raw))
        except ValueError:
            return [lo]
        tick = raw
        for step in (1, 2, 2.5, 5, 10):
            tick = step * mag
            if span / tick <= n + 1:
                break
        start = math.ceil(lo / tick - 1e-9) * tick
        ticks, v = [], start
        while v <= hi + tick * 1e-6:
            ticks.append(round(v, 10))
            v += tick
        return ticks or [lo]


    def paintEvent(self, event):
        """Handle paint event. Args: event (QPaintEvent)."""
        if self.width() < 4 or self.height() < 4:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        self._draw(p, self.width(), self.height())
        p.end()


    def render_to_pixmap(self, w: int, h: int) -> QPixmap:
        """Render chart off-screen at given pixel dimensions for saving. Args: w (int), h (int). Returns: QPixmap."""
        px = QPixmap(max(1, w), max(1, h))
        px.fill(self.bg_color)
        p = QPainter(px)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        self._draw(p, w, h)
        p.end()
        return px


    def _draw(self, p: QPainter, w: int, h: int):
        """Draw the full chart including grid, axes, series, and overlays. Args: p (QPainter), w (int), h (int)."""
        if w < 4 or h < 4:
            return
        pr = self._plot_rect(w, h)
        font = QFont()
        if self.font_family:
            font.setFamily(self.font_family)
        font.setPointSize(self.font_size)
        small = QFont()
        if self.font_family:
            small.setFamily(self.font_family)
        small.setPointSize(max(7, self.font_size - 1))
        fm = QFontMetrics(font)
        sfm = QFontMetrics(small)
        p.fillRect(QRect(0, 0, w, h), self.bg_color)
        p.fillRect(pr.toRect(), QColor(248, 249, 252))
        y_cursor = self._MT_BASE
        if self.overall_title:
            tf = QFont()
            if self.font_family:
                tf.setFamily(self.font_family)
            tf.setPointSize(self.title_font_size)
            tf.setBold(True)
            p.setFont(tf)
            p.setPen(QPen(self.axis_color))
            p.drawText(
                0, y_cursor, w, self._TITLE_H,
                Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter,
                self.overall_title,
            )
            y_cursor += self._TITLE_H
        if self.subplot_title:
            stf = QFont()
            if self.font_family:
                stf.setFamily(self.font_family)
            stf.setPointSize(self.font_size)
            stf.setBold(True)
            p.setFont(stf)
            p.setPen(QPen(self.axis_color))
            p.drawText(
                self._ML, y_cursor, w - self._ML, self._SUB_H,
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                self.subplot_title,
            )
        p.setFont(font)
        p.save()
        p.translate(12, int(pr.center().y()))
        p.rotate(-90)
        p.setPen(QPen(self.axis_color))
        yw = fm.horizontalAdvance(self.ylabel)
        p.drawText(-yw // 2, fm.ascent(), self.ylabel)
        p.restore()
        p.setFont(small)
        y_ticks = self._nice_ticks(self._vy_min, self._vy_max, 5)
        for yv in y_ticks:
            _, py = self._to_px(0, yv, pr)
            if not (pr.top() - 1 <= py <= pr.bottom() + 1):
                continue
            if self.show_grid:
                p.setPen(QPen(QColor(215, 215, 225), 1, Qt.PenStyle.DotLine))
                p.drawLine(int(pr.left()), int(py), int(pr.right()), int(py))
            p.setPen(QPen(self.axis_color))
            lbl = f"{yv:.4g}"
            lw = sfm.horizontalAdvance(lbl)
            p.drawText(int(pr.left() - lw - 5), int(py + sfm.ascent() // 2), lbl)
        x_ticks = self._nice_ticks(self._vx_min, self._vx_max, 6)
        for xv in x_ticks:
            px_c, _ = self._to_px(xv, 0, pr)
            if not (pr.left() - 1 <= px_c <= pr.right() + 1):
                continue
            if self.show_grid:
                p.setPen(QPen(QColor(215, 215, 225), 1, Qt.PenStyle.DotLine))
                p.drawLine(int(px_c), int(pr.top()), int(px_c), int(pr.bottom()))
            if self.show_x_axis:
                p.setPen(QPen(self.axis_color))
                lbl = self.x_formatter(xv) if self.x_formatter else f"{xv:.4g}"
                lw = sfm.horizontalAdvance(lbl)
                p.drawText(int(px_c - lw / 2), int(pr.bottom() + sfm.height() + 3), lbl)
        p.setPen(QPen(QColor(90, 90, 90), 1))
        p.drawRect(pr.toRect())
        clip = pr.adjusted(1, 1, -1, -1)
        if clip.isValid():
            p.setClipRect(clip.toRect())
        for s in self.series:
            if len(s.x) == 0 or len(s.y) == 0:
                continue
            pen = QPen(s.color, s.width, _PEN_STYLE.get(s.style, Qt.PenStyle.SolidLine))
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            p.setPen(pen)
            path = QPainterPath()
            started = False
            for xv, yv in zip(s.x, s.y):
                if not (math.isfinite(xv) and math.isfinite(yv)):
                    started = False
                    continue
                cx_p, cy_p = self._to_px(xv, yv, pr)
                if not started:
                    path.moveTo(cx_p, cy_p)
                    started = True
                else:
                    path.lineTo(cx_p, cy_p)
            if started:
                p.drawPath(path)
        p.setClipping(False)
        visible = [s for s in self.series if s.label and not s.label.startswith("_")]
        if len(visible) > 1:
            p.setFont(small)
            lx = int(pr.right()) - 6
            ly = int(pr.top()) + 6
            for s in visible:
                tw = sfm.horizontalAdvance(s.label)
                bx = lx - tw - 26
                p.fillRect(bx - 3, ly - 1, tw + 32, sfm.height() + 2, QColor(255, 255, 255, 210))
                p.setPen(QPen(s.color, s.width))
                p.drawLine(bx, ly + sfm.height() // 2, bx + 18, ly + sfm.height() // 2)
                p.setPen(QPen(self.axis_color))
                p.drawText(bx + 22, ly + sfm.ascent(), s.label)
                ly += sfm.height() + 4
        if self._rb_origin is not None and self._rb_current is not None:
            rb = QRectF(self._rb_origin, self._rb_current).normalized()
            rb = rb.intersected(pr)
            if rb.width() > 2 and rb.height() > 2:
                p.setPen(QPen(QColor(80, 80, 80), 1, Qt.PenStyle.DashLine))
                p.setBrush(QColor(100, 100, 100, 40))
                p.drawRect(rb)
                p.setBrush(Qt.BrushStyle.NoBrush)


    def mousePressEvent(self, event):
        """Handle mouse press to start rubber-band zoom selection. Args: event (QMouseEvent)."""
        if event.button() == Qt.MouseButton.LeftButton:
            pr = self._plot_rect(self.width(), self.height())
            pos = event.position()
            if pr.contains(pos):
                self._rb_origin = QPointF(pos)
                self._rb_current = QPointF(pos)


    def mouseMoveEvent(self, event):
        """Handle mouse move to update rubber-band overlay. Args: event (QMouseEvent)."""
        if self._rb_origin is not None:
            self._rb_current = QPointF(event.position())
            self.update()


    def mouseReleaseEvent(self, event):
        """Handle mouse release to apply rubber-band zoom. Args: event (QMouseEvent)."""
        if self._rb_origin is None:
            return
        origin = self._rb_origin
        end = QPointF(event.position())
        self._rb_origin = None
        self._rb_current = None
        pr = self._plot_rect(self.width(), self.height())
        x0 = min(origin.x(), end.x())
        x1 = max(origin.x(), end.x())
        y0 = min(origin.y(), end.y())
        y1 = max(origin.y(), end.y())
        if x1 - x0 > 8 and y1 - y0 > 8:
            pw = max(1.0, pr.width())
            ph = max(1.0, pr.height())
            xr = self._vx_max - self._vx_min
            yr = self._vy_max - self._vy_min
            nx_min = self._vx_min + (x0 - pr.left()) / pw * xr
            nx_max = self._vx_min + (x1 - pr.left()) / pw * xr
            ny_min = self._vy_min + (pr.bottom() - y1) / ph * yr
            ny_max = self._vy_min + (pr.bottom() - y0) / ph * yr
            if nx_max > nx_min and ny_max > ny_min:
                self._vx_min, self._vx_max = nx_min, nx_max
                self._vy_min, self._vy_max = ny_min, ny_max
        self.update()


    def mouseDoubleClickEvent(self, event):
        """Double-click resets zoom to full data range. Args: event (QMouseEvent)."""
        self.reset_view()


    def set_x_view_range(self, lo: float, hi: float):
        """Manually set the X-axis viewport range. Args: lo (float), hi (float)."""
        if math.isfinite(lo) and math.isfinite(hi) and hi > lo:
            self._vx_min, self._vx_max = lo, hi
            self.update()


    def set_y_view_range(self, lo: float, hi: float):
        """Manually set the Y-axis viewport range. Args: lo (float), hi (float)."""
        if math.isfinite(lo) and math.isfinite(hi) and hi > lo:
            self._vy_min, self._vy_max = lo, hi
            self.update()


class MultiChartWidget(QWidget):
    """Stacks ChartWidgets vertically with a shared overall title drawn inside the first chart."""

    def __init__(self, parent = None):
        """Initialize the multi-chart container. Args: parent (QWidget, optional)."""
        super().__init__(parent)
        self.charts: List[ChartWidget] = []
        self._overall_title = ""
        self._overall_title_font_size = 13
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(2)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)


    def set_overall_title(self, text: str, font_size: int = 13):
        """Set the overall title drawn in the first chart. Args: text (str), font_size (int)."""
        self._overall_title = text
        self._overall_title_font_size = font_size
        for i, c in enumerate(self.charts):
            c.overall_title = text if i == 0 else ""
            c.title_font_size = font_size
            c.update()


    def set_font_size(self, size: int):
        """Set font size for all charts. Args: size (int)."""
        for c in self.charts:
            c.font_size = size
            c.update()


    def set_grid(self, on: bool):
        """Toggle grid visibility for all charts. Args: on (bool)."""
        for c in self.charts:
            c.show_grid = on
            c.update()


    def reset_view(self):
        """Reset zoom on all charts to full data range."""
        for c in self.charts:
            c.reset_view()


    def set_font_family(self, family: str):
        """Set font family for all charts. Args: family (str)."""
        for c in self.charts:
            c.font_family = family
            c.update()


    def set_font_color(self, color: QColor):
        """Set axis/label text color for all charts. Args: color (QColor)."""
        for c in self.charts:
            c.axis_color = color
            c.update()


    def set_chart_height_weight(self, index: int, weight: int):
        """Set relative height of chart at index. Args: index (int), weight (int)."""
        if 0 <= index < self._layout.count():
            self._layout.setStretch(index, max(1, weight))


    def clear(self):
        """Remove all charts from the widget."""
        for c in self.charts:
            c.deleteLater()
        self.charts.clear()
        while self._layout.count():
            item = self._layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()


    def load_results(self, results: dict, variables: List[str], t_start: float,
                     variable_meta: dict, zone_colors: List[str]):
        """Populate ChartWidgets from a simulation results dict. Args: results (dict), variables (List[str]), t_start (float), variable_meta (dict), zone_colors (List[str])."""
        import torch
        self.clear()
        try:
            time_vec = results["t"][0, :].detach().cpu().numpy().flatten()
        except Exception:
            return

        def _fmt(xv: float) -> str:
            """Format a time value as a 12-hour clock string. Args: xv (float). Returns: str."""
            try:
                tod = (t_start + xv) % 86400
                h = int(tod / 3600)
                h12 = ((h - 1) % 12) + 1
                return f"{h12} {'AM' if h < 12 else 'PM'}"
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
            chart.x_formatter = _fmt
            if i == 0 and self._overall_title:
                chart.overall_title = self._overall_title
                chart.title_font_size = self._overall_title_font_size
            try:
                data = results.get(var)
                if isinstance(data, torch.Tensor) and data.ndim == 3:
                    n = min(len(time_vec), data.shape[1])
                    n_feat = data.shape[2]
                    series = []
                    for feat in range(n_feat):
                        y = data[0, :n, feat].detach().cpu().numpy().copy()
                        if scale is not None:
                            y = scale(y)
                        series.append(LineSeries(
                            x = time_vec[:n].copy(),
                            y = y,
                            label = f"Zone {feat + 1}" if n_feat > 1 else label,
                            color = QColor(zone_colors[feat % len(zone_colors)]),
                            width = 2,
                            style = "Solid",
                        ))
                    chart.set_series(series)
            except Exception:
                pass
            self.charts.append(chart)
            self._layout.addWidget(chart, 1)


    def save_to_file(self, path: str, chart_width: int = 1200, chart_height: int = 240):
        """Render all charts to a PNG or JPEG file. Args: path (str), chart_width (int), chart_height (int)."""
        if not self.charts:
            return
        total_h = chart_height * len(self.charts)
        canvas = QPixmap(max(1, chart_width), max(1, total_h))
        canvas.fill(QColor(255, 255, 255))
        p = QPainter(canvas)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        y = 0
        for chart in self.charts:
            px = chart.render_to_pixmap(chart_width, chart_height)
            p.drawPixmap(0, y, px)
            y += chart_height
        p.end()
        canvas.save(path)
