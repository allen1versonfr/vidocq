"""Public canaries verify that mocked tests cannot hide total provider failure."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import app
probes=[app.run_adapter('Wikipedia index',app.encyclopedia,'Ada Lovelace'),app.run_adapter('Regional Internet Registry',app.network_registry,'8.8.8.8')]
for probe in probes:print(probe['provider'],probe['status'],len(probe['rows']),probe.get('message',''))
if not any(p['status']=='ok' and p['rows'] for p in probes):raise SystemExit('No live public canary returned records; release blocked.')
print('At least one live index returned records. Individual provider outages remain possible. Brave requires a user key and is tested with mocked responses only.')
