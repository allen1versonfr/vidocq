"""Normalize an explicitly downloaded upstream arf.json; no remote code execution."""
import argparse,collections,hashlib,json
from pathlib import Path
from urllib.parse import urlparse

parser=argparse.ArgumentParser();parser.add_argument('input',type=Path);parser.add_argument('--revision',required=True);parser.add_argument('--output',type=Path,default=Path('source-catalog.json'));args=parser.parse_args()
root=json.loads(args.input.read_text(encoding='utf-8'))
entries=[]
def walk(node,path=()):
    if node.get('url'):
        name=str(node.get('name','Untitled'));url=str(node['url']);p=urlparse(url)
        categories=list(path[1:]) or ['Other']
        pricing=str(node.get('pricing') or 'unknown').lower()
        if pricing not in ('free','freemium','free/freemium','paid'):pricing='unknown'
        host=p.hostname or ''
        if host in ('crt.sh','web.archive.org','openlibrary.org'):integration='integrated';reason='A reviewed read-only adapter retrieves existing records inside Vidocq.'
        elif (host in ('www.google.com','www.bing.com') and p.path in ('','/','/search','/advanced_search')) or (host in ('duckduckgo.com','scholar.google.com','pubmed.ncbi.nlm.nih.gov','patents.google.com') and p.path in ('','/')):integration='prepared-search';reason='Reviewed search-index links are available; no original result page is visited automatically.'
        else:integration='index-only';reason='Search indexed pages from this source through Google. The provider tool itself is not integrated or executed.'
        if pricing=='paid':integration='excluded';reason='Upstream marks this entry as paid. It is excluded from the free-access catalog by default.'
        elif pricing=='unknown':integration='unverified';reason='Upstream does not establish a free tier. No free-access or working-tool claim is made.'
        # Preserve conflicting upstream flags instead of treating a passive label as proof of safety.
        opsec=str(node.get('opsec') or 'unknown').lower()
        caution=[]
        if opsec!='passive':caution.append('Upstream marks behavior as '+opsec+'.')
        if node.get('localInstall') or '(T)' in name:caution.append('Separate installation is required; Vidocq does not install or run this tool.')
        if node.get('registration') or '(R)' in name:caution.append('Registration may be required.')
        if node.get('editUrl') or '(M)' in name:caution.append('Original URL contains a manual template; it is not filled or opened by Vidocq.')
        status=str(node.get('status') or 'unknown').lower()
        if status!='live':caution.append('Upstream status: '+status+'.')
        text=(name+' '+str(node.get('description',''))+' '+str(node.get('opsecNote',''))).lower()
        if any(x in text for x in ('password-reset','password reset','account recovery','account existence','account-existence','enumeration','scan','screenshot','credential','breach')):
            caution.append('Do not infer notification safety from directory metadata. Target checks, submissions, scans, and credential lookups are not enabled by this catalog.')
        entries.append({'id':hashlib.sha256((url+'|'+str(categories)+'|'+name+'|'+str(len(entries))).encode()).hexdigest()[:20],
            'name':name,'url':url,'category':categories,'pricing':pricing,'upstream_status':status,'upstream_opsec':opsec,
            'registration':bool(node.get('registration') or '(R)' in name),'local_install':bool(node.get('localInstall') or '(T)' in name),
            'api_listed':bool(node.get('api')),'description':str(node.get('description') or 'No description supplied by the framework.'),
            'integration':integration,'reason':reason,'cautions':caution})
    for child in node.get('children',[]):walk(child,path+(str(node.get('name','')),))
walk(root)
summary={'entries':len(entries),'pricing':dict(collections.Counter(x['pricing'] for x in entries)),
         'integration':dict(collections.Counter(x['integration'] for x in entries)),
         'free_access':sum(x['pricing'] in ('free','freemium','free/freemium') for x in entries)}
result={'schema_version':1,'provenance':{'source':'https://osintframework.com/','repository':'https://github.com/lockfale/OSINT-Framework','path':'public/arf.json','revision':args.revision,'sha256':hashlib.sha256(args.input.read_bytes()).hexdigest(),'retrieved_on':'2026-11-03','license':'MIT','notice':'Pricing, status and descriptions are upstream metadata, not individual live verification. Index searches are not provider integrations.'},'summary':summary,'categories':sorted(set(x['category'][0] for x in entries)),'entries':entries}
args.output.write_text(json.dumps(result,ensure_ascii=True,separators=(',',':')),encoding='utf-8')
print(json.dumps(summary,indent=2))
