from .base import ICameraDescriptor

from pylablib.core.utils import files as file_utils, string as string_utils

import os
import sys
import importlib

folder=os.path.dirname(__file__)
root_module_name=__name__.rsplit(".",maxsplit=1)[0]
def find_camera_descriptors():
    """Find all camera descriptor classes"""
    files=file_utils.list_dir_recursive(folder,file_filter=r".*\.py$",visit_folder_filter=string_utils.get_string_filter(exclude="__pycache__")).files
    cam_classes={}
    for f in files:
        if f not in ["__init__.py","base.py"]:
            module_name="{}.{}".format(root_module_name,os.path.splitext(f)[0].replace("\\",".").replace("/","."))
            if module_name not in sys.modules:
                spec=importlib.util.spec_from_file_location(module_name,os.path.join(folder,f))
                mod=importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                sys.modules[module_name]=mod
            mod=sys.modules[module_name]
            for v in mod.__dict__.values():
                if isinstance(v,type) and issubclass(v,ICameraDescriptor) and v is not ICameraDescriptor and v._cam_kind is not None:
                    cam_classes[v._cam_kind]=v
    return cam_classes