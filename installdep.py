import os
import sys
import subprocess
import time

def get_executable(console=False):
    """
    Get Python executable.

    If ``console==True`` and the current executable is windowed (i.e., ``"pythonw.exe"``), return the corresponding ``"python.exe"`` instead.
    """
    folder,file=os.path.split(sys.executable)
    if file.lower()=="pythonw.exe" and console:
        return os.path.join(folder,"python.exe")
    return sys.executable
def pip_install(pkg, upgrade=False):
    """
    Call ``pip install`` for a given package.
    
    If ``upgrade==True``, call with ``--upgrade`` key (upgrade current version if it is already installed).
    """
    if upgrade:
        subprocess.call([get_executable(console=True), "-m", "pip", "install", "--upgrade", pkg])
    else:
        subprocess.call([get_executable(console=True), "-m", "pip", "install", pkg])
def install_wheel(path, upgrade=True, verbose=True):
    """Install a wheel file with the given path, if it exists"""
    if verbose:
        print("Installing {}".format(path))
    if os.path.exists(path):
        pip_install(path,upgrade=upgrade)
    elif verbose:
        print("Could not find file {}".format(path))


def main():
    install_wheel("BFModule-1.0.1-cp38-cp38-win_amd64.whl")
    time.sleep(3.)

if __name__=="__main__":
    main()