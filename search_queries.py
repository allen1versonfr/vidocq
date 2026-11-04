"""One query representation for scheduling, request sharing and provider calls."""
import unicodedata

INDEX_SITES=('instagram.com','tiktok.com','vsco.co','steamcommunity.com','linkedin.com','github.com','last.fm')

def render_query(terms,site=None):
    if site is not None and site not in INDEX_SITES:raise ValueError('Unsupported social index scope.')
    if not isinstance(terms,list) or not 1<=len(terms)<=4 or any(not isinstance(t,str) or not t.strip() or len(t)>2000 or any(ord(c)<32 for c in t) for t in terms) or sum(len(t) for t in terms)>2200:raise ValueError('Invalid context search terms.')
    cleaned=[' '.join(unicodedata.normalize('NFKC',t).replace('"','').replace('\\','').split()) for t in terms]
    if any(not t for t in cleaned):raise ValueError('Search terms cannot be empty after formatting.')
    return ('site:'+site+' ' if site else '')+' '.join('"'+t+'"' for t in cleaned)

def query_key(terms,site=None):return render_query(terms,site).casefold()
