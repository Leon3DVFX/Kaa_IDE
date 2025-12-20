from PySide6 import QtGui
from importlib import resources
import json
import sys

#Строка - версия Python
def version():
    major = str(sys.version_info.major)
    minor = str(sys.version_info.minor)
    micro = str(sys.version_info.micro)
    string = f'{major}.{minor}.{micro}'
    return string


# Загрузчик JSON
def jsonLoader(name: str) -> dict:
    with open(str(resources.files('Kaa_IDE.Docs.Json').joinpath(name)), "r", encoding='utf-8') as file:
        elements = json.load(file)
        return elements


#Загрузчик QIcon
def iconLoader(normal: str, disabled: str = None, active: str = None, selected: str = None) -> QtGui.QIcon:
    normal_path = str(resources.files('Kaa_IDE.UI.Icons').joinpath(normal))
    icon = QtGui.QIcon()
    icon.addFile(normal_path,mode=QtGui.QIcon.Mode.Normal)

    if disabled:
        disabled_path = str(resources.files('Kaa_IDE.UI.Icons').joinpath(disabled))
        icon.addFile(disabled_path,mode=QtGui.QIcon.Mode.Disabled)
    if active:
        active_path = str(resources.files('Kaa_IDE.UI.Icons').joinpath(active))
        icon.addFile(active_path, mode=QtGui.QIcon.Mode.Active)
    if selected:
        selected_path = str(resources.files('Kaa_IDE.UI.Icons').joinpath(selected))
        icon.addFile(selected_path,mode=QtGui.QIcon.Mode.Selected)

    return icon


#Загрузчик pixmap
def pixmapLoader(name: str) -> QtGui.QPixmap:
    with resources.as_file(resources.files('Kaa_IDE.UI.Icons').joinpath(name)) as path:
        pixmap = QtGui.QPixmap(str(path))
        return pixmap


#Загрузчик css
def cssLoader(name: str) -> str:
    with resources.as_file(resources.files('Kaa_IDE.UI.Styles').joinpath(name)) as path:
        qss = path.read_text(encoding='utf-8')
        return qss


if __name__ == '__main__':
    print(iconLoader(normal='complitter_icons',active=r'complitter_icons/icon.png'))