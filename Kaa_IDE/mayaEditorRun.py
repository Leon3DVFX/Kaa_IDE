from Kaa_IDE.UI.MainUI.mainWindow import MainButton

_script_editor_button = None
def run():
    global _script_editor_button
    if _script_editor_button is None:
        _script_editor_button = MainButton()
        _script_editor_button.show()
        _script_editor_button.raise_()
        _script_editor_button.destroyed.connect(_on_destr)
    return _script_editor_button

def _on_destr(obj = None):
    global _script_editor_button
    _script_editor_button = None
# Активация соотв. API
