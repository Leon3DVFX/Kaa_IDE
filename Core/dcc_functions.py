import webbrowser

# Проверки на соответствующие API
# Autodesk Maya
def is_maya():
    try:
        import maya.cmds
        return True
    except ImportError:
        return False
# Side FX Houdini
def is_houdini():
    try:
        import hou
        return True
    except ImportError:
        return False
# Autodesk 3dsMax
def is_max():
    try:
        import pymxs
        return True
    except ImportError:
        return False

# Запуск обозревателя ПУ
def run_webbrowser(url: str):
    webbrowser.open(url)