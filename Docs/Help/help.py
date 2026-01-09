from PySide6 import QtWidgets, QtCore, QtWebEngineWidgets
import os


class HelpViewer(QtWebEngineWidgets.QWebEngineView):
    def __init__(self, parent = None):
        super().__init__(parent)
        # Удаление при закрытии
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_DeleteOnClose)

        # Убрать контекстное меню
        self.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.NoContextMenu)

        self.en_path = os.path.abspath(os.path.join('help_en', 'help_en.html'))
        self.ru_path = os.path.abspath(os.path.join('help_ru', 'help_ru.html'))
        self.setUrl(QtCore.QUrl.fromLocalFile(self.ru_path))


if __name__ == '__main__':
    import sys
    app = QtWidgets.QApplication(sys.argv)
    win = HelpViewer()
    win.show()
    sys.exit(app.exec())