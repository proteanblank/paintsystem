# Fixes UnicodeDecodeError bug
STRING_CACHE = {}
def intern_enum_items(items):
    def intern_string(s):
        if not isinstance(s, str):
            return s
        global STRING_CACHE
        if s not in STRING_CACHE:
            STRING_CACHE[s] = s
        return STRING_CACHE[s]
    return [tuple(intern_string(s) for s in item) for item in items]