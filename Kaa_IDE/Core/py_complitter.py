from PySide6 import QtWidgets, QtCore, QtGui
from Kaa_IDE.Core.loaders import jsonLoader, iconLoader
import ast


class ItemModel(QtGui.QStandardItemModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.elements = jsonLoader('python_keyword.json')
        self.setColumnCount(2)
        # Нулевой компонент не для удаления
        elem1 = QtGui.QStandardItem('__doc__')
        elem1.setFlags(QtCore.Qt.ItemFlag.NoItemFlags)
        elem2 = QtGui.QStandardItem('doc string')
        elem2.setFlags(QtCore.Qt.ItemFlag.NoItemFlags)
        self.appendRow([elem1,elem2])

        self.k_icon = iconLoader(r'complitter_icons\keywords_icon.png')
        self.append_to_tab("keywords", self.k_icon)

        self.b_icon = iconLoader(r'complitter_icons\builtins_icon.png')
        self.append_to_tab("builtins", self.b_icon)
        # Список общих модулей (временно отключаю)
        self.mod_icon = iconLoader(r'complitter_icons\std_mod_icon.png')
        # self.append_to_tab("modules", self.mod_icon)
        # Список магических методов (временно отключаю)
        self.magic_icon = iconLoader(r'complitter_icons\magic_icon.png')
        # self.append_to_tab("magic", self.magic_icon)

        # Дополнительные иконки
        self.obj_icon = iconLoader(r'complitter_icons\obj_icon.png')
        self.class_icon = iconLoader(r'complitter_icons\class_icon.png')
        self.c_class_icon = iconLoader(r'complitter_icons\c_class_icon.png')
        self.f_icon = iconLoader(r'complitter_icons\f_icon.png')

    def append_to_tab(self, j_type, icon):
        w_list = self.elements.get(j_type, [])

        for e in w_list:
            elem1 = QtGui.QStandardItem()
            elem1.setText(e)
            elem1.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignVCenter)
            elem1.setIcon(icon)
            elem1.setForeground(QtGui.QColor('#D5D5D5'))

            elem2 = QtGui.QStandardItem()
            elem2.setText(j_type)
            elem2.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignRight)

            self.appendRow([elem1, elem2])

    def silent_clean(self):
        # начинаем с последней строки и идём к 1 (не трогаем 0)
        for row in reversed(range(1, self.rowCount())):
            self.takeRow(row)

# Представление в виде таблицы
class CompleterTableView(QtWidgets.QTableView):
    def __init__(self, parent=None):
        super().__init__(parent)
        # Запуск прокси модели
        self.editor = parent
        self.base_model = ItemModel(self)
        self.proxy_model = QtCore.QSortFilterProxyModel(self)
        self.proxy_model.setSourceModel(self.base_model)
        self.proxy_model.setFilterCaseSensitivity(QtCore.Qt.CaseSensitivity.CaseInsensitive)
        self.setModel(self.proxy_model)
        self.setRowHidden(0,True)
        # ВАЖНО! Popup не захватывает фокус ввода
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        # Общий шрифт
        self.setFont(QtGui.QFont('JetBrains Mono', 10))
        # popup
        self.setWindowFlags(QtCore.Qt.WindowType.Tool |
                            QtCore.Qt.WindowType.FramelessWindowHint)
        self.setMinimumWidth(500)
        self.setMaximumHeight(240)
        self.setItemDelegate(CombinedDelegate(self))
        #Авто-ширина столбцов
        self.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeMode.Stretch)
        self.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setShowGrid(False)
        self.setColumnHidden(1, True)

        self.horizontalHeader().hide()
        self.verticalHeader().hide()
        self.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
        self.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
        self.sortByColumn(0, QtCore.Qt.SortOrder.AscendingOrder)
        self.selectRow(0)
        # Глобальные переменные, функции, классы
        self.vars_f = ObjFinder()
        self.def_f = DefFinder()
        self.import_f = ImportFinder()
        self.var_items = []
        self.func_items = []
        self.class_items = []
        self.import_items = []
        self.vars = set()
        self.funcs = set()
        self.classes = set()
        self.imports = set()
        self.editor.document().blockCountChanged.connect(self.on_var)

    # Сброс ПУ
    def rebuild_base(self):
        self.base_model.silent_clean()
        self.base_model.append_to_tab("builtins", self.base_model.b_icon)
        self.base_model.append_to_tab("keywords", self.base_model.k_icon)
        self.on_var()

    def on_var(self):
        self.vars_f.vars.clear()
        self.def_f.funcs.clear()
        self.import_f.visible.clear()
        code = self.editor.toPlainText()
        # Проходим по каждому блоку документа

        try:
            tree = ast.parse(code)
            self.vars_f.visit(tree)
            self.def_f.visit(tree)
            self.import_f.visit(tree)
        except SyntaxError:
            # пропускаем недописанные строки
            return

        self.vars = self.vars_f.vars
        self.funcs = self.def_f.funcs
        self.classes = self.def_f.classes
        self.imports = self.import_f.visible
        # Очистка предыдущих
        for item in self.var_items + self.func_items + self.class_items + self.import_items:
            self.base_model.removeRow(item.row())

        self.var_items.clear()
        self.func_items.clear()
        self.class_items.clear()
        self.import_items.clear()
        # Глобальные переменные
        if self.vars:
            for e in self.vars:
                elem1 = QtGui.QStandardItem()
                elem1.setText(e)
                elem1.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignVCenter)
                elem1.setForeground(QtGui.QColor('#D5D5D5'))
                elem1.setIcon(self.base_model.obj_icon)  # Иконка

                elem2 = QtGui.QStandardItem()
                elem2.setText("obj")
                elem2.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignRight)

                row = self.base_model.rowCount()
                self.base_model.appendRow([elem1, elem2])
                # сохраняем ссылку на строку
                self.var_items.append(self.base_model.item(row))
        # Все функции
        if self.funcs:
            for e in self.funcs:
                if e.startswith('__'):
                    continue
                elem1 = QtGui.QStandardItem()
                elem1.setText(e)
                elem1.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignVCenter)
                elem1.setForeground(QtGui.QColor('#D5D5D5'))
                elem1.setIcon(self.base_model.f_icon)

                elem2 = QtGui.QStandardItem()
                elem2.setText('def function')
                elem2.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignRight)

                row = self.base_model.rowCount()
                self.base_model.appendRow([elem1, elem2])
                # сохраняем ссылку на строку
                self.func_items.append(self.base_model.item(row))
        # Все классы
        if self.classes:
            for e in self.classes:
                elem1 = QtGui.QStandardItem()
                elem1.setText(e)
                elem1.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignVCenter)
                elem1.setForeground(QtGui.QColor('#D5D5D5'))
                elem1.setIcon(self.base_model.class_icon)

                elem2 = QtGui.QStandardItem()
                elem2.setText('class')
                elem2.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignRight)

                row = self.base_model.rowCount()
                self.base_model.appendRow([elem1, elem2])
                # сохраняем ссылку на строку
                self.class_items.append(self.base_model.item(row))
        # Импорты
        if self.imports:
            for e in self.imports:
                elem1 = QtGui.QStandardItem()
                elem1.setText(e)
                elem1.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignVCenter)
                elem1.setForeground(QtGui.QColor('#D5D5D5'))
                elem1.setIcon(self.base_model.mod_icon)

                elem2 = QtGui.QStandardItem()
                elem2.setText('import')
                elem2.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignRight)

                row = self.base_model.rowCount()
                self.base_model.appendRow([elem1, elem2])
                # сохраняем ссылку на строку
                self.class_items.append(self.base_model.item(row))

    def filter_proxy(self, text):
        self.proxy_model.setFilterFixedString(text)
        self.proxy_model.setDynamicSortFilter(True)

        rows = self.proxy_model.rowCount()
        if rows == 0:
            self.setFixedHeight(0)
            self.hide()
            return
        else:
            row_height = self.rowHeight(0)
            height = min(rows * row_height + 2 * self.frameWidth(), 240)
            self.setFixedHeight(height)
            self.selectRow(0)

    def select_next(self):
        rows = self.proxy_model.rowCount()
        current_row = self.currentIndex().row()

        new_row = current_row + 1
        if new_row >= rows:
            new_row = 0

        self.selectRow(new_row)
        self.scrollTo(self.model().index(new_row, 0),
                      QtWidgets.QAbstractItemView.ScrollHint.PositionAtCenter)

    def select_previous(self):
        rows = self.proxy_model.rowCount()
        current_row = self.currentIndex().row()

        new_row = current_row - 1
        if new_row < 0:
            new_row = rows - 1

        self.selectRow(new_row)
        self.scrollTo(self.model().index(new_row, 0),
                      QtWidgets.QAbstractItemView.ScrollHint.PositionAtCenter)


class CombinedDelegate(QtWidgets.QStyledItemDelegate):
    def paint(self, painter, option, index):
        if index.column() == 0:
            super().paint(painter, option, index)

            # Берём данные из второй ячейки
            model = index.model()
            tag_index = model.index(index.row(), 1)
            tag_text = model.data(tag_index)
            align_flag = QtCore.Qt.AlignmentFlag.AlignVCenter | QtCore.Qt.AlignmentFlag.AlignRight
            # Рисуем справа "keywords", "builtins", ...
            rect = option.rect.adjusted(0, 0, -12, 0)
            painter.save()
            painter.setPen(QtGui.QColor(150, 150, 150))
            painter.drawText(rect, align_flag, '"' + tag_text + '"')
            painter.restore()
        else:
            # вторую колонку делаем невидимой
            return


# Поисковик глобальных переменных
class ObjFinder(ast.NodeVisitor):
    def __init__(self):
        self.vars = set()

    def visit_Assign(self, node):
        for t in node.targets:
            if isinstance(t, ast.Name):
                self.vars.add(t.id)
            elif isinstance(t, ast.Tuple):
                for e in t.elts:
                    if isinstance(e, ast.Name):
                        self.vars.add(e.id)
        self.generic_visit(node)


# Поисковик функций и классов
class DefFinder(ast.NodeVisitor):
    def __init__(self):
        self.funcs = set()
        self.classes = set()

    def visit_FunctionDef(self, node):
        self.funcs.add(node.name)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node):
        self.funcs.add(node.name)
        self.generic_visit(node)

    def visit_ClassDef(self, node):
        self.classes.add(node.name)
        self.generic_visit(node)

# Поисковик модулей
class ImportFinder(ast.NodeVisitor):
    def __init__(self):
        self.visible = set()   # имена, доступные в коде

    def visit_Import(self, node):
        for n in node.names:
            if n.asname:
                self.visible.add(n.asname)
            else:
                # import a.b.c → доступен "a"
                self.visible.add(n.name.split('.')[0])

    def visit_ImportFrom(self, node):
        for n in node.names:
            if n.asname:
                self.visible.add(n.asname)
            else:
                self.visible.add(n.name)

if __name__ == '__main__':
    import sys

    app = QtWidgets.QApplication(sys.argv)
    win = CompleterTableView()
    win.show()
    sys.exit(app.exec())
