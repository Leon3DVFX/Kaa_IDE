import io, traceback, sys, re

from PySide6 import QtWidgets, QtCore, QtGui

from Kaa_IDE.UI.MainUI.editorWidget import Editor
from Kaa_IDE.UI.MainUI.logWidget import Logout

from Kaa_IDE.Core.loaders import iconLoader, pixmapLoader, cssLoader
from Kaa_IDE.Core.temp import TempSystem
from Kaa_IDE.Core.inspector import inspect_attr
from Kaa_IDE.UI.Styles.tab_bar import css as tab_css
from Kaa_IDE.UI.MainUI.internetBrowser import BrowserWindow


#Главная кнопка ("Зазывала" главного окна)
class MainButton(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._old_pos = None
        self._delta = None
        self.buttonPos = self.pos()
        self.setWindowOpacity(0.3)
        self.opAnim = QtCore.QPropertyAnimation(self, b'windowOpacity')
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_DeleteOnClose)
        #Таймер для фиксации между кликом и драгом
        self.clickTimer = QtCore.QTimer()
        self.clickTimer.setInterval(200)
        self.clickTimer.setSingleShot(True)
        #Форма кнопки
        self.resize(83, 65)
        self.pixmapOn = pixmapLoader('Kaa_online.png').scaled(
            50, 65,
            QtCore.Qt.AspectRatioMode.KeepAspectRatio,
            QtCore.Qt.TransformationMode.SmoothTransformation
        )
        self.pixmapOff = pixmapLoader('Kaa_offline.png').scaled(
            50, 65,
            QtCore.Qt.AspectRatioMode.KeepAspectRatio,
            QtCore.Qt.TransformationMode.SmoothTransformation
        )

        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground, True)

        self.setWindowFlags(QtCore.Qt.WindowType.WindowStaysOnTopHint |
                            QtCore.Qt.WindowType.FramelessWindowHint)

        #Возможность следить за состоянием
        self.state = 'hide'
        #Скрытый запуск главного окна
        self.mainWindow = KaaMDIWindow(self)
        self.mdi_area = self.mainWindow.centralWidget()
        self.mainWindow.hide()

        #Дополнительные кнопки
        #Кнопка общего закрытия
        self.x_button = XButton(self, normal='x_normal.png',
                                hovered='x_hovered.png',
                                activate='x_activate.png')
        self.x_button.move(self.pos() + QtCore.QPoint(51, 0))
        self.x_button.show()
        self.x_button.clicked.connect(self.close)
        #Кнопка запуска виджета сохранения-загрузки
        self.save_button = XButton(self, normal='save_normal.png',
                                   hovered='save_hovered.png',
                                   activate='save_activate.png',
                                   size=28)
        self.save_button.move(self.pos() + QtCore.QPoint(54, 33))
        self.save_button.show()
        self.save_button.clicked.connect(self.save_widget_action)

        # Виджет с панелью сохранения + их диалоги
        self.save_widget = SaveLoadWidget(self)
        self.save_widget.hide()
        self.save_py = self.py_save_dialog()
        self.save_kaa = self.kaa_save_dialog()
        self.load_kaa = self.kaa_load_dialog()
        self.load_py = self.py_load_dialog()

        self.save_widget.btn_save_py.clicked.connect(self.save_pyexec)
        self.save_widget.btn_save_k.clicked.connect(self.save_kaa.exec)
        self.save_widget.btn_load_k.clicked.connect(self.load_kaa.exec)
        self.save_widget.btn_load_py.clicked.connect(self.load_py.exec)

        #Обработка сигналов
        self._showing = False
        # self.mainWindow.closeSignal.connect(self.toggle)
        # Восстановление позиции при запуске
        temp = self.mainWindow.centralWidget().temp
        self.move(temp.x, temp.y)
        self.mainWindow.resize(temp.width, temp.height)

    # Обработчик для вывода виджета сохр-загрузки
    @QtCore.Slot()
    def save_widget_action(self):
        if self.save_widget.isHidden():
            self.save_widget.move(self.pos() + QtCore.QPoint(85, 0))
            self.save_widget.show()
        else:
            self.save_widget.hide()

    # Обработчик с защитой
    @QtCore.Slot()
    def show_hide_main(self):
        mdi_area = self.mainWindow.centralWidget()
        mdi_area._ignore_activation = True

        if self.state == 'open':
            self.mainWindow.move(self.mapToGlobal(QtCore.QPoint(0, self.height())))
            self.mainWindow.show()
            self.mainWindow.raise_()
            self.mainWindow.activateWindow()
        else:
            self.mainWindow.hide()

        QtCore.QTimer.singleShot(100, lambda: setattr(mdi_area, '_ignore_activation', False))

    # Диалоги системы сохранения-загрузки
    # Диалог сохранения Py из текущего таба
    def py_save_dialog(self):
        fd = QtWidgets.QFileDialog(self.mainWindow)
        fd.setNameFilter('Py (*.py *.pyc *.txt)')
        fd.setDirectory(self.mdi_area.temp.work_dir)
        fd.setAcceptMode(QtWidgets.QFileDialog.AcceptMode.AcceptSave)
        fd.setViewMode(QtWidgets.QFileDialog.ViewMode.Detail)
        fd.setFileMode(QtWidgets.QFileDialog.FileMode.AnyFile)

        fd.fileSelected.connect(self.save_python_to_file)

        return fd

    # Диалог сохранения kaa
    def kaa_save_dialog(self):
        fd = QtWidgets.QFileDialog(self.mainWindow)
        fd.setNameFilter('Kaa (*.kaa)')
        fd.setDirectory(self.mdi_area.temp.work_dir)
        fd.setAcceptMode(QtWidgets.QFileDialog.AcceptMode.AcceptSave)
        fd.setViewMode(QtWidgets.QFileDialog.ViewMode.Detail)
        fd.setFileMode(QtWidgets.QFileDialog.FileMode.AnyFile)

        fd.fileSelected.connect(self.save_kaa_to_file)

        return fd

    # Диалог загрузки Kaa
    def kaa_load_dialog(self):
        fd = QtWidgets.QFileDialog(self.mainWindow)
        fd.setNameFilter('Kaa (*.kaa)')
        fd.setDirectory(self.mdi_area.temp.work_dir)
        fd.setAcceptMode(QtWidgets.QFileDialog.AcceptMode.AcceptOpen)
        fd.setViewMode(QtWidgets.QFileDialog.ViewMode.Detail)
        fd.setFileMode(QtWidgets.QFileDialog.FileMode.AnyFile)

        fd.fileSelected.connect(self.load_kaa_from_file)

        return fd

    # Диалог загрузки Python
    def py_load_dialog(self):
        fd = QtWidgets.QFileDialog(self.mainWindow)
        fd.setNameFilter('Py (*.py *.pyc *.txt)')
        fd.setDirectory(self.mdi_area.temp.work_dir)
        fd.setAcceptMode(QtWidgets.QFileDialog.AcceptMode.AcceptOpen)
        fd.setViewMode(QtWidgets.QFileDialog.ViewMode.Detail)
        fd.setFileMode(QtWidgets.QFileDialog.FileMode.ExistingFiles)

        fd.filesSelected.connect(self.load_py_from_file)
        return fd

    # Exec для сохранения py
    def save_pyexec(self):
        name = ''
        if self.mainWindow.isVisible():
            name = self.mdi_area.activeSubWindow().windowTitle()
        self.save_py.setDirectory(self.mdi_area.temp.work_dir)
        self.save_py.selectFile(name)
        self.save_py.exec()

    # Функция сохранения Py
    def save_python_to_file(self, path):
        self.mdi_area.temp.work_dir = path
        self.save_py.setDirectory(path)
        self.mdi_area.temp.save_py_file(self.mdi_area, path)

    # Функция сохранения Kaa
    def save_kaa_to_file(self, path):
        self.mdi_area.temp.work_dir = path
        self.save_kaa.setDirectory(path)
        self.mdi_area.temp.save_kaa_file(self.mdi_area, path)

    # Функция загрузки Kaa
    def load_kaa_from_file(self, path):
        self.mdi_area.temp.work_dir = path
        self.load_kaa.setDirectory(path)
        # Проверка наличия текста в одном из окон
        subwindows = self.mdi_area.subWindowList()
        message = None
        for sub in subwindows:
            editor = sub.widget().editor
            if not editor.toPlainText().strip():
                continue
            else:
                title = 'Overwrite operation'
                text = ('One or more tabs contain text.\n'
                        'This operation will overwrite all tabs.\n'
                        'Do you want to continue?')
                message = QtWidgets.QMessageBox.question(
                    self.mainWindow,
                    title,
                    text,
                    QtWidgets.QMessageBox.StandardButton.Yes |
                    QtWidgets.QMessageBox.StandardButton.No,
                    QtWidgets.QMessageBox.StandardButton.No  # Кнопка по умолчанию
                )
                break

        if message == QtWidgets.QMessageBox.StandardButton.Yes or message is None:
            # Загрузка Kaa
            self.mdi_area.temp.load_kaa_file(self.mdi_area, path)

    # Загрузка Python в новые табы
    def load_py_from_file(self, paths):
        self.mdi_area.temp.work_dir = paths[-1]
        self.mdi_area.temp.load_py_files(self.mdi_area, paths)

    # Реализация свободного перетаскивания за кнопку
    def mousePressEvent(self, e):
        self.save_widget.hide()
        if e.button() == QtCore.Qt.MouseButton.LeftButton:
            self.clickTimer.start()
            self._old_pos = e.globalPosition().toPoint()
            e.accept()
            return
        super().mousePressEvent(e)

    def mouseMoveEvent(self, e):
        if self._old_pos is not None:
            self._delta = e.globalPosition().toPoint() - self._old_pos
            self.move(self.pos() + self._delta)
            self._old_pos = e.globalPosition().toPoint()
            self.update_window_position()
            self.update()
        super().mouseMoveEvent(e)

    def mouseReleaseEvent(self, e):
        if e.button() == QtCore.Qt.MouseButton.LeftButton:
            if self.clickTimer.isActive():
                self.clickTimer.stop()
                if self.state == 'hide':
                    self.state = 'open'
                else:
                    self.state = 'hide'
                self.update()
                self.show_hide_main()
            self._old_pos = None
            self._delta = None
            e.accept()
            return
        super().mouseReleaseEvent(e)

    def update_window_position(self):
        if self.mainWindow.isVisible():
            self.buttonPos = self.mapToGlobal(QtCore.QPoint(0, 0))
            self.mainWindow.move(self.buttonPos + QtCore.QPoint(0, self.height()))

    #Перерисовка иконка-кнопка
    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.SmoothPixmapTransform)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        if self.state == 'hide':
            pixmap = self.pixmapOff
        else:
            pixmap = self.pixmapOn

        painter.drawPixmap(QtCore.QRect(0, 0, 50, 65), pixmap)

    #Вызов закрытия главного окна вслед за кнопкой
    def closeEvent(self, event):
        if hasattr(self, 'mainWindow') and self.mainWindow is not None:
            mdi_area = self.mainWindow.findChild(QtWidgets.QMdiArea)
            mdi_area.temp.save_temp_file(mdi_area)
            self.x_button.state = 'normal'
            self.state = 'hide'
            self.mainWindow.close()
        self.save_widget.close()
        self.close()
        event.accept()

    #Анимация прозрачности при входе - выходе курсора
    def enterEvent(self, event):
        self.opAnim.stop()
        self.opAnim.setDuration(200)
        self.opAnim.setStartValue(self.windowOpacity())
        self.opAnim.setEndValue(1.0)
        self.opAnim.start()

    def leaveEvent(self, event):
        self.opAnim.stop()
        self.opAnim.setDuration(1000)
        self.opAnim.setStartValue(self.windowOpacity())
        self.opAnim.setEndValue(0.3)
        self.opAnim.start()


#Обертка главного окна (настройка)
class KaaMDIWindow(QtWidgets.QMainWindow):
    closeSignal = QtCore.Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumWidth(550)
        self.setMinimumHeight(400)
        self.resize(400, 600)
        self.setWindowFlags(
            QtCore.Qt.WindowType.FramelessWindowHint |
            QtCore.Qt.WindowType.Tool
        )

        self.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowTitle('Kaa_IDE v0.12')
        self.mdi_central = MDIArea(self)
        self.setCentralWidget(self.mdi_central)

        self.tool_bar_opacity = self.create_tool_bar()
        self.addToolBar(QtCore.Qt.ToolBarArea.LeftToolBarArea, self.tool_bar_opacity)

    def create_tool_bar(self):
        tool_bar = QtWidgets.QToolBar(self)
        tool_bar.setOrientation(QtCore.Qt.Orientation.Vertical)
        tool_bar.setAllowedAreas(QtCore.Qt.ToolBarArea.LeftToolBarArea)
        tool_bar.setMovable(False)
        tool_bar.setFloatable(False)
        op_slider = self.create_opacity_slider()
        tool_bar.addWidget(op_slider)
        tool_bar.setObjectName('opacity_tool')
        return tool_bar

    def create_opacity_slider(self):
        slider = QtWidgets.QSlider(QtCore.Qt.Orientation.Vertical, self)
        slider.setObjectName('op_slider')
        slider.setRange(150, 255)
        slider.setValue(255)
        slider.valueChanged.connect(self.opacity_correct)
        return slider

    def opacity_correct(self, val):
        subwindows = self.mdi_central.subWindowList()
        for subwindow in subwindows:
            subwindow.widget().editor.alpha = val
            subwindow.widget().logout.alpha = val
            subwindow.widget().editor.update()
            subwindow.widget().logout.update()

    # Сигнал для кнопки (на случай отдельного закрытия)
    def closeEvent(self, e):
        self.closeSignal.emit()


#MDI - оболочка
class MDIArea(QtWidgets.QMdiArea):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._font = QtGui.QFont('JetBrains Mono', 10)
        # Start layout
        self.startSubWindow = self.addSubWindow(MDISubWindow(self))
        self.startSubWindow.show()
        self.setViewMode(QtWidgets.QMdiArea.ViewMode.TabbedView)
        self.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)
        self.setTabsMovable(True)
        self.setTabsClosable(True)
        self.main_win = parent
        #Текущее окно при создании
        self.current = self.startSubWindow
        self._current_subwindow = None
        self._ignore_activation = False
        #Иконки
        self.non_act_icon = QtGui.QIcon()
        self.act_icon = QtGui.QIcon()
        self.non_act_icon.addPixmap(pixmapLoader('py_non_active.png'))
        self.act_icon.addPixmap(pixmapLoader('py_active.png'))
        self.current.setWindowIcon(self.act_icon)
        # Для actions табов
        self.create_icon = QtGui.QIcon()
        self.create_icon.addPixmap(pixmapLoader(r'actions_icons\NewTab.png'))
        self.close_icon = QtGui.QIcon()
        self.close_icon.addPixmap(pixmapLoader(r'actions_icons\CloseTab.png'))
        self.rename_icon = QtGui.QIcon()
        self.rename_icon.addPixmap(pixmapLoader(r'actions_icons\RenameTab.png'))
        #Инициализация таб-бара
        self.refresh_tabbar()
        self.subWindowActivated.connect(self.on_subwindow_activated)
        self.subWindowActivated.connect(self.opacity_recalc)
        self.subWindowActivated.connect(self.update)
        #Система сохранения - загрузки
        self.temp = TempSystem(self)
        self.temp.load_temp_file(self)
        self.adjustSize()

    # Пересчет прозрачности от слайдера при активации подокна(+создание нового)
    @QtCore.Slot(QtWidgets.QMdiSubWindow)
    def opacity_recalc(self, subwindow):
        if subwindow:
            editor = subwindow.widget().editor
            log = subwindow.widget().logout
            slider = self.parent().findChild(QtWidgets.QSlider, 'op_slider')
            if slider:
                editor.alpha = slider.value()
                log.alpha = slider.value()
            editor.update()
            log.update()

    @QtCore.Slot(QtWidgets.QMdiSubWindow)
    def on_subwindow_activated(self, subwindow):
        if getattr(self, '_ignore_activation', False):
            return

        if subwindow is None:
            return

        if getattr(self, '_current_subwindow', None) == subwindow:
            return
        self._current_subwindow = subwindow

        for s in self.subWindowList():
            s.setWindowIcon(self.non_act_icon)
            subwindow.setWindowIcon(self.act_icon)

        if not subwindow.isMaximized():
            subwindow.showMaximized()

        editor = subwindow.widget().editor

        def set_focus_if_active():
            if self._current_subwindow == subwindow:
                editor.setFocus(QtCore.Qt.FocusReason.ActiveWindowFocusReason)

        QtCore.QTimer.singleShot(50, set_focus_if_active)
        # Дергаем курсор
        cursor = QtGui.QTextCursor(editor.textCursor())
        editor.setTextCursor(cursor)

        self.temp.save_temp_file(self)

    # Обновление таб-бара
    def refresh_tabbar(self):
        tab_bar = self.findChild(QtWidgets.QTabBar)
        if not tab_bar:
            return
        else:
            tab_bar.setStyleSheet(tab_css)
        #Настройка
        tab_bar.setExpanding(False)
        tab_bar.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        tab_bar.setToolTip('Python Editor')
        #Подключение контекстного меню
        tab_bar.customContextMenuRequested.connect(self.add_context_menu)

    # Создание контекстного меню
    @QtCore.Slot(QtCore.QPoint)
    def add_context_menu(self, point):
        #Проверка наличия таб бара
        tab_bar = self.findChild(QtWidgets.QTabBar)
        if not tab_bar:
            return
        #Проверка наличия индекса
        idx = tab_bar.tabAt(point)
        if idx < 0:
            return
        #Создаем меню
        menu = QtWidgets.QMenu()
        menu.setFont(self._font)
        #Создать новый таб
        act1 = QtGui.QAction('New Tab')
        act1.setIcon(self.create_icon)
        menu.addAction(act1)
        act1.triggered.connect(self.new_tab)
        # Переименовать таб
        act2 = QtGui.QAction('Rename Tab')
        act2.setData(idx)
        act2.setIcon(self.rename_icon)
        menu.addAction(act2)
        act2.triggered.connect(self.rename_tab)

        #Позиция вызова
        global_pos = tab_bar.mapToGlobal(point)
        #Вызов
        menu.exec(global_pos)

    # Функции контекстного меню табов
    # Создание нового таба
    def new_tab(self):
        new_win = MDISubWindow()
        self.addSubWindow(new_win)
        new_win.showMaximized()
        self.setActiveSubWindow(new_win)

    # Переименовать таб
    def rename_tab(self):
        action = self.sender()
        idx = action.data()
        tab_bar = self.findChild(QtWidgets.QTabBar)
        # Активное окно
        current_active = self.activeSubWindow()

        tab_rect = tab_bar.tabRect(idx)
        subwindow = self.subWindowList()[idx]
        # Dialog
        input_d = QtWidgets.QInputDialog(self.parent())
        input_d.setFont(self._font)
        input_d.setMinimumWidth(100)
        input_d.setLabelText('New name:')
        input_d.setWindowFlags(QtCore.Qt.WindowType.FramelessWindowHint |
                               QtCore.Qt.WindowType.WindowStaysOnTopHint |
                               QtCore.Qt.WindowType.Dialog)
        input_d.setTextValue(subwindow.windowTitle())
        input_d.setInputMode(QtWidgets.QInputDialog.InputMode.TextInput)
        # Вызов диалога
        start_pos = tab_bar.mapToGlobal(QtCore.QPoint(tab_rect.x(),
                                                      tab_rect.y() + tab_rect.height() + 2))
        input_d.move(start_pos)
        if input_d.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            new_name = input_d.textValue()
            result = re.sub(r'\s+', '_', new_name)
            if result:
                subwindow.setWindowTitle(result)
        # Восстановление фокуса
        self.setActiveSubWindow(current_active)
        current_active.widget().editor.setFocus()

    # Закрытие таба
    def close_tab(self, idx):
        subwindows = self.subWindowList()
        if 0 <= idx < len(subwindows):
            subwindow = subwindows[idx]
            subwindow.close()
        #Активация соседнего окна
        remaining = self.subWindowList(QtWidgets.QMdiArea.WindowOrder.CreationOrder)
        if remaining:
            new_idx = min(idx, len(remaining) - 1)
            active_win = remaining[new_idx]
            self.setActiveSubWindow(active_win)
            active_win.showMaximized()

    # Восстановление по Temp файлу (внутри модуля temp)
    def restore_window(self, index, text, cursor_pos, win_name):
        # Проверка наличия окна
        subwindows = self.subWindowList()
        # Гарантия наличия окна с нужным индексом
        while len(subwindows) <= index:
            self.new_tab()
            subwindows = self.subWindowList()

        # Перезапись вновь созданного окна
        subwindow = subwindows[index]
        subwindow.setWindowTitle(win_name)
        editor = subwindow.widget().editor
        editor.clear()
        editor.setPlainText(text)
        editor.setFocus()
        # Восстановление позиции курсора
        cursor = editor.textCursor()
        cursor.setPosition(min(cursor_pos, len(text)))
        editor.setTextCursor(cursor)


#Вкладываемые главные окна
class MDISubWindow(QtWidgets.QMdiSubWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWidget(MainWindow(self))
        self.setMinimumWidth(300)
        self.mdi_area = parent
        #Настройка параметров
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setWindowFlags(QtCore.Qt.WindowType.FramelessWindowHint |
                            QtCore.Qt.WindowType.SubWindow)
        self.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)
        # Курсоры
        self.cursors = [
            QtGui.QCursor(pixmapLoader(r'cursor_icons/hor_cursor.png'), 16, 16),  # 0 - Гор неактивный
            QtGui.QCursor(pixmapLoader(r'cursor_icons/hor_act_cursor.png'), 16, 16),  # 1 - Гор активный
            QtGui.QCursor(pixmapLoader(r'cursor_icons/vert_cursor.png'), 16, 16),  # 2 - Верт неактивный
            QtGui.QCursor(pixmapLoader(r'cursor_icons/vert_act_cursor.png'), 16, 16),  # 3 - Верт активный
            QtGui.QCursor(pixmapLoader(r'cursor_icons/r_diag_cursor.png'), 16, 16),  # 4 - П.Диаг неактивный
            QtGui.QCursor(pixmapLoader(r'cursor_icons/r_diag_act_cursor.png'), 16, 16)  # 5 - П.Диаг активный
        ]
        # Ресайз
        self.setMouseTracking(True)
        self._margin = 5
        self._resizing = False
        self._resize_dir = None
        self._margin_dir = None
        self._drag_start_pos = None
        self._start_geometry = None
        # Настройка пера
        self.std_pen = QtGui.QPen()
        self.color1 = QtGui.QColor('#67CCFF')
        self.color2 = QtGui.QColor('#CCCCCC')
        self.color1.setAlpha(255)
        self.color2.setAlpha(150)
        self.std_pen.setColor(self.color2)
        self.std_pen.setCapStyle(QtCore.Qt.PenCapStyle.RoundCap)

    def paintEvent(self, event):
        self.draw_border_lines()

    def draw_border_lines(self):
        painter = QtGui.QPainter(self)
        painter.setCompositionMode(QtGui.QPainter.CompositionMode.CompositionMode_SourceOver)
        # Pen 1
        pen1 = QtGui.QPen()
        color1 = QtGui.QColor('#CCCCCC')
        color1.setAlpha(200)
        pen1.setCapStyle(QtCore.Qt.PenCapStyle.RoundCap)
        pen1.setColor(color1)
        pen1.setWidthF(0.15)
        # Pen 2
        pen2 = QtGui.QPen()
        color2 = QtGui.QColor('#67CCFF')
        color2.setAlpha(255)
        pen2.setCapStyle(QtCore.Qt.PenCapStyle.RoundCap)
        pen2.setColor(color2)
        pen2.setWidthF(0.5)
        # Pen 3
        pen3 = QtGui.QPen()
        color3 = QtGui.QColor('#67CCFF')
        color3.setAlpha(255)
        pen3.setCapStyle(QtCore.Qt.PenCapStyle.RoundCap)
        pen3.setColor(color3)
        pen3.setWidthF(0.15)

        painter.setPen(pen1)
        rect = self.rect()
        new_rect = QtCore.QRect()
        new_rect.setWidth(rect.width() - 1)
        new_rect.setHeight(rect.height() - 1)
        new_rect.setX(rect.x() + 1)
        new_rect.setY(rect.y() + 1)
        painter.drawRect(new_rect)
        # Рамка справа
        # Линия 1
        x1 = rect.right() - 2
        y1 = rect.height() / 2 + 70
        x2 = rect.right() - 2
        y2 = rect.height() / 2 - 70
        # Линия 2
        x3 = rect.right() - 4
        y3 = rect.height() / 2 + 50
        x4 = rect.right() - 4
        y4 = rect.height() / 2 - 50
        # Линия 3
        x5 = rect.right() - 6
        y5 = rect.height() / 2 + 30
        x6 = rect.right() - 6
        y6 = rect.height() / 2 - 30
        # Прорисовка
        painter.drawLine(x1, y1, x2, y2)
        painter.drawLine(x3, y3, x4, y4)
        painter.drawLine(x5, y5, x6, y6)
        # Рамка снизу
        # Линия 1
        x1 = rect.right() / 2 + 70
        y1 = rect.height() - 2
        x2 = rect.right() / 2 - 70
        y2 = rect.height() - 2
        # Линия 2
        x3 = rect.right() / 2 + 50
        y3 = rect.height() - 4
        x4 = rect.right() / 2 - 50
        y4 = rect.height() - 4
        # Линия 3
        x5 = rect.right() / 2 + 30
        y5 = rect.height() - 6
        x6 = rect.right() / 2 - 30
        y6 = rect.height() - 6

        painter.drawLine(x1, y1, x2, y2)
        painter.drawLine(x3, y3, x4, y4)
        painter.drawLine(x5, y5, x6, y6)
        # Угловая рамка
        # Уголок 1
        x1 = rect.right() - 70
        y1 = rect.bottom() - 2
        x2 = rect.right() - 2
        y2 = rect.bottom() - 2
        x3 = rect.right() - 2
        y3 = rect.bottom() - 70
        # Уголок 2
        x4 = rect.right() - 50
        y4 = rect.bottom() - 4
        x5 = rect.right() - 4
        y5 = rect.bottom() - 4
        x6 = rect.right() - 4
        y6 = rect.bottom() - 50
        # Уголок 3
        x7 = rect.right() - 30
        y7 = rect.bottom() - 6
        x8 = rect.right() - 6
        y8 = rect.bottom() - 6
        x9 = rect.right() - 6
        y9 = rect.bottom() - 30

        painter.drawPolyline([QtCore.QPoint(x1, y1), QtCore.QPoint(x2, y2), QtCore.QPoint(x3, y3)])
        painter.drawPolyline([QtCore.QPoint(x4, y4), QtCore.QPoint(x5, y5), QtCore.QPoint(x6, y6)])
        painter.drawPolyline([QtCore.QPoint(x7, y7), QtCore.QPoint(x8, y8), QtCore.QPoint(x9, y9)])

        if self._resizing:
            painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
            painter.setCompositionMode(QtGui.QPainter.CompositionMode.CompositionMode_HardLight)
            painter.setPen(pen3)
            painter.drawRect(new_rect)
            painter.setPen(pen2)
            if self._resize_dir == 'right':
                # Линия 1
                x1 = rect.right() - 2
                y1 = rect.height() / 2 + 70
                x2 = rect.right() - 2
                y2 = rect.height() / 2 - 70
                # Линия 2
                x3 = rect.right() - 4
                y3 = rect.height() / 2 + 50
                x4 = rect.right() - 4
                y4 = rect.height() / 2 - 50
                # Линия 3
                x5 = rect.right() - 6
                y5 = rect.height() / 2 + 30
                x6 = rect.right() - 6
                y6 = rect.height() / 2 - 30
                # Прорисовка
                painter.drawLine(x1, y1, x2, y2)
                painter.drawLine(x3, y3, x4, y4)
                painter.drawLine(x5, y5, x6, y6)
            elif self._resize_dir == 'bottom':
                # Рамка снизу
                # Линия 1
                x1 = rect.right() / 2 + 70
                y1 = rect.height() - 2
                x2 = rect.right() / 2 - 70
                y2 = rect.height() - 2
                # Линия 2
                x3 = rect.right() / 2 + 50
                y3 = rect.height() - 4
                x4 = rect.right() / 2 - 50
                y4 = rect.height() - 4
                # Линия 3
                x5 = rect.right() / 2 + 30
                y5 = rect.height() - 6
                x6 = rect.right() / 2 - 30
                y6 = rect.height() - 6

                painter.drawLine(x1, y1, x2, y2)
                painter.drawLine(x3, y3, x4, y4)
                painter.drawLine(x5, y5, x6, y6)
            elif self._resize_dir == 'corner':
                # Угловая рамка
                # Уголок 1
                x1 = rect.right() - 70
                y1 = rect.bottom() - 2
                x2 = rect.right() - 2
                y2 = rect.bottom() - 2
                x3 = rect.right() - 2
                y3 = rect.bottom() - 70
                # Уголок 2
                x4 = rect.right() - 50
                y4 = rect.bottom() - 4
                x5 = rect.right() - 4
                y5 = rect.bottom() - 4
                x6 = rect.right() - 4
                y6 = rect.bottom() - 50
                # Уголок 3
                x7 = rect.right() - 30
                y7 = rect.bottom() - 6
                x8 = rect.right() - 6
                y8 = rect.bottom() - 6
                x9 = rect.right() - 6
                y9 = rect.bottom() - 30

                painter.drawPolyline([QtCore.QPoint(x1, y1), QtCore.QPoint(x2, y2), QtCore.QPoint(x3, y3)])
                painter.drawPolyline([QtCore.QPoint(x4, y4), QtCore.QPoint(x5, y5), QtCore.QPoint(x6, y6)])
                painter.drawPolyline([QtCore.QPoint(x7, y7), QtCore.QPoint(x8, y8), QtCore.QPoint(x9, y9)])

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            rect = self.rect()
            pos = event.position()
            margin = self._margin
            if rect.right() - pos.x() <= margin and rect.bottom() - pos.y() <= margin:
                self._resizing = True
                self._resize_dir = 'corner'
            elif rect.right() - pos.x() <= margin:
                self._resizing = True
                self._resize_dir = 'right'
            elif rect.bottom() - pos.y() <= margin:
                self._resizing = True
                self._resize_dir = 'bottom'
            self._drag_start_pos = event.globalPosition().toPoint()
            self._start_geometry = self.geometry()
            self.update()

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        # Сюда приделываем курсоры
        if not self._resizing:
            self.unsetCursor()
            rect = self.rect()
            pos = event.position()
            margin = self._margin
            if rect.right() - pos.x() <= margin and rect.bottom() - pos.y() <= margin:
                self._margin_dir = 'corner'
                self.setCursor(self.cursors[4])
            elif rect.right() - pos.x() <= margin:
                self._margin_dir = 'right'
                self.setCursor(self.cursors[0])
            elif rect.bottom() - pos.y() <= margin:
                self._margin_dir = 'bottom'
                self.setCursor(self.cursors[2])

            else:
                self._margin_dir = None
                self.unsetCursor()

        if self._resizing and self._start_geometry:
            current_global_pos = event.globalPosition().toPoint()
            delta = current_global_pos - self._drag_start_pos

            if self._resize_dir == 'right':
                new_width = self._start_geometry.width() + delta.x()
                self._start_geometry.setWidth(new_width)
                self.setCursor(self.cursors[1])
            elif self._resize_dir == 'bottom':
                new_height = self._start_geometry.height() + delta.y()
                self._start_geometry.setHeight(new_height)
                self.setCursor(self.cursors[3])
            elif self._resize_dir == 'corner':
                new_width = self._start_geometry.width() + delta.x()
                new_height = self._start_geometry.height() + delta.y()
                self._start_geometry.setWidth(new_width)
                self._start_geometry.setHeight(new_height)
                self.setCursor(self.cursors[5])

            # self.setGeometry(new_geometry)
            main_window = self.window()
            tb = main_window.findChild(QtWidgets.QToolBar, 'opacity_tool')
            tb_w = tb.width()
            main_window.resize(
                self._start_geometry.width() + tb_w,
                self._start_geometry.height() + 24
            )

            self._drag_start_pos = current_global_pos

    def mouseReleaseEvent(self, event):
        self.update()
        self._resizing = False
        self._resize_dir = None
        self._drag_start_pos = None
        self._start_geometry = None
        super().mouseReleaseEvent(event)

    #Невозможно оставить MDI Area без хотя бы одного окна
    def closeEvent(self, e):
        mdi_area = self.mdiArea()
        if mdi_area and len(mdi_area.subWindowList()) == 1:
            e.ignore()
        else:
            e.accept()


#Главное окно редактора !!!КАК КОМПЛЕКТУЕМЫЙ ВИДЖЕТ!!!
class MainWindow(QtWidgets.QWidget):
    closeSignal = QtCore.Signal()

    #Инициализация главного окна (конструктор)
    def __init__(self, parent=None):
        super().__init__(parent)
        #Стартовая инициализация
        self.setWindowTitle('Py')
        self.setWindowFlags(QtCore.Qt.WindowType.FramelessWindowHint)
        #Упаковка редактора, логера и браузера в Splitter
        self.editor_main = Editor()
        self.editor = self.editor_main.getEditor()  #Доступ к объ через обертку
        self.editor.setPlaceholderText('Enter Python code (Ctrl+Enter to run)')

        self.logout_main = Logout()
        self.logout = self.logout_main.getLogout()
        self.splitter1 = EditorSplitter()
        self.splitter1.addWidget(self.editor_main)
        self.splitter1.addWidget(self.logout_main)
        #Стартовые параметры размеров и растяжки (для лога - не менять размер)
        self.splitter1.setStretchFactor(0, 100)
        self.splitter1.setStretchFactor(1, 0)
        self.splitter1.setSizes([450, 150])

        #Упаковка виджетов окна
        self.box = QtWidgets.QVBoxLayout(self)
        self.box.addWidget(self.splitter1)

        #Обработка сигналов
        self.editor.runCodeSignal.connect(self.run_code)
        self.editor.envRefresh.connect(self.env_refresh)
        self.editor.getEnv.connect(self.get_env)
        self.editor.pointNote.connect(self.point_note_complitter)
        self.editor_main.editorFontChanged.connect(self.logoutFontChange)
        self.editor.setFocus()
        self.setMouseTracking(True)
        # Словарь для хранения глобальных переменных между запусками
        self.global_env = {
            '__name__': '__main__',
            '__builtins__': __builtins__,
        }

    # Разбор точечной нотации + смена моделей для комплиттера
    def point_note_complitter(self, text):
        if not text or text.endswith((')', ']', '"', "'")):
            return

        parts = text.split('.')
        root_name = parts[0]
        # print(text)
        # 1 есть ли корень в env
        root = self.global_env.get(root_name)
        if root is None:
            return
        # 2 пытаемся пройти по атрибутам
        obj = root
        try:
            for part in parts[1:]:
                obj = getattr(obj, part)
        except Exception:
            return
        # 3 obj — валидный объект
        attrs = set(dir(obj))
        if hasattr(obj, "__dict__"):
            attrs |= obj.__dict__.keys()

        sym = []

        for name in attrs:
            if name.startswith('_'):
                continue

            val, kind = inspect_attr(obj, name)
            if val is None:
                continue
            sym.append((name, kind, val))

        # print(sym)
        # attrs в модель комплитера
        self.rebuild_complitter(sym)

    def rebuild_complitter(self, sym):
        # 1 - Чистка базовой модели
        self.editor.complitter.base_model.silent_clean()

        for name, kind, val in sym:
            elem1 = QtGui.QStandardItem(name)
            elem1.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignVCenter)
            elem1.setForeground(QtGui.QColor('#D5D5D5'))
            elem1.setIcon(self.editor.complitter.base_model.mod_icon)

            elem2 = QtGui.QStandardItem(kind)
            elem2.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignRight)

            self.editor.complitter.base_model.appendRow([elem1, elem2])

        self.editor.complitter.proxy_model.setFilterRegularExpression("")
        self.editor.complitter.sortByColumn(0, QtCore.Qt.SortOrder.AscendingOrder)
        self.editor.on_complitter_show()

    # Получение env в виде текста в Logout
    def get_env(self):
        self.logout.clear()
        gl_dict = self.global_env
        res_str = ''

        for k in gl_dict.keys():
            if k.startswith('_'):
                continue

            res_str += f"Object -> '{k}', Type -> {type(gl_dict.get(k))}, Value - {gl_dict.get(k)}\n"

        if res_str == '':
            message = 'Environment is clear'
            self.logout.setPlainText(message)
            QtCore.QTimer.singleShot(1500, self.logout.clear)
        else:
            self.logout.setPlainText(res_str)

    # Сброс env
    def env_refresh(self):
        self.global_env = {
            '__name__': '__main__',
            '__builtins__': __builtins__,
        }
        self.logout.clear()
        self.logout.setPlainText('Environment has been successfully refreshed')
        QtCore.QTimer.singleShot(1500, self.logout.clear)

    #Сигнал для кнопки (на случай отдельного закрытия)
    def closeEvent(self, e):
        self.closeSignal.emit()

    #Запуск кода в основном потоке
    @QtCore.Slot()
    def run_code(self):
        self.logout.clear()
        self.cursor = self.editor.textCursor()
        code = None
        if self.cursor.hasSelection():
            code = self.cursor.selectedText().replace('\u2029', '\n')
        else:
            code = self.editor.toPlainText()

        # Перенаправляем stdout/stderr
        buffer = io.StringIO()
        old_stdout, old_stderr = sys.stdout, sys.stderr
        sys.stdout, sys.stderr = buffer, buffer

        try:
            _compiled = compile(code, '<Script Editor>', "exec")
            exec(_compiled, self.global_env)
        except Exception as e:
            _tb = ''.join(traceback.format_exception(type(e), e, e.__traceback__))
            buffer.write(_tb)
        finally:
            sys.stdout, sys.stderr = old_stdout, old_stderr

        self.logout.appendPlainText(buffer.getvalue())

        # self.logout.appendPlainText(str(self.global_env)) #Тестер

    @QtCore.Slot(QtGui.QFont)
    def logoutFontChange(self, font):
        self.logout_main.setFont(QtGui.QFont(font.family(), self.logout.font().pointSize()))


class XButton(QtWidgets.QPushButton):
    def __init__(self, parent=None, normal=None, hovered=None, activate=None, size=32):
        super().__init__(parent)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground, True)

        self.setWindowFlags(QtCore.Qt.WindowType.WindowStaysOnTopHint |
                            QtCore.Qt.WindowType.FramelessWindowHint)
        self.setFixedSize(size, size)
        self.state = 'normal'
        #Варианты отрисовки
        self.pixmapOut = pixmapLoader(normal).scaled(
            self.width(), self.height(),
            QtCore.Qt.AspectRatioMode.KeepAspectRatio,
            QtCore.Qt.TransformationMode.SmoothTransformation
        )
        self.pixmapIn = pixmapLoader(hovered).scaled(
            self.width(), self.width(),
            QtCore.Qt.AspectRatioMode.KeepAspectRatio,
            QtCore.Qt.TransformationMode.SmoothTransformation
        )
        self.pixmapAct = pixmapLoader(activate).scaled(
            self.width(), self.width(),
            QtCore.Qt.AspectRatioMode.KeepAspectRatio,
            QtCore.Qt.TransformationMode.SmoothTransformation
        )

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.SmoothPixmapTransform)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        pixmap = self.pixmapOut
        match self.state:
            case 'normal':
                pixmap = self.pixmapOut
            case 'hovered':
                pixmap = self.pixmapIn
            case 'activate':
                pixmap = self.pixmapAct
        painter.drawPixmap(self.rect(), pixmap)

    def enterEvent(self, event):
        self.state = 'hovered'

    def leaveEvent(self, event):
        self.state = 'normal'

    def mousePressEvent(self, e):
        if e.button() == QtCore.Qt.MouseButton.LeftButton:
            self.state = 'activate'
            self.update()
            e.accept()
        super().mousePressEvent(e)

    def mouseReleaseEvent(self, e):
        if e.button() == QtCore.Qt.MouseButton.LeftButton:
            self.state = 'hovered' if self.underMouse() else 'normal'
            self.update()
        super().mouseReleaseEvent(e)


class SaveLoadWidget(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(QtCore.Qt.WindowType.FramelessWindowHint |
                            QtCore.Qt.WindowType.Tool)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(320, 65)
        self.frame = pixmapLoader('save_rect_frame.png')
        self.box = QtWidgets.QHBoxLayout(self)

        self.btn_save_py = XButton(normal=r'save_load_widget_buttons\save_py_normal.png',
                                   hovered=r'save_load_widget_buttons\save_py_hovered.png',
                                   activate=r'save_load_widget_buttons\save_py_activate.png',
                                   size=46)
        self.btn_save_py.setToolTip('Save Python File\nfrom current tab')
        self.btn_save_k = XButton(normal=r'save_load_widget_buttons\save_k_normal.png',
                                  hovered=r'save_load_widget_buttons\save_k_hovered.png',
                                  activate=r'save_load_widget_buttons\save_k_activate.png',
                                  size=46)
        self.btn_save_k.setToolTip('Save Kaa File')
        self.btn_load_py = XButton(normal=r'save_load_widget_buttons\load_py_normal.png',
                                   hovered=r'save_load_widget_buttons\load_py_hovered.png',
                                   activate=r'save_load_widget_buttons\load_py_activate.png',
                                   size=46)
        self.btn_load_py.setToolTip('Load Python Files')

        self.btn_load_k = XButton(normal=r'save_load_widget_buttons\load_k_normal.png',
                                  hovered=r'save_load_widget_buttons\load_k_hovered.png',
                                  activate=r'save_load_widget_buttons\load_k_activate.png',
                                  size=46)
        self.btn_load_k.setToolTip('Load Kaa File')

        self.box.addWidget(self.btn_save_py, alignment=QtCore.Qt.AlignmentFlag.AlignVCenter)
        self.box.addWidget(self.btn_save_k, alignment=QtCore.Qt.AlignmentFlag.AlignVCenter)
        self.box.addWidget(self.btn_load_py, alignment=QtCore.Qt.AlignmentFlag.AlignVCenter)
        self.box.addWidget(self.btn_load_k, alignment=QtCore.Qt.AlignmentFlag.AlignVCenter)

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.drawPixmap(QtCore.QPoint(0, 0), self.frame)


#Оконный сплиттер
class EditorSplitter(QtWidgets.QSplitter):
    def __init__(self):
        super().__init__()
        self.setOrientation(QtCore.Qt.Orientation.Vertical)
        self.setMouseTracking(True)


#Тестер
if __name__ == '__main__':
    import sys

    app = QtWidgets.QApplication(sys.argv)
    win = MainButton()
    win.show()
    sys.exit(app.exec())
