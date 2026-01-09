from PySide6 import QtWidgets,QtCore, QtGui

class HelpViewer(QtWidgets.QTextBrowser):
    def __init__(self, parent = None):
        super().__init__(parent)
        self.setSource(QtCore.QUrl(r'help_en\help_en.html'),
                       type = QtGui.QTextDocument.ResourceType.HtmlResource)


if __name__ == '__main__':
    import sys
    app = QtWidgets.QApplication(sys.argv)
    win = HelpViewer()
    win.show()
    sys.exit(app.exec())