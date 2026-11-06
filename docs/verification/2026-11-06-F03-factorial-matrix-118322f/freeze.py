"""Freeze immutable reuse and valid factorial cells before numeric execution."""
from pathlib import Path
import json,hashlib,shutil,wave,itertools,datetime,subprocess
import numpy as np
from scipy.io import savemat
R=Path.cwd();O=Path(__file__).resolve().parent;T=R/'tmp/verification-f03-factorial-matrix';P=R/'tmp/verification-f03-three-implementations';OLD=R/'docs/verification/2026-11-06-F03-three-implementations-118322f';OFF=R/'tmp/c01-material/official'
T.mkdir(exist_ok=True);(T/'inputs').mkdir(exist_ok=True)
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(n,x):(O/n).write_text(json.dumps(x,indent=2),encoding='utf8')
prev=json.loads((OLD/'delivery-integrity.json').read_text())
for rel,m in prev['files'].items():assert sha(OLD/rel)==m['sha256']
f=json.loads((OLD/'frozen-inputs.json').read_text())
for rel,h in f['raw_inputs'].items():assert sha(OFF/rel)==h
with wave.open(str(next(OFF.rglob('calibration signal sine 1kHz 60dB.wav')))) as w:x=np.frombuffer(w.readframes(w.getnframes()),'<i2').astype(float)/32768
cal={'sqrt':2*np.sqrt(2),'cal':.02/np.sqrt(np.mean(x*x))};assert abs(cal['cal']-2.835797716391444)<1e-14
for s in range(2,26):
 with wave.open(str(next(OFF.rglob(f'Test signal {s} (*.wav')))) as w:x=np.frombuffer(w.readframes(w.getnframes()),'<i2').astype(float)/32768
 for c,a in cal.items():
  y=x*a;np.save(T/f'inputs/sig{s}-{c}.npy',y)
  if s in [6,15,16,25]:savemat(T/f'inputs/sig{s}-{c}.mat',{'x':y.reshape(-1,1)})
source={};modifications=[]
for u in ['022','024']:
 for mode in ['round','noround']:
  d=T/f'mos{u}-{mode}'/'mosqito';shutil.copytree(P/f'mos{u}/mosqito',d,ignore=shutil.ignore_patterns('__pycache__'),dirs_exist_ok=True)
  p=d/'sq_metrics/loudness/loudness_zwst/_calc_slopes.py';raw=p.read_text(encoding='utf8')
  if mode=='noround':
   lines=['    N[N <= 16] = floor(N[N <= 16] * 1000 + 0.5) / 1000\n','    N[N > 16] = floor(N[N > 16] * 100 + 0.5) / 100\n']
   for line in lines:assert raw.count(line)==1;raw=raw.replace(line,'')
   p.write_text(raw,encoding='utf8');modifications.append({'variant':u,'mode':mode,'removed_statements':[z.strip() for z in lines],'negative_clamp_retained':'    N[N < 0] = 0' in raw,'sha256':sha(p)})
  source[f'mos{u}-{mode}']={q.relative_to(d).as_posix():sha(q) for q in d.rglob('*.py')}
design=[]
for s,F,G,W,U,B in itertools.product(range(2,6),['annex','noct'],['sqrt','cal'],[0,.2],['022','024'],['c','sqat','mos-round','mos-noround']):
 design.append({'id':f'A-s{s}-{F}-{G}-w{W}-{U}-{B}','domain':'stationary','signal':s,'frontend':F,'calibration':G,'skip_s':W,'usl':U,'backend':B,'execution':'new','native_or_hybrid':'hybrid shared levels; original stage' if B!='mos-noround' else 'hybrid diagnostic no-round'})
for s,F in itertools.product(range(2,6),['annex','noct']):design.append({'id':f'crop-s{s}-{F}','domain':'crop-control','signal':s,'frontend':F,'calibration':'sqrt','skip_s':0,'usl':'022','backend':'c','crop_samples':9600,'execution':'new'})
rawhashes=json.loads((OLD/'raw-output-hashes.json').read_text())
for s,G,U,B in itertools.product([6,15,16,25],['sqrt','cal'],['022','024'],['c','sqat','mos-round','mos-noround']):
 reuse=G=='sqrt' and B!='mos-noround';engine=B.split('-')[0];ext='mat' if engine=='sqat' else 'npz';path=f'{engine}{U}-outputs/sig{s}.{ext}'
 cell={'id':f'B-s{s}-{G}-{U}-{B}','domain':'timevarying','signal':s,'calibration':G,'usl':U,'backend':B,'execution':'reuse' if reuse else 'new'}
 if reuse:assert sha(P/path)==rawhashes[path];cell.update(reuse_path=path,reuse_sha256=rawhashes[path])
 design.append(cell)
write('design-matrix.json',design)
write('frozen-inputs.json',{'frozen_at':datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat(),'head':subprocess.check_output(['git','rev-parse','HEAD']).decode().strip(),'product':'118322f8300dc752f1d38a79db230a2db5ff2870','calibration':cal,'original_inputs':f['raw_inputs'],'generated_inputs':{p.relative_to(T).as_posix():sha(p) for p in (T/'inputs').iterdir()},'source_hashes':source,'mo_no_round_changes':modifications,'prior_delivery_manifest_sha256':sha(OLD/'delivery-integrity.json'),'prior_raw_outputs':rawhashes,'c_dlls':{u:sha(P/f'c{u}/reference.dll') for u in ['022','024']},'annex_frontend_dll':sha(R/'tmp/verification-f03-filter-independent/c022/reference.dll'),'sqat_freeze':json.loads((OLD/'sqat-freeze.json').read_text()),'preregistration_sha256':sha(O/'preregistration.md'),'preregistration_zh_sha256':sha(O/'preregistration.zh-TW.md')})
print('Frozen: stationary256 + crop8 new; TV64=24reuse+40new; new total304')
