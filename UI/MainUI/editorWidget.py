from PySide6 import QtWidgets, QtCore, QtGui

from Kaa_IDE.Core.loaders import pixmapLoader, cssLoader, version
from Kaa_IDE.Core.py_complitter import CompleterTableView
from Kaa_IDE.Core.highliter import EditorHighlighter
from Kaa_IDE.Core.block_analyzer import BlockAnalyzer


#Обертка-виджет
class Editor(QtWidgets.QWidget):
    editorFontChanged = QtCore.Signal(QtGui.QFont)

    def __init__(self):
        super().__init__()
        self.box = QtWidgets.QVBoxLayout(self)
        self.box.setContentsMargins(5, 5, 10, 0)
        self.editor = EditorMain(self)
        self.line_info = LineInfo(self)
        self.setWindowFlags(QtCore.Qt.WindowType.FramelessWindowHint)
        #Добавление виджетов
        self.box.addWidget(self.editor)
        self.box.addWidget(self.line_info, alignment=QtCore.Qt.AlignmentFlag.AlignLeft)
        #Удержание размеров шрифта
        self._fsize = None
        #Обработка сигналов
        self.setInitialFont()
        self.line_info.sb.setFont(self.editor.font())
        self.line_info.label1.setFont(self.editor.font())
        self.line_info.label2.setFont(self.editor.font())
        self.line_info.label4.setFont(self.editor.font())
        self.setMouseTracking(True)

    #Метод начальной установки шрифта
    def setInitialFont(self):
        """Установка начального моноширного шрифта"""
        fonts = ['JetBrains Mono', 'Consolas', 'Monaco',
                 'DejaVu Sans Mono', 'Source Code Pro', 'Courier New']

        available_fonts = QtGui.QFontDatabase.families()

        for font_name in fonts:
            if font_name in available_fonts:
                font = QtGui.QFont(font_name, 10)
                self._fsize = 10
                self.editor.setFont(font)
                break

    @QtCore.Slot(QtGui.QFont)
    def fontChanger(self, font):
        old_font = self.editor.font()
        old_family = old_font.family()
        new_family = font.family()
        if old_family == new_family:
            return

        self._fsize = old_font.pointSize()
        new_font = QtGui.QFont(font)
        new_font.setPointSize(self._fsize)
        self.editor.setFont(new_font)
        self.editorFontChanged.emit(new_font)

    def getEditor(self):
        return self.editor


#Редактор текста
class EditorMain(QtWidgets.QPlainTextEdit):
    #Сигнал для CTRL+Enter (оба варианта - Return или Num Enter)
    runCodeSignal = QtCore.Signal()
    #Сигнал - пересчет изменения блоков
    blockStateChanged = QtCore.Signal(int, int, int, bool)
    # Сигнал сброса env
    envRefresh = QtCore.Signal()
    # Сигнал на получение env
    getEnv = QtCore.Signal()
    # Сигнал для передачи точечной нотации
    pointNote = QtCore.Signal(str)

    #Инициализация редактора текста
    def __init__(self, parent):
        super().__init__(parent)
        # Point-note regex
        self.pt_regex1 = QtCore.QRegularExpression(r'[^a-zA-Z]([a-zA-Z]+.*)\.$')
        self.pt_regex2 = QtCore.QRegularExpression(r'([a-zA-Z]+.*)\.$')
        # Таймер для комплиттера
        self.compl_timer = QtCore.QTimer()
        self.compl_timer.setSingleShot(True)
        self.compl_timer.setInterval(150)
        self.compl_timer.timeout.connect(self.on_complitter_show)
        self.setWindowFlags(QtCore.Qt.WindowType.FramelessWindowHint)
        self.setFocusPolicy(QtCore.Qt.FocusPolicy.ClickFocus)
        self.setTabChangesFocus(False)
        self.setLineWrapMode(QtWidgets.QPlainTextEdit.LineWrapMode.NoWrap)
        self.setStyleSheet(cssLoader(r'qplain_text_edit.css'))  #Cтиль окна (qss)
        self.deco_icon = pixmapLoader(r'deco\deco_icon.png')
        self.alpha = 255
        # Хайлайтер
        self.highliter = EditorHighlighter(self.document())
        #Назначение документа и курсора
        self._font = self.font()
        self._fontSize = self._font.pointSize()
        #Line Number Area (нумерация блоков)
        self.line_number_area = LineNumberArea(self)
        self.blockCountChanged.connect(self.update_line_number_area_width)
        self.updateRequest.connect(self.update_line_number_area)
        self.update_line_number_area_width(0)
        self.cursor_line_visible = True
        self.cursor_line_color = QtGui.QColor('#453D3E43')
        self.cursorPositionChanged.connect(self.update)
        # Автокомплиттер
        self.complitter = CompleterTableView(self)
        self.start_complete = 0
        self.end_complete = 0
        self.complitter.hide()
        self.document().contentsChange.connect(self.new_contents_change)
        self.complitter.activated.connect(self.on_complite)
        # Анализатор блочности
        self.block_analyzer = BlockAnalyzer(self.document())
        self.block_structure = self.block_analyzer.analyze_document(self.document())
        self.blockCountChanged.connect(self.analyze_block_structure)
        # Доп кнопки
        self.unfold_all_btn = self.create_unfold_all_btn()
        self.show_hide_lines_btn = self.create_show_hide_lines_btn()
        self.env_btn = self.create_env_btn()
        self.updateRequest.connect(self.update_unfold_btn_pos)
        self.updateRequest.connect(self.update_lines_btn_pos)
        self.updateRequest.connect(self.update_env_btn_pos)
        self.unfold_all_btn.clicked.connect(self.unfold_all)
        #Шорткаты окна
        #Zoom (CTRL++, CTRL+-)
        self.ZoomInId1 = self.grabShortcut(QtGui.QKeySequence('Ctrl++'), QtCore.Qt.ShortcutContext.WidgetShortcut)
        self.ZoomInId2 = self.grabShortcut(QtGui.QKeySequence('Ctrl+='), QtCore.Qt.ShortcutContext.WidgetShortcut)
        self.shZoomOutId = self.grabShortcut(QtGui.QKeySequence('Ctrl+-'), QtCore.Qt.ShortcutContext.WidgetShortcut)
        #Run code (CTRL+ENTER)
        self.runCodeId1 = self.grabShortcut(QtGui.QKeySequence('Ctrl+Return'), QtCore.Qt.ShortcutContext.WidgetShortcut)
        self.runCodeId2 = self.grabShortcut(QtGui.QKeySequence('Ctrl+Enter'), QtCore.Qt.ShortcutContext.WidgetShortcut)
        #Copy and Insert Block (CTRL+D)
        self.pasteId = self.grabShortcut(QtGui.QKeySequence('Ctrl+D'), QtCore.Qt.ShortcutContext.WidgetShortcut)
        #SHIFT+TAB
        self.removeTabId = self.grabShortcut(QtGui.QKeySequence('Shift+Tab'), QtCore.Qt.ShortcutContext.WidgetShortcut)
        # CTRL+R - сброс env для текущего таба (Editor)
        self.refreshTab = self.grabShortcut(QtGui.QKeySequence('Ctrl+R'), QtCore.Qt.ShortcutContext.WidgetShortcut)
        #  CTRL+E - env to log
        self.envToLog = self.grabShortcut(QtGui.QKeySequence('Ctrl+E'), QtCore.Qt.ShortcutContext.WidgetShortcut)
        #Сигналы
        self.cursorPositionChanged.connect(self.on_cursor_change)
        self.cursorPositionChanged.connect(lambda: self.complitter.hide())
        # Считывание позиций курсора на изменение блоков
        self._last_cursor = self.textCursor().position()
        self._is_added = False
        self._old_block_count = self.blockCount()
        self._added = 0
        self._deleted = 0
        self.document().contentsChange.connect(self._old_cursor_recalc)
        self.blockCountChanged.connect(self.block_changer)

    # Доп кнопки и их пересчет
    def create_unfold_all_btn(self):
        btn = SubButton(parent=self.viewport(), normal=r'line_area_icons\unfold_all_normal.png',
                        hovered=r'line_area_icons\unfold_all_hovered.png',
                        active=r'line_area_icons\unfold_all_active.png')
        btn.setToolTip('Unfold All')
        x = self.viewport().width() - btn.width() - 2
        y = 0

        btn.move(QtCore.QPoint(x, y))
        return btn

    def create_show_hide_lines_btn(self):
        btn = SubButton(parent=self.viewport(), normal=r'line_area_icons\lines_normal.png',
                        hovered=r'line_area_icons\lines_hovered.png',
                        active=r'line_area_icons\lines_active.png')
        btn.setCheckable(True)
        btn.setChecked(True)
        btn.state = 'activate'
        btn.effect.setOpacity(0.3)
        btn.setToolTip('Show/Hide\nBlock Lines')

        x = self.viewport().width() - 2 * btn.width() - 2
        y = 0

        btn.move(QtCore.QPoint(x, y))
        return btn

    def create_env_btn(self):
        btn = SubButton(parent=self.viewport(), normal=r'line_area_icons\env_normal.png',
                        hovered=r'line_area_icons\env_hovered.png',
                        active=r'line_area_icons\env_active.png', sizeX=39, sizeY=24)

        btn.effect.setOpacity(0.3)
        btn.setToolTip('Environment Info')

        x = self.viewport().width() - 2 * self.show_hide_lines_btn.width() - btn.width() - 2
        y = 0

        btn.move(QtCore.QPoint(x, y))
        btn.clicked.connect(self.get_env)
        return btn

    def update_unfold_btn_pos(self):
        vp = self.viewport()
        self.unfold_all_btn.move(
            vp.width() - self.unfold_all_btn.width() - 4,
            4
        )

    def update_lines_btn_pos(self):
        vp = self.viewport()
        self.show_hide_lines_btn.move(
            vp.width() - 2 * self.show_hide_lines_btn.width() - 4,
            4
        )

    def update_env_btn_pos(self):
        vp = self.viewport()
        self.env_btn.move(
            vp.width() - 2 * self.show_hide_lines_btn.width() - self.env_btn.width() - 8,
            8
        )

    def get_env(self):
        self.getEnv.emit()

    @QtCore.Slot()
    def unfold_all(self):
        block_id = 0
        while self.document().findBlockByNumber(block_id).isValid():
            block = self.document().findBlockByNumber(block_id)
            block.setVisible(True)
            block_id += 1
        self.line_number_area.folding_data = []
        self.document().adjustSize()

    # Пересчет курсора
    def _old_cursor_recalc(self, pos, deleted, added):
        if added > 0:
            self._is_added = True
            self._added = added
        else:
            self._is_added = False
            self._deleted = deleted

    # Генерация сигнала на добавление-удаление блоков
    def block_changer(self):
        new_pos = self.textCursor().position()
        old_pos = 0
        new_block_count = self.blockCount()
        old_block_count = self._old_block_count
        if self._is_added:
            old_pos = new_pos - self._added
        else:
            old_pos = new_pos + self._deleted
        # Расчет дельты изменения блоков
        delta = abs(new_block_count - old_block_count)
        # Обнуление
        self._added = 0
        self._deleted = 0
        self._old_block_count = new_block_count

        if new_block_count > old_block_count:
            self._is_added = True
        else:
            self._is_added = False

        self.blockStateChanged.emit(old_pos, new_pos, delta, self._is_added)
        # print(old_pos,new_pos,delta,self._is_added) #Тестер

    def analyze_block_structure(self):
        self.block_structure = self.block_analyzer.analyze_document(self.document())
        # self.block_structure = self.block_structure[:-1]

    def paintEvent(self, event):
        # Задний фон
        self.draw_background(event)
        #Иконка - украшение
        self.draw_deco_icon(event)
        # Цветовая покраска маркеров закгладок
        self.draw_bookmark_lines(event)
        # Линия под курсором
        if self.cursor_line_visible:
            self.draw_cursor_line(event)
        # Линии - маркеры блоков
        self.draw_block_lines(event)
        # Иконки фолдинга
        self.draw_folded_icons(event)

        super().paintEvent(event)

    def draw_background(self, event):
        painter = QtGui.QPainter(self.viewport())
        painter.setCompositionMode(QtGui.QPainter.CompositionMode.CompositionMode_Source)
        color = QtGui.QColor('#1E1F22')
        color.setAlpha(self.alpha)
        painter.fillRect(self.rect(), color)

    def draw_bookmark_lines(self, event):
        painter = QtGui.QPainter(self.viewport())
        bookmark_data = self.line_number_area.bookmark_data
        doc = self.document()

        for bookmark in bookmark_data:
            block_number = bookmark[0]
            color = self.line_number_area.colors[bookmark[1]]

            block_geo = self.blockBoundingGeometry(doc.findBlockByNumber(block_number)).translated(self.contentOffset())
            painter.fillRect(block_geo, color)

    # Отрисовка иконок фолдинга (справа от текста)
    def draw_folded_icons(self, event):
        painter = QtGui.QPainter(self.viewport())
        painter.setOpacity(0.5)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        folding_data = self.line_number_area.folding_data
        metr = self.fontMetrics().horizontalAdvance(' ')

        pixmap = self.line_number_area.folded_pixmap
        scaled_pixmap = pixmap.scaledToHeight(self.fontMetrics().height() - 2,
                                              QtCore.Qt.TransformationMode.SmoothTransformation)

        for data in folding_data:
            fold_block_id = data[0]
            block = self.document().findBlockByNumber(fold_block_id)
            if not block.isVisible():
                continue

            block_rect = self.blockBoundingGeometry(block).translated(self.contentOffset())
            chars = len(block.text())

            width = metr * chars
            # Позиция справа от текста
            x = block_rect.left() + width + 10
            y = block_rect.y()

            painter.drawPixmap(int(x), int(y), scaled_pixmap)

    # Отрисовка линий курсора (подсветка блока с курсором)
    def draw_cursor_line(self, event):
        painter = QtGui.QPainter(self.viewport())
        current_block = self.textCursor().block()

        block_geo = self.blockBoundingGeometry(current_block).translated(self.contentOffset())
        # Градиент вместо сплошного цвета
        gradient = QtGui.QLinearGradient(block_geo.topLeft(), block_geo.topRight())
        gradient.setColorAt(0, QtGui.QColor('#803D3E43'))
        gradient.setColorAt(1, QtGui.QColor('#103D3E43'))

        painter.fillRect(block_geo, gradient)

    # Отрисовка иконки (правый нижн. угол)
    def draw_deco_icon(self, event):
        painter = QtGui.QPainter(self.viewport())
        painter.setCompositionMode(QtGui.QPainter.CompositionMode.CompositionMode_Screen)
        pixmap = self.deco_icon

        p_rect = pixmap.rect()
        s_rect = self.viewport().rect()

        x = s_rect.width() - 5 - p_rect.width()
        y = s_rect.height() - 5 - p_rect.height()

        painter.drawPixmap(QtCore.QPoint(x, y), pixmap)

    # Отрисовка вспомогательных линий
    def draw_block_lines(self, event):
        if not self.show_hide_lines_btn.isChecked():
            self.update()
            return
        # Рисуем в viewport()
        painter = QtGui.QPainter(self.viewport())
        pen = QtGui.QPen(QtGui.QColor('#bababa'))
        pen.setWidthF(0.15)
        painter.setPen(pen)

        space = self.fontMetrics().horizontalAdvance(' ')
        x_offset = self.horizontalScrollBar().value()  # компенсация горизонтального скроллинга
        pad = max(2, int(self.fontMetrics().height() * 0.08))  # пару пикселей padding

        lines = []  # активные: [[QLineF, indent], ...]
        ended_lines = []  # завершённые: [QLineF, ...]

        for s in self.block_structure:
            block = self.document().findBlockByNumber(s['id'])
            if not block.isValid() or not block.isVisible():
                continue

            indent = s['indent']
            level = s['level']
            is_opener = s['is_opener']

            # пропускаем верхние уровни
            if level is None or level == 0:
                if lines:
                    for line, line_indent in lines:
                        y_line = line.y2()
                        top = self.blockBoundingGeometry(block).translated(self.contentOffset()).top()
                        x = line_indent * space - x_offset
                        line.setP2(QtCore.QPointF(x, top - pad))
                        ended_lines.append(line)
                        lines.pop()
                continue
            # геометрия текущего блока
            geom = self.blockBoundingGeometry(block).translated(self.contentOffset())
            top = geom.top()
            bottom = geom.bottom()

            # --- СНАЧАЛА обновляем существующие линии (растягиваем или закрываем)
            new_active = []
            for line, line_indent in lines:
                if line_indent < indent:
                    # линия выше по уровню — продлеваем до верхней части текущей видимой области (не до bottom)
                    x = line_indent * space - x_offset
                    # подрезаем линию до верхней границы текущего блока минус pad:
                    line.setP2(QtCore.QPointF(x, bottom - pad))
                    new_active.append([line, line_indent])
                else:
                    # линия должна завершиться (ее уровень >= текущего)
                    # её завершаем чуть выше текущей строки (чтобы не лезла на text)
                    x = line_indent * space - x_offset
                    line.setP2(QtCore.QPointF(x, top - pad))
                    ended_lines.append(line)

            lines = new_active
            # --- ТЕПЕРЬ обрабатываем текущую строку
            if is_opener:
                # Для opener: создаём новую линию, стартующая чуть ниже bottom (чтобы не лезть на сам текст opener)
                x = indent * space - x_offset
                y0 = bottom + pad  # старт чуть ниже bottom
                new_line = QtCore.QLineF(QtCore.QPointF(x, y0), QtCore.QPointF(x, y0))
                lines.append([new_line, indent])
            else:
                # Для обычной строки: уже сделали подрез/закрытие выше — ничего больше не нужно
                pass

        # в конце: нарисуем активные и завершённые линии
        for line_info in lines:
            painter.drawLine(line_info[0])
        for line in ended_lines:
            painter.drawLine(line)

    #Перехват конкретных шорткатов (сочетания)
    def event(self, e):
        match e.type():
            case QtCore.QEvent.Type.Shortcut:
                if e.shortcutId() == self.ZoomInId1 or e.shortcutId() == self.ZoomInId2:
                    self.font_size_change(delta=1)
                    self.update_line_number_area_width(self.blockCount())
                    self.update()
                    return True
                elif e.shortcutId() == self.shZoomOutId:
                    self.font_size_change(delta=-1)
                    self.update_line_number_area_width(self.blockCount())
                    self.update()
                    return True
                elif e.shortcutId() == self.runCodeId1 or e.shortcutId() == self.runCodeId2:
                    self.runCodeSignal.emit()
                    return True
                elif e.shortcutId() == self.pasteId:
                    self.pasteFragment()
                    return True
                elif e.shortcutId() == self.removeTabId:
                    self.shiftTabKey()
                    return True
                elif e.shortcutId() == self.refreshTab:
                    self.envRefresh.emit()
                    return True
                elif e.shortcutId() == self.envToLog:
                    self.getEnv.emit()
                    return True
            case _:
                return super().event(e)

        return False

    # Перехват одиночных нажатий
    def keyPressEvent(self, e):
        # Тестовая проверка
        match e.key():
            case QtCore.Qt.Key.Key_Space:
                self.complitter.rebuild_base()
                super().keyPressEvent(e)
            case QtCore.Qt.Key.Key_Tab:
                self.tabKey()
                e.accept()
            case QtCore.Qt.Key.Key_Return:
                if self.complitter.isVisible():  # Учет комплиттера
                    self.on_complite()
                    self.complitter.rebuild_base()
                else:
                    self.enterKey()
                    self.complitter.rebuild_base()
                    self.compl_timer.stop()  # Отключаем вывод комплиттера при явном Enter
                e.accept()
            case QtCore.Qt.Key.Key_Enter:
                if self.complitter.isVisible():  # Учет комплиттера
                    self.on_complite()
                    self.complitter.rebuild_base()
                else:
                    self.enterKey()
                    self.complitter.rebuild_base()
                    self.compl_timer.stop()  # Отключаем вывод комплиттера при явном Enter
                e.accept()
            case QtCore.Qt.Key.Key_Apostrophe:
                self.insertPair(left="'", right="'")
                e.accept()
            case QtCore.Qt.Key.Key_QuoteDbl:
                self.insertPair(left='"', right='"')
                e.accept()
            case QtCore.Qt.Key.Key_ParenLeft:
                self.insertPair(left='(', right=')')
                e.accept()
            case QtCore.Qt.Key.Key_ParenRight:
                self.closePair(right=')')
                e.accept()
            case QtCore.Qt.Key.Key_BraceLeft:
                self.insertPair(left='{', right='}')
                e.accept()
            case QtCore.Qt.Key.Key_BraceRight:
                self.closePair(right='}')
                e.accept()
            case QtCore.Qt.Key.Key_BracketLeft:
                self.insertPair(left='[', right=']')
                e.accept()
            case QtCore.Qt.Key.Key_BracketRight:
                self.closePair(right=']')
                e.accept()
            case QtCore.Qt.Key.Key_Slash:
                if e.modifiers() & QtCore.Qt.KeyboardModifier.ControlModifier:
                    self.comment()
                    e.accept()
                else:
                    self.textCursor().insertText('/')
                    e.accept()
            case QtCore.Qt.Key.Key_Up:
                if self.complitter.isVisible():
                    self.up_arrow()
                    e.accept()
                else:
                    if e.modifiers() & QtCore.Qt.KeyboardModifier.ControlModifier:
                        self.move_to_bookmark(direction='up')
                    else:
                        return super().keyPressEvent(e)
            case QtCore.Qt.Key.Key_Down:
                if self.complitter.isVisible():
                    self.down_arrow()
                    e.accept()
                else:
                    if e.modifiers() & QtCore.Qt.KeyboardModifier.ControlModifier:
                        self.move_to_bookmark(direction='down')
                    else:
                        return super().keyPressEvent(e)
            case QtCore.Qt.Key.Key_Period:
                super().keyPressEvent(e)
                self.point_note()
            case _:
                return super().keyPressEvent(e)

    #Методы для автоматических операций (одиночные клавиши)
    # Точечная нотация
    def point_note(self):
        result = ''
        cursor = QtGui.QTextCursor(self.textCursor())
        pattern = '()=, '
        # 1 - Смещаемся на точку
        cursor.movePosition(QtGui.QTextCursor.MoveOperation.Left)
        # 2 - Проверяем не в начале ли блока
        if cursor.atBlockStart():
            return

        # 3 - двигаем с выделением
        while True:
            cursor.movePosition(QtGui.QTextCursor.MoveOperation.Left,
                                QtGui.QTextCursor.MoveMode.KeepAnchor)
            if cursor.atBlockStart():
                break

            txt = cursor.selectedText()

            if txt.startswith(tuple(pattern)):
                cursor.movePosition(QtGui.QTextCursor.MoveOperation.Right,
                                    QtGui.QTextCursor.MoveMode.KeepAnchor)
                break
        # 4 - корректируем результат
        result = cursor.selectedText()
        if result.startswith('.'):
            result = ''
        elif result.startswith('('):
            result = result[1:]

        self.pointNote.emit(result)
        # print('Нажата точка', result) # Тестилка

    #Smart-отступы для ввода (Enter-Return)
    def enterKey(self):
        spacer = ''
        std_spacer = ''
        ender = ''

        self.textCursor().beginEditBlock()
        regex_ident = QtCore.QRegularExpression(r'^ +')
        regex_end = QtCore.QRegularExpression(r':\s*$')

        block_str = self.textCursor().block().text()
        match1 = regex_ident.match(block_str)
        match2 = regex_end.match(block_str)

        if match1.hasMatch():  # Контроль отступов
            spacer = match1.captured(0)
        if match2.hasMatch():  # Контроль отступов после (:)
            block_num = self.textCursor().blockNumber()
            if self.textCursor().atBlockEnd():
                if self.document().findBlockByNumber(block_num + 1).isValid() and not self.document().findBlockByNumber(
                        block_num + 1).isVisible():
                    while self.document().findBlockByNumber(
                            block_num + 1).isValid() and not self.document().findBlockByNumber(
                        block_num + 1).isVisible():
                        block_num += 1
                    end_block = self.document().findBlockByNumber(block_num)
                    pos = end_block.position() + end_block.length() - 1
                    cursor = self.textCursor()
                    cursor.setPosition(pos)
                    self.setTextCursor(cursor)
                else:
                    std_spacer = ' ' * 4

        self.insertPlainText('\n' + spacer + std_spacer + ender)

        self.textCursor().endEditBlock()

    #Подмена Tab на 4 пробела
    def tabKey(self):
        cursor = self.textCursor()
        doc = self.document()

        cursor.beginEditBlock()
        try:
            if cursor.hasSelection():
                start_block = doc.findBlock(cursor.selectionStart())
                end_block = doc.findBlock(cursor.selectionEnd())

                for block_num in range(start_block.blockNumber(), end_block.blockNumber() + 1):
                    block = doc.findBlockByNumber(block_num)
                    c = QtGui.QTextCursor(block)
                    c.movePosition(QtGui.QTextCursor.MoveOperation.StartOfBlock)
                    c.insertText(' ' * 4)
            else:
                self.insertPlainText(' ' * 4)
        finally:
            cursor.endEditBlock()

    #МЕТОДЫ для автоматических операций (комбинации клавиш)
    #SHIFT+TAB удаление отступов (обертка в 1 действие)
    def shiftTabKey(self):
        cursor = self.textCursor()
        doc = self.document()
        regex = QtCore.QRegularExpression(r"^ +")
        cursor.beginEditBlock()
        try:
            if cursor.hasSelection():
                start_block = doc.findBlock(cursor.selectionStart())
                end_pos = cursor.selectionEnd()
                if end_pos > cursor.selectionStart():
                    end_pos -= 1
                end_block = doc.findBlock(end_pos)

                for block_num in range(start_block.blockNumber(),
                                       end_block.blockNumber() + 1):
                    block = doc.findBlockByNumber(block_num)
                    text = block.text()
                    match = regex.match(text)
                    if match.hasMatch():
                        remove = min(4, len(match.captured(0)))
                        c = QtGui.QTextCursor(block)
                        c.movePosition(QtGui.QTextCursor.MoveOperation.StartOfBlock)
                        c.movePosition(QtGui.QTextCursor.MoveOperation.Right,
                                       QtGui.QTextCursor.MoveMode.KeepAnchor,
                                       n=remove)
                        c.removeSelectedText()
            else:
                block = cursor.block()
                text = block.text()
                match = regex.match(text)
                if match.hasMatch():
                    remove = min(4, len(match.captured(0)))
                    c = QtGui.QTextCursor(block)
                    c.movePosition(QtGui.QTextCursor.MoveOperation.StartOfBlock)
                    c.movePosition(QtGui.QTextCursor.MoveOperation.Right,
                                   QtGui.QTextCursor.MoveMode.KeepAnchor,
                                   n=remove)
                    c.removeSelectedText()
        finally:
            cursor.endEditBlock()
            self.setTextCursor(cursor)

    #Метод для CTRL+D
    def pasteFragment(self):
        cursor = self.textCursor()
        cursor.beginEditBlock()

        try:
            if cursor.hasSelection():
                sel_text = cursor.selectedText().replace('\u2029', '\n')
                start_pos = cursor.selectionStart()
                end_pos = cursor.selectionEnd()
                cursor.clearSelection()
                cursor.setPosition(end_pos)
                cursor.insertText(sel_text)
                cursor.movePosition(QtGui.QTextCursor.MoveOperation.Left,
                                    QtGui.QTextCursor.MoveMode.KeepAnchor, n=end_pos - start_pos)
            else:
                cursor.select(QtGui.QTextCursor.SelectionType.BlockUnderCursor)
                sel_text = cursor.selectedText().replace('\u2029', '\n')
                cursor.movePosition(QtGui.QTextCursor.MoveOperation.EndOfBlock)

                if sel_text.startswith('\n'):
                    cursor.insertText(sel_text)
                else:
                    cursor.insertText('\n' + sel_text)
        finally:
            cursor.endEditBlock()
            self.setTextCursor(cursor)

    #Метод для измененния QFont (шорткаты CTRL++ и CTRL+-)
    def font_size_change(self, delta: int) -> None:
        self._fontSize += delta
        if self._fontSize < 6:
            self._fontSize = 6
        elif self._fontSize > 14:
            self._fontSize = 14

        new_font = self.font()
        new_font.setPointSize(self._fontSize)
        self.setFont(new_font)

    #Метод для самрт-комментирования строк (CTRL+/)
    def comment(self):
        cursor = self.textCursor()
        doc = self.document()
        regex1 = QtCore.QRegularExpression(r"^ +")
        regex2 = QtCore.QRegularExpression(r"^ +#+")
        regex3 = QtCore.QRegularExpression(r"^#+")
        regex4 = QtCore.QRegularExpression(r"^ +\Z")
        regex5 = QtCore.QRegularExpression(r"^\Z")
        cursor.beginEditBlock()
        try:
            if cursor.hasSelection():
                start_block = doc.findBlock(cursor.selectionStart())
                end_pos = cursor.selectionEnd()
                if end_pos > cursor.selectionStart():
                    end_pos -= 1
                end_block = doc.findBlock(end_pos)
                for block_num in range(start_block.blockNumber(),
                                       end_block.blockNumber() + 1):
                    block = doc.findBlockByNumber(block_num)
                    text = block.text()
                    match1 = regex1.match(text)
                    if match1.hasMatch():
                        c_move = len(match1.captured(0))
                        c = QtGui.QTextCursor(block)
                        match2 = regex2.match(text)
                        match3 = regex4.match(text)
                        match4 = regex5.match(text)
                        c.movePosition(QtGui.QTextCursor.MoveOperation.StartOfBlock)
                        c.movePosition(QtGui.QTextCursor.MoveOperation.Right,
                                       QtGui.QTextCursor.MoveMode.MoveAnchor,
                                       n=c_move)
                        if match2.hasMatch():
                            c_select = len(match2.captured(0)) - c_move
                            c.movePosition(QtGui.QTextCursor.MoveOperation.Right,
                                           QtGui.QTextCursor.MoveMode.KeepAnchor,
                                           n=c_select)
                            c.removeSelectedText()
                        elif match3.hasMatch() or match4.hasMatch():
                            pass
                        else:
                            c.insertText('#')
                    else:
                        match2 = regex3.match(text)
                        match3 = regex4.match(text)
                        match4 = regex5.match(text)
                        if match2.hasMatch():
                            c = QtGui.QTextCursor(block)
                            c_select = len(match2.captured(0))
                            c.movePosition(QtGui.QTextCursor.MoveOperation.StartOfBlock)
                            c.movePosition(QtGui.QTextCursor.MoveOperation.Right,
                                           QtGui.QTextCursor.MoveMode.KeepAnchor,
                                           n=c_select)
                            c.removeSelectedText()
                        elif match3.hasMatch() or match4.hasMatch():
                            pass
                        else:
                            c = QtGui.QTextCursor(block)
                            c.movePosition(QtGui.QTextCursor.MoveOperation.StartOfBlock)
                            c.insertText('#')
            else:
                block = doc.findBlock(cursor.position())
                text = block.text()
                match1 = regex1.match(text)
                if match1.hasMatch():
                    c_move = len(match1.captured(0))
                    c = QtGui.QTextCursor(block)
                    match2 = regex2.match(text)
                    match3 = regex4.match(text)
                    c.movePosition(QtGui.QTextCursor.MoveOperation.StartOfBlock)
                    c.movePosition(QtGui.QTextCursor.MoveOperation.Right,
                                   QtGui.QTextCursor.MoveMode.MoveAnchor,
                                   n=c_move)
                    if match2.hasMatch():
                        c_select = len(match2.captured(0)) - c_move
                        c.movePosition(QtGui.QTextCursor.MoveOperation.Right,
                                       QtGui.QTextCursor.MoveMode.KeepAnchor,
                                       n=c_select)
                        c.removeSelectedText()
                    elif match3.hasMatch():
                        pass
                    else:
                        c.insertText('#')
                else:
                    match2 = regex3.match(text)
                    match3 = regex5.match(text)
                    if match2.hasMatch():
                        c = QtGui.QTextCursor(block)
                        c_select = len(match2.captured(0))
                        c.movePosition(QtGui.QTextCursor.MoveOperation.StartOfBlock)
                        c.movePosition(QtGui.QTextCursor.MoveOperation.Right,
                                       QtGui.QTextCursor.MoveMode.KeepAnchor,
                                       n=c_select)
                        c.removeSelectedText()
                    elif match3.hasMatch():
                        pass
                    else:
                        c = QtGui.QTextCursor(block)
                        c.movePosition(QtGui.QTextCursor.MoveOperation.StartOfBlock)
                        c.insertText('#')
        finally:
            cursor.endEditBlock()

    #ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ
    #Универсальный метод вставки пары
    def insertPair(self, left: str, right: str) -> None:
        cursor = self.textCursor()
        cursor.beginEditBlock()
        if cursor.hasSelection():
            pos_start = cursor.selectionStart()
            pos_end = cursor.selectionEnd()
            cursor.setPosition(pos_end)
            cursor.insertText(right)
            cursor.setPosition(pos_start)
            cursor.insertText(left)
            cursor.setPosition(pos_start + 1)
            cursor.movePosition(QtGui.QTextCursor.MoveOperation.Right,
                                QtGui.QTextCursor.MoveMode.KeepAnchor,
                                n=pos_end - pos_start)
        else:
            pos = cursor.position()
            cursor.movePosition(QtGui.QTextCursor.MoveOperation.Left,
                                QtGui.QTextCursor.MoveMode.KeepAnchor)
            prev_char = cursor.selectedText()
            cursor.clearSelection()
            cursor.setPosition(pos)
            cursor.movePosition(QtGui.QTextCursor.MoveOperation.Right,
                                QtGui.QTextCursor.MoveMode.KeepAnchor)
            next_char = cursor.selectedText()
            cursor.clearSelection()
            cursor.setPosition(pos)

            if prev_char in [left, right] or next_char in [left, right]:
                cursor.insertText(left)
                cursor.setPosition(pos + 1)
            else:
                cursor.insertText(left + right)
                cursor.setPosition(pos + 1)

        cursor.endEditBlock()
        self.setTextCursor(cursor)

    #Избегание добавления закр. пары внутри
    def closePair(self, right: str) -> None:
        cursor = self.textCursor()
        pos = cursor.position()
        cursor.movePosition(QtGui.QTextCursor.MoveOperation.Right,
                            QtGui.QTextCursor.MoveMode.KeepAnchor)
        char = cursor.selectedText()
        cursor.movePosition(QtGui.QTextCursor.MoveOperation.Left,
                            QtGui.QTextCursor.MoveMode.MoveAnchor)
        cursor.clearSelection()
        if char == right:
            cursor.setPosition(pos + 1)
            self.setTextCursor(cursor)
        else:
            cursor.setPosition(pos)
            cursor.insertText(right)

    # Move to bookmarks
    def move_to_bookmark(self, direction: str) -> None:
        bookmarks = list(self.line_number_area.bookmark_blocks)
        bookmarks.sort()
        cursor = self.textCursor()
        current_block = self.textCursor().blockNumber()
        block = self.document().findBlockByNumber(current_block)
        new_block_num = None

        if direction == 'up':
            bookmarks.reverse()
            for b in bookmarks:
                if current_block > b:
                    new_block_num = b
                    if not self.document().findBlockByNumber(b).isVisible():
                        new_block_num = None
                        continue
                    else:
                        break
                else:
                    new_block_num = None
        else:
            for b in bookmarks:
                if current_block < b:
                    new_block_num = b
                    if not self.document().findBlockByNumber(b).isVisible():
                        new_block_num = None
                        continue
                    else:
                        break
                else:
                    new_block_num = None

        if new_block_num is None:
            cursor.setPosition(block.position() + block.length() - 1)
            self.setTextCursor(cursor)
            self.ensureCursorVisible()
        else:
            new_block = self.document().findBlockByNumber(new_block_num)
            cursor.setPosition(new_block.position() + new_block.length() - 1)
            self.setTextCursor(cursor)
            self.ensureCursorVisible()

    #Line Number Area Methods
    def line_number_area_width(self):
        digits = len(str(max(1, self.blockCount())))
        space = 40 + self.fontMetrics().horizontalAdvance('0') * digits
        return space

    def update_line_number_area_width(self, new_block_count):
        self.setViewportMargins(self.line_number_area_width() + 2, 0, 0, 0)

    def update_line_number_area(self, rect, dy):
        if dy:
            self.line_number_area.scroll(0, dy)
        else:
            self.line_number_area.update(0, rect.y(), self.line_number_area_width(), rect.height())

    def resizeEvent(self, event):
        super().resizeEvent(event)
        cr = self.contentsRect()
        self.line_number_area.setGeometry(QtCore.QRect(cr.left(), cr.top(),
                                                       self.line_number_area_width(), cr.height()))
        self.complitter.hide()

    def line_number_area_paint_event(self, event):
        painter = QtGui.QPainter(self.line_number_area)
        painter.fillRect(event.rect(), QtGui.QColor('#203D3E43'))
        pen = QtGui.QPen(QtGui.QColor('#bababa'))
        pen.setWidthF(0.15)
        painter.setPen(pen)
        painter.drawLine(event.rect().right(),
                         event.rect().top(),
                         event.rect().right(),
                         event.rect().bottom())
        painter.setFont(self.font())
        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        top = self.blockBoundingGeometry(block).translated(self.contentOffset()).top()
        bottom = top + self.blockBoundingRect(block).height()
        fold_data = self.line_number_area.folding_data

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(block_number + 1)
                painter.setPen(pen)

                if block_number in self.line_number_area.bookmark_blocks:  # Рисуем флажки или цифры номеров блоков
                    for i, elem in enumerate(self.line_number_area.bookmark_data):
                        if block_number == elem[0]:
                            idx = elem[1]
                            pix = self.line_number_area.bookmark_icons[idx]
                            sc_pix = pix.scaledToHeight(self.fontMetrics().height() - 2,
                                                        QtCore.Qt.TransformationMode.SmoothTransformation)
                            x = 10
                            y = top + (self.blockBoundingRect(block).height() - sc_pix.height()) / 2
                            painter.setCompositionMode(QtGui.QPainter.CompositionMode.CompositionMode_Screen)
                            painter.drawPixmap(int(x), int(y), sc_pix)
                            painter.setCompositionMode(QtGui.QPainter.CompositionMode.CompositionMode_SourceOver)
                else:
                    painter.drawText(0, top, self.line_number_area_width() - 30,
                                     self.fontMetrics().height(),
                                     QtCore.Qt.AlignmentFlag.AlignCenter, number)
            # Отрисовка фолдеров
            if 0 <= block_number < len(self.block_structure) and block.isVisible():
                if self.block_structure[block_number]['is_opener'] and self.line_number_area.icon_opacity > 0:
                    painter.setOpacity(self.line_number_area.icon_opacity)

                    pixmap = self.line_number_area.fold_pixmap

                    for elem in fold_data:
                        if block_number == elem[0]:
                            pixmap = self.line_number_area.unfold_pixmap
                            break
                        else:
                            pixmap = self.line_number_area.fold_pixmap

                    painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
                    scaled_pixmap = pixmap.scaledToHeight(self.fontMetrics().height() - 2,
                                                          QtCore.Qt.TransformationMode.SmoothTransformation)
                    x = self.line_number_area.width() - scaled_pixmap.width() - 4  # отступ справа
                    y = top + (self.blockBoundingRect(block).height() - scaled_pixmap.height()) / 2  # по центру блока
                    painter.drawPixmap(int(x), int(y), scaled_pixmap)
                    painter.setOpacity(1.0)

            block = block.next()
            top = bottom
            bottom = top + self.blockBoundingRect(block).height()
            block_number += 1

    #Обработчики сигналов
    def on_cursor_change(self):
        self.ensureCursorVisible()
    # Переделываем
    def new_contents_change(self, cursor_pos, deleted, created):
        self.compl_timer.stop()
        self.complitter.hide()

        if deleted > 0 or created > 10:
            return

        group = tuple('().{}[] ,')

        cursor = QtGui.QTextCursor(self.textCursor())
        txt = ''

        while True:
            if cursor.atBlockStart():
                break

            cursor.movePosition(QtGui.QTextCursor.MoveOperation.Left,
                                QtGui.QTextCursor.MoveMode.KeepAnchor)

            if cursor.selectedText().startswith(group) or cursor.atBlockStart():
                txt = cursor.selectedText()[1:]
                break

        if len(txt) > 0:
            self.complitter.filter_proxy(txt)
            self.complitter.sortByColumn(0, QtCore.Qt.SortOrder.DescendingOrder)
            self.compl_timer.start()

        if cursor.atBlockStart():
            self.start_complete = cursor.selectionStart()
        else:
            self.start_complete = cursor.selectionStart() + 1
        self.end_complete = cursor.selectionEnd()
        cursor.clearSelection()

    # Отображение комплиттера по таймеру
    def on_complitter_show(self):
        if self.complitter.height() <= 0:  #Предотвращаем show 0-го комплиттера
            return

        cursor = self.textCursor()
        rect = self.cursorRect(cursor)
        global_pos = self.mapToGlobal(rect.bottomLeft())

        screen_geo = QtWidgets.QApplication.primaryScreen().availableGeometry()
        complitter_size = self.complitter.size()

        if global_pos.y() + complitter_size.height() > screen_geo.bottom():
            global_pos = self.mapToGlobal(rect.topLeft() - QtCore.QPoint(0, complitter_size.height()))

        self.complitter.move(global_pos)
        self.complitter.show()

    # Функция Enter для комплиттера ()
    @QtCore.Slot()
    def on_complite(self):
        index = self.complitter.currentIndex()
        if not index.isValid():
            return

        text = index.data()  # текст выбранного пункта
        meta = index.sibling(index.row(), 1).data()  # текст мета (1ой колонки) для анализа поведения курсора

        if meta == "builtins" or meta == "def function" or meta == "methods" or meta == "functions":
            cursor = self.textCursor()
            cursor.setPosition(self.start_complete)
            cursor.setPosition(self.end_complete, QtGui.QTextCursor.MoveMode.KeepAnchor)
            cursor.removeSelectedText()
            cursor.insertText(text + "()")
            cursor.movePosition(QtGui.QTextCursor.MoveOperation.Left)
            self.setTextCursor(cursor)
            self.compl_timer.stop()
        else:
            cursor = self.textCursor()
            cursor.setPosition(self.start_complete)
            cursor.setPosition(self.end_complete, QtGui.QTextCursor.MoveMode.KeepAnchor)
            cursor.removeSelectedText()
            cursor.insertText(text)
            self.compl_timer.stop()

    # Функции стрелок для комплиттера
    def up_arrow(self):
        self.complitter.select_previous()

    def down_arrow(self):
        self.complitter.select_next()


#Линии редактора + код фолдинг + bookmarks
class LineNumberArea(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.editor = parent
        # Иконки фолдинга
        self.unfold_pixmap = pixmapLoader(r'line_area_icons\unfold_icon.png')
        self.fold_pixmap = pixmapLoader(r'line_area_icons\fold_icon.png')
        self.folded_pixmap = pixmapLoader(r'line_area_icons\folded_icon.png')
        # Данные фолдинга
        self.folding_data = []
        # Данные bookmark + цвета + иконки
        self.bookmark_data = []
        self.bookmark_blocks = set()
        self.colors = [QtGui.QColor.fromRgb(245, 22, 62, a=30),
                       QtGui.QColor.fromRgb(97, 245, 22, a=30),
                       QtGui.QColor.fromRgb(22, 180, 245, a=30),
                       QtGui.QColor.fromRgb(198, 22, 245, a=30),
                       QtGui.QColor.fromRgb(245, 233, 23, a=30),
                       QtGui.QColor.fromRgb(22, 245, 237, a=30)]
        self.bookmark_icons = [pixmapLoader(r'line_area_icons\Book_0.png'),
                               pixmapLoader(r'line_area_icons\Book_1.png'),
                               pixmapLoader(r'line_area_icons\Book_2.png'),
                               pixmapLoader(r'line_area_icons\Book_3.png'),
                               pixmapLoader(r'line_area_icons\Book_4.png'),
                               pixmapLoader(r'line_area_icons\Book_5.png'),
                               pixmapLoader(r'line_area_icons\Book_vis.png')]
        # Данные о курсорах

        self.setMouseTracking(True)
        self.icon_opacity = 0.0
        self.anim = QtCore.QPropertyAnimation(self, b'icon_opacity_prop')
        self.anim.setDuration(300)
        self.editor.blockStateChanged.connect(self.update_folding_data)
        self.editor.blockStateChanged.connect(self.update_bookmark_data)

    def _update_cursor(self, old, new):
        self._old_cursor = old
        self._new_cursor = new

    @QtCore.Slot()
    def update_bookmark_data(self, old_pos, new_pos, delta, is_added):

        if not self.bookmark_data:
            return

        doc = self.editor.document()
        block_count = self.editor.blockCount()
        delta = abs(delta)

        start_pos = min(old_pos, new_pos)
        end_pos = max(old_pos, new_pos)
        start_block = doc.findBlock(start_pos)
        start_block_num = start_block.blockNumber()

        new_bookmarks = []
        new_bookmark_blocks = set()

        for book in self.bookmark_data:
            block_num = book[0]

            # --- защита
            if block_num < 0 or block_num >= block_count:
                continue

            # --- добавление блоков
            if is_added:
                if block_num > start_block_num:
                    block_num += delta

            # --- удаление блоков
            else:
                if start_block_num < block_num < start_block_num + delta:
                    continue  # bookmark удалён
                elif block_num >= start_block_num + delta:
                    block_num -= delta

            # --- финальная проверка
            if 0 <= block_num < block_count:
                book[0] = block_num
                new_bookmarks.append(book)
                new_bookmark_blocks.add(block_num)

        self.bookmark_data = new_bookmarks
        self.bookmark_blocks = new_bookmark_blocks

    @QtCore.Slot()
    def update_folding_data(self, old_pos, new_pos, delta, is_added):

        doc = self.editor.document()
        structure = self.editor.block_structure
        block_count = self.editor.blockCount()

        start_pos = min(old_pos, new_pos)
        start_block = doc.findBlock(start_pos)
        start_block_num = start_block.blockNumber()

        new_folding = []

        for opener, folded_blocks in self.folding_data:

            # --- 1. Блок вышел за пределы документа
            if opener >= block_count:
                continue

            # --- 2. Добавление блоков
            if is_added:
                if opener >= start_block_num:
                    opener += delta
                    folded_blocks = [b + delta for b in folded_blocks]

            # --- 3. Удаление блоков
            else:
                if opener > start_block_num:
                    opener -= delta
                    folded_blocks = [b - delta for b in folded_blocks]

                elif opener == start_block_num:
                    continue  # opener удалён → весь folding исчезает

            # --- 4. Проверка, что opener всё ещё валиден
            if opener < 0 or opener >= len(structure):
                continue

            if not structure[opener]['is_opener']:
                continue

            new_folding.append([opener, folded_blocks])

        self.folding_data = new_folding

    def get_icon_opacity(self):
        return self.icon_opacity

    def set_icon_opacity(self, value):
        self.icon_opacity = value
        self.update()

    icon_opacity_prop = QtCore.Property(float, get_icon_opacity, set_icon_opacity)

    def sizeHint(self):
        return QtCore.QSize(self.editor.line_number_area_width(), 0)

    def paintEvent(self, event):
        self.editor.line_number_area_paint_event(event)

    def enterEvent(self, event):
        self.anim.stop()
        self.anim.setStartValue(self.icon_opacity)
        self.anim.setEndValue(1.0)
        self.anim.start()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.anim.stop()
        self.anim.setStartValue(self.icon_opacity)
        self.anim.setEndValue(0.0)
        self.anim.start()
        super().leaveEvent(event)

    # Клики по Line Number Area
    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.MouseButton.LeftButton:  # Клики ЛКМ
            w = self.editor.line_number_area_width()
            x = event.pos().x()
            y = event.pos().y()
            structure = self.editor.block_structure
            if x > w / 2:  # Fold - unfold по клику (плавая половина Line Number Area)
                cursor = self.editor.cursorForPosition(QtCore.QPoint(0, y))
                block_id = cursor.block().blockNumber()
                if structure[block_id].get('is_opener'):
                    if self.folding_data:
                        for elem in self.folding_data:
                            if block_id == elem[0]:
                                self.unfold(block_id)
                                return

                    hiddens = self.fold(block_id)
                    start = block_id
                    self.folding_data.append([start, hiddens])
                    # print(self.folding_data)  # Тест
            else:  # Bookmark по клику (плавая половина Line Number Area)
                cursor = self.editor.cursorForPosition(QtCore.QPoint(0, y))
                block_id = cursor.block().blockNumber()

                if self.bookmark_data:
                    if block_id in self.bookmark_blocks:
                        for i, elem in enumerate(self.bookmark_data):
                            if block_id == elem[0]:
                                if event.modifiers() & QtCore.Qt.KeyboardModifier.AltModifier:
                                    elem[1] -= 1
                                else:
                                    elem[1] += 1
                                if elem[1] >= len(self.colors) or elem[1] < 0:
                                    self.bookmark_data.pop(i)
                                    self.bookmark_blocks.discard(block_id)
                                break
                    else:
                        if not event.modifiers() & QtCore.Qt.KeyboardModifier.AltModifier:
                            self.bookmark_blocks.add(block_id)
                            self.bookmark_data.append([block_id, 0])
                else:
                    if not event.modifiers() & QtCore.Qt.KeyboardModifier.AltModifier:
                        self.bookmark_blocks.add(block_id)
                        self.bookmark_data.append([block_id, 0])
                if event.modifiers() & QtCore.Qt.KeyboardModifier.ControlModifier:  # CTRL+ЛКМ (убираем закладку)
                    self.bookmark_blocks.discard(block_id)
                    for i, elem in enumerate(self.bookmark_data):
                        if block_id == elem[0]:
                            self.bookmark_data.pop(i)
                            break

                # print(self.bookmark_data)  # Тестер

        super().mousePressEvent(event)

    def wheelEvent(self, event):
        delta = event.angleDelta().y() / 8
        steps = delta / 15
        scroll_bar = self.editor.verticalScrollBar()
        scroll_bar.setValue(scroll_bar.value() - scroll_bar.singleStep() * steps)
        event.accept()

    # Свертывание по клику
    def fold(self, block_id):
        id = block_id
        structure = self.editor.block_structure
        start_level = structure[block_id]['level']
        start_indent = structure[block_id]['indent']
        hiddens = []
        doc = self.editor.document()

        while True:
            id += 1
            # Предохранители (выход за пределы id, пустой уровень, уменьш. отступ, одноуровневые старты)
            if id >= len(structure):
                break
            if structure[id]['level'] is None:
                break
            if structure[id]['indent'] < start_indent:
                break
            if structure[id]['is_opener'] and structure[id]['indent'] == start_indent:
                break

            # Одинаковый уровень + открывания (блоки на одном уровне)
            if structure[id]['is_opener'] and structure[id]['level'] == start_level:
                break
            elif not structure[id]['is_opener'] and structure[id]['level'] < start_level:
                break
            elif not structure[id]['is_opener'] and structure[id]['level'] == start_level:
                block = self.editor.document().findBlockByNumber(id)
                hiddens.append(id)
                block.setVisible(False)

                doc.markContentsDirty(block.position(), block.length())
            elif not structure[id]['is_opener'] and structure[id]['level'] > start_level:
                if structure[id]['indent'] > start_indent:
                    block = self.editor.document().findBlockByNumber(id)
                    hiddens.append(id)
                    block.setVisible(False)
                    doc.markContentsDirty(block.position(), block.length())
                else:
                    break
            elif structure[id]['is_opener'] and structure[id]['level'] > start_level:
                block = self.editor.document().findBlockByNumber(id)
                hiddens.append(id)
                block.setVisible(False)
                doc.markContentsDirty(block.position(), block.length())

        rev_hiddens = hiddens[::-1]
        for i, idx in enumerate(rev_hiddens):
            block = self.editor.document().findBlockByNumber(idx)
            text = block.text()
            if text.strip() == '':
                rev_hiddens.pop(i)
                block.setVisible(True)
            else:
                break
        return rev_hiddens[::-1]

    # Развертывание по клику
    def unfold(self, block_id):
        if self.folding_data:
            for index, elem in enumerate(self.folding_data):
                if block_id == elem[0]:
                    grab = elem[1]
                    for b in grab:
                        block = self.editor.document().findBlockByNumber(b)
                        block.setVisible(True)
                        doc = self.editor.document()
                        doc.markContentsDirty(block.position(), block.length())
                    self.folding_data.pop(index)

            for elem in self.folding_data:
                grab = elem[1]
                for b in grab:
                    block = self.editor.document().findBlockByNumber(b)
                    block.setVisible(False)
                    doc = self.editor.document()
                    doc.markContentsDirty(block.position(), block.length())

    # Расчет фолдинга при загрузке
    def calculate_folding(self, fold_data):
        self.folding_data = fold_data
        if self.folding_data:
            for folder in self.folding_data:
                list_to_folding = folder[1]
                for idx in list_to_folding:
                    block = self.editor.document().findBlockByNumber(idx)
                    block.setVisible(False)
                    doc = self.editor.document()
                    doc.markContentsDirty(block.position(), block.length())

    # Расчет бук- подсветки при загрузке
    def calculate_books(self, book_data):
        if book_data:
            self.bookmark_data = book_data
            for books in book_data:
                self.bookmark_blocks.add(books[0])


# Вспомогалки (кнопки)
class SubButton(QtWidgets.QPushButton):
    def __init__(self, parent=None, normal=None, hovered=None, active=None, sizeX=32, sizeY=32):
        super().__init__(parent)
        self.effect = QtWidgets.QGraphicsOpacityEffect(self)
        self.effect.setOpacity(0.3)
        self.setGraphicsEffect(self.effect)
        self.opAnim = QtCore.QPropertyAnimation(self.effect, b'opacity')

        if self.isChecked():
            self.state = 'activate'
        else:
            self.state = 'normal'

        self.setFixedSize(sizeX, sizeY)
        self.pixmapOut = pixmapLoader(normal).scaled(
            sizeX, sizeY,
            QtCore.Qt.AspectRatioMode.KeepAspectRatio,
            QtCore.Qt.TransformationMode.SmoothTransformation
        )
        self.pixmapIn = pixmapLoader(hovered).scaled(
            sizeX, sizeY,
            QtCore.Qt.AspectRatioMode.KeepAspectRatio,
            QtCore.Qt.TransformationMode.SmoothTransformation
        )
        self.pixmapAct = pixmapLoader(active).scaled(
            sizeX, sizeY,
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
        if self.isChecked():
            self.state = 'activate'
        else:
            self.state = 'hovered'

        self.opAnim.stop()
        self.opAnim.setDuration(200)
        self.opAnim.setStartValue(self.effect.opacity())
        self.opAnim.setEndValue(1.0)
        self.opAnim.start()

    def leaveEvent(self, event):
        if self.isChecked():
            self.state = 'activate'
        else:
            self.state = 'normal'

        self.opAnim.stop()
        self.opAnim.setDuration(1000)
        self.opAnim.setStartValue(self.effect.opacity())
        if self.isChecked():
            self.opAnim.setEndValue(0.75)
        else:
            self.opAnim.setEndValue(0.3)
        self.opAnim.start()

    def mousePressEvent(self, e):
        if not self.isChecked():
            if e.button() == QtCore.Qt.MouseButton.LeftButton:
                self.state = 'activate'
                e.accept()
        self.update()

        super().mousePressEvent(e)

    def mouseReleaseEvent(self, e):
        if e.button() == QtCore.Qt.MouseButton.LeftButton:
            if self.isChecked():
                self.state = 'activate'
            else:
                self.state = 'normal'
            self.update()
        super().mouseReleaseEvent(e)


# Виджет с общей информацией + системой навигации по тексту
class LineInfo(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.editor = parent.editor
        self.box = QtWidgets.QHBoxLayout(self)
        self.setMaximumHeight(22)
        # self.setMinimumWidth(550)
        self.box.setContentsMargins(0, 0, 0, 0)
        self.box.setSpacing(6)
        self.setStyleSheet(cssLoader('line_info.css'))
        # Перерключатель по линиям
        self.sb = QtWidgets.QSpinBox(self)
        self.sb.setObjectName('spin_01')
        self.box.addWidget(self.sb, alignment=QtCore.Qt.AlignmentFlag.AlignLeft, stretch=0)
        self.sb.setMinimum(1)
        self.sb.setMinimumWidth(70)
        self.sb.setFrame(False)
        self.sb.setCorrectionMode(QtWidgets.QAbstractSpinBox.CorrectionMode.CorrectToNearestValue)
        self.sb.setAccelerated(True)
        self.sb.setToolTip('Go to Line')
        # Метка 1 - количество линий
        self.label1 = QtWidgets.QLabel()
        self.label1.setObjectName('label_01')
        self.label1.setText("<span style = 'color:#9958B9E9;'><b>Current Line:</b></span>")
        w0 = self.fontMetrics().horizontalAdvance('Current Line:') + 10
        self.label1.setMaximumWidth(w0)

        self.box.addWidget(self.label1, alignment=QtCore.Qt.AlignmentFlag.AlignLeft, stretch=0)
        self.editor.cursorPositionChanged.connect(self.label1_out)

        # Метка 2 - количество символов
        self.label2 = QtWidgets.QLabel()
        self.label2.setObjectName('label_02')
        self.label2.setText("<span style = 'color:#9958B9E9;'><b>Lines Count:</b></span>")
        w1 = self.fontMetrics().horizontalAdvance('Lines Count:') + 10
        self.label2.setMaximumWidth(w1)

        self.box.addWidget(self.label2, alignment=QtCore.Qt.AlignmentFlag.AlignLeft, stretch=0)
        self.editor.document().blockCountChanged.connect(self.label2_out)
        # Метка 3-4 - версия Python
        frame = QtWidgets.QFrame()
        frame.setObjectName('icon_box')
        frame.setContentsMargins(0, 0, 0, 0)
        self.label3 = QtWidgets.QLabel()
        self.label4 = QtWidgets.QLabel()
        box2 = QtWidgets.QHBoxLayout(frame)
        box2.setContentsMargins(2, 2, 2, 2)
        box2.addWidget(self.label3, alignment=QtCore.Qt.AlignmentFlag.AlignVCenter)
        box2.addWidget(self.label4)
        pix = pixmapLoader(r'deco\Version_icon.png')
        p = pix.scaledToHeight(15)
        self.label3.setPixmap(p)
        self.label4.setText(f'<span style = "color:#50D5D5D5;">{version()}</span>')
        self.label3.setAlignment(QtCore.Qt.AlignmentFlag.AlignVCenter)

        self.box.addWidget(frame, alignment=QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter,
                           stretch=0)
        # Авто обновление максимального числа блоков
        self.editor.document().blockCountChanged.connect(self.sb_max_changed)
        self.sb.editingFinished.connect(self.go_to_line)

    # Активное изменение максимума в зависимости от кол-ва блоков
    def sb_max_changed(self, new_max):
        self.sb.setMaximum(new_max)

    # Прыжки по блокам
    def go_to_line(self):
        block_num = self.sb.value() - 1
        doc = self.editor.document()
        cursor = self.editor.textCursor()
        block = doc.findBlockByNumber(block_num)
        if block.isVisible():
            new_pos = block.position() + block.length() - 1
            cursor.setPosition(new_pos)
            self.editor.setFocus()
            self.editor.setTextCursor(cursor)
            self.editor.ensureCursorVisible()
        else:
            self.editor.setFocus()

    # Вывод текущей позиции курсора
    def label1_out(self):
        cur_line = self.editor.textCursor().blockNumber() + 1
        text = f"""<span style = 'color:#9958B9E9;'><b>Current Line:</b></span>
                <span style = 'color:#E2D5D5D5;'> {cur_line}</span>"""
        self.label1.setText(text)

        w = self.fontMetrics().horizontalAdvance(text) + 10
        self.label1.setMaximumWidth(w)

    # Вывод общего числа линий
    def label2_out(self):
        block_count = self.editor.document().blockCount()
        text = f"""<span style = 'color:#9958B9E9;'><b>Lines Count:</b></span>
                <span style = 'color:#E2D5D5D5;'> {block_count}</span>"""
        self.label2.setText(text)

        w = self.fontMetrics().horizontalAdvance(text) + 10
        self.label2.setMaximumWidth(w)


#Тестер
if __name__ == '__main__':
    import sys

    app = QtWidgets.QApplication(sys.argv)
    win = Editor()
    win.show()

    sys.exit(app.exec())
