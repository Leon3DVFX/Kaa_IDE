from PySide6 import QtWidgets, QtCore, QtGui
from Kaa_IDE.Core.loaders import jsonLoader, iconLoader
import ast


class ItemModel(QtGui.QStandardItemModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.elements = jsonLoader('python_keyword.json')
        self.setColumnCount(2)

        self.k_icon = iconLoader(r'complitter_icons\keywords_icon.png')
        self.append_to_tab("keywords", self.k_icon)

        self.b_icon = iconLoader(r'complitter_icons\builtins_icon.png')
        self.append_to_tab("builtins", self.b_icon)

        self.mod_icon = iconLoader(r'complitter_icons\std_mod_icon.png')
        self.append_to_tab("modules", self.mod_icon)

        self.magic_icon = iconLoader(r'complitter_icons\magic_icon.png')
        self.append_to_tab("magic", self.magic_icon)

        # Дополнительные иконки
        self.obj_icon = iconLoader(r'complitter_icons\obj_icon.png')
        self.class_icon = iconLoader(r'complitter_icons\class_icon.png')
        self.f_icon = iconLoader(r'complitter_icons\f_icon.png')

    def append_to_tab(self, j_type, icon):
        w_list = self.elements.get(j_type, [])
        COLORS = {
            "keywords": "#cb8964",
            "builtins": "#a7a7e8",
            "modules": "#e0d57b",
            "magic": "#e03792"
        }
        for e in w_list:
            elem1 = QtGui.QStandardItem()
            elem1.setText(e)
            elem1.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignVCenter)
            elem1.setIcon(icon)
            elem1.setForeground(QtGui.QColor(COLORS[j_type]))

            elem2 = QtGui.QStandardItem()
            elem2.setText(j_type)
            elem2.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignRight)

            self.appendRow([elem1, elem2])


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
        # ВАЖНО! Popup не захватывает фокус ввода
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        # Общий шрифт
        self.setFont(QtGui.QFont('JetBrains Mono', 10))
        # popup
        self.setWindowFlags(QtCore.Qt.WindowType.Tool |
                            QtCore.Qt.WindowType.FramelessWindowHint)
        self.setMinimumWidth(380)
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
        self.var_items = []
        self.func_items = []
        self.class_items = []
        self.vars = set()
        self.funcs = set()
        self.classes = set()
        self.editor.document().contentsChange.connect(self.on_var)

    def on_var(self):
        self.vars_f.vars.clear()
        self.def_f.funcs.clear()
        self.def_f.classes.clear()
        code = self.editor.toPlainText()
        # Проходим по каждому блоку документа

        try:
            tree = ast.parse(code)
            self.vars_f.visit(tree)
            self.def_f.visit(tree)
        except SyntaxError:
            # пропускаем недописанные строки
            return

        self.vars = self.vars_f.vars
        self.funcs = self.def_f.funcs
        self.classes = self.def_f.classes
        # Очистка предыдущих
        for item in self.var_items + self.func_items + self.class_items:
            self.base_model.removeRow(item.row())

        self.var_items.clear()
        self.func_items.clear()
        self.class_items.clear()
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
                elem1 = QtGui.QStandardItem()
                elem1.setText(e)
                elem1.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignVCenter)
                elem1.setForeground(QtGui.QColor('#D489FF'))
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
                elem1.setForeground(QtGui.QColor('#EE8133'))
                elem1.setIcon(self.base_model.class_icon)

                elem2 = QtGui.QStandardItem()
                elem2.setText('class')
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


if __name__ == '__main__':
    import sys

    app = QtWidgets.QApplication(sys.argv)
    win = CompleterTableView()
    win.show()
    sys.exit(app.exec())
