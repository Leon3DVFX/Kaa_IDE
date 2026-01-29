from PySide6 import QtWidgets, QtCore, QtWebEngineWidgets, QtGui
from importlib import resources
from Kaa_IDE.Core.loaders import iconLoader, pixmapLoader

# Общий виджет - обертка
class HelpWidget(QtWidgets.QWidget):
    closeSignal = QtCore.Signal()
    def __init__(self, parent = None):
        super().__init__(parent)
        self.setStyleSheet('HelpWidget {background-color: #202020;}')
        self.box = QtWidgets.QVBoxLayout(self)
        self.help = HelpViewer(self)
        self.header = Header(self)
        self.resize(800,700)
        self.setWindowFlags(QtCore.Qt.WindowType.WindowStaysOnTopHint)
        self.setWindowModality(QtCore.Qt.WindowModality.WindowModal)
        self.setWindowTitle('Kaa_IDE Help')
        self.box.addWidget(self.header,stretch=0)
        self.box.addWidget(self.help,stretch=1)
        self.setWindowIcon(iconLoader('help_activate.png'))
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_DeleteOnClose)
        # Языковые настройки
        self.l_id = 0

        self.header.langSignal.connect(self.on_lang)

    def on_lang(self, l_id):
        if self.l_id == l_id:
            return

        if l_id == 0:
            self.help.setUrl(QtCore.QUrl.fromLocalFile(self.help.en_path))
            self.l_id = 0
        elif l_id == 1:
            self.help.setUrl(QtCore.QUrl.fromLocalFile(self.help.ru_path))
            self.l_id = 1

    def closeEvent(self, event):
        self.closeSignal.emit()
        super().closeEvent(event)
# Заголовок с кнопками
class Header(QtWidgets.QWidget):
    langSignal = QtCore.Signal(int)
    def __init__(self, parent=None):
        super().__init__(parent)

        self.layout = QtWidgets.QVBoxLayout(self)
        self.layout.setContentsMargins(0,0,0,0)

        self.grp_box = QtWidgets.QFrame(self)
        self.h_box = QtWidgets.QHBoxLayout()
        self.h_box.setContentsMargins(0, 0, 0, 0)
        self.h_box.setSpacing(3)
        self.en_btn = LangBtn(self, pixN=r'help_icons\en_normal.png',
                                   pixA=r'help_icons\en_activate.png')
        self.en_btn.setChecked(True)

        self.ru_btn = LangBtn(self, pixN=r'help_icons\ru_normal.png',
                                   pixA=r'help_icons\ru_activate.png')

        self.h_box.addWidget(self.en_btn)
        self.h_box.addWidget(self.ru_btn)
        self.h_box.addStretch(1)

        self.grp_box.setLayout(self.h_box)
        self.layout.addWidget(self.grp_box)

        self.grp = QtWidgets.QButtonGroup(self)
        self.grp.setExclusive(True)
        self.grp.addButton(self.en_btn, id = 0)
        self.grp.addButton(self.ru_btn, id = 1)
        self.grp.buttonClicked.connect(self.on_lang)

    def on_lang(self, btn):
        if btn == self.en_btn:
            self.langSignal.emit(0)
        elif btn == self.ru_btn:
            self.langSignal.emit(1)

# Основной браузер для Help
class HelpViewer(QtWebEngineWidgets.QWebEngineView):
    def __init__(self, parent = None):
        super().__init__(parent)
        # Удаление при закрытии
        self.page().setBackgroundColor(QtCore.Qt.GlobalColor.transparent)

        # Убрать контекстное меню
        self.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.NoContextMenu)
        # Набор справок
        self.en_path = str(resources.files('Kaa_IDE.Docs.Help.help_en').joinpath('help_en.html'))
        self.ru_path = str(resources.files('Kaa_IDE.Docs.Help.help_ru').joinpath('help_ru.html'))
        # Стартовая справки
        self.setUrl(QtCore.QUrl.fromLocalFile(self.en_path))

# Кнопки под выбор языка
class LangBtn(QtWidgets.QPushButton):
    def __init__(self, parent = None, pixN = None, pixA = None):
        super().__init__(parent)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground)
        self.iconN = pixmapLoader(pixN)
        self.iconA = pixmapLoader(pixA)
        self.setCheckable(True)

    def sizeHint(self):
        return self.iconN.size()

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)

        if self.isChecked():
            painter.drawPixmap(QtCore.QPoint(0,0), self.iconA)
        else:
            painter.drawPixmap(QtCore.QPoint(0, 0), self.iconN)

if __name__ == '__main__':
    import sys
    app = QtWidgets.QApplication(sys.argv)
    win = HelpWidget()
    win.show()
    sys.exit(app.exec())