"""Diagnose a finished local benchmark without any provider calls."""
import argparse,hashlib,json,os,re,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from benchmark_diagnostics import diagnose_misses

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report',type=Path,required=True);parser.add_argument('--key',type=Path,required=True)
    parser.add_argument('--controls',type=Path);parser.add_argument('--seal',type=Path);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();paths=[args.report,args.key]+([args.seal] if args.seal else [])
    def overlaps(p):return args.output.resolve()==p.resolve() or (args.output.exists() and p.exists() and os.path.samefile(args.output,p))
    if any(overlaps(p) for p in paths):raise ValueError('Output must not replace a sealed input.')
    for p in paths:
        if p.stat().st_size>32_000_000:raise ValueError('Input exceeds the 32 MB diagnostic limit.')
    raw=args.report.read_bytes();sheet=json.loads(args.key.read_text(encoding='utf-8'));controls={}
    if args.seal and json.loads(args.seal.read_text(encoding='utf-8')).get('sha256')!=hashlib.sha256(raw).hexdigest():raise ValueError('Sealed report hash mismatch.')
    if args.controls:
        for row in sheet.get('accounts',[]):
            if not isinstance(row.get('id'),str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,64}',row['id']):raise ValueError('Invalid control id.')
            p=args.controls/(row['id']+'-index.json')
            if p.is_file():
                if p.stat().st_size>4_000_000:raise ValueError('Control exceeds 4 MB.')
                if overlaps(p):raise ValueError('Output must not replace a control.')
                controls[row['id']]=json.loads(p.read_text(encoding='utf-8'))
    result=diagnose_misses(json.loads(raw),sheet,controls);result['external_seal_verified']=bool(args.seal)
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps({'stages':result['stages'],'network_requests':0,'discovery_score_changed':False}))

if __name__=='__main__':main()
