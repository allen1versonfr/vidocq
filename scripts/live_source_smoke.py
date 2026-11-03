"""Public canaries verify that mocked tests cannot hide total provider failure."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import app
from web_search import WebSearch
free=WebSearch();free.configure({'provider':'mwmbl','enabled':True})
probes=[app.run_adapter('Mwmbl free web index',free.search,'Ada Lovelace'),app.run_adapter('Wikipedia index',app.encyclopedia,'Ada Lovelace'),app.run_adapter('Regional Internet Registry',app.network_registry,'8.8.8.8')]
for probe in probes:print(probe['provider'],probe['status'],len(probe['rows']),probe.get('message',''))
if not (probes[0]['status']=='ok' and probes[0]['rows']):raise SystemExit('Free Mwmbl canary did not return records; release blocked.')
if not any(p['status']=='ok' and p['rows'] for p in probes):raise SystemExit('No live public canary returned records; release blocked.')
print('Free anonymous Mwmbl returned live records. Individual provider outages remain possible. Optional Brave is tested with synthetic responses; no paid key is used.')
