"""Dated operator-verified public controls; no account existence inferred from failures."""
from datetime import date,datetime,timezone
import json,re,secrets
from pathlib import Path
from collector_policy import MAIGRET_SITES,CHECKER_HOLDS
from managed_local_ai import safe_path

class CheckerHealth:
    def __init__(self,data,collectors):
        self.path=Path(data)/'checker-health.json';self.collectors=collectors;self.records={}
        try:
            if safe_path(self.path).is_file() and self.path.stat().st_size<50000:
                records=json.loads(self.path.read_text(encoding='utf-8'))
                if isinstance(records,dict):self.records={k:v for k,v in records.items() if k in MAIGRET_SITES and isinstance(v,dict)}
        except (OSError,ValueError):pass
        for site,record in self.records.items():
            if record.get('state')=='control-mismatch' or record.get('quarantined'):self.collectors.quarantined_sites[site]='Verified public control mismatch'
    def status(self):
        result={site:dict(self.records.get(site,{'state':'unavailable' if site in CHECKER_HOLDS else 'not-validated','reason':CHECKER_HOLDS.get(site,'No dated public control has been run. No accuracy guarantee.')})) for site in MAIGRET_SITES}
        for record in result.values():
            if record.get('state')=='passed':
                try:age=(date.today()-date.fromisoformat(record['public_verified_on'])).days
                except (KeyError,TypeError,ValueError):age=31
                if not 0<=age<=30:record.update(state='expired',reason='Public control is older than 30 days; validate a current public fixture.')
        return result
    def run(self,p):
        site=p.get('site');username=p.get('username');expected=p.get('expected');verified=p.get('public_verified_on')
        if p.get('consent') is not True or p.get('public_verified') is not True:raise ValueError('Confirm this is a dated, independently checked public control and approve the platform request.')
        if site not in MAIGRET_SITES or not isinstance(username,str) or not re.fullmatch(r'[A-Za-z0-9_][A-Za-z0-9_.-]{0,63}',username) or expected not in ('candidate','absent'):raise ValueError('Choose a reviewed site and expected candidate/absent result.')
        try:age=(date.today()-date.fromisoformat(verified)).days
        except (TypeError,ValueError):raise ValueError('Enter the public control verification date.') from None
        if not 0<=age<=30:raise ValueError('Use a public control independently checked within the last 30 days.')
        result=self.collectors.maigret(username,'control-'+secrets.token_hex(6),[site],ignore_health=True)
        check=next((x for r in result.get('results',[]) for x in r.get('checks',[]) if x.get('site')==site),{})
        outcome=check.get('outcome','unknown');state='passed' if outcome==expected else 'control-mismatch' if outcome in ('candidate','absent') else 'unavailable'
        record={'state':state,'outcome':outcome,'expected':expected,'username':username,'public_verified_on':verified,'checked_at':datetime.now(timezone.utc).isoformat(),'notice':'This checks one platform fixture, not ownership or overall investigation accuracy.'}
        self.records[site]=record
        if state=='control-mismatch':self.collectors.quarantined_sites[site]='Verified control mismatch'
        elif state=='passed':self.collectors.quarantined_sites.pop(site,None)
        record['quarantined']=site in self.collectors.quarantined_sites
        self.path.parent.mkdir(parents=True,exist_ok=True);safe_path(self.path).write_text(json.dumps(self.records),encoding='utf-8')
        return record
