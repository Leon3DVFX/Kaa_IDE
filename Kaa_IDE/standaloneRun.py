from PySide6 import QtWidgets

import Kaa_IDE.UI.MainUI.mainWindow as editor


def standalone_run():
    import sys
    app = QtWidgets.QApplication(sys.argv)
    win = editor.MainWindow()
    win.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    standalone_run()