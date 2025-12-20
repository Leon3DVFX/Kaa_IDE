from Kaa_IDE.UI.MainUI.mainWindow import MainButton

_script_editor_button = None
def run():
    global _script_editor_button
    if _script_editor_button is None:
        _script_editor_button = MainButton()
    _script_editor_button.show()
    _script_editor_button.raise_()
    return _script_editor_button

# Активация соотв. API
