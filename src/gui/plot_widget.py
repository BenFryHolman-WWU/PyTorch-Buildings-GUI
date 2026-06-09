"""Custom plotting widgets for simulation result visualization."""

import math
from dataclasses import dataclass, field
from typing import Callable, List, Optional

import numpy as np

from PyQt6.QtCore import Qt, QMimeData, QRectF, QRect, QPointF, QPoint, pyqtSignal
from PyQt6.QtGui import (
    QColor, QDrag, QFont, QFontMetrics, QPainter, QPainterPath, QPen, QPixmap,
)
from PyQt6.QtWidgets import (
    QAbstractItemView, QLabel, QListWidget, QListWidgetItem,
    QSizePolicy, QVBoxLayout, QWidget,
)


STYLE_OPTIONS = ["Solid", "Dashed", "Dotted", "Dash-dot"]

_PEN_STYLE: dict = {
    "Solid":    Qt.PenStyle.SolidLine,
    "Dashed":   Qt.PenStyle.DashLine,
    "Dotted":   Qt.PenStyle.DotLine,
    "Dash-dot": Qt.PenStyle.DashDotLine,
}


def _padded_range(values: np.ndarray, fraction: float = 0.05, min_pad: float = 0.5):
    """
    Summary: Padded range.
    Args: fraction, min_pad
    Returns: Return the computed value.
    """
    values = np.asarray(values, dtype=float)
    values = values[np.isfinite(values)]
    if len(values) == 0:
        return 0.0, 1.0
    lo = float(values.min())
    hi = float(values.max())
    span = hi - lo
    pad = max(span * fraction, min_pad)
    if span <= 0:
        return lo - pad, hi + pad
    return lo - pad, hi + pad


def _time_domain_with_margin(time_vec: np.ndarray):
    """
    Summary: Time domain with margin.
    Args: time_vec
    Returns: Return the computed value.
    """
    time_vec = np.asarray(time_vec, dtype=float)
    time_vec = time_vec[np.isfinite(time_vec)]
    if len(time_vec) == 0:
        return 0.0, 1.0
    lo = float(time_vec.min())
    hi = float(time_vec.max())
    if len(time_vec) > 1:
        diffs = np.diff(np.sort(np.unique(time_vec)))
        diffs = diffs[diffs > 0]
        pad = float(np.median(diffs)) * 0.5 if len(diffs) else max((hi - lo) * 0.05, 0.5)
    else:
        pad = 0.5
    if hi <= lo:
        hi = lo
    return lo - pad, hi + pad


@dataclass
class LineSeries:
    x: np.ndarray
    y: np.ndarray
    label: str = ""
    color: QColor = field(default_factory=lambda: QColor("#1f77b4"))
    width: int = 2
    style: str = "Solid"
    opacity: float = 1.0

    @property
    def visible(self) -> bool:
        return self.opacity > 0.0


class ChartWidget(QWidget):

    _ML = 72
    _MR = 14
    _TITLE_H = 30
    _SUB_H = 22
    _MT_BASE = 6
    _MB_X = 40
    _MB_NOX = 6
    _DRAG_H = 14

    def __init__(self, ylabel: str = "", show_x_axis: bool = False, parent = None):
        """
        Summary: Init.
        Args: ylabel, show_x_axis
        """
        super().__init__(parent)
        self.series: List[LineSeries] = []
        self.ylabel = ylabel
        self.value_label, self.value_unit = self._split_axis_label(ylabel)
        self.temperature_units_enabled = False
        self._manual_y_range = False
        self.subplot_title = ""
        self.overall_title = ""
        self.title_font_size = 13
        self.show_x_axis = show_x_axis
        self.show_grid = True
        self.font_size = 9
        self.font_family: str = ""
        self.axis_color: QColor = QColor(55, 65, 95)
        self.bg_color = QColor(240, 242, 248)
        self.x_formatter: Optional[Callable[[float], str]] = None
        self._x_min = self._x_max = 0.0
        self._y_min = self._y_max = 1.0
        self._vx_min = self._vx_max = 0.0
        self._vy_min = self._vy_max = 1.0
        self._rb_origin: Optional[QPointF] = None
        self._rb_current: Optional[QPointF] = None
        self.var_key: str = ""
        self.remove_callback: Optional[Callable] = None
        self.grid_toggle_callback: Optional[Callable] = None
        self._close_btn_rect: Optional[QRect] = None
        self._grid_btn_rect: Optional[QRect] = None
        self._drag_press_pos: Optional[QPoint] = None
        self._hover_handle: bool = False
        self._hover_sample: Optional[dict] = None
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumHeight(100)
        self.setCursor(Qt.CursorShape.CrossCursor)
        self.setMouseTracking(True)


    def _mt(self) -> int:
        h = self._MT_BASE
        if self.overall_title:
            h += self._TITLE_H
        if self.subplot_title:
            h += self._SUB_H
        return h


    def _mb(self) -> int:
        return self._MB_X if self.show_x_axis else self._MB_NOX


    @staticmethod
    def _split_axis_label(ylabel: str):
        text = (ylabel or "").strip()
        if text.endswith("]") and "[" in text:
            label, unit = text.rsplit("[", 1)
            return label.strip(), unit[:-1].strip()
        return text, ""


    def set_value_axis(self, label: str, unit: str = "", temperature_units_enabled: bool = False):
        self.value_label = label or self.value_label or self.ylabel
        self.value_unit = unit or ""
        self.temperature_units_enabled = bool(temperature_units_enabled)
        self._sync_ylabel()


    def _sync_ylabel(self):
        self.ylabel = f"{self.value_label} [{self.value_unit}]" if self.value_unit else self.value_label


    def set_temperature_unit(self, unit: str):
        if not self.temperature_units_enabled or unit not in {"C", "K"} or unit == self.value_unit:
            return
        delta = 273.15 if self.value_unit == "C" and unit == "K" else -273.15
        for series in self.series:
            series.y = series.y + delta
        self._y_min += delta
        self._y_max += delta
        self._vy_min += delta
        self._vy_max += delta
        self.value_unit = unit
        self._sync_ylabel()
        self._hover_sample = None
        self.update()


    def set_y_axis_range(self, y_min: float, y_max: float):
        if not (math.isfinite(y_min) and math.isfinite(y_max)) or y_max <= y_min:
            return False
        self._manual_y_range = True
        self._y_min = float(y_min)
        self._y_max = float(y_max)
        self._vy_min = self._y_min
        self._vy_max = self._y_max
        self._hover_sample = None
        self.update()
        return True


    def auto_fit_y_axis(self):
        self._manual_y_range = False
        self.refit_y_to_visible_series()
        self.update()


    def _plot_rect(self, w: int, h: int) -> QRectF:
        return QRectF(
            self._ML, self._mt(),
            max(10.0, w - self._ML - self._MR),
            max(10.0, h - self._mt() - self._mb()),
        )


    def set_series(self, series: List[LineSeries]):
        self.series = series
        self._hover_sample = None
        self._fit_all()
        self.update()


    def _fit_all(self):
        """Summary: Fit all."""
        valid = [s for s in self.series if s.visible and len(s.x) > 0 and len(s.y) > 0]
        if not valid:
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
            self._x_min, self._x_max = _time_domain_with_margin(xs)
            self._y_min, self._y_max = _padded_range(ys)
        except Exception:
            return
        self._manual_y_range = False
        self._vx_min, self._vx_max = self._x_min, self._x_max
        self._vy_min, self._vy_max = self._y_min, self._y_max


    def refit_y_to_visible_series(self):
        """Summary: Refit y to visible series."""
        if self._manual_y_range:
            self._vy_min, self._vy_max = self._y_min, self._y_max
            return
        valid = [s for s in self.series if s.visible and len(s.y) > 0]
        if not valid:
            valid = [s for s in self.series if len(s.y) > 0]
        if not valid:
            return
        try:
            ys = np.concatenate([s.y for s in valid])
            self._y_min, self._y_max = _padded_range(ys)
            self._vy_min, self._vy_max = self._y_min, self._y_max
        except Exception:
            return


    def reset_view(self):
        self._vx_min, self._vx_max = self._x_min, self._x_max
        self._vy_min, self._vy_max = self._y_min, self._y_max
        self.update()


    def _to_px(self, xv: float, yv: float, pr: QRectF):
        xr = self._vx_max - self._vx_min or 1.0
        yr = self._vy_max - self._vy_min or 1.0
        px = pr.left() + (xv - self._vx_min) / xr * pr.width()
        py = pr.bottom() - (yv - self._vy_min) / yr * pr.height()
        return px, py


    def _nearest_sample(self, pos: QPointF, pr: QRectF):
        """
        Summary: Nearest sample.
        Args: pos, pr
        Returns: Return the computed value.
        """
        if not pr.contains(pos):
            return None
        nearest = None
        best_dist = float("inf")
        for series_index, series in enumerate(self.series):
            if not series.visible:
                continue
            for sample_index, (xv, yv) in enumerate(zip(series.x, series.y)):
                if not (math.isfinite(float(xv)) and math.isfinite(float(yv))):
                    continue
                px, py = self._to_px(float(xv), float(yv), pr)
                if not (pr.left() - 1 <= px <= pr.right() + 1 and pr.top() - 1 <= py <= pr.bottom() + 1):
                    continue
                dist = math.hypot(px - pos.x(), py - pos.y())
                if dist < best_dist:
                    best_dist = dist
                    nearest = {
                        "series_index": series_index,
                        "sample_index": sample_index,
                        "series": series,
                        "x": float(xv),
                        "y": float(yv),
                        "px": float(px),
                        "py": float(py),
                        "distance": float(dist),
                    }
        return nearest


    def _format_hover_x(self, x: float) -> str:
        if self.x_formatter is not None:
            formatted = self.x_formatter(x)
            if formatted:
                return formatted
        return f"{x:.4g}"


    def _format_hover_y(self, y: float) -> str:
        return f"{y:.4g}"


    @staticmethod
    def _nice_ticks(lo: float, hi: float, n: int = 5) -> List[float]:
        """
        Summary: Nice ticks.
        Args: lo, hi, n
        Returns: Return the computed value.
        """
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
        if self.width() < 4 or self.height() < 4:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        self._draw(p, self.width(), self.height())
        p.end()


    def render_to_pixmap(self, w: int, h: int, scale: float = 1.0) -> QPixmap:
        """
        Summary: Render to pixmap.
        Args: scale
        Returns: Return the computed value.
        """
        phys_w = max(1, int(w * scale))
        phys_h = max(1, int(h * scale))
        px = QPixmap(phys_w, phys_h)
        px.setDevicePixelRatio(scale)
        px.fill(self.bg_color)
        p = QPainter(px)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        self._draw(p, w, h)
        p.end()
        return px


    def _draw(self, p: QPainter, w: int, h: int):
        """
        Summary: Draw.
        Args: p
        """
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
        p.fillRect(pr.toRect(), QColor(255, 255, 255))


        y_cursor = self._MT_BASE
        if self.overall_title:
            tf = QFont()
            if self.font_family:
                tf.setFamily(self.font_family)
            tf.setPointSize(self.title_font_size)
            tf.setBold(True)
            p.setFont(tf)
            p.setPen(QPen(QColor(28, 36, 60)))
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
            p.fillRect(self._ML, y_cursor + 3, 3, self._SUB_H - 6, QColor(74, 127, 193))
            p.setFont(stf)
            p.setPen(QPen(self.axis_color))
            p.drawText(
                self._ML + 8, y_cursor, w - self._ML - 8, self._SUB_H,
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
                p.setPen(QPen(QColor(218, 222, 238), 1, Qt.PenStyle.SolidLine))
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
                p.setPen(QPen(QColor(218, 222, 238), 1, Qt.PenStyle.SolidLine))
                p.drawLine(int(px_c), int(pr.top()), int(px_c), int(pr.bottom()))
            if self.show_x_axis:
                p.setPen(QPen(self.axis_color))
                lbl = self.x_formatter(xv) if self.x_formatter else f"{xv:.4g}"
                lw = sfm.horizontalAdvance(lbl)
                p.drawText(int(px_c - lw / 2), int(pr.bottom() + sfm.height() + 3), lbl)


        p.setPen(QPen(QColor(155, 165, 195), 1))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(pr.adjusted(0, 0, -1, -1), 2, 2)


        clip = pr.adjusted(1, 1, -1, -1)
        if clip.isValid():
            p.setClipRect(clip.toRect())
        for s in self.series:
            if not s.visible or len(s.x) == 0 or len(s.y) == 0:
                continue
            color = QColor(s.color)
            color.setAlphaF(max(0.0, min(1.0, s.opacity)))
            pen = QPen(color, s.width, _PEN_STYLE.get(s.style, Qt.PenStyle.SolidLine))
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


        if self._hover_sample is not None and self._rb_origin is None:
            sample = self._hover_sample
            sx = sample["px"]
            sy = sample["py"]
            series = sample["series"]
            p.setPen(QPen(QColor(62, 72, 102, 135), 1, Qt.PenStyle.DashLine))
            p.drawLine(int(sx), int(pr.top()), int(sx), int(pr.bottom()))
            p.drawLine(int(pr.left()), int(sy), int(pr.right()), int(sy))
            p.setBrush(QColor(255, 255, 255))
            p.setPen(QPen(series.color, 2))
            p.drawEllipse(QPointF(sx, sy), 4.5, 4.5)

            p.setFont(small)
            title = series.label or self.ylabel or "Series"
            lines = [
                title,
                f"x: {self._format_hover_x(sample['x'])}",
                f"y: {self._format_hover_y(sample['y'])}",
            ]
            text_w = max(sfm.horizontalAdvance(line) for line in lines)
            row_h = sfm.height()
            card_w = text_w + 18
            card_h = row_h * len(lines) + 12
            card_x = sx + 12
            card_y = sy - card_h - 10
            if card_x + card_w > pr.right() - 4:
                card_x = sx - card_w - 12
            if card_y < pr.top() + 4:
                card_y = sy + 12
            card_x = max(pr.left() + 4, min(card_x, pr.right() - card_w - 4))
            card_y = max(pr.top() + 4, min(card_y, pr.bottom() - card_h - 4))
            card_rect = QRectF(card_x, card_y, card_w, card_h)
            card_path = QPainterPath()
            card_path.addRoundedRect(card_rect, 5, 5)
            p.setBrush(QColor(255, 255, 255, 235))
            p.setPen(QPen(QColor(184, 193, 216), 1))
            p.drawPath(card_path)
            ty = card_y + 6
            for idx, line in enumerate(lines):
                p.setPen(QPen(series.color if idx == 0 else QColor(35, 42, 68)))
                p.drawText(int(card_x + 9), int(ty + sfm.ascent()), line)
                ty += row_h


        visible = [s for s in self.series if s.visible and s.label and not s.label.startswith("_")]
        if len(visible) > 1:
            p.setFont(small)
            row_h = sfm.height() + 5
            pad_x, pad_y = 8, 6
            max_tw = max(sfm.horizontalAdvance(s.label) for s in visible)
            card_w = max_tw + 34 + pad_x * 2
            card_h = row_h * len(visible) + pad_y * 2 - 3
            card_x = int(pr.right()) - card_w - 8
            card_y = int(pr.top()) + 8
            legend_path = QPainterPath()
            legend_path.addRoundedRect(QRectF(card_x, card_y, card_w, card_h), 5, 5)
            p.setBrush(QColor(255, 255, 255, 225))
            p.setPen(QPen(QColor(195, 200, 218), 1))
            p.drawPath(legend_path)
            p.setBrush(Qt.BrushStyle.NoBrush)
            ly = card_y + pad_y
            lx = card_x + pad_x
            for s in visible:
                color = QColor(s.color)
                color.setAlphaF(max(0.0, min(1.0, s.opacity)))
                p.setPen(QPen(color, s.width + 1, _PEN_STYLE.get(s.style, Qt.PenStyle.SolidLine)))
                p.drawLine(lx, ly + sfm.height() // 2, lx + 18, ly + sfm.height() // 2)
                p.setPen(QPen(QColor(35, 42, 68)))
                p.drawText(lx + 22, ly + sfm.ascent(), s.label)
                ly += row_h


        p.setClipping(False)
        if self._hover_handle:
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(72, 120, 200, 38))
            p.drawRect(QRectF(0, 0, w, self._DRAG_H))


        if self.grid_toggle_callback is not None:
            bs = 15
            bx = 5
            by = 4
            self._grid_btn_rect = QRect(bx, by, bs, bs)
            fill = QColor(72, 120, 200, 215) if self.show_grid else QColor(190, 196, 220, 200)
            stroke = QColor(255, 255, 255, 230) if self.show_grid else QColor(60, 70, 110)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(fill)
            p.drawEllipse(QRectF(bx, by, bs, bs))
            grid_pen = QPen(stroke, 1.1)
            grid_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            p.setPen(grid_pen)
            for offset in (5, 10):
                p.drawLine(bx + offset, by + 4, bx + offset, by + bs - 4)
                p.drawLine(bx + 4, by + offset, bx + bs - 4, by + offset)
        else:
            self._grid_btn_rect = None


        if self.remove_callback is not None:
            bs = 15
            bx = w - bs - 5
            by = 4
            self._close_btn_rect = QRect(bx, by, bs, bs)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(190, 196, 220, 200))
            p.drawEllipse(QRectF(bx, by, bs, bs))
            xpen = QPen(QColor(60, 70, 110), 1.5)
            xpen.setCapStyle(Qt.PenCapStyle.RoundCap)
            p.setPen(xpen)
            m = 4
            p.drawLine(bx + m, by + m, bx + bs - m, by + bs - m)
            p.drawLine(bx + bs - m, by + m, bx + m, by + bs - m)


        if self._rb_origin is not None and self._rb_current is not None:
            rb = QRectF(self._rb_origin, self._rb_current).normalized()
            rb = rb.intersected(pr)
            if rb.width() > 2 and rb.height() > 2:
                p.setPen(QPen(QColor(74, 127, 193), 1, Qt.PenStyle.DashLine))
                p.setBrush(QColor(74, 127, 193, 30))
                p.drawRect(rb)
                p.setBrush(Qt.BrushStyle.NoBrush)


    def _drag_zone(self) -> QRect:
        return QRect(0, 0, self.width(), self._DRAG_H)

    def _start_reorder_drag(self):
        """Summary: Start reorder drag."""
        parent = self.parent()
        if not (hasattr(parent, "charts") and hasattr(parent, "charts_reordered")):
            return
        try:
            idx = parent.charts.index(self)
        except ValueError:
            return
        mime = QMimeData()
        mime.setText(f"chartreorder:{idx}")
        drag = QDrag(self)
        drag.setMimeData(mime)
        pm = QPixmap(max(1, self.width()), 28)
        pm.fill(QColor(210, 216, 235, 200))
        drag.setPixmap(pm)
        drag.setHotSpot(QPoint(pm.width() // 2, pm.height() // 2))
        drag.exec(Qt.DropAction.MoveAction)

    def mousePressEvent(self, event):
        """Summary: Mousepressevent."""
        if event.button() == Qt.MouseButton.LeftButton:
            pos_pt = event.position().toPoint()
            if self.remove_callback is not None and self._close_btn_rect is not None:
                if self._close_btn_rect.contains(pos_pt):
                    self.remove_callback()
                    return
            if self.grid_toggle_callback is not None and self._grid_btn_rect is not None:
                if self._grid_btn_rect.contains(pos_pt):
                    self.grid_toggle_callback()
                    return
            if self._drag_zone().contains(pos_pt):
                self._drag_press_pos = pos_pt
                return
            pr = self._plot_rect(self.width(), self.height())
            pos = event.position()
            if pr.contains(pos):
                self._rb_origin = QPointF(pos)
                self._rb_current = QPointF(pos)


    def mouseMoveEvent(self, event):
        """Summary: Mousemoveevent."""
        pos_pt = event.position().toPoint()
        if self._drag_press_pos is not None:
            if (pos_pt - self._drag_press_pos).manhattanLength() > 6:
                self._drag_press_pos = None
                self._start_reorder_drag()
            return
        if self._rb_origin is not None:
            self._rb_current = QPointF(event.position())
            if self._hover_sample is not None:
                self._hover_sample = None
            self.update()
            return
        in_handle = self._drag_zone().contains(pos_pt)
        pr = self._plot_rect(self.width(), self.height())
        next_hover = None if in_handle else self._nearest_sample(QPointF(event.position()), pr)
        hover_changed = (
            (next_hover is None) != (self._hover_sample is None)
            or (
                next_hover is not None
                and self._hover_sample is not None
                and (
                    next_hover["series_index"] != self._hover_sample["series_index"]
                    or next_hover["sample_index"] != self._hover_sample["sample_index"]
                )
            )
        )
        self._hover_sample = next_hover
        if in_handle != self._hover_handle:
            self._hover_handle = in_handle
            hover_changed = True
        self.setCursor(Qt.CursorShape.SizeVerCursor if in_handle else Qt.CursorShape.CrossCursor)
        if hover_changed:
            self.update()


    def mouseReleaseEvent(self, event):
        """Summary: Mousereleaseevent."""
        self._drag_press_pos = None
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


    def leaveEvent(self, event):
        changed = False
        if self._hover_handle:
            self._hover_handle = False
            changed = True
        if self._hover_sample is not None:
            self._hover_sample = None
            changed = True
        if changed:
            self.update()

    def mouseDoubleClickEvent(self, event):
        self.reset_view()


    def set_x_view_range(self, lo: float, hi: float):
        if math.isfinite(lo) and math.isfinite(hi) and hi > lo:
            self._vx_min, self._vx_max = lo, hi
            self.update()


    def set_y_view_range(self, lo: float, hi: float):
        if math.isfinite(lo) and math.isfinite(hi) and hi > lo:
            self._vy_min, self._vy_max = lo, hi
            self.update()


from .plot_containers import MultiChartWidget, VarListWidget
