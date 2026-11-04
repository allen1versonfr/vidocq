"""Validate local keys and score sealed reports offline. No network access."""
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from benchmark_evaluation import validate_key,compare_conditions

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--key',type=Path,required=True)
    parser.add_argument('--report',type=Path,action='append',default=[])
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();key=json.loads(args.key.read_text(encoding='utf-8'))
    result=compare_conditions([(str(i+1),json.loads(p.read_text(encoding='utf-8'))) for i,p in enumerate(args.report)],key) if args.report else validate_key(key)
    args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print('Saved local validation/scoring output. No provider queries were made.')
if __name__=='__main__':main()
