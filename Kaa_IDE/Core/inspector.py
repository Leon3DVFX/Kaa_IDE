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
        kind = "function"

    elif inspect.ismethod(val):
        kind = "method"

    elif inspect.ismethoddescriptor(val):
        kind = "method"

    elif inspect.isbuiltin(val):
        kind = "builtin"

    elif isinstance(val, property):
        kind = "property"

    elif hasattr(val, '__get__'):   # дескрипторы
        kind = "descriptor"

    else:
        kind = "variable"

    return val, kind