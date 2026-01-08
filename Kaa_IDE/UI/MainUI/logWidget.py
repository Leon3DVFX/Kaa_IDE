from PySide6 import QtWidgets, QtCore, QtGui
from Kaa_IDE.Core.loaders import pixmapLoader, cssLoader


class Logout(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.logout = LogoutMain()
        self.box = QtWidgets.QVBoxLayout(self)
        self.box.setContentsMargins(5, 0, 10, 10)
        self.box.addWidget(self.logout)

    def getLogout(self):
        return self.logout


class LogoutMain(QtWidgets.QPlainTextEdit):
    def __init__(self):
        super().__init__()
        self.alpha = 255
        self.setReadOnly(True)
        self.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.TextSelectableByMouse |
                                     QtCore.Qt.TextInteractionFlag.TextSelectableByKeyboard)
        self.setLineWrapMode(QtWidgets.QPlainTextEdit.LineWrapMode.NoWrap)
        self.setInitialFont()
        self.setStyleSheet(cssLoader('qplain_text_edit.css'))
        self.deco_plank = pixmapLoader(r'deco\plank.png')

    def draw_background(self,event):
        painter = QtGui.QPainter(self.viewport())
        painter.setCompositionMode(QtGui.QPainter.CompositionMode.CompositionMode_Source)
        color = QtGui.QColor('#1E1F22')
        color.setAlpha(self.alpha)
        painter.fillRect(self.rect(),color)

    def paintEvent(self, event):
        self.draw_background(event)
        super().paintEvent(event)
    #
    # def draw_plank(self):
    #     painter = QtGui.QPainter(self.viewport())
    #     pixmap = self.deco_plank
    #     x_offset = self.horizontalScrollBar().value()
    #     y_offset = self.verticalScrollBar().value()
    #
    #     p_rect = pixmap.rect()
    #     s_rect = self.viewport().rect()
    #
    #     x = s_rect.width() - 5 - p_rect.width()
    #     y = s_rect.height() - 5 - p_rect.height()
    #
    #     painter.drawPixmap(QtCore.QPoint(x, y), pixmap)

    def setInitialFont(self):
        """Установка начального моноширного шрифта"""
        fonts = ['JetBrains Mono', 'Consolas', 'Monaco',
                 'DejaVu Sans Mono', 'Source Code Pro', 'Courier New']

        available_fonts = QtGui.QFontDatabase.families()

        for font_name in fonts:
            if font_name in available_fonts:
                font = QtGui.QFont(font_name, 10)
                self.document().setDefaultFont(font)
                break
