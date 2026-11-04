"""Build Windows EXE from this checkout. Requires PyInstaller and psutil."""
from pathlib import Path
import os
import shutil
from build_release import VERSION
from PyInstaller.__main__ import run
ROOT=Path(__file__).resolve().parents[1]
if __name__=='__main__':
    if os.name!='nt': raise SystemExit('Build the Windows EXE on Windows')
    stage=ROOT/'paper/_build/native-source'/VERSION/'pasadhi'
    stage.mkdir(parents=True,exist_ok=True)
    for directory in ['app','core','brand']:
        shutil.copytree(ROOT/directory,stage/directory,dirs_exist_ok=True,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    for filename in ['__init__.py','launcher.py']:
        shutil.copy2(ROOT/filename,stage/filename)
    run(['--noconfirm','--clean','--onefile','--name','pasadhi','--paths',str(stage.parent),'--icon',str(ROOT/'brand/logo-light-transparent.png'),'--distpath',str(ROOT/'paper/_build/native'/VERSION),'--workpath',str(ROOT/'paper/_build/pyinstaller'/VERSION),'--specpath',str(ROOT/'paper/_build'),str(stage/'launcher.py')])
