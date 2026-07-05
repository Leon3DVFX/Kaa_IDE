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
# Для Maya
def run_webbrowser(url: str):
    webbrowser.open(url)


# Houdini functions
#=======================================================================

# Проверка наличия пути к параметру Houdini в источнике данных
def has_houdini_parm_path(source):
    if not is_houdini():
        return False

    try:
        import hou
        return source.hasFormat(hou.qt.mimeType.parmPath)
    except (AttributeError, ImportError):
        return False


# Восстанавливаем путь к параметру Houdini из источника данных
def get_houdini_parm_path(source):
    if not has_houdini_parm_path(source):
        return None

    import hou
    return bytes(source.data(hou.qt.mimeType.parmPath)).decode("utf-8")


def split_houdini_parm_paths(parm_path):
    return tuple(path for path in parm_path.split("\t") if path)


def get_houdini_parm_tuple_path(parm_path):
    if not is_houdini():
        return None

    import hou
    try:
        parm = hou.parm(parm_path)
    except Exception:
        return None

    if parm is None:
        return None

    try:
        parm_tuple = parm.tuple()
        node = parm_tuple.node()
        return f"{node.path()}/{parm_tuple.name()}"
    except Exception:
        return None


def format_houdini_parm_path(parm_path, as_string=False):
    paths = split_houdini_parm_paths(parm_path)
    if not paths:
        return None

    if as_string:
        if len(paths) > 1:
            return repr(paths)
        return repr(paths[0])

    if len(paths) > 1:
        tuple_path = get_houdini_parm_tuple_path(paths[0])
        if tuple_path is not None:
            return f"hou.parmTuple({tuple_path!r})"
        return f"hou.parm({paths[0]!r}).tuple()"

    return f"hou.parm({paths[0]!r})"

# Проверка, является ли текст именем узла Houdini
def is_node(text):
    if not is_houdini():
        return False

    import hou
    node = hou.node(text)
    return isinstance(node, hou.Node)

# Проверка - можем ли мы редактировать Parm Template
def can_edit_houdini_parm_template(parm_path):
    if not is_houdini():
        return False, "Not in Houdini"

    import hou
    parm = hou.parm(parm_path)
    if parm is None:
        return False, "Parm not found"

    try:
        parm_tuple = parm.tuple()
        node = parm_tuple.node()
        template = parm_tuple.parmTemplate()
        group = node.parmTemplateGroup()

        found = group.find(template.name())
        if found is None:
            return False, "Template not found"

        return True, "Can edit"
    except hou.PermissionError as e:
        return False, f"Permission denied: {e}"
    except hou.OperationFailed as e:
        return False, f"Operation failed: {e}"
    except Exception as e:
        return False, f"Error: {e}"

# Назначение Call Back
def set_houdini_parm_callback(parm_path,code):
    import hou

    ok, reason = can_edit_houdini_parm_template(parm_path)
    if not ok:
        return False, reason

    try:
        parm_tuple = hou.parm(parm_path).tuple()
        node = parm_tuple.node()
        group = node.parmTemplateGroup()
        template = group.find(parm_tuple.name())
        if template is None:
            return False, "Template not found"

        template.setScriptCallback(code)
        template.setScriptCallbackLanguage(hou.scriptLanguage.Python)

        group.replace(parm_tuple.name(), template)
        node.setParmTemplateGroup(group)

        updated_template = node.parmTemplateGroup().find(parm_tuple.name())
        if updated_template is None:
            return False, "Template was not found after update"
        if updated_template.scriptCallback() != code:
            return False, "Callback was not saved"

        return True, ""
    except hou.PermissionError as e:
        return False, f"Permission denied: {e}"
    except hou.OperationFailed as e:
        return False, f"Operation failed: {e}"
    except Exception as e:
        return False, f"Error: {e}"


def set_houdini_parm_python_expression(parm_path, code):
    import hou

    try:
        parm = hou.parm(parm_path)
        if parm is None:
            return False, "Parm not found"

        parm.setExpression(code, language=hou.exprLanguage.Python)
        return True, ""
    except hou.PermissionError as e:
        return False, f"Permission denied: {e}"
    except hou.OperationFailed as e:
        return False, f"Operation failed: {e}"
    except Exception as e:
        return False, f"Error: {e}"
