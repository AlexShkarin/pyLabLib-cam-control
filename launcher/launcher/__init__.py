import subprocess
import sys
import os

def run_script(path):
    subprocess.run([sys.executable,os.path.join("cam-control",path)]+sys.argv[1:])
def run_control():
    run_script("control.py")
def run_detect():
    run_script("detect.py")
def run_control_splash():
    run_script("splash.py")