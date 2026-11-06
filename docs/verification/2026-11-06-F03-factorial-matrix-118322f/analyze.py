"""Paired deterministic effects; never subtract unmatched maxima as causal effects."""
from pathlib import Path
import json,hashlib,itertools,math
import numpy as np
from scipy.io import loadmat
R=Path.cwd();O=Path(__file__).resolve().parent;T=R/'tmp/verification-f03-factorial-matrix';P=R/'tmp/verification-f03-three-implementations'
design=json.loads((O/'design-matrix.json').read_text());refs=json.loads((T/'refs.json').read_text());frozen=json.loads((O/'frozen-inputs.json').read_text());cachehash={}
def write(n,x):(O/n).write_text(json.dumps(x,indent=2,allow_nan=False),encoding='utf8')
def loadpath(p,verify=None):
 if verify:
  h=hashlib.sha256(p.read_bytes()).hexdigest();assert h==verify
  cachehash[str(p.relative_to(R))]=h
 d=loadmat(p) if p.suffix=='.mat' else np.load(p)
 n=np.asarray(d['n']).ravel();ns=np.asarray(d['ns']).reshape(240,-1);t=np.asarray(d['t']).ravel();assert ns.shape[1]==len(n)==len(t) and np.isfinite(n).all() and np.isfinite(ns).all()
 physical=np.arange(len(n))*.002
 is_mos=p.parent.name.startswith('mos') or 'mos-' in p.name
 if not is_mos:assert np.max(abs(t-physical))<1e-8,(str(p),'returned time grid')
 return {'n':n,'ns':ns,'t':physical,'reported_t':t}
def old(engine,u,s):
 rel=f'{engine}{u}-outputs/sig{s}.{"mat" if engine=="sqat" else "npz"}'
 return loadpath(P/rel,frozen['prior_raw_outputs'][rel])
def tv(cell):
 if cell['execution']=='reuse':return loadpath(P/cell['reuse_path'],cell['reuse_sha256'])
 p=T/'tv-outputs'/f'{cell["id"]}.{"mat" if cell["backend"]=="sqat" else "npz"}'
 return loadpath(p)
def metric(a,r):
 a=np.asarray(a);r=np.asarray(r);assert a.shape==r.shape
 d=a-r;ad=abs(d);idx=int(ad.argmax());valid=abs(r)>=1e-4;rel=np.zeros(r.shape);rel[valid]=100*ad[valid]/abs(r[valid]);loc=list(map(int,np.unravel_index(idx,a.shape)))
 return {'points':int(a.size),'max_abs':float(ad.flat[idx]),'rms':float(np.sqrt(np.mean(d*d))),'mean_signed':float(np.mean(d)),'max_index':loc,'reference_at_max':float(r.flat[idx]),'test_at_max':float(a.flat[idx]),'signed_at_max':float(d.flat[idx]),'relative_max_percent_ref_ge_1e4':float(rel.max()) if valid.any() else None,'relative_excluded':int((~valid).sum())}
def tvlocation(m,specific=False,bark=None):
 ix=m['max_index'];m['max_time_s']=ix[-1]*.002
 if specific:m['max_bark']=(ix[0]+1)/10 if len(ix)>1 else bark
 return m
def effect(y):
 y=np.asarray(y);ns=y[1:];i=int(abs(ns).argmax())
 return {'N_signed':float(y[0]),'Nprime_max_abs':float(abs(ns[i])),'Nprime_signed_at_max':float(ns[i]),'Nprime_max_bark':(i+1)/10,'Nprime_rms':float(np.sqrt(np.mean(ns*ns)))}
raw=dict(np.load(T/'stationary-python.npz'));keys=json.loads((T/'stationary-level-index.json').read_text())
sq={u:loadmat(T/f'stationary-sqat{u}.mat') for u in ['022','024']}
for c in design:
 if c['domain']=='stationary' and c['backend']=='sqat':
  key=f's{c["signal"]}-{c["frontend"]}-{c["calibration"]}-w{c["skip_s"]}-crop0';i=keys.index(key);raw[c['id']]=np.r_[sq[c['usl']]['n'].ravel()[i],sq[c['usl']]['ns'][:,i]]
assert len(raw)==264
np.savez_compressed(T/'stationary-all.npz',**raw)
stationary=[];ranking=[]
for c in design:
 if c['domain'] not in ['stationary','crop-control']:continue
 s=c['signal'];y=raw[c['id']];cref=raw[f'A-s{s}-annex-sqrt-w0.2-022-c'];wref=np.r_[refs[str(s)]['n'][0],np.array(refs[str(s)]['specific']).ravel()]
 row={**c,'N':float(y[0]),'official_c':{'N':metric(y[:1],cref[:1]),'Nprime':metric(y[1:],cref[1:])},'workbook':{'N':metric(y[:1],wref[:1]),'Nprime':metric(y[1:],wref[1:])}};stationary.append(row)
for s,b in itertools.product(range(2,6),['c','sqat','mos-round','mos-noround']):
 group=[x for x in stationary if x['domain']=='stationary' and x['signal']==s and x['backend']==b]
 for ref,outcome in itertools.product(['official_c','workbook'],['N','Nprime']):
  a=sorted(group,key=lambda x:x[ref][outcome]['max_abs']);ranking.append({'signal':s,'backend':b,'reference':ref,'criterion':outcome+'_max_abs','best':{'id':a[0]['id'],'error':a[0][ref][outcome]['max_abs']},'worst':{'id':a[-1]['id'],'error':a[-1][ref][outcome]['max_abs']}})
contrasts=[];walsh=[];recon=[]
factor_names=['frontend_annex_minus_noct','calibration_cal_minus_sqrt','skip_0p2_minus_0','usl_024_minus_022']
def decompose(cells,names,label):
 X=[];Y=[]
 for c in cells:
  x=[1 if c['frontend']=='annex' else -1,1 if c['calibration']=='cal' else -1,1 if c['skip_s']==.2 else -1,1 if c['usl']=='024' else -1]
  if len(names)==5:x.append(1 if c['backend']=='mos-round' else -1)
  X.append(x);Y.append(raw[c['id']])
 X=np.array(X);Y=np.array(Y);assert len(X)==2**len(names);prediction=np.zeros_like(Y)
 for order in range(len(names)+1):
  for inds in itertools.combinations(range(len(names)),order):
   sign=np.prod(X[:,inds],axis=1) if inds else np.ones(len(X));coef=np.mean(Y*sign[:,None],axis=0);prediction+=sign[:,None]*coef
   item={**label,'order':order,'factors':[names[i] for i in inds],'walsh_coefficient':effect(coef),'paired_contrast':effect(coef*2**order)};walsh.append(item)
   if order in [1,2]:contrasts.append(item)
 err=float(abs(prediction-Y).max());assert err<=1e-12;recon.append({**label,'terms':2**len(names),'max_reconstruction_error':err})
for s,b in itertools.product(range(2,6),['c','sqat','mos-round','mos-noround']):decompose([c for c in design if c['domain']=='stationary' and c['signal']==s and c['backend']==b],factor_names,{'signal':s,'backend':b})
for s in range(2,6):decompose([c for c in design if c['domain']=='stationary' and c['signal']==s and c['backend'].startswith('mos')],factor_names+['rounding_on_minus_off'],{'signal':s,'backend':'mos-five-factor'})
crop=[]
for c in design:
 if c['domain']=='crop-control':
  r=raw[f'A-s{c["signal"]}-{c["frontend"]}-sqrt-w0.2-022-c'];crop.append({'signal':c['signal'],'frontend':c['frontend'],'crop_reset_minus_postfilter_skip':effect(raw[c['id']]-r)})
stationary_round=[]
for c in design:
 if c['domain']=='stationary' and c['backend']=='mos-round':
  a=raw[c['id']];b=raw[c['id'].replace('-mos-round','-mos-noround')];assert np.array_equal(a[1:],b[1:]);stationary_round.append({'id':c['id'],'N_rounding_effect':float(a[0]-b[0]),'Nprime_bitwise_identical':True})
write('stationary-cell-results.json',stationary);write('stationary-rankings.json',ranking);write('paired-effects.json',contrasts);write('full-walsh-decomposition.json',walsh);write('reconstruction-controls.json',recon);write('crop-controls.json',crop);write('stationary-rounding-controls.json',stationary_round)
uslchecks=[]
for c in design:
 if c['domain']=='stationary' and c['usl']=='022':
  eq=np.array_equal(raw[c['id']],raw[c['id'].replace('-022-','-024-')]);assert eq;uslchecks.append({'id022':c['id'],'N_and_Nprime_bitwise_unchanged':eq})
write('stationary-usl-controls.json',uslchecks)
print('Stationary analysis complete',flush=True)
# Complete prior all-20 time-varying reanalysis at identical coordinates.
cancel=[];specific=[]
for s,engine in itertools.product(range(6,26),['c','sqat','mos']):
 lo=old(engine,'022',s);hi=old(engine,'024',s);r=np.asarray(refs[str(s)]['n']);k=len(r);assert len(lo['n'])>=k and len(hi['n'])>=k
 assert np.max(abs(np.asarray(refs[str(s)]['time'])-np.arange(k)*.002))<1e-8
 e0=lo['n'][:k]-r;d=hi['n'][:k]-lo['n'][:k];e1=hi['n'][:k]-r;res=float(abs(e0+d-e1).max());assert res<=1e-12
 deltaabs=abs(e1)-abs(e0);i0=int(abs(e0).argmax());i1=int(abs(e1).argmax());idx=4803 if s==15 else i1
 def point(i):return {'frame':i,'time_s':i*.002,'reference':float(r[i]),'N022':float(lo['n'][i]),'N024':float(hi['n'][i]),'e022':float(e0[i]),'delta_024_minus_022':float(d[i]),'e024':float(e1[i]),'absolute_error_change_024_minus_022':float(deltaabs[i])}
 cancel.append({'signal':s,'engine':engine,'points':k,'unchanged':int((abs(deltaabs)<=1e-12).sum()),'024_improves':int((deltaabs < -1e-12).sum()),'024_worsens':int((deltaabs > 1e-12).sum()),'opposing_sign_effect':int(((e0*d)<0).sum()),'reinforcing_sign_effect':int(((e0*d)>0).sum()),'opposes_but_overshoots':int(((e0*d<0)&(deltaabs>1e-12)).sum()),'max022':point(i0),'max024':point(i1),'fixed_audit_point':point(idx),'decomposition_max_residual':res})
 cr=lo if engine=='c' else old('c','022',s);ks=min(lo['ns'].shape[1],hi['ns'].shape[1],cr['ns'].shape[1])
 groups=[('C022_full_grid',lo['ns'][:,:ks],hi['ns'][:,:ks],cr['ns'][:,:ks],None)]
 if 'specific' in refs[str(s)]:
  bark=refs[str(s)]['bark'];bi=round(bark*10)-1;groups.append(('workbook_available',lo['ns'][bi,:k],hi['ns'][bi,:k],np.asarray(refs[str(s)]['specific']).ravel(),bark))
 for reference,a,b,rns,bark in groups:
  e=a-rns;dd=b-a;ee=b-rns;da=abs(ee)-abs(e);res=float(abs(e+dd-ee).max());assert res<=1e-12
  specific.append({'signal':s,'engine':engine,'reference':reference,'points':int(a.size),'024_improves':int((da < -1e-12).sum()),'024_worsens':int((da > 1e-12).sum()),'unchanged':int((abs(da)<=1e-12).sum()),'opposing_sign_effect':int((e*dd<0).sum()),'opposes_but_overshoots':int(((e*dd<0)&(da>1e-12)).sum()),'error022':tvlocation(metric(a,rns),True,bark),'error024':tvlocation(metric(b,rns),True,bark),'cell_effect':tvlocation(metric(b,a),True,bark),'decomposition_max_residual':res})
write('all-tv-cancellation.json',cancel)
write('all-tv-specific-cancellation.json',specific)
# B matrix can be analyzed only when every new output is present.
tvdesign=[c for c in design if c['domain']=='timevarying']
missing=[c['id'] for c in tvdesign if c['execution']=='new' and not (T/'tv-outputs'/f'{c["id"]}.{"mat" if c["backend"]=="sqat" else "npz"}').exists()]
if missing:write('pending-tv.json',missing);print('TV pending',missing,flush=True);raise SystemExit(0)
results=[];tvcontrasts=[];roundchecks=[];lengths=[];tvzero=[]
for s in [6,15,16,25]:
 cr=old('c','022',s);wr=np.asarray(refs[str(s)]['n']);cells=[c for c in tvdesign if c['signal']==s];outs={c['id']:tv(c) for c in cells}
 for c in cells:
  y=outs[c['id']];k=min(len(y['n']),len(cr['n']));kw=len(wr);entry={**c,'official_c':{'N':metric(y['n'][:k],cr['n'][:k]),'Nprime':metric(y['ns'][:,:k],cr['ns'][:,:k])},'workbook':{'N':metric(y['n'][:kw],wr)}}
  for group in entry['official_c'],entry['workbook']:
   for outcome,m in group.items():tvlocation(m,outcome=='Nprime')
  if 'specific' in refs[str(s)]:
   row=round(refs[str(s)]['bark']*10)-1;entry['workbook']['Nprime']=tvlocation(metric(y['ns'][row,:kw],np.array(refs[str(s)]['specific']).ravel()),True,refs[str(s)]['bark'])
  if s==15:
   j=4803;entry['fixed_9p606s']={'N':float(y['n'][j]),'workbook_error':float(y['n'][j]-wr[j]),'C022_error':float(y['n'][j]-cr['n'][j])}
  results.append(entry);lengths.append({'id':c['id'],'frames':len(y['n']),'vs_C_common':k,'workbook_frames':kw,'reported_label_max_drift_s':float(abs(y['reported_t']-y['t']).max())})
 for b in ['c','sqat','mos-round','mos-noround']:
  y={(g,u):outs[f'B-s{s}-{g}-{u}-{b}'] for g,u in itertools.product(['sqrt','cal'],['022','024'])};k=min(len(v['n']) for v in y.values())
  for target in ['n','ns']:
   z={q:v[target][...,:k] for q,v in y.items()};F=((z['cal','022']-z['sqrt','022'])+(z['cal','024']-z['sqrt','024']))/2;U=((z['sqrt','024']-z['sqrt','022'])+(z['cal','024']-z['cal','022']))/2;I=(z['cal','024']-z['cal','022'])-(z['sqrt','024']-z['sqrt','022'])
   for name,a in [('calibration',F),('USL',U),('calibration_x_USL',I)]:tvcontrasts.append({'signal':s,'backend':b,'outcome':target,'contrast':name,**tvlocation(metric(a,np.zeros(a.shape)),target=='ns')})
  if s==25:
   for g in ['sqrt','cal']:
    eq=all(np.array_equal(y[g,'022'][v],y[g,'024'][v]) for v in ['n','ns']);assert eq;tvzero.append({'signal':s,'backend':b,'calibration':g,'N_and_Nprime_bitwise_USL_unchanged':eq})
 for g,u in itertools.product(['sqrt','cal'],['022','024']):
  a=outs[f'B-s{s}-{g}-{u}-mos-round'];b=outs[f'B-s{s}-{g}-{u}-mos-noround'];assert np.array_equal(a['ns'],b['ns']);roundchecks.append({'signal':s,'calibration':g,'usl':u,'Nprime_bitwise_identical':True,'N_rounding_effect':metric(a['n'],b['n'])})
write('tv-cell-results.json',results);write('tv-paired-effects.json',tvcontrasts);write('tv-rounding-controls.json',roundchecks);write('tv-length-alignment.json',lengths)
write('tv-zero-controls.json',tvzero)
tvranks=[]
for s,b,ref,outcome in itertools.product([6,15,16,25],['c','sqat','mos-round','mos-noround'],['official_c','workbook'],['N','Nprime']):
 group=[x for x in results if x['signal']==s and x['backend']==b and outcome in x[ref]]
 if not group:continue
 a=sorted(group,key=lambda x:x[ref][outcome]['max_abs']);tvranks.append({'signal':s,'backend':b,'reference':ref,'criterion':outcome+'_max_abs','best':{'id':a[0]['id'],'error':a[0][ref][outcome]['max_abs']},'worst':{'id':a[-1]['id'],'error':a[-1][ref][outcome]['max_abs']}})
write('tv-rankings.json',tvranks)
write('verified-reused-output-hashes.json',cachehash)
write('new-output-hashes.json',{p.relative_to(T).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in list((T/'tv-outputs').glob('*'))+list(T.glob('stationary-*.npz'))+list(T.glob('stationary-sqat*.mat'))})
if (O/'pending-tv.json').exists():(O/'pending-tv.json').unlink()
print('Full matrix analysis complete',flush=True)
