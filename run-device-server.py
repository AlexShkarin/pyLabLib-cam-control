import os
import sys
os.chdir(os.path.abspath(os.path.dirname(sys.argv[0])))
sys.path.append(os.path.abspath("."))  # set current folder to the file location and add it to the search path

import pylablib
from pylablib.core.fileio import loadfile
from pylablib.core.utils import rpyc_utils

path="settings.cfg"
if os.path.exists(path):
    settings=loadfile.load_dict(path)
    if "dlls" in settings:
        for k,v in settings["dlls"].items():
            pylablib.par["devices/dlls",k]=v
rpyc_utils.run_device_service(verbose=True)