import json,pathlib,hashlib,sys
p=pathlib.Path(__file__).resolve().parent
allcases={}
for name in ['rust','c']:
 rows=[json.loads(line) for line in (p/f'{name}-results.jsonl').read_text(encoding='utf-8-sig').splitlines() if line.strip()]
 allcases[name]={'cases':len(rows),'passed':sum(v['pass'] for v in rows),'failed':sum(not v['pass'] for v in rows),'failures':[v for v in rows if not v['pass']]}
pyr=json.loads((p/'python-results.json').read_text(encoding='utf8'))
allcases['python']={'cases':len(pyr['cases']),'passed':pyr['passed'],'failed':pyr['failed']}
source=pathlib.Path('tmp/acceptance-031/source');wav=[]
for f in sorted((source/'data/annexb').glob('*.wav')):wav.append({'name':f.name,'sha256':hashlib.sha256(f.read_bytes()).hexdigest()})
result=dict(status='passed' if all(v['failed']==0 for v in allcases.values()) else 'failed',languages=allcases,input_wav_hashes=wav,first_mismatch=None if all(v['failed']==0 for v in allcases.values()) else 'see language case records',prefix_official_signals=[3,5,10],prefix_lengths=[4801,24013,47927],prefix_comparison='n,time_axis,all240Bark rows using f64::to_bits',C_boundary_scenarios={'0':'bad fs plus NaN =>3','1':'short plus NaN =>2','2':'two nonfinite =>4, C has no index return','3':'smallest positive subnormal','4':'positive zero','5':'negative zero','6':'1e300'})
(p/'results.json').write_text(json.dumps(result,indent=2),encoding='utf8');print(json.dumps(allcases));sys.exit(result['status']!='passed')
