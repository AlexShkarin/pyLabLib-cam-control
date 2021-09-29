import subprocess
import argparse
import shutil


def clear_build():
    shutil.rmtree("_build",ignore_errors=True)


def make(builder="html"):
    subprocess.call(["sphinx-build","-M",builder,".","_build"])


parser=argparse.ArgumentParser()
parser.add_argument("-c","--clear",action="store_true")
args=parser.parse_args()

if args.clear:
    print("Clearing build\n")
    clear_build()
make()