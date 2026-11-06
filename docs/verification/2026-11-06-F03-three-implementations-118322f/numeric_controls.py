"""Final source-isolation and full-output controls; no product changes."""
from pathlib import Path
import hashlib,json,ctypes as C,sys
import numpy as np
from scipy.io import loadmat
ROOT=Path.cwd();OUT=Path(__file__).resolve().parent;TMP=ROOT/'tmp/verification-f03-three-implementations';OFF=ROOT/'tmp/c01-material/official'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
freeze=json.loads((OUT/'frozen-inputs.json').read_text());sq=json.loads((OUT/'sqat-freeze.json').read_text())
checks={}
for rel,h in freeze['raw_inputs'].items():assert sha(OFF/rel)==h
checks['raw_inputs_unchanged']=len(freeze['raw_inputs'])
for rel,h in freeze['generated_inputs'].items():assert sha(TMP/rel)==h
checks['generated_inputs_unchanged']=len(freeze['generated_inputs'])
for rel,h in freeze['mosqito_source'].items():assert sha(TMP/'mos024/mosqito'/rel)==h
for rel,h in sq['baseline'].items():assert sha(TMP/'sqat-v2.0'/rel)==h
for rel,h in sq['counterfactual'].items():assert sha(TMP/'sqat022'/rel)==h
checks['baseline_sources_unchanged']=True
diffs={}
for engine,a,b,glob in [('mos','mos024/mosqito','mos022/mosqito','*.py'),('sqat','sqat-v2.0','sqat022','*.m')]:
 aa=TMP/a;bb=TMP/b;paths={p.relative_to(aa).as_posix() for p in aa.rglob(glob)};assert paths=={p.relative_to(bb).as_posix() for p in bb.rglob(glob)}
 changed=[p for p in paths if (aa/p).read_bytes()!=(bb/p).read_bytes()];assert len(changed)==1
 old=(aa/changed[0]).read_bytes();new=(bb/changed[0]).read_bytes();positions=[i for i,(x,y) in enumerate(zip(old,new)) if x!=y]
 assert len(old)==len(new) and len(positions)==1 and old[positions[0]]==ord('4') and new[positions[0]]==ord('2')
 diffs[engine]={'only_changed_source':changed[0],'changed_byte_offset':positions[0],'baseline_byte':'4','counterfactual_byte':'2'}
old=(TMP/'c022/ISO_532-1.c').read_bytes();new=(TMP/'c024/ISO_532-1.c').read_bytes();positions=[i for i,(x,y) in enumerate(zip(old,new)) if x!=y]
assert len(old)==len(new) and len(positions)==1 and old[positions[0]]==ord('2') and new[positions[0]]==ord('4')
diffs['c']={'only_changed_source':'ISO_532-1.c','changed_byte_offset':positions[0],'baseline_byte':'2','counterfactual_byte':'4'}
checks['source_isolation']=diffs
outcounts={}
for engine in ['c','mos','sqat']:
 for v in ['022','024']:
  count=0
  for s in range(1,26):
   p=TMP/f'{engine}{v}-outputs'/f'sig{s}.{ "mat" if engine=="sqat" else "npz"}'
   d=loadmat(p) if engine=='sqat' else np.load(p)
   n=np.asarray(d['n']).ravel();ns=np.asarray(d['ns']).reshape(240,-1);t=np.asarray(d['t']).ravel()
   assert len(t)==len(n)==ns.shape[1] and np.isfinite(n).all() and np.isfinite(ns).all() and np.isfinite(t).all()
   assert n.min()>=0 and ns.min()>=-1e-10
   count+=1
  outcounts[engine+v]=count
checks['finite_shape_checked_outputs']=outcounts
# Independently load the pre-existing original-source DLL and freshly evaluate inputs.
# This verifies that adding exports/core extraction in this round did not change C results.
P=C.POINTER(C.c_double);PP=C.POINTER(P)
class Input(C.Structure):_fields_=[('NumSamples',C.c_int),('SampleRate',C.c_double),('pData',P)]
def ptrs(a):return (P*len(a))(*(row.ctypes.data_as(P) for row in a))
previous=ROOT/'tmp/verification-f03-filter-independent/c022/reference.dll';lib=C.CDLL(str(previous))
lib.f_loudness_from_signal.argtypes=[C.POINTER(Input),C.c_int,C.c_int,C.c_double,P,PP,C.c_int]
lib.f_loudness_from_levels.argtypes=[PP,C.c_int,C.c_int,C.c_int,P,PP]
checked=[]
for s in range(1,26):
 x=np.load(TMP/f'inputs/sig{s}.npy');k=len(x)//24 if s>=6 else 1;n=np.zeros(k);ns=np.zeros((240,k))
 if s==1:
  lv=x.reshape(28,1).copy();rc=lib.f_loudness_from_levels(ptrs(lv),1,0,0,n.ctypes.data_as(P),ptrs(ns))
 else:
  inp=Input(len(x),48000,x.ctypes.data_as(P));rc=lib.f_loudness_from_signal(C.byref(inp),int(s==15),int(s>=6),.2 if s<=5 else 0,n.ctypes.data_as(P),ptrs(ns),k)
 assert rc==k
 if s>=6:n=n[::4];ns=ns[:,::4]
 d=np.load(TMP/f'c022-outputs/sig{s}.npz');assert np.array_equal(n,d['n']) and np.array_equal(ns,d['ns'])
 checked.append(s)
checks['c_wrapper_vs_prior_original_dll_fresh_evaluations']={'signals':checked,'bitwise_equal':True,'prior_dll_sha256':sha(previous),'prior_numeric_outputs_reused':False}
checks['common_controls_exact_zero']=all(json.loads((OUT/'common-stage-metrics.json').read_text())[e][name]['N_delta']==0 for e in ['c','mos','sqat'] for name in ['zero-control','signal2-control'])
assert checks['common_controls_exact_zero']
(OUT/'numeric-controls.json').write_text(json.dumps(checks,indent=2),encoding='utf8')
print(json.dumps(checks,indent=2))
