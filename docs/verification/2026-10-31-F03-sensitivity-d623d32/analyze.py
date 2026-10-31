from pathlib import Path
import argparse, ctypes as ct, hashlib, json, subprocess
import numpy as np

p=argparse.ArgumentParser();p.add_argument('--prior-work',type=Path,required=True);p.add_argument('--probe-root',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
a.out.mkdir(parents=True,exist_ok=False)
exe=a.probe_root/'target/release/f03-sensitivity-probe.exe'
lib=ct.CDLL(str((a.probe_root/'c/slopes.dll').resolve()));DP=ct.POINTER(ct.c_double)
lib.f_calc_slopes.argtypes=[ct.POINTER(DP),DP,ct.POINTER(DP),ct.c_int];lib.f_calc_slopes.restype=None
def ptr(x):return x.ctypes.data_as(DP)
def metric(x,y):
 d=abs(x-y);tol=np.maximum(.1,.05*abs(y));idx=np.unravel_index(np.argmax(d),d.shape)
 return {'max_abs':float(d[idx]),'index':[int(v) for v in idx],'got':float(x[idx]),'reference':float(y[idx]),'tolerance_at_worst':float(tol[idx]),'exceptions':int((d>tol).sum()),'max_tolerance_fraction':float((d/tol).max())}
def calc(case,mode,input_path,field='free',labels=None):
 d=a.out/case;subprocess.run([str(exe),mode,str(input_path),str(d),field],check=True)
 nm=np.fromfile(d/'nm.bin',dtype='<f8').reshape(-1,21);k=len(nm)
 # Independently guarded C rows; use exactly the same nm frames as both Rust variants.
 cg=np.full((21,k+2),987654.);cg[:,1:-1]=nm.T
 sg=np.full((240,k+2),987654.);sg[:,1:-1]=0.;ng=np.full(k+2,987654.);ng[1:-1]=0.
 cp=(DP*21)(*[ptr(r[1:-1]) for r in cg]);sp=(DP*240)(*[ptr(r[1:-1]) for r in sg])
 for t in range(k):lib.f_calc_slopes(cp,ptr(ng[1:-1]),sp,t)
 assert np.all(cg[:,[0,-1]]==987654.) and np.all(sg[:,[0,-1]]==987654.) and np.all(ng[[0,-1]]==987654.)
 cn=ng[1:-1];cs=sg[:,1:-1].T
 r={v:(np.fromfile(d/f'n{v}.bin',dtype='<f8'),np.fromfile(d/f's{v}.bin',dtype='<f8').reshape(k,240)) for v in ['24','22']}
 assert all(np.isfinite(x).all() for x in [cn,cs,*r['24'],*r['22']])
 n24,s24=r['24'];n22,s22=r['22'];changed=np.any(s24!=s22,axis=1)
 q={'case':case,'mode':mode,'field':field,'frames':k,'input_sha256':hashlib.sha256(input_path.read_bytes()).hexdigest(),'nm_sha256':hashlib.sha256((d/'nm.bin').read_bytes()).hexdigest(),'changed_spec_frames':int(changed.sum()),'changed_n_frames':int((n24!=n22).sum()),'pair_n':metric(n24,n22),'pair_spec':metric(s24,s22),'rust24_vs_c_n':metric(n24,cn),'rust22_vs_c_n':metric(n22,cn),'rust24_vs_c_spec':metric(s24,cs),'rust22_vs_c_spec':metric(s22,cs),'c_guards_pass':True}
 if labels:
  q['fixtures']=[{'label':label,'nm':nm[i].tolist(),'n24':float(n24[i]),'n22':float(n22[i]),'c_n':float(cn[i]),'max_spec_pair':float(abs(s24[i]-s22[i]).max()),'max_spec24_c':float(abs(s24[i]-cs[i]).max()),'max_spec22_c':float(abs(s22[i]-cs[i]).max())}for i,label in enumerate(labels)]
 if mode=='tv':
  w24=np.fromfile(d/'weighted24.bin',dtype='<f8')[::4];w22=np.fromfile(d/'weighted22.bin',dtype='<f8')[::4];q['weighted_pair_n']=metric(w24,w22)
 if mode!='nm':
  prior=input_path.parent;ref=np.load(prior/'c-reference.npz');rn=ref['n'];rs=ref['spec'];m=len(rn)
  bn=np.fromfile(prior/'n.bin',dtype='<f8');bs=np.fromfile(prior/'spec.bin',dtype='<f8')
  actual={v:(np.fromfile(d/f'weighted{v}.bin',dtype='<f8')[::4],r[v][1][::4].T) if mode=='tv' else (r[v][0],r[v][1][0]) for v in ['24','22']}
  if mode=='tv':bs=bs.reshape(240,-1)
  q['saved_c_reference_sha256']=hashlib.sha256((prior/'c-reference.npz').read_bytes()).hexdigest()
  q['baseline24_vs_prior_rust_n']=metric(actual['24'][0][:len(bn)],bn)
  q['baseline24_vs_prior_rust_spec']=metric(actual['24'][1],bs)
  q['output_frames']=len(actual['24'][0]);q['saved_c_output_frames']=m
  for v in ['24','22']:
   nn,ss=actual[v];q[f'output{v}_vs_saved_c_n_common']=metric(nn[:m],rn)
   q[f'output{v}_vs_saved_c_spec_common']=metric(ss[:,:m] if mode=='tv' else ss,rs)
 (d/'c_n.bin').write_bytes(cn.astype('<f8').tobytes());(d/'c_spec.bin').write_bytes(cs.astype('<f8').tobytes())
 print(json.dumps(q,ensure_ascii=False),flush=True);return q

rows=[];labels=[]
for band in [3,4,5]:
 for level in [.299999,.30,.300001,.35,.419999,.42,.420001,.5,1.0]:
  x=np.zeros(21);x[band]=level;rows.append(x);labels.append(f'spike_band{band}_nm{level}')
rows.append(np.full(21,.35));labels.append('flat_nm0.35_control')
rows.append(np.zeros(21));labels.append('silence_control')
f=a.out/'fixtures.bin';np.asarray(rows,dtype='<f8').tofile(f)
cases=[calc('targeted','nm',f,labels=labels)]
for i,mode in [(1,'core'),(10,'tv'),(14,'tv')]:
 cases.append(calc(f'annexb{i:02d}',mode,a.prior_work/f'runs/{i}-{mode}-avx2/input.bin'))
summary={'head':'d623d32931d07c11e327b3226398cd45440ef121','scope':'local slope stage, same nm for two Rust variants and official C; TV total additionally same temporal weighting; not full Annex B acceptance','c_source_sha256':hashlib.sha256((a.probe_root/'c/ISO_532-1.c').read_bytes()).hexdigest(),'cases':cases}
(a.out/'summary.json').write_text(json.dumps(summary,indent=2,ensure_ascii=False),encoding='utf8')
