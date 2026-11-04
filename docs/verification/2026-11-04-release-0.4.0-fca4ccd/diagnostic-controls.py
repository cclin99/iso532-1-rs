"""Additional diagnostic controls; these are not correctness references."""
from pathlib import Path
import subprocess,re,json,ctypes as C,hashlib,difflib
import numpy as np
R=Path.cwd();B=R/'tmp/acceptance-040-astra';W=B/'numeric';O=R/'docs/verification/2026-11-04-release-0.4.0-fca4ccd';DP=C.POINTER(C.c_double)
def cp(x):return x.ctypes.data_as(DP)
def cmp(a,b):
 d=abs(a-b);idx=np.unravel_index(d.argmax(),d.shape);return {'max_abs':float(d[idx]),'coordinate':list(map(int,idx)),'a_bits':f'{a[idx].view(np.uint64):016x}','b_bits':f'{b[idx].view(np.uint64):016x}'}
base=(W/'diagnostic/ISO_532-1.c').read_text();all64=re.sub(r'(?<=\d)f\b','',base);grid=base.replace('Z           = 0.1f;','Z           = 0.1;').replace('ZK = ZK + 0.1f','ZK = ((double)IdxNS+1.)/10.').replace('ZK  = ZK + 0.1f','ZK  = ((double)IdxNS+1.)/10.')
res={}
for name,src in [('all_constants_binary64',all64),('indexed_grid_control',grid)]:
 d=W/name;d.mkdir(exist_ok=True);(d/'ISO_532-1.c').write_text(src);(d/'ISO_532-1.h').write_bytes((W/'official/ISO_532-1.h').read_bytes());(d/'wrapper.c').write_bytes((O/'numeric-wrapper.c.txt').read_bytes());(d/'build.cmd').write_bytes((W/'official/build.cmd').read_bytes());p=subprocess.run(['cmd','/c',str(d/'build.cmd')],cwd=d,capture_output=True,text=True);(O/(name+'-build.log')).write_text(p.stdout+p.stderr);assert p.returncode==0
 (O/(name+'.diff.txt')).write_text(''.join(difflib.unified_diff(base.splitlines(True),src.splitlines(True),fromfile='diagnostic.c',tofile=name+'.c')))
 lib=C.CDLL(str(d/'wrapper.dll'));lib.av_signal.argtypes=[DP,C.c_int,DP,DP];lib.av_slopes.argtypes=[DP,C.c_int,DP,DP];r={'source_sha256':hashlib.sha256((d/'ISO_532-1.c').read_bytes()).hexdigest(),'signals':{}}
 for ip in sorted((B/'candidate/data/golden-c').glob('*/sig.bin')):
  nm=ip.parent.name;rd=W/'signals'/nm;nl=np.fromfile(rd/'nl.bin',dtype='<f8').reshape(21,-1);k=nl.shape[1];cn=np.zeros(k);cs=np.zeros((240,k));lib.av_slopes(cp(nl),k,cp(cn),cp(cs));rn=np.fromfile(rd/'slope-n.bin',dtype='<f8');rs=np.fromfile(rd/'slope-s.bin',dtype='<f8').reshape(240,-1);entry={'same_nl_total':cmp(rn,cn),'same_nl_specific':cmp(rs,cs)}
  x=np.fromfile(ip,dtype='<f8');frames=(len(x)+95)//96;nk=4*(frames+1);xp=np.zeros(nk*24);xp[:len(x)]=x;cn=np.zeros(nk);cs=np.zeros((240,nk));assert lib.av_signal(cp(xp),len(xp),cp(cn),cp(cs))==nk;rn=np.fromfile(rd/'n.bin',dtype='<f8');rs=np.fromfile(rd/'s.bin',dtype='<f8').reshape(240,-1);entry['pipeline_total']=cmp(rn,cn[:frames*4:4]);entry['pipeline_specific']=cmp(rs,cs[:,:frames*4:4]);r['signals'][nm]=entry
 res[name]=r
# Explicit boundary counterexample explains why epsilon removal changes sample ownership.
z=np.float64(np.float32(.1));step=z
for _ in range(8):z+=step
res['boundary_control']={'cell':8,'nominal_bark':.9,'float32_step_sum':float(z),'sum_bits':f'{z.view(np.uint64):016x}','binary64_zup':.9,'greater_than_zup':bool(z>.9),'effect':'At zero epsilon, the ninth sample is deferred from band 0 to band 1; an indexed grid restores the boundary ownership.'}
(O/'diagnostic-controls.json').write_text(json.dumps(res,indent=2))
