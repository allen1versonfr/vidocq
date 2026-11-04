"""Portable Windows entry point and isolated updater helper."""
import ctypes
import os
from pathlib import Path
import sys
import traceback

if len(sys.argv)==3 and sys.argv[1]=='--browser-capture':
    from browser_bridge import relay_to_running
    capture_data=Path(os.environ.get('VIDOCQ_DATA') or os.environ.get('LOCALAPPDATA',Path.home()/'.local/share'))/'Vidocq' if not os.environ.get('VIDOCQ_DATA') else Path(os.environ['VIDOCQ_DATA'])
    if relay_to_running(sys.argv[2],capture_data):raise SystemExit(0)

if len(sys.argv)>1 and sys.argv[1]=='--maigret-companion':
    sys.argv.pop(1)
    from scripts.maigret_bridge import main
    main()
    raise SystemExit(0)

if len(sys.argv) == 3 and sys.argv[1] == '--apply-update':
    from updater import apply_update
    raise SystemExit(apply_update(sys.argv[2]))

data = Path(os.environ.get('VIDOCQ_DATA') or os.environ.get('ALL_SEEING_EYES_DATA') or os.environ.get('OSINT_DESK_DATA') or (Path(os.environ.get('LOCALAPPDATA', Path.home()/'.local/share'))/'Vidocq'))
data.mkdir(parents=True, exist_ok=True)
log = (data/'startup.log').open('w', encoding='utf-8', buffering=1)
sys.stdout = log
sys.stderr = log
try:
    if os.name=='nt':
        # Stable taskbar grouping, independent of Python or PyInstaller defaults.
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('Vidocq.Desktop')
    import app
    app.main()
except Exception:
    traceback.print_exc()
    if not any(a in sys.argv for a in ('--smoke-test', '--self-test')):
        try:
            ctypes.windll.user32.MessageBoxW(None, 'Vidocq could not start.\nDetails: '+str(data/'startup.log'), 'Vidocq', 0x10)
        except Exception:
            pass
    raise SystemExit(1)
