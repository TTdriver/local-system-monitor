#!/usr/bin/env python3
"""Install this release's app files and Linux launcher; never change user data."""
import ast
import os
from pathlib import Path
import shutil
import subprocess
import sys

APP_VERSION = '0.1.1'
COMPONENT = 'desktop-monitor'
APP_NAME = 'System Monitor'
LAUNCHER_ID = 'local-system-monitor'
ENTRY = 'monitor.py'
ICON = 'app-icon.png'
ROOT = Path(__file__).resolve().parent
HOME_DIR = Path.home()

def main():
    if ROOT.joinpath('VERSION').read_text().strip() != APP_VERSION:
        raise RuntimeError('Installer and VERSION differ.')
    tree=ast.parse((ROOT/ENTRY).read_text())
    version=next(ast.literal_eval(node.value) for node in tree.body if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='APP_VERSION' for t in node.targets))
    if version != APP_VERSION:
        raise RuntimeError('App and installer versions differ.')
    target=HOME_DIR/'.local/share/local-ai-apps'/COMPONENT
    target.mkdir(parents=True,exist_ok=True)
    for source in ROOT.iterdir():
        if source.is_file() and (source.suffix in ('.py','.png','.svg','.json','.txt','.md') or source.name in ('VERSION','Dockerfile')):
            shutil.copy2(source,target/source.name)
    runtime=Path('/usr/bin/python3')
    if COMPONENT=='desktop-webui':
        venv=HOME_DIR/'.local/share/local-webui-runtime'
        runtime=venv/'bin/python'
        if not runtime.exists():subprocess.run([sys.executable,'-m','venv',str(venv)],check=True)
        subprocess.run([str(runtime),'-m','pip','install','-r',str(ROOT/'requirements.txt')],check=True)
    launcher=HOME_DIR/'.local/share/applications'/f'{LAUNCHER_ID}.desktop'
    launcher.parent.mkdir(parents=True,exist_ok=True)
    launch=target/'launch.sh'
    launch.write_text('#!/usr/bin/env bash\nset -euo pipefail\nexec "'+str(runtime)+'" "'+str(target/ENTRY)+'"\n')
    launch.chmod(0o755)
    icon=str(target/ICON) if ICON else 'utilities-system-monitor'
    launcher.write_text(f'[Desktop Entry]\nType=Application\nName={APP_NAME}\nExec="{launch}"\nIcon={icon}\nTerminal=false\nCategories=Utility;\n')
    desktop=HOME_DIR/'Desktop'
    if shutil.which('xdg-user-dir'):
        result=subprocess.run(['xdg-user-dir','DESKTOP'],capture_output=True,text=True)
        if result.returncode==0 and result.stdout.strip():desktop=Path(result.stdout.strip())
    if desktop.is_dir() and desktop!=HOME_DIR:
        shortcut=desktop/f'{APP_NAME}.desktop';shutil.copy2(launcher,shortcut);shortcut.chmod(0o755)
        if shutil.which('gio'):subprocess.run(['gio','set',str(shortcut),'metadata::trusted','true'],capture_output=True)
    if shutil.which('update-desktop-database'):subprocess.run(['update-desktop-database',str(launcher.parent)],check=False)
    print(f'Installed {APP_NAME} v{APP_VERSION}.')

if __name__=='__main__':main()
