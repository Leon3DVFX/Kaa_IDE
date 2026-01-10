from PySide6 import QtWidgets, QtCore, QtWebEngineWidgets
import os

# Общий виджет - обертка
class HelpWidget(QtWidgets.QWidget):
    def __init__(self, parent = None):
        super().__init__(parent)
# Заголовок с кнопками
class Header(QtWidgets.QWidget):
    def __init__(self, parent = None):
        super().__init__(parent)
# Основной браузер для Help
class HelpViewer(QtWebEngineWidgets.QWebEngineView):
    def __init__(self, parent = None):
        super().__init__(parent)
        # Удаление при закрытии
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_DeleteOnClose)
        self.page().setBackgroundColor(QtCore.Qt.GlobalColor.transparent)
        self.setFixedWidth(600)
        self.setFixedHeight(700)

        # Убрать контекстное меню
        self.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.NoContextMenu)
        # Набор справок
        self.en_path = os.path.abspath(os.path.join('help_en', 'help_en.html'))
        self.ru_path = os.path.abspath(os.path.join('help_ru', 'help_ru.html'))
        # Стартовая справки
        self.setUrl(QtCore.QUrl.fromLocalFile(self.en_path))


if __name__ == '__main__':
    import sys
    app = QtWidgets.QApplication(sys.argv)
    win = HelpViewer()
    win.show()
    sys.exit(app.exec())