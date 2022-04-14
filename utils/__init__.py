version="2.2.0"

import re
def compare_version(v):
    """Compare version `v` with the current one"""
    if v is None:
        return "x"
    if not re.match(r"^\d+\.\d+\.\d+$",v):
        return "?"
    sv1=[int(i) for i in v.split(".")]
    sv2=[int(i) for i in version.split(".")]
    if sv1>sv2:
        return ">"
    elif sv1<sv2:
        return "<"
    return "="