from pylablib.core.utils import files as file_utils, string as string_utils, module as module_utils

import argparse
import os
import sys
import re
import subprocess
import distutils.ccompiler

from utils import version


### Setup comman line arguments
parser=argparse.ArgumentParser()
parser.add_argument("--force","-f",action="store_true",help="clean the cam-control and pylablib folder, but keep the python interpreter")
parser.add_argument("--full-force","-ff",action="store_true",help="completely clean and overwrite the destination folder")
parser.add_argument("--interpreter","-i",metavar="INTERPRETER",help="python interpreter (a path to the set up interpreter folder)")
parser.add_argument("--noarchive",action="store_true",help="skip creating the zip file")
parser.add_argument("--nocompile",action="store_true",help="skip re-compiling executables (it is only necessary when python file names or icons are changed)")
parser.add_argument("dst",metavar="DST",help="destination folder")
clargs=parser.parse_args()

control_folder=os.path.abspath(os.path.split(sys.argv[0])[0])
pll_folder=os.path.abspath(module_utils.get_library_path())
portable_folder=os.path.abspath(os.path.join(pll_folder,"..","tools","portable"))

def prepare_dst(dst, force=False, full_force=False):
    if full_force:
        file_utils.retry_clean_dir(dst)
    elif force:
        file_utils.retry_clean_dir(os.path.join(dst,"cam-control"))
        file_utils.retry_clean_dir(os.path.join(dst,"docs"))
    elif os.path.exists(dst):
        print("destination path {} already exists; aborting".format(dst))
        sys.exit(1)

def copy_interpreter(dst, interpreter=None):
    if os.path.exists(os.path.join(dst,"python")):
        print("interpreter already exists")
        return
    if interpreter is None:
        subprocess.call(["python.exe",os.path.join(portable_folder,"setup-embedded.py"),os.path.join(dst,"python"),"-r","cam-control"])
    else:
        file_utils.retry_copy_dir(interpreter,os.path.join(dst,"python"))
pll_copy_file_filter=string_utils.StringFilter(include=r".*\.py$")
pll_copy_folder_filter=string_utils.StringFilter(exclude=r"__pycache__")
def copy_pll(dst):
    file_utils.retry_copy_dir(pll_folder,os.path.join(dst,"cam-control","pylablib"),folder_filter=pll_copy_folder_filter,file_filter=pll_copy_file_filter)
include_plugins=["filter","server","trigger_save"]
control_copy_file_filter=string_utils.StringFilter(include=r".*\.py|.*\.png|LICENSE|requirements.txt|icon.ico$",exclude=r"pack\.py$")
control_copy_folder_filter=string_utils.StringFilter(exclude=r"__pycache__|\.git|\.vscode|docs|launcher")
def copy_control(dst):
    dst_control=os.path.join(dst,"cam-control")
    file_utils.retry_copy_dir(control_folder,dst_control,folder_filter=control_copy_folder_filter,file_filter=control_copy_file_filter)
    file_utils.retry_copy_dir(control_folder,dst_control,folder_filter=control_copy_folder_filter,file_filter=control_copy_file_filter)
    file_utils.retry_copy(os.path.join(control_folder,"settings_deploy.cfg"),os.path.join(dst_control,"settings.cfg"))
    if version:
        with open(os.path.join(dst_control,"settings.cfg"),"a") as f:
            f.write("\ninfo/version\t{}".format(version))
    for f in file_utils.list_dir(os.path.join(dst_control,"plugins"),file_filter=r".*\.py").files:
        if f[:-3] not in include_plugins+["__init__","base"]:
            file_utils.retry_remove(os.path.join(dst_control,"plugins",f))
def copy_docs(dst):
    subprocess.call(["python.exe","make-sphinx.py","-c"],cwd="docs")
    file_utils.retry_copy_dir(os.path.join("docs","_build","html"),os.path.join(dst,"docs"))
def make_bat(dst):
    with open(os.path.join(dst,"python","local-python.bat"),"w") as f:
        f.write("set PATH=%CD%;%CD%\\Scripts;%PATH%\ncmd /k")
def make_launcher(dst, recompile=True):
    compiler=distutils.ccompiler.new_compiler()
    for fs in [["run-control-splash","icon.rc"],["run-control"],["run-detect"]]:
        ps=[os.path.join("launcher",f) for f in fs]
        if recompile or not os.path.exists(ps[0]+".exe"):
            sps=[p+".c" if not p.endswith(".rc") else p for p in ps]
            obj=compiler.compile(sps)
            compiler.link_executable(obj,ps[0])
    file_utils.retry_copy(os.path.join("launcher","run-control-splash.exe"),os.path.join(dst,"control.exe"))
    file_utils.retry_copy(os.path.join("launcher","run-control.exe"),os.path.join(dst,"control-console.exe"))
    file_utils.retry_copy(os.path.join("launcher","run-detect.exe"),os.path.join(dst,"detect.exe"))

zip_name="cam-control{}.zip".format("-"+version if version else "")
def zip_dst(dst, zip_name):
    zip_path=os.path.join(dst,zip_name)
    if os.path.exists(zip_path):
        file_utils.retry_remove(zip_path)
    folders,files=file_utils.list_dir(dst)
    for f in folders:
        file_utils.zip_folder(zip_path,os.path.join(dst,f),inside_path=os.path.join("cam-control",f))
    for f in files:
        file_utils.zip_file(zip_path,os.path.join(dst,f),inside_name=os.path.join("cam-control",f))

print("preparing destination path {}".format(clargs.dst))
prepare_dst(clargs.dst,force=clargs.force,full_force=clargs.full_force)
print("copying interpreter")
copy_interpreter(clargs.dst,interpreter=clargs.interpreter)
print("copying pylablib")
copy_pll(clargs.dst)
print("copying cam-control")
copy_control(clargs.dst)
print("preparing executable files")
make_launcher(clargs.dst,recompile=not clargs.nocompile)
print("copying docs")
copy_docs(clargs.dst)
print("preparing batch files")
make_bat(clargs.dst)
if not clargs.noarchive:
    print("archiving folder to {}".format(zip_name))
    zip_dst(clargs.dst,zip_name)