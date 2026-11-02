import json,sys,hashlib,pathlib
import numpy as np
import iso532
out=[]
def check(case,passed,**kw):out.append(dict(case=case,pass_=bool(passed),**kw))
for fn in (iso532.loudness_zwst,iso532.loudness_zwtv):
 for name,v in [('nan',np.nan),('pinf',np.inf),('ninf',-np.inf)]:
  for idx in (0,2400,4799):
   x=np.zeros(4800);x[idx]=v
   try:fn(x,48000.);check(f'{fn.__name__}/{name}/{idx}',False,message='accepted')
   except Exception as e:check(f'{fn.__name__}/{name}/{idx}',isinstance(e,ValueError) and f'index {idx}' in str(e),message=str(e))
 x=np.zeros(4800);x[73]=np.nan;x[2500]=np.inf
 try:fn(x,48000.);check(f'{fn.__name__}/first_index',False)
 except Exception as e:check(f'{fn.__name__}/first_index',isinstance(e,ValueError) and 'index 73' in str(e),message=str(e))
 for fs,l,expected in [(44100.,4800,'48000'),(48000.,4799,'too short')]:
  try:fn(x[:l],fs);check(f'{fn.__name__}/precedence/{fs}/{l}',False)
  except Exception as e:check(f'{fn.__name__}/precedence/{fs}/{l}',isinstance(e,ValueError) and expected in str(e) and 'non-finite' not in str(e),message=str(e))
 for name,v in [('subnormal',np.nextafter(0.,1.)),('positive_zero',0.),('negative_zero',-0.),('huge',1e300)]:
  try:fn(np.full(4800,v),48000.);check(f'{fn.__name__}/finite/{name}',True,message='success')
  except Exception as e:check(f'{fn.__name__}/finite/{name}','non-finite' not in str(e),message=str(e))
for l in [4800,4801,4823,4824,4825,4895,4896,4897,24013,47905,47916,47927,47928,47952,47999,48000]:
 x=np.ascontiguousarray(.02*np.sin(np.arange(l)*.13));n,s,b,t=iso532.loudness_zwtv(x,48000.);f=((l+23)//24+3)//4;want=np.array([96*j/48000 for j in range(f)]);diff=np.flatnonzero(t.view('u8')!=want.view('u8'))
 check(f'grid/{l}',n.shape==(f,) and s.shape==(240,f) and t.shape==(f,) and len(diff)==0,shapes=[list(n.shape),list(s.shape),list(t.shape)],first_mismatch=None if not len(diff) else int(diff[0]),time_last_hex=f'{int(t.view("u8")[-1]):016x}')
result=dict(module=iso532.__file__,module_sha256=hashlib.sha256(pathlib.Path(iso532.__file__).read_bytes()).hexdigest(),cases=out,passed=sum(v['pass_'] for v in out),failed=sum(not v['pass_'] for v in out))
result['extension_hashes']={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in pathlib.Path(iso532.__file__).parent.glob('*.pyd')}
pathlib.Path(sys.argv[1]).write_text(json.dumps(result,indent=2),encoding='utf8')
sys.exit(bool(result['failed']))
