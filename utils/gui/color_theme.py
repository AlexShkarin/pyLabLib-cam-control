
from pylablib.core.gui import is_pyside2
from pylablib.core.utils import funcargparse
import qdarkstyle

import re

def load_style(style="light"):
    """
    Load color theme style.
    
    Can be ``"standard"`` (default OS style), ``"dark"`` (qdarkstyle dark), or ``"light"`` (qdarkstyle light).
    """
    funcargparse.check_parameter_range(style,"style",["standard","light","dark"])
    if style=="standard":
        return ""
    palette=qdarkstyle.DarkPalette if style=="dark" else qdarkstyle.LightPalette
    accent_color="#406482" if style=="dark" else "#94c1e0"
    stylesheet=qdarkstyle.load_stylesheet(pyside=is_pyside2,palette=palette)
    m=re.search(r"QPushButton:checked\s*{[^}]*}",stylesheet,flags=re.DOTALL)
    end=m.span()[1]
    stylesheet=stylesheet[:end]+"\n\nQPushButton:checked {{background-color: {};}}".format(accent_color)+stylesheet[end:]
    return stylesheet
