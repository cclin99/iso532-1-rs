"""Execute new TV cells only; immutable prior outputs are referenced in the design."""
from pathlib import Path
import json,sys,time,ctypes as C
import numpy as np
R=Path.cwd();O=Path(__file__).resolve().parent;T=R/'tmp/verification-f03-factorial-matrix';P0=R/'tmp/verification-f03-three-implementations'
B,U=sys.argv[1:3];(T/'tv-outputs').mkdir(exist_ok=True)
P=C.POINTER(C.c_double);PP=C.POINTER(P)
class Input(C.Structure):_fields_=[('NumSamples',C.c_int),('SampleRate',C.c_double),('pData',P)]
def ptrs(a):return (P*len(a))(*(r.ctypes.data_as(P) for r in a))
if B=='c':
 lib=C.CDLL(str(P0/f'c{U}/reference.dll'));lib.f_loudness_from_signal.argtypes=[C.POINTER(Input),C.c_int,C.c_int,C.c_double,P,PP,C.c_int]
else:
 sys.path.insert(0,str(T/f'mos{U}-{B.split("-")[1]}'))
 from mosqito.sq_metrics import loudness_zwtv
for cell in json.loads((O/'design-matrix.json').read_text()):
 if cell['domain']!='timevarying' or cell['execution']!='new' or cell['backend']!=B or cell['usl']!=U:continue
 tick=time.perf_counter();s=cell['signal'];G=cell['calibration'];x=np.load(T/f'inputs/sig{s}-{G}.npy')
 if B=='c':
  k=len(x)//24;n=np.zeros(k);ns=np.zeros((240,k));inp=Input(len(x),48000,x.ctypes.data_as(P));rc=lib.f_loudness_from_signal(C.byref(inp),int(s==15),1,0,n.ctypes.data_as(P),ptrs(ns),k);assert rc==k;n=n[::4];ns=ns[:,::4];t=np.arange(len(n))*.002
 else:n,ns,_,t=loudness_zwtv(x,48000,'diffuse' if s==15 else 'free')
 np.savez_compressed(T/'tv-outputs'/f'{cell["id"]}.npz',n=n,ns=ns,t=t)
 print(json.dumps({'id':cell['id'],'frames':len(n),'seconds':time.perf_counter()-tick}),flush=True)
print('DONE',B,U,flush=True)
