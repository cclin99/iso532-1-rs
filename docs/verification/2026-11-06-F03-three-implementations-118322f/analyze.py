"""Compare independently executed native outputs. No recalibration or alignment fitting."""
from pathlib import Path
import json,hashlib,sys,datetime
import numpy as np
from scipy.io import loadmat
ROOT=Path.cwd();OUT=Path(__file__).resolve().parent;TMP=ROOT/'tmp/verification-f03-three-implementations'
def write(n,o):(OUT/n).write_text(json.dumps(o,indent=2,allow_nan=False),encoding='utf8')
def load(engine,v,s):
 p=TMP/f'{engine}{v}-outputs'/f'sig{s}.{ "mat" if engine=="sqat" else "npz"}'
 if not p.exists():return None
 d=loadmat(p) if engine=='sqat' else np.load(p)
 a={k:np.asarray(d[k]).ravel() if k in ['n','t'] else np.asarray(d[k]).reshape(240,-1) for k in ['n','ns','t']}
 a['reported_t']=a['t'].copy()
 if engine=='mos' and s>=6:a['t']=np.arange(len(a['n']))*.002
 return a
def coordinate(idx,shape,t,s,barks=None):
 row,col=(0,idx) if len(shape)==1 else np.unravel_index(idx,shape)
 o={'signal':s,'frame_zero_based':int(col),'time_s':float(t[col])}
 if barks is not None:o['bark']=float(barks[row])
 return o
def metrics(test,ref,t,s,barks=None):
 assert test.shape==ref.shape,(s,test.shape,ref.shape)
 assert np.isfinite(test).all() and np.isfinite(ref).all()
 diff=test-ref;ab=np.abs(diff);idx=int(np.argmax(ab));m=np.abs(ref)>=1e-4
 rel=np.zeros(ref.shape);rel[m]=100*ab[m]/np.abs(ref[m]);ri=int(np.argmax(rel))
 big=np.abs(ref)>=1;rb=100*ab[big]/np.abs(ref[big])
 return {'points':int(ref.size),'max_abs':float(ab.flat[idx]),'rms':float(np.sqrt(np.mean(diff*diff))),
  'signed_delta_at_max':float(diff.flat[idx]),'reference_at_max':float(ref.flat[idx]),'test_at_max':float(test.flat[idx]),'max_abs_at':coordinate(idx,ref.shape,t,s,barks),
  'above_1e12':int((ab>1e-12).sum()),'above_1e4':int((ab>1e-4+1e-12).sum()),
  'max_relative_percent_ref_ge_1e4':float(rel.max()),'relative_excluded_ref_lt_1e4':int((~m).sum()),'max_relative_at':coordinate(ri,ref.shape,t,s,barks),
  'max_relative_percent_ref_ge_1':float(rb.max()) if len(rb) else None,'relative_points_ref_ge_1':int(big.sum())}
def intersect(a,b):
 ia=np.rint(a/.002).astype(int);ib=np.rint(b/.002).astype(int)
 assert np.max(abs(a-ia*.002))<1e-8 and np.max(abs(b-ib*.002))<1e-8
 assert len(np.unique(ia))==len(a) and len(np.unique(ib))==len(b)
 common,ix,iy=np.intersect1d(ia,ib,return_indices=True)
 return common*.002,ix,iy
def aggregate(ms):
 if not ms:return None
 n=sum(m['points'] for m in ms);maxm=max(ms,key=lambda m:m['max_abs']);relm=max(ms,key=lambda m:m['max_relative_percent_ref_ge_1e4'])
 return {'points':n,'max_abs':maxm['max_abs'],'rms':float(np.sqrt(sum(m['rms']**2*m['points'] for m in ms)/n)),
 'max_abs_at':maxm['max_abs_at'],'reference_at_max':maxm['reference_at_max'],'test_at_max':maxm['test_at_max'],'signed_delta_at_max':maxm['signed_delta_at_max'],
 'above_1e12':sum(m['above_1e12'] for m in ms),'above_1e4':sum(m['above_1e4'] for m in ms),
 'max_relative_percent_ref_ge_1e4':relm['max_relative_percent_ref_ge_1e4'],'max_relative_at':relm['max_relative_at'],'relative_excluded_ref_lt_1e4':sum(m['relative_excluded_ref_lt_1e4'] for m in ms),
 'max_relative_percent_ref_ge_1':max((m['max_relative_percent_ref_ge_1'] for m in ms if m['max_relative_percent_ref_ge_1'] is not None),default=None),'relative_points_ref_ge_1':sum(m['relative_points_ref_ge_1'] for m in ms)}
refs=json.loads((TMP/'refs.json').read_text());results={};coverage={};lengths=[]
for engine,base in [('c','022'),('mos','024'),('sqat','024')]:
 results[engine]={'workbook':{},'official_c':{},'cell_024_minus_022':{},'counterfactual_workbook':{},'counterfactual_official_c':{}};coverage[engine]=[]
 for s in range(1,26):
  a=load(engine,base,s)
  if a is None:continue
  coverage[engine].append(s);r=refs[str(s)];refn=np.asarray(r['n']);rt=np.asarray(r['time'])
  t,ai,ri=intersect(a['t'],rt);assert len(t)==len(rt),(engine,s,'missing workbook timestamps')
  lengths.append({'engine':engine,'signal':s,'output_frames':len(a['t']),'workbook_frames':len(rt),'matched_frames':len(t),'extra_output_frames':len(a['t'])-len(t),'input_samples':int(len(np.load(TMP/f'inputs/sig{s}.npy'))),'last_output_time_s':float(a['t'][-1]),'last_reported_time_s':float(a['reported_t'][-1]),'reported_time_max_drift_s':float(np.max(abs(a['reported_t']-a['t']))),'last_workbook_time_s':float(rt[-1])})
  z={'N':metrics(a['n'][ai],refn[ri],t,s)}
  if 'specific' in r:
   rows=np.arange(240) if s<=5 else np.array([round(r['bark']*10)-1]);b=(rows+1)/10
   z['Nprime']=metrics(a['ns'][rows][:,ai],np.asarray(r['specific'])[:,ri],t,s,b)
  results[engine]['workbook'][str(s)]=z
  c=load('c','022',s);t,ai,ci=intersect(a['t'],c['t'])
  results[engine]['official_c'][str(s)]={'N':metrics(a['n'][ai],c['n'][ci],t,s),'Nprime':metrics(a['ns'][:,ai],c['ns'][:,ci],t,s,np.arange(1,241)/10)}
  lo=load(engine,'022',s);hi=load(engine,'024',s)
  if lo is not None and hi is not None:
   assert np.array_equal(lo['t'],hi['t'])
   results[engine]['cell_024_minus_022'][str(s)]={'N':metrics(hi['n'],lo['n'],lo['t'],s),'Nprime':metrics(hi['ns'],lo['ns'],lo['t'],s,np.arange(1,241)/10)}
   alt=hi if base=='022' else lo
   t,ai,ri=intersect(alt['t'],rt)
   z={'N':metrics(alt['n'][ai],refn[ri],t,s)}
   if 'specific' in r:
    rows=np.arange(240) if s<=5 else np.array([round(r['bark']*10)-1]);b=(rows+1)/10
    z['Nprime']=metrics(alt['ns'][rows][:,ai],np.asarray(r['specific'])[:,ri],t,s,b)
   results[engine]['counterfactual_workbook'][str(s)]=z
   t,ai,ci=intersect(alt['t'],c['t'])
   results[engine]['counterfactual_official_c'][str(s)]={'N':metrics(alt['n'][ai],c['n'][ci],t,s),'Nprime':metrics(alt['ns'][:,ai],c['ns'][:,ci],t,s,np.arange(1,241)/10)}
summary={}
for engine,groups in results.items():
 summary[engine]={}
 for group,signals in groups.items():
  summary[engine][group]={'signals':sorted(map(int,signals)),'N':aggregate([x['N'] for x in signals.values()]),'Nprime':aggregate([x['Nprime'] for x in signals.values() if 'Nprime' in x])}
write('per-signal-metrics.json',results);write('summary.json',summary);write('length-alignment.json',lengths);write('coverage.json',coverage)
strata={}
for engine,groups in results.items():
 strata[engine]={}
 for category,selected in [('levels_1',[1]),('stationary_2_5',range(2,6)),('timevarying_6_25',range(6,26))]:
  strata[engine][category]={}
  for group,signals in groups.items():
   ss={k:v for k,v in signals.items() if int(k) in selected}
   strata[engine][category][group]={'signals':sorted(map(int,ss)),'N':aggregate([x['N'] for x in ss.values()]),'Nprime':aggregate([x['Nprime'] for x in ss.values() if 'Nprime' in x])}
write('stratified-summary.json',strata)
stage={};names=json.loads((OUT/'common-core.json').read_text())['names']
for engine in ['c','mos','sqat']:
 if engine=='sqat':
  p=TMP/'sqat-common-slope.mat'
  if not p.exists():continue
  d=loadmat(p);v={k:{'n':d['n'+k].ravel(),'ns':d['ns'+k].T} for k in ['022','024']}
 else:v={k:dict(np.load(TMP/f'{engine}{k}-common.npz')) for k in ['022','024']}
 stage[engine]={}
 for j,name in enumerate(names):
  delta=v['024']['ns'][:,j]-v['022']['ns'][:,j];ix=int(np.argmax(abs(delta)))
  stage[engine][name]={'N022':float(v['022']['n'][j]),'N024':float(v['024']['n'][j]),'N_delta':float(v['024']['n'][j]-v['022']['n'][j]),'Nprime_max_abs_delta':float(abs(delta[ix])),'Nprime_max_abs_bark':(ix+1)/10,'specific_4p6_022':float(v['022']['ns'][45,j]),'specific_4p6_024':float(v['024']['ns'][45,j])}
write('common-stage-metrics.json',stage)
hashes={p.relative_to(TMP).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in TMP.glob('*-outputs/*') if p.suffix in ['.npz','.mat']}
write('raw-output-hashes.json',hashes)
print(json.dumps({'coverage':coverage,'summary':summary,'common_stage':stage},indent=2))
