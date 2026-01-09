from PySide6 import QtWidgets,QtCore

class HelpViewer(QtWidgets.QTextBrowser):
    def __init__(self, parent = None):
        super().__init__(parent)

if __name__ == '__main__':
    import sys
    app = QtWidgets.QApplication(sys.argv)
    win = HelpViewer()
    win.show()
    sys.exit(app.exec())