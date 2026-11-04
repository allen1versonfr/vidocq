"""Dated operator-verified public controls; no account existence inferred from failures."""
from datetime import date,datetime,timezone
import json,re,secrets,hashlib
from pathlib import Path
from collector_policy import MAIGRET_SITES,CHECKER_HOLDS
from managed_local_ai import safe_path

class CheckerHealth:
    def __init__(self,data,collectors):
        self.path=Path(data)/'checker-health.json';self.collectors=collectors;self.records={}
        try:
            if safe_path(self.path).is_file() and self.path.stat().st_size<500000:
                records=json.loads(self.path.read_text(encoding='utf-8'))
                if isinstance(records,dict):self.records={k:v for k,v in records.items() if k in MAIGRET_SITES and isinstance(v,dict)}
        except (OSError,ValueError):pass
        for site,record in self.records.items():
            if record.get('state')=='control-mismatch' or record.get('quarantined'):self.collectors.quarantined_sites[site]='Verified public control mismatch'
    def status(self):
        result={site:dict(self.records.get(site,{'state':'unavailable' if site in CHECKER_HOLDS else 'not-validated','reason':CHECKER_HOLDS.get(site,'No dated public control has been run. No accuracy guarantee.')})) for site in MAIGRET_SITES}
        for record in result.values():
            if record.get('state')=='passed':
                for control in record.get('controls',{'legacy':record}).values():
                    try:age=(date.today()-date.fromisoformat(control['public_verified_on'])).days
                    except (KeyError,TypeError,ValueError):age=31
                    if not 0<=age<=30:record.update(state='expired',reason='A public control is older than 30 days; validate current positive and negative fixtures.')
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
        control={'state':state,'outcome':outcome,'expected':expected,'username':username,'public_verified_on':verified,'checked_at':datetime.now(timezone.utc).isoformat(),'response_sha256':hashlib.sha256(json.dumps(result,sort_keys=True).encode()).hexdigest(),'diagnostics':check.get('diagnostics',{})}
        previous=self.records.get(site,{});controls=dict(previous.get('controls',{}));controls[expected]=control
        current=[]
        for value in controls.values():
            try:age=(date.today()-date.fromisoformat(value['public_verified_on'])).days
            except (KeyError,ValueError,TypeError):age=31
            if value.get('state')=='passed' and 0<=age<=30:current.append(value['expected'])
        both=set(current)=={'candidate','absent'}
        aggregate='control-mismatch' if any(c.get('state')=='control-mismatch' for c in controls.values()) else 'passed' if both else 'partial-validation' if current else 'unavailable'
        record={**control,'state':aggregate,'controls':controls,'history':(previous.get('history',[])+[control])[-12:],'notice':'A passing dated positive AND negative control are needed to clear quarantine. This validates these fixtures, not all accounts or ownership.'}
        self.records[site]=record
        if aggregate=='control-mismatch':self.collectors.quarantined_sites[site]='Verified control mismatch'
        elif both:self.collectors.quarantined_sites.pop(site,None)
        record['quarantined']=site in self.collectors.quarantined_sites
        self.path.parent.mkdir(parents=True,exist_ok=True);part=safe_path(self.path.with_name('checker-health.json.part'));part.write_text(json.dumps(self.records),encoding='utf-8');part.replace(safe_path(self.path))
        return record
