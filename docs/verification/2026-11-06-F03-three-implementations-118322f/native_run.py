"""Native official C or MoSQITo worker. Public algorithms unchanged except variant cell."""
from pathlib import Path
import sys,ctypes as C,time,json,hashlib
import numpy as np
ROOT=Path.cwd(); OUT=Path(__file__).resolve().parent; TMP=ROOT/'tmp/verification-f03-three-implementations'
engine,variant=sys.argv[1:3];dest=TMP/f'{engine}{variant}-outputs';dest.mkdir(exist_ok=True)
P=C.POINTER(C.c_double); PP=C.POINTER(P)
class Input(C.Structure):_fields_=[('NumSamples',C.c_int),('SampleRate',C.c_double),('pData',P)]
def ptrs(a):return (P*len(a))(*(row.ctypes.data_as(P) for row in a))
if engine=='c':
    lib=C.CDLL(str(TMP/f'c{variant}/reference.dll'))
    lib.f_loudness_from_signal.argtypes=[C.POINTER(Input),C.c_int,C.c_int,C.c_double,P,PP,C.c_int]
    lib.f_loudness_from_levels.argtypes=[PP,C.c_int,C.c_int,C.c_int,P,PP]
else:
    sys.path.insert(0,str(TMP/f'mos{variant}'))
    from mosqito.sq_metrics import loudness_zwst,loudness_zwtv
    from mosqito.sq_metrics.loudness.loudness_zwst._main_loudness import _main_loudness
    from mosqito.sq_metrics.loudness.loudness_zwst._calc_slopes import _calc_slopes
for s in range(1,26):
    t0=time.perf_counter();x=np.load(TMP/'inputs'/f'sig{s}.npy');field=int(s==15)
    if engine=='c':
        k=len(x)//24 if s>=6 else 1;n=np.zeros(k);ns=np.zeros((240,k))
        if s==1:
            lv=x.reshape(28,1).copy();rc=lib.f_loudness_from_levels(ptrs(lv),1,0,0,n.ctypes.data_as(P),ptrs(ns))
        else:
            inp=Input(len(x),48000,x.ctypes.data_as(P));rc=lib.f_loudness_from_signal(C.byref(inp),field,int(s>=6),.2 if s<=5 else 0.,n.ctypes.data_as(P),ptrs(ns),k)
        assert rc==k,(s,rc,k)
        if s>=6:n=n[::4];ns=ns[:,::4]
        times=np.arange(len(n))*.002
    else:
        if s==1:n,ns=_calc_slopes(_main_loudness(x,'free'));times=np.array([0.])
        elif s<=5:n,ns,b=loudness_zwst(x,48000);times=np.array([0.])
        else:n,ns,b,times=loudness_zwtv(x,48000,'diffuse' if field else 'free')
        n=np.atleast_1d(n);ns=np.asarray(ns).reshape(240,-1)
    np.savez_compressed(dest/f'sig{s}.npz',n=n,ns=ns,t=times)
    print(json.dumps({'engine':engine,'variant':variant,'signal':s,'input_length':len(x),'output_frames':len(n),'seconds':time.perf_counter()-t0,'n_max':float(np.max(n))}),flush=True)
print('DONE',engine,variant,flush=True)
