"""Read-only follow-up to failed total gate: no tolerance or source changes.
Uses binaries and arrays from an already completed run, and computes additional
Rust padded outputs under a new diagnostic scratch subdirectory.
"""
import argparse, datetime, hashlib, json, subprocess
from pathlib import Path
import numpy as np
ap=argparse.ArgumentParser();ap.add_argument('--work',type=Path,required=True);ap.add_argument('--out',type=Path,required=True)
a=ap.parse_args();work=a.work.resolve();out=a.out.resolve();primary=json.loads((out/'results.json').read_text(encoding='utf8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,x):p.write_text(json.dumps(x,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf8',newline='\n')
def metrics(x,y):
    assert x.shape==y.shape and np.isfinite(x).all() and np.isfinite(y).all()
    d=np.abs(x-y);bad=np.argwhere(d>1e-14);bits=np.argwhere(x.view('u8')!=y.view('u8'))
    i=np.unravel_index(np.argmax(d),d.shape)
    return {'count':x.size,'max_abs_diff':float(d[i]),'max_coordinate':list(map(int,i)),
            'count_above_1e_minus14':len(bad),'first_above_1e_minus14':None if not len(bad) else list(map(int,bad[0])),
            'bitwise_mismatch_count':len(bits)}
exe=work/'probe/target/release/c01-probe.exe';root=work/'history-diagnostic';root.mkdir(exist_ok=False)
r={'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'tested_commit':primary['tested_commit'],
   'primary_results_sha256_before_redaction':sha(out/'results.json'),'rust_probe_sha256':sha(exe),
   'purpose':'determine whether discrepancy predates the added point; no root-cause isolation','signals':[],'commands':[]}
assert sha(exe)==primary['binary_hashes']['c01-probe.exe']
for s in primary['signals']:
    sig=s['signal'];old=work/f'signal-{sig}-rust';n=np.fromfile(old/'n.bin',dtype='<f8');spec=np.fromfile(old/'spec.bin',dtype='<f8').reshape(240,-1)
    cn=np.fromfile(work/f'signal-{sig}-unpadded-c-n.bin',dtype='<f8');cs=np.fromfile(work/f'signal-{sig}-unpadded-c-spec.bin',dtype='<f8').reshape(240,-1)
    nc=cn[::4];sc=cs[:,::4];common=len(nc)
    d=root/f'signal-{sig}';d.mkdir();x=np.fromfile(old/'input.bin',dtype='<f8');xp=np.r_[x,np.zeros(s['L_pad']-len(x))];xp.tofile(d/'input.bin')
    assert sha(d/'input.bin')==s['input']['padded_pressure_f64le_sha256']
    cmd=[str(exe),str(d/'input.bin'),str(d)];p=subprocess.run(cmd,capture_output=True,text=True,encoding='utf8')
    r['commands'].append({'command':cmd,'exit_code':p.returncode,'stdout':p.stdout,'stderr':p.stderr});assert p.returncode==0
    pn=np.fromfile(d/'n.bin',dtype='<f8');ps=np.fromfile(d/'spec.bin',dtype='<f8').reshape(240,-1)
    r['signals'].append({'signal':sig,'common_output_points':common,
        'C_vs_Rust_common_total':metrics(nc,n[:common]),'C_vs_Rust_common_specific':metrics(sc.copy(),spec[:,:common].copy()),
        'Rust_unpadded_vs_padded_all_original_total':metrics(n,pn[:len(n)]),
        'Rust_unpadded_vs_padded_all_original_specific':metrics(spec,ps[:,:len(n)].copy()),
        'Rust_target_abs_diff':float(abs(n[-1]-pn[s['j']]))})
r['source_observations']={
  'C_pipeline':'ISO_532-1.c:1002-1015: f_calc_slopes writes total/specific, then f_temporal_weight_loudness modifies ONLY OutLoudness',
  'C_history':'ISO_532-1.c:553-574: Y1=B0*X0+A1*Y1, interpolation advances historical state; 607-614 combine 3.5 ms/70 ms branches',
  'Rust_pipeline':'iso532/src/zwtv/mod.rs:130-150: slope totals feed temporal_weighting; specific is sampled directly',
  'Rust_history':'iso532/src/zwtv/temporal_weighting.rs:40-55: y_fast/y_slow carry prior state; combine 0.47/0.53',
  'limitation':'No pre-weighting stage arrays or coefficient intervention measured; root cause and F-03 causality are NOT established.'}
r['source_sha256']={str(p.relative_to(work)):sha(p) for p in [work/'c/ISO_532-1.c',work/'snapshot/iso532/src/zwtv/mod.rs',work/'snapshot/iso532/src/zwtv/temporal_weighting.rs']}
r['finished_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat();write(out/'history-diagnostic.json',r)
print(json.dumps([{k:v for k,v in s.items() if k!='C_vs_Rust_common_specific'} for s in r['signals']],indent=2))
