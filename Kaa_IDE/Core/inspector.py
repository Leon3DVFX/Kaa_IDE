import inspect

def inspect_attr(owner, name):
    try:
        val = getattr(owner, name)
    except Exception:
        return None, "unresolved"

    # --- классификация ---
    if inspect.isclass(val):
        kind = "class"

    elif inspect.isfunction(val):
        kind = "functions"

    elif inspect.ismethod(val):
        kind = "methods"

    elif inspect.ismethoddescriptor(val):
        kind = "methods"

    elif inspect.isbuiltin(val):
        kind = "builtins"

    elif isinstance(val, property):
        kind = "property"

    elif hasattr(val, '__get__'):   # дескрипторы
        kind = "descriptors"

    else:
        kind = "variables"

    return val, kind
