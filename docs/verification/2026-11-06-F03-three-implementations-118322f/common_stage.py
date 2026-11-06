"""Same exact 21-band slope input for native C, Python and extracted native SQAT .m."""
from pathlib import Path
import ctypes as C,sys,importlib.util,json,hashlib
import numpy as np
from scipy.io import savemat
ROOT=Path.cwd();OUT=Path(__file__).resolve().parent;TMP=ROOT/'tmp/verification-f03-three-implementations'
P=C.POINTER(C.c_double);PP=C.POINTER(P)
class Input(C.Structure):_fields_=[('NumSamples',C.c_int),('SampleRate',C.c_double),('pData',P)]
def ptrs(a):return (P*len(a))(*(row.ctypes.data_as(P) for row in a))
libs={}
for v in ['022','024']:
 l=C.CDLL(str(TMP/f'c{v}/reference.dll'));l.audit_core.argtypes=[C.POINTER(Input),C.c_int,C.c_int,C.c_double,PP]
 l.f_calc_slopes.argtypes=[PP,P,PP,C.c_int];libs[v]=l
def core(s):
 x=np.load(TMP/f'inputs/sig{s}.npy');k=len(x)//24 if s>=6 else 1;a=np.zeros((21,k));inp=Input(len(x),48000,x.ctypes.data_as(P))
 rc=libs['022'].audit_core(C.byref(inp),int(s==15),int(s>=6),.2 if s<=5 else 0,ptrs(a));assert rc==k
 return a
def slopes(a,v):
 n=np.zeros(a.shape[1]);ns=np.zeros((240,a.shape[1]));cp=ptrs(a);sp=ptrs(ns)
 for j in range(len(n)):libs[v].f_calc_slopes(cp,n.ctypes.data_as(P),sp,j)
 return n,ns
a=core(6);lo=slopes(a,'022');hi=slopes(a,'024');idx=int(np.argmax(abs(lo[0]-hi[0])))
synthetic=np.zeros(21);synthetic[4]=.35
shared=np.ascontiguousarray(np.column_stack([synthetic,np.zeros(21),a[:,idx],core(2)[:,0]]))
names=['synthetic-band5-0p35','zero-control','signal6-sensitive','signal2-control']
savemat(TMP/'common-core.mat',{'core':shared});np.save(TMP/'common-core.npy',shared)
meta={'selection':'maximum absolute unweighted N delta on all native C signal6 core frames','signal6_internal_frame':idx,'signal6_time_s':idx*.0005,'signal6_max_unweighted_n_cell_effect':float(abs(lo[0][idx]-hi[0][idx])),'names':names,'vectors':shared.T.tolist(),'common_core_npy_sha256':hashlib.sha256((TMP/'common-core.npy').read_bytes()).hexdigest(),'analytic_local_segment':{'N0':.35,'delta_z':.2,'specific_022':.35-.22*.2,'specific_024':.35-.24*.2,'specific_difference':.004,'segment_area_difference':.0004,'meaning':'local 0.2 Bark segment only, not full N'}}
sys.path.insert(0,str(TMP/'mos024'))
for engine in ['c','mos']:
 for v in ['022','024']:
  if engine=='c':n,ns=slopes(shared.copy(),v)
  else:
   p=TMP/f'mos{v}/mosqito/sq_metrics/loudness/loudness_zwst/_calc_slopes.py'
   spec=importlib.util.spec_from_file_location('native_slope_'+v,p);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
   n,ns=mod._calc_slopes(shared.copy())
  np.savez(TMP/f'{engine}{v}-common.npz',n=n,ns=ns)
(OUT/'common-core.json').write_text(json.dumps(meta,indent=2),encoding='utf8')
print(json.dumps({k:v for k,v in meta.items() if k!='vectors'},indent=2))
