"""Offline framework catalog. External tools are never executed by catalog actions."""
from functools import lru_cache
import json
from pathlib import Path
import re
import sys
from urllib.parse import urlencode,urlparse

ROOT=Path(getattr(sys,'_MEIPASS',Path(__file__).resolve().parent))
FREE_PRICING={'free','freemium','free/freemium'}

@lru_cache(maxsize=1)
def catalog():
    data=json.loads((ROOT/'source-catalog.json').read_text(encoding='utf-8'))
    if not isinstance(data.get('entries'),list):raise ValueError('Invalid source catalog.')
    return data


def query_catalog(params):
    query=str(params.get('q','')).strip().casefold()[:240]
    category=str(params.get('category',''))[:160]
    pricing=str(params.get('pricing','free-access'))
    mode=str(params.get('mode','all'))
    try:offset=max(0,min(int(params.get('offset',0)),10000))
    except (ValueError,TypeError):raise ValueError('Invalid source page.')
    data=catalog();rows=[]
    for item in data['entries']:
        if pricing=='free-access' and item['pricing'] not in FREE_PRICING:continue
        if pricing in ('free','freemium','paid','unknown') and item['pricing']!=pricing:continue
        if category and item['category'][0]!=category:continue
        if mode!='all' and item['integration']!=mode:continue
        if query and query not in (' '.join(item['category'])+' '+item['name']+' '+item['description']+' '+item['url']).casefold():continue
        rows.append(item)
    return {'total':len(rows),'offset':offset,'limit':30,'entries':rows[offset:offset+30],
            'categories':data['categories'],'summary':data['summary'],'provenance':data['provenance']}


def indexed_source_url(source_id,query):
    if not isinstance(query,str) or not query.strip() or len(query)>240 or any(ord(c)<32 for c in query):
        raise ValueError('Enter a query of 1–240 characters.')
    item=next((x for x in catalog()['entries'] if x['id']==source_id),None)
    if not item or item['pricing'] not in FREE_PRICING:raise ValueError('Choose a source with upstream free-access metadata.')
    host=urlparse(item['url']).hostname or ''
    if not re.fullmatch(r'[a-zA-Z0-9-]+(?:\.[a-zA-Z0-9-]+)+',host):raise ValueError('This entry does not have a supported index-search domain.')
    # Search only a third-party index; never visit the source URL or substitute a subject into it.
    return 'https://www.google.com/search?'+urlencode({'q':'site:'+host+' "'+query.strip().replace('"','')+'"'})
