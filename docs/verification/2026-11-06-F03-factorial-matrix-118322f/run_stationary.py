"""New native filter levels and original/native diagnostic downstream matrix."""
from pathlib import Path
import sys,ctypes as C,json,hashlib,importlib.util
import numpy as np
from scipy.io import savemat
R=Path.cwd();O=Path(__file__).resolve().parent;T=R/'tmp/verification-f03-factorial-matrix';P0=R/'tmp/verification-f03-three-implementations'
sys.path.insert(0,str(T/'mos024-round'))
from mosqito.sound_level_meter.noct_spectrum._center_freq import _center_freq
from mosqito.sound_level_meter.noct_spectrum._filter_bandwidth import _filter_bandwidth
from mosqito.sound_level_meter import noct_spectrum
from mosqito.utils import amp2db
from mosqito.sq_metrics.loudness.loudness_zwst._main_loudness import _main_loudness
orig=T/'mos024-round/mosqito/sound_level_meter/noct_spectrum/_n_oct_time_filter.py';raw=orig.read_text();needle='    level = sqrt(mean(sig_filt ** 2, axis=0))';assert raw.count(needle)==1
adapted=raw.replace(needle,'    from numpy import ceil\n    sig_filt = sig_filt[int(ceil(AUDIT_SKIP_S * fs)):]\n'+needle)
(T/'noct_postskip.py').write_text(adapted);scope={'AUDIT_SKIP_S':0,'__name__':'audit_frontend'};exec(compile(adapted,str(T/'noct_postskip.py'),'exec'),scope)
fc,_=_center_freq(fmin=24,fmax=12600,n=3,G=10,fr=1000);alpha,_,_=_filter_bandwidth(fc,n=3)
def noct(x,skip):
 scope['AUDIT_SKIP_S']=skip
 return amp2db(np.squeeze(np.array([scope['_n_oct_time_filter'](x[:,None],48000,f,a) for f,a in zip(fc,alpha)])),ref=2e-5)
P=C.POINTER(C.c_double);PP=C.POINTER(P)
class Input(C.Structure):_fields_=[('NumSamples',C.c_int),('SampleRate',C.c_double),('pData',P)]
def ptrs(a):return (P*len(a))(*(r.ctypes.data_as(P) for r in a))
front=C.CDLL(str(R/'tmp/verification-f03-filter-independent/c022/reference.dll'));front.f_calc_third_octave_levels.argtypes=[C.POINTER(Input),PP,C.c_int,C.c_int,C.c_double]
def annex(x,skip):
 out=np.zeros((28,1));inp=Input(len(x),48000,x.ctypes.data_as(P));rc=front.f_calc_third_octave_levels(C.byref(inp),ptrs(out),len(x),0,skip);assert rc==0;return out[:,0]
libs={};slopes={}
for u in ['022','024']:
 lib=C.CDLL(str(P0/f'c{u}/reference.dll'));lib.f_loudness_from_levels.argtypes=[PP,C.c_int,C.c_int,C.c_int,P,PP];libs[u]=lib
 for mode in ['round','noround']:
  path=T/f'mos{u}-{mode}/mosqito/sq_metrics/loudness/loudness_zwst/_calc_slopes.py';sp=importlib.util.spec_from_file_location(f'slope{u}{mode}',path);mod=importlib.util.module_from_spec(sp);sp.loader.exec_module(mod);slopes[u,mode]=mod._calc_slopes
def backend(l,u,b):
 if b=='c':
  l=l.reshape(28,1).copy(order='C');n=np.zeros(1);ns=np.zeros((240,1));rc=libs[u].f_loudness_from_levels(ptrs(l),1,0,0,n.ctypes.data_as(P),ptrs(ns));assert rc==1;return n[0],ns[:,0]
 return slopes[u,b.split('-')[1]](_main_loudness(l.copy(),'free'))
design=json.loads((O/'design-matrix.json').read_text());levelmap={};levelmeta=[];parity=[];results=[];arrays={};repeats=[]
for cell in design:
 if cell['domain'] not in ['stationary','crop-control']:continue
 s,F,G,W=cell['signal'],cell['frontend'],cell['calibration'],cell['skip_s'];crop=cell.get('crop_samples',0);key=f's{s}-{F}-{G}-w{W}-crop{crop}'
 if key not in levelmap:
  x=np.load(T/f'inputs/sig{s}-{G}.npy')[crop:].copy();l=annex(x,W) if F=='annex' else noct(x,W)
  levelmap[key]=l;levelmeta.append({'key':key,'signal':s,'frontend':F,'calibration':G,'skip_s':W,'crop_samples':crop,'levels':l.tolist(),'levels_f64_sha256':hashlib.sha256(l.astype('<f8').tobytes()).hexdigest()})
  if F=='noct' and W==0 and crop==0:
   native=amp2db(noct_spectrum(x,48000,24,12600)[0],ref=2e-5);assert np.array_equal(native,l)
   parity.append({'signal':s,'calibration':G,'all_28_levels_bitwise_equal_native_api':True})
 if cell['backend']=='sqat':continue
 before=levelmap[key].tobytes();n,ns=backend(levelmap[key],cell['usl'],cell['backend']);assert levelmap[key].tobytes()==before;arrays[cell['id']]=np.r_[n,ns]
 results.append({'id':cell['id'],'level_key':key,'n':float(n)})
 if s==2 and F=='annex' and G=='sqrt' and W==0 and crop==0 and cell['usl']=='022':
  n2,ns2=backend(levelmap[key],cell['usl'],cell['backend']);assert levelmap[key].tobytes()==before;assert n==n2 and np.array_equal(ns,ns2);repeats.append({'backend':cell['backend'],'exact_repeat':True})
np.savez_compressed(T/'stationary-python.npz',**arrays)
primary=[m for m in levelmeta if m['crop_samples']==0];savemat(T/'stationary-levels.mat',{'levels':np.array([m['levels'] for m in primary]).T})
(T/'stationary-level-index.json').write_text(json.dumps([m['key'] for m in primary]))
(O/'shared-levels.json').write_text(json.dumps(levelmeta,indent=2));(O/'stationary-run-index.json').write_text(json.dumps(results,indent=2))
(O/'frontend-controls.json').write_text(json.dumps({'mo_skip0_parity':parity,'repeats':repeats,'original_frontend_sha256':hashlib.sha256(orig.read_bytes()).hexdigest(),'mechanical_postskip_sha256':hashlib.sha256((T/'noct_postskip.py').read_bytes()).hexdigest(),'only_adaptation':'Slice sig_filt at ceil(skip_s * fs_after_decimation) immediately before original RMS statement'},indent=2))
print('Stationary new C/Mo matrix and crop controls done; SQAT32 levels ×2 variants ready',flush=True)
