"""Independent numeric acceptance. Usage: python run.py --repo REPO_ROOT"""
import argparse, hashlib, importlib.util, json, math, os, re, subprocess, sys
from pathlib import Path
import numpy as np
from scipy.io import wavfile
from scipy.signal import resample_poly
p=argparse.ArgumentParser(); p.add_argument('--repo',type=Path,required=True); args=p.parse_args()
repo=args.repo.resolve(); out=Path(__file__).resolve().parent; work=repo/'tmp/acceptance-031'; src=work/'source'; base=work/'baseline'; tmp=work/'numerics-work'; tmp.mkdir(exist_ok=True)
env=dict(os.environ,CARGO_BUILD_JOBS='2',RAYON_NUM_THREADS='2')
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def run(cmd,log,cwd=None):
 r=subprocess.run([str(x) for x in cmd],cwd=cwd,env=env,capture_output=True,text=True,encoding='utf-8',errors='replace'); (out/log).write_text('$ '+' '.join(map(str,cmd))+'\n'+r.stdout+r.stderr,encoding='utf-8'); return r
result={'baseline_commit':subprocess.check_output(['git','rev-parse','v0.3.0^{commit}'],cwd=repo,text=True).strip(),'baseline_tag_object_sha':subprocess.check_output(['git','rev-parse','v0.3.0'],cwd=repo,text=True).strip(),'source_commit':'30e427963da88db8b23e82cf612f047f36cd164b','tools':{'python':sys.version,'numpy':np.__version__},'inputs':[],'comparisons':[],'controls':[],'margins':[]}
exes={}
for label,source in [('old',base),('new',src)]:
 d=tmp/label; d.mkdir(exist_ok=True); (d/'src').mkdir(exist_ok=True)
 (d/'Cargo.toml').write_text('[package]\nname="numeric_acceptance_'+label+'"\nversion="0.0.0"\nedition="2021"\n[workspace]\n[dependencies]\niso532={path="'+(source/'iso532').as_posix()+'"}\n',encoding='utf-8')
 (d/'src/main.rs').write_text((out/'harness.rs').read_text(encoding='utf-8-sig').replace('COMMON_PATH',(src/'iso532/tests/common/mod.rs').as_posix()),encoding='utf-8')
 lock=out/(label+'-Cargo.lock')
 if lock.exists(): (d/'Cargo.lock').write_bytes(lock.read_bytes())
 target=work/('numerics-target-'+label); r=run(['cargo','build','--release','--offline','--manifest-path',d/'Cargo.toml','--target-dir',target],label+'-build.log'); assert r.returncode==0,r.stderr
 exes[label]=target/'release'/('numeric_acceptance_'+label+'.exe'); result[label+'_binary_sha256']=sha(exes[label])
 print('built',label,flush=True)
inputs=[]
for i,w in enumerate(sorted((src/'data/annexb').glob('*.wav'))):
 fs,raw=wavfile.read(w); x=raw.astype(np.float64)
 if raw.dtype.kind=='i': x/=2**(raw.dtype.itemsize*8-1)
 elif raw.dtype==np.uint8: x=(x-128)/128
 if x.ndim>1: x=x.mean(axis=1)
 x*=2*math.sqrt(2)
 if fs!=48000: g=math.gcd(int(fs),48000); x=resample_poly(x,48000//g,int(fs)//g)
 f=tmp/f'wav_{i}.bin'; np.asarray(x,dtype='<f8').tofile(f); inputs.append((w.name,f));result['inputs'].append({'name':w.name,'wav_sha256':sha(w),'original_fs':int(fs),'original_dtype':str(raw.dtype),'prepared_samples':len(x),'prepared_f64_sha256':sha(f),'preparation':'PCM normalized, mono mean if multichannel, calibration 2*sqrt(2), scipy.resample_poly to 48000 if needed'})
spec=importlib.util.spec_from_file_location('frozen_testkit',src/'tools/iso532_testkit.py'); mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
f=tmp/'contract.bin'; mod.contract_signal(3*48000).astype('<f8').tofile(f);inputs.append(('contract_3s',f));result['inputs'].append({'name':'contract_3s','samples':3*48000,'prepared_f64_sha256':sha(f),'generator_sha256':sha(src/'tools/iso532_testkit.py')})
for i,(name,f) in enumerate(inputs):
 for label in exes:
  r=run([exes[label],'compute',f,tmp/f'{label}_{i}'],f'{label}-input-{i}.log');assert r.returncode==0,r.stderr
 for field in ['st_n','st_spec','tv_n','tv_spec','tv_time']:
  a=tmp/f'old_{i}'/(field+'.bin'); b=tmp/f'new_{i}'/(field+'.bin'); av=np.fromfile(a,dtype='<u8');bv=np.fromfile(b,dtype='<u8'); dif=np.flatnonzero(av!=bv) if len(av)==len(bv) else np.array([]); first=None
  if len(dif):
   j=int(dif[0]);first={'flat_index':j,'old_bits':f'{int(av[j]):016x}','new_bits':f'{int(bv[j]):016x}'}
   if field=='tv_spec':first.update(bark_row=j//(len(av)//240),frame=j%(len(av)//240))
  result['comparisons'].append({'input':name,'field':field,'old_count':len(av),'new_count':len(bv),'old_sha256':sha(a),'new_sha256':sha(b),'equal':a.read_bytes()==b.read_bytes(),'first_diff':first})
 print('compared',name,flush=True)
r=run([exes['new'],'controls'],'validator-controls.log');assert r.returncode==0; result['direct_control_count']=len(r.stdout.strip().splitlines())
# Actual copies, always under tmp, never data.
original=(src/'data/annexb/test_signal_3.csv').read_text(encoding='utf-8-sig').splitlines()
for name,repl in [('unparsable','abc'),('blank','  '),('bom','\ufeff0.0'),('nan','NaN'),('posinf','inf'),('neginf','-inf')]:
 lines=original.copy(); lines[120]=repl;f=tmp/(name+'.csv');f.write_text('\n'.join(lines)+'\n',encoding='utf-8');r=run([exes['new'],'csv',f],name+'-csv.log'); ok=(r.returncode!=0 if name in ['unparsable','blank','bom'] else 'Invalid' in r.stdout);result['controls'].append({'name':'csv_'+name,'passed':ok,'exit_code':r.returncode,'copy_sha256':sha(f)})
for name,lines in [('missing_row',original[:-1]),('header_only',original[:1]),('empty',[])]:
 f=tmp/(name+'.csv');f.write_text('\n'.join(lines)+'\n',encoding='utf-8');r=run([exes['new'],'csv',f],name+'-csv.log');result['controls'].append({'name':'csv_'+name,'passed':r.returncode!=0,'exit_code':r.returncode,'copy_sha256':sha(f)})
raw=(src/'data/golden/annexb_sig10/tv_nref.bin').read_bytes()
for size in [1,7,9,15,17]:
 f=tmp/f'truncated-{size}.bin';f.write_bytes(raw[:size]);r=run([exes['new'],'bin',f],f'bin-{size}.log');result['controls'].append({'name':f'bin_truncated_{size}','passed':r.returncode!=0,'exit_code':r.returncode,'copy_sha256':sha(f)})
# Recreate the five actual Annex test comparisons using frozen input bins.
for signal in [3,5,10]:
 d=tmp/f'margin_{signal}';r=run([exes['new'],'compute',src/f'data/golden/annexb_sig{signal}/sig.bin',d],f'margin-{signal}.log');assert r.returncode==0
 curves=[('tv_n',np.fromfile(src/'data/golden/annexb_sig10/tv_nref.bin',dtype='<f8'))] if signal==10 else [('st_n',np.array([4.019 if signal==3 else 10.498])),('st_spec',np.loadtxt(src/f'data/annexb/test_signal_{signal}.csv',skiprows=1,encoding='utf-8-sig'))]
 for field,ref in curves:
  got=np.fromfile(d/(field+'.bin'),dtype='<f8'); margin=np.maximum(.1,.05*np.abs(ref))-np.abs(got-ref);j=int(np.argmin(margin)); rf=tmp/f'ref-{signal}-{field}.bin';ref.astype('<f8').tofile(rf);v=run([exes['new'],'verdict',d/(field+'.bin'),rf],f'verdict-{signal}-{field}.log');assert 'Pass' in v.stdout
  result['margins'].append({'signal':signal,'field':field,'points':len(ref),'minimum_margin':float(margin[j]),'index_zero_based':j,'got_bits':f'{int(got.view(np.uint64)[j]):016x}','reference_bits':f'{int(ref.view(np.uint64)[j]):016x}','passed':bool(np.all(margin>=0))})
result['minimum_margin']=min(result['margins'],key=lambda x:x['minimum_margin'])
result['finite_status']='passed' if all(c['equal'] for c in result['comparisons']) else 'failed'
result['validator_status']='passed' if all(c['passed'] for c in result['controls']) and all(c['passed'] for c in result['margins']) else 'failed'
result['compared_f64_count']=sum(c['old_count'] for c in result['comparisons']);result['source_hashes']={str(f.relative_to(src)):sha(f) for f in [src/'iso532/tests/common/annexb_check.rs',src/'iso532/tests/common/mod.rs',src/'iso532/tests/annexb.rs',src/'iso532/tests/hash_gate.rs']}
(out/'results.json').write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
print(result['finite_status'],result['validator_status'],result['minimum_margin'],flush=True)
