from PySide6 import QtWidgets, QtCore,QtWebEngineWidgets,QtWebEngineCore

#Обёртка-виджет
class BrowserWindow(QtWidgets.QWidget):
    def __init__(self,parent=None):
        super().__init__(parent)
        self.vbox = QtWidgets.QVBoxLayout(self)
        self.browser = MyBrowser()
        self.vbox.addWidget(self.browser)
#Окно браузера
class MyBrowser(QtWebEngineWidgets.QWebEngineView):
    def __init__(self):
        super().__init__()
        self.startUrl = QtCore.QUrl('https://help.autodesk.com/cloudhelp/2025/ENU/Maya-Tech-Docs/CommandsPython/')
        self.load(self.startUrl)

if __name__ == '__main__':
    import sys
    app = QtWidgets.QApplication(sys.argv)
    win = BrowserWindow()
    win.show()
    sys.exit(app.exec())