# Author: Leon3DVFX
# License: MIT

import math

from PySide6 import QtCore, QtGui, QtWidgets

# Действие для радиального меню
class RadialMenuItem(QtGui.QAction):
    def __init__(
        self,
        parent=None,
        icon=None,
        text="",
        triggered=None,
        data=None,
        enabled=True,
    ):
        super().__init__(parent)
        if icon is not None:
            self.setIcon(_make_icon(icon))
        if text:
            self.setText(text)
        if data is not None:
            self.setData(data)
        self.setEnabled(enabled)
        if triggered is not None:
            self.triggered.connect(lambda checked=False: triggered())

# Основное радиальное меню
class RadialMenu(QtWidgets.QWidget):
    triggered = QtCore.Signal(QtGui.QAction)
    hovered = QtCore.Signal(QtGui.QAction)

    def __init__(
        self,
        parent=None,
        radius1=50,
        radius2=100,
        num_items=6,
        sector=None,
        items_icons=None,
        items_actions=None,
        animation_duration=140,
        selection_animation_duration=220,
        highlight_color=None,
        take_focus=True,
    ):
        super().__init__(parent)

        self.setWindowFlags(
            QtCore.Qt.WindowType.Popup
            | QtCore.Qt.WindowType.FramelessWindowHint
            | QtCore.Qt.WindowType.NoDropShadowWindowHint
        )
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMouseTracking(True)
        self._take_focus = bool(take_focus)
        self._update_focus_policy()

        self.radius1, self.radius2 = sorted((int(radius1), int(radius2)))
        self.radius1 = max(0, self.radius1)
        self.radius2 = max(self.radius1 + 1, self.radius2)
        self.num_items = max(1, int(num_items))
        self.sector = sector or (0.0, 360.0)
        self.start_angle, self.sector_span = _normalize_sector(self.sector)

        self.padding = 8
        self.gap_angle = 2.0
        self.icon_size = QtCore.QSize(28, 28)
        self.text_margin = 4
        self.animation_duration = max(0, int(animation_duration))
        self.selection_animation_duration = max(0, int(selection_animation_duration))

        self.bg_color = QtGui.QColor(34, 36, 42, 225)
        self.hover_color = _make_color(highlight_color, QtGui.QColor(80, 135, 220, 240))
        self.disabled_color = QtGui.QColor(55, 56, 62, 130)
        self.border_color = QtGui.QColor(255, 255, 255, 35)
        self.text_color = QtGui.QColor(235, 238, 245)
        self.disabled_text_color = QtGui.QColor(170, 174, 184, 125)

        self._actions = []
        self._hover_index = -1
        self._pressed_index = -1
        self._popup_scale = 1.0
        self._selection_progress = 0.0
        self._selected_index = -1
        self._pending_action = None
        self._show_animation = QtCore.QPropertyAnimation(self, b"popupScale", self)
        self._show_animation.setEasingCurve(QtCore.QEasingCurve.Type.OutCubic)
        self._selection_animation = QtCore.QPropertyAnimation(self, b"selectionProgress", self)
        self._selection_animation.setEasingCurve(QtCore.QEasingCurve.Type.InOutCubic)
        self._selection_animation.finished.connect(self._finish_selection_animation)

        icons = list(items_icons or [])
        actions = list(items_actions or [])

        for index, action in enumerate(actions):
            icon = icons[index] if index < len(icons) else None
            self.addAction(action, icon=icon)

        if icons and not actions:
            for icon in icons:
                self.addItem(icon=icon)

        self.num_items = max(self.num_items, len(self._actions), len(icons))
        self._sync_size()

    def popupScale(self):
        return self._popup_scale

    def setPopupScale(self, scale):
        self._popup_scale = max(0.0, min(1.0, float(scale)))
        self.update()

    popupScale = QtCore.Property(float, popupScale, setPopupScale)

    def selectionProgress(self):
        return self._selection_progress

    def setSelectionProgress(self, progress):
        self._selection_progress = max(0.0, min(1.0, float(progress)))
        self.update()

    selectionProgress = QtCore.Property(float, selectionProgress, setSelectionProgress)

    def takeFocus(self):
        return self._take_focus

    def setTakeFocus(self, take_focus):
        self._take_focus = bool(take_focus)
        self._update_focus_policy()

    takeFocus = QtCore.Property(bool, takeFocus, setTakeFocus)

    def highlightColor(self):
        return QtGui.QColor(self.hover_color)

    def setHighlightColor(self, color):
        self.hover_color = _make_color(color, self.hover_color)
        self.update()

    highlightColor = QtCore.Property(QtGui.QColor, highlightColor, setHighlightColor)

    def chooseHighlightColor(self, parent=None):
        color = QtWidgets.QColorDialog.getColor(
            self.hover_color,
            parent or self,
            "Highlight color",
            QtWidgets.QColorDialog.ColorDialogOption.ShowAlphaChannel,
        )
        if color.isValid():
            self.setHighlightColor(color)
            return color
        return None

    def choose_highlight_color(self, parent=None):
        return self.chooseHighlightColor(parent)

    def actions(self):
        return list(self._actions)

    def addAction(self, action, icon=None, callback=None):
        if isinstance(action, QtGui.QAction):
            radial_action = action
            if icon is not None:
                radial_action.setIcon(_make_icon(icon))
            if callback is not None:
                radial_action.triggered.connect(lambda checked=False: callback())
        elif callable(action):
            radial_action = RadialMenuItem(self, icon=icon, triggered=action)
        else:
            radial_action = RadialMenuItem(self, icon=icon, text=str(action))
            if callback is not None:
                radial_action.triggered.connect(lambda checked=False: callback())

        if radial_action.parent() is None:
            radial_action.setParent(self)

        if radial_action not in self._actions:
            self._actions.append(radial_action)
            super().addAction(radial_action)

        self.num_items = max(self.num_items, len(self._actions))
        self.update()
        return radial_action

    def addItem(self, text="", icon=None, callback=None, data=None, enabled=True):
        action = RadialMenuItem(
            self,
            icon=icon,
            text=text,
            triggered=callback,
            data=data,
            enabled=enabled,
        )
        return self.addAction(action)

    def add_item(self, text="", icon=None, callback=None, data=None, enabled=True):
        return self.addItem(text, icon, callback, data, enabled)

    def add_action(self, action, icon=None, callback=None):
        return self.addAction(action, icon, callback)

    def clear(self):
        for action in self._actions:
            super().removeAction(action)
            action.setParent(None)
        self._actions.clear()
        self._hover_index = -1
        self._pressed_index = -1
        self._selected_index = -1
        self._pending_action = None
        self.setSelectionProgress(0.0)
        self.update()

    def show_at(self, global_pos):
        if not isinstance(global_pos, QtCore.QPoint):
            global_pos = QtCore.QPoint(*global_pos)
        self._sync_size()
        center = QtCore.QPoint(self.width() // 2, self.height() // 2)
        self.move(global_pos - center)
        self._hover_index = -1
        self._pressed_index = -1
        self._show_animation.stop()
        self._selection_animation.stop()
        self._selected_index = -1
        self._pending_action = None
        self.setSelectionProgress(0.0)
        self.setPopupScale(0.0 if self.animation_duration else 1.0)
        self.show()
        self.raise_()
        if self._take_focus:
            self.activateWindow()
            self.setFocus(QtCore.Qt.FocusReason.PopupFocusReason)
        self._start_show_animation()

    def popup(self, global_pos):
        self.show_at(global_pos)

    def actionAt(self, pos, enabled_only=False):
        index = self._index_at(pos)
        if 0 <= index < len(self._actions):
            action = self._actions[index]
            if enabled_only and not action.isEnabled():
                return None
            return action
        return None

    def setItemEnabled(self, item, enabled):
        action = self._action_from_item(item)
        if action is None:
            return False
        action.setEnabled(enabled)
        self.update()
        return True

    def set_item_enabled(self, item, enabled):
        return self.setItemEnabled(item, enabled)

    def set_highlight_color(self, color):
        self.setHighlightColor(color)

    def sizeHint(self):
        side = (self.radius2 + self.padding) * 2
        return QtCore.QSize(side, side)

    def paintEvent(self, event):
        del event
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)

        center = self._center()
        if self._popup_scale <= 0.001:
            return

        painter.translate(center)
        painter.scale(self._popup_scale, self._popup_scale)
        painter.translate(-center)

        outer_rect = QtCore.QRectF(
            center.x() - self.radius2,
            center.y() - self.radius2,
            self.radius2 * 2,
            self.radius2 * 2,
        )
        inner_rect = QtCore.QRectF(
            center.x() - self.radius1,
            center.y() - self.radius1,
            self.radius1 * 2,
            self.radius1 * 2,
        )

        painter.setPen(QtGui.QPen(self.border_color, 1.0))

        for index in range(self.num_items):
            action = self._actions[index] if index < len(self._actions) else None
            slot_start, slot_span = self._slot_angles(index)
            path = self._sector_path(outer_rect, inner_rect, slot_start, slot_span)
            item_center = self._slot_center_point(center, slot_start, slot_span)
            item_scale = self._item_selection_scale(index)
            if item_scale <= 0.001:
                continue

            enabled = action is not None and action.isEnabled()
            if not enabled:
                fill_color = QtGui.QColor(self.disabled_color)
            elif index == self._hover_index:
                fill_color = QtGui.QColor(self.hover_color)
            else:
                fill_color = QtGui.QColor(self.bg_color)

            if self._is_selection_active() and index == self._selected_index:
                fill_color = self._selection_flicker_color(fill_color)

            painter.save()
            painter.translate(item_center)
            painter.scale(item_scale, item_scale)
            painter.translate(-item_center)
            painter.setOpacity(self._item_selection_opacity(index))
            painter.setBrush(fill_color)
            painter.drawPath(path)

            if action is not None:
                self._paint_action(painter, action, center, slot_start, slot_span)
            painter.restore()

    def mouseMoveEvent(self, event):
        if self._is_selection_active():
            event.accept()
            return
        index = self._selectable_index_at(event.position().toPoint())
        if index != self._hover_index:
            self._hover_index = index
            action = self.actionAt(event.position().toPoint(), enabled_only=True)
            if action is not None:
                self.hovered.emit(action)
                if action.toolTip():
                    QtWidgets.QToolTip.showText(event.globalPosition().toPoint(), action.toolTip(), self)
            else:
                QtWidgets.QToolTip.hideText()
            self.update()
        super().mouseMoveEvent(event)

    def mousePressEvent(self, event):
        if self._is_selection_active():
            event.accept()
            return
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            self._pressed_index = self._selectable_index_at(event.position().toPoint())
            event.accept()
            return
        if event.button() == QtCore.Qt.MouseButton.RightButton:
            self._show_animation.stop()
            self._cancel_selection_animation()
            self.hide()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if self._is_selection_active():
            event.accept()
            return
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            index = self._selectable_index_at(event.position().toPoint())
            action = self.actionAt(event.position().toPoint(), enabled_only=True)
            if index == self._pressed_index and action is not None and action.isEnabled():
                self._start_selection_animation(index, action)
            self._pressed_index = -1
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def leaveEvent(self, event):
        if self._is_selection_active():
            event.accept()
            return
        self._hover_index = -1
        self.update()
        super().leaveEvent(event)

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key.Key_Escape:
            self._show_animation.stop()
            self._cancel_selection_animation()
            self.hide()
            event.accept()
            return
        super().keyPressEvent(event)

    def focusOutEvent(self, event):
        if self._take_focus:
            self._show_animation.stop()
            self._cancel_selection_animation()
            self.hide()
        super().focusOutEvent(event)

    def _sync_size(self):
        self.resize(self.sizeHint())

    def _center(self):
        return QtCore.QPointF(self.width() * 0.5, self.height() * 0.5)

    def _update_focus_policy(self):
        if self._take_focus:
            self.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)
        else:
            self.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)

    def _start_show_animation(self):
        if not self.animation_duration:
            self.setPopupScale(1.0)
            return
        self._show_animation.setDuration(self.animation_duration)
        self._show_animation.setStartValue(0.0)
        self._show_animation.setEndValue(1.0)
        self._show_animation.start()

    def _start_selection_animation(self, index, action):
        self._show_animation.stop()
        self.setPopupScale(1.0)
        self._hover_index = index
        self._selected_index = index
        self._pending_action = action
        self.setSelectionProgress(0.0)

        if not self.selection_animation_duration:
            self._finish_selection_animation()
            return

        self._selection_animation.stop()
        self._selection_animation.setDuration(self.selection_animation_duration)
        self._selection_animation.setStartValue(0.0)
        self._selection_animation.setEndValue(1.0)
        self._selection_animation.start()

    def _finish_selection_animation(self):
        action = self._pending_action
        should_trigger = action is not None and action.isEnabled()

        self._selection_animation.stop()
        self._pending_action = None
        self._selected_index = -1
        self.setSelectionProgress(0.0)
        self.hide()

        if should_trigger:
            action.trigger()
            self.triggered.emit(action)

    def _cancel_selection_animation(self):
        self._selection_animation.stop()
        self._pending_action = None
        self._selected_index = -1
        self.setSelectionProgress(0.0)

    def _slot_angles(self, index):
        slot_span = self.sector_span / self.num_items
        gap = min(self.gap_angle, max(0.0, slot_span * 0.25))
        return self.start_angle + index * slot_span + gap * 0.5, max(0.0, slot_span - gap)

    def _selectable_index_at(self, pos):
        index = self._index_at(pos)
        if index < 0:
            return -1
        if index >= len(self._actions) or not self._actions[index].isEnabled():
            return -1
        return index

    def _action_from_item(self, item):
        if isinstance(item, QtGui.QAction):
            return item if item in self._actions else None
        if isinstance(item, int) and 0 <= item < len(self._actions):
            return self._actions[item]
        return None

    def _slot_center_point(self, center, start_angle, span_angle):
        angle = math.radians(start_angle + span_angle * 0.5)
        radius = (self.radius1 + self.radius2) * 0.5
        return QtCore.QPointF(
            center.x() + math.cos(angle) * radius,
            center.y() - math.sin(angle) * radius,
        )

    def _is_selection_active(self):
        return self._selected_index >= 0 or self._selection_progress > 0.0

    def _item_selection_scale(self, index):
        if not self._is_selection_active():
            return 1.0
        if index == self._selected_index:
            pulse = math.sin(self._selection_progress * math.pi * 2.0) ** 2
            return 1.0 + 0.035 * pulse
        return max(0.0, 1.0 - _smoothstep(self._selection_progress))

    def _item_selection_opacity(self, index):
        if not self._is_selection_active():
            return 1.0
        if index == self._selected_index:
            return max(0.0, 1.0 - self._selection_fade_progress())
        return max(0.0, 1.0 - _smoothstep(self._selection_progress))

    def _selection_flicker_color(self, base_color):
        flicker = math.sin(self._selection_progress * math.pi * 2.0) ** 2
        flicker *= 1.0 - self._selection_fade_progress()
        color = QtGui.QColor(base_color)
        color.setRed(min(255, int(color.red() + 45 * flicker)))
        color.setGreen(min(255, int(color.green() + 45 * flicker)))
        color.setBlue(min(255, int(color.blue() + 45 * flicker)))
        color.setAlpha(min(255, int(color.alpha() + 20 * flicker)))
        return color

    def _selection_fade_progress(self):
        fade_start = 0.68
        progress = (self._selection_progress - fade_start) / (1.0 - fade_start)
        return _smoothstep(max(0.0, min(1.0, progress)))

    def _sector_path(self, outer_rect, inner_rect, start_angle, span_angle):
        path = QtGui.QPainterPath()
        path.moveTo(_point_on_circle(outer_rect.center(), self.radius2, start_angle))
        path.arcTo(outer_rect, start_angle, span_angle)
        path.lineTo(_point_on_circle(inner_rect.center(), self.radius1, start_angle + span_angle))
        if self.radius1 > 0:
            path.arcTo(inner_rect, start_angle + span_angle, -span_angle)
        else:
            path.lineTo(inner_rect.center())
        path.closeSubpath()
        return path

    def _paint_action(self, painter, action, center, start_angle, span_angle):
        angle = math.radians(start_angle + span_angle * 0.5)
        radius = (self.radius1 + self.radius2) * 0.5
        point = QtCore.QPointF(
            center.x() + math.cos(angle) * radius,
            center.y() - math.sin(angle) * radius,
        )

        enabled = action.isEnabled()
        text = action.text().replace("&", "")
        has_icon = not action.icon().isNull()
        mode = QtGui.QIcon.Mode.Normal if enabled else QtGui.QIcon.Mode.Disabled

        if has_icon:
            rect = QtCore.QRectF(QtCore.QPointF(0, 0), QtCore.QSizeF(self.icon_size))
            rect.moveCenter(point)
            if text:
                rect.translate(0, -7)
            action.icon().paint(
                painter,
                rect.toRect(),
                QtCore.Qt.AlignmentFlag.AlignCenter,
                mode,
                QtGui.QIcon.State.Off,
            )

        if text:
            painter.save()
            painter.setPen(self.text_color if enabled else self.disabled_text_color)
            font = painter.font()
            font.setPointSize(max(7, font.pointSize() - 1))
            painter.setFont(font)
            metrics = QtGui.QFontMetrics(font)
            width = min(max(metrics.horizontalAdvance(text) + 8, 36), max(42, self.radius2 - self.radius1 + 32))
            height = metrics.height() + 2
            rect = QtCore.QRectF(0, 0, width, height)
            rect.moveCenter(point)
            if has_icon:
                rect.translate(0, self.icon_size.height() * 0.5 + self.text_margin)
            painter.drawText(rect, QtCore.Qt.AlignmentFlag.AlignCenter, metrics.elidedText(text, QtCore.Qt.TextElideMode.ElideRight, int(width)))
            painter.restore()

    def _index_at(self, pos):
        center = self._center()
        scale = max(self._popup_scale, 0.001)
        if scale < 0.08:
            return -1

        logical_pos = QtCore.QPointF(
            center.x() + (pos.x() - center.x()) / scale,
            center.y() + (pos.y() - center.y()) / scale,
        )
        dx = logical_pos.x() - center.x()
        dy = logical_pos.y() - center.y()
        distance = math.hypot(dx, dy)
        if distance < self.radius1 or distance > self.radius2:
            return -1

        angle = (math.degrees(math.atan2(-dy, dx)) + 360.0) % 360.0
        start = self.start_angle % 360.0
        while angle < start:
            angle += 360.0

        rel_angle = angle - start
        if rel_angle < 0.0 or rel_angle > self.sector_span:
            return -1

        slot_span = self.sector_span / self.num_items
        index = min(int(rel_angle / slot_span), self.num_items - 1)
        visual_start, visual_span = self._slot_angles(index)
        visual_rel = angle - visual_start
        if visual_rel < 0.0 or visual_rel > visual_span:
            return -1
        if index >= len(self._actions):
            return -1
        return index


def _normalize_sector(sector):
    if len(sector) != 2:
        raise ValueError("sector must contain start and end angles")
    start = float(sector[0])
    end = float(sector[1])
    raw_span = end - start
    if abs(raw_span) < 0.0001 or abs(raw_span) >= 360.0:
        span = 360.0
    elif raw_span < 0.0:
        span = raw_span % 360.0
    else:
        span = raw_span
    return start % 360.0, span


def _point_on_circle(center, radius, angle_degrees):
    angle = math.radians(angle_degrees)
    return QtCore.QPointF(
        center.x() + math.cos(angle) * radius,
        center.y() - math.sin(angle) * radius,
    )


def _smoothstep(value):
    value = max(0.0, min(1.0, float(value)))
    return value * value * (3.0 - 2.0 * value)


def _make_icon(icon):
    if isinstance(icon, QtGui.QIcon):
        return icon
    if isinstance(icon, QtGui.QPixmap):
        return QtGui.QIcon(icon)
    return QtGui.QIcon(str(icon))


def _make_color(color, fallback):
    if color is None:
        return QtGui.QColor(fallback)
    if isinstance(color, QtGui.QColor):
        return QtGui.QColor(color)
    if isinstance(color, (tuple, list)):
        return QtGui.QColor(*color)
    result = QtGui.QColor(str(color))
    return result if result.isValid() else QtGui.QColor(fallback)

if __name__ == "__main__":
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    menu = RadialMenu(radius1=120, radius2=180, num_items=4, sector=(0, 250))
    style = app.style()
    menu.addItem("Open", style.standardIcon(QtWidgets.QStyle.StandardPixmap.SP_DialogOpenButton), lambda: print("Open"))
    menu.addItem("Save", style.standardIcon(QtWidgets.QStyle.StandardPixmap.SP_DialogSaveButton), lambda: print("Save"))
    menu.addItem("Edit", style.standardIcon(QtWidgets.QStyle.StandardPixmap.SP_FileDialogDetailedView), lambda: print("Edit"))
    menu.addItem("Delete", style.standardIcon(QtWidgets.QStyle.StandardPixmap.SP_TrashIcon), lambda: print("Delete"))
    menu.setItemEnabled(1, False)
    menu.show_at(QtGui.QCursor.pos())
    app.exec()
