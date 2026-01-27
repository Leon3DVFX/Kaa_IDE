from PySide6 import QtWidgets, QtCore, QtWebEngineWidgets
from importlib import resources
from Kaa_IDE.Core.loaders import iconLoader

# Общий виджет - обертка
class HelpWidget(QtWidgets.QWidget):
    closeSignal = QtCore.Signal()
    def __init__(self, parent = None):
        super().__init__(parent)
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

    def closeEvent(self, event):
        self.closeSignal.emit()
        super().closeEvent(event)
# Заголовок с кнопками
class Header(QtWidgets.QWidget):
    def __init__(self, parent = None):
        super().__init__(parent)

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
        self.ru_path = str(resources.files('Kaa_IDE.Docs.Help.help_en').joinpath('help_ru.html'))
        # Стартовая справки
        self.setUrl(QtCore.QUrl.fromLocalFile(self.en_path))


if __name__ == '__main__':
    import sys
    app = QtWidgets.QApplication(sys.argv)
    win = HelpWidget()
    win.show()
    sys.exit(app.exec())