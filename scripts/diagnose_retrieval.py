"""Analyze already-sealed controls locally. No API keys or network required."""
import argparse,json,sys
from collections import Counter
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from retrieval_diagnostics import diagnose_control


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--answer-sheet',type=Path,required=True)
    parser.add_argument('--controls',type=Path,required=True,help='Directory containing <account-id>-index.json responses')
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();accounts=json.loads(args.answer_sheet.read_text(encoding='utf-8'))['accounts'];rows=[]
    for account in accounts:
        key=account['id']
        if not isinstance(key,str) or not key or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-' for c in key):raise ValueError('Invalid control id.')
        path=args.controls/(key+'-index.json')
        if not path.is_file() or not account.get('canonical_url'):continue
        rows.append({'id':key,**diagnose_control(account['canonical_url'],json.loads(path.read_text(encoding='utf-8')))})
    args.output.write_text(json.dumps({'controls':rows,'stages':dict(Counter(r['stage'] for r in rows))},indent=2),encoding='utf-8')
    print(json.dumps({'controls':len(rows),'stages':dict(Counter(r['stage'] for r in rows))}))


if __name__=='__main__':main()
