"""MIT licensed fixed contracts shared by isolated collector executables."""
import re
from collector_policy import HARVESTER_SOURCES

HARVESTER_COMMIT='6790b147f52309e4eee22ed941db1d285ab2ec23'
OSINTGRAM_COMMIT='a560498be79a3bf40d7f3b203ad174661b8e81e7'
PHOTON_COMMIT='c8d2566841d69a268b244609921143d84b72b0c6'
OG_COMMANDS=('get_user_info','get_account_about','get_captions','get_hashtags')
FLAGS=('dns_brute','dns_lookup','dns_resolve','routeviews','shodan','screenshot','takeover','api_scan','vhost')

def harvester_request(p):
    allowed={'target','sources','limit','source_workers','deadline_seconds','dns_recursive_depth',*FLAGS}
    if not isinstance(p,dict) or set(p)-allowed:raise ValueError('Unsupported collector request fields.')
    target=p.get('target');sources=p.get('sources')
    if not isinstance(target,str) or len(target)>253 or not re.fullmatch(r'(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,63}',target):raise ValueError('Choose a domain name.')
    if not isinstance(sources,list) or not 1<=len(sources)<=4 or any(s not in HARVESTER_SOURCES for s in sources):raise ValueError('Choose up to four reviewed passive sources.')
    if any(p.get(f,False) is not False for f in FLAGS) or p.get('dns_recursive_depth',0)!=0:raise ValueError('Managed theHarvester supports passive P0 activity only.')
    if any(type(p.get(k)) is not int or p[k]!=v for k,v in [('limit',50),('source_workers',1),('deadline_seconds',60)]):raise ValueError('Managed collector limits must remain fixed.')
    return p
