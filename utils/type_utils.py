#updated date: 20/4/2025

def get_type(element):
    if type(element) is int:
        return "int"
    if type(element) is str:
        return "str"
    if type(element) is dict:
        return "dict"
    if type(element) is list:
        return "list"
    if "class" in str(type(element)):
        return "class"
    return "unknown"

def get_class_name(element):
    if element and get_type(element) == "class":
        return type(element).__name__
    return "unknown"