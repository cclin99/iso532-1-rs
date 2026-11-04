"""Independent acceptance numerical runner. Run from repository root with numpy Python.
Frozen archives must first exist under tmp/acceptance-040-astra.
"""
import pathlib as P,subprocess as S,json,re,hashlib,ctypes as C,math,wave,os,difflib
import numpy as np
R=P.Path.cwd();B=R/'tmp/acceptance-040-astra';O=R/'docs/verification/2026-11-04-release-0.4.0-fca4ccd';W=B/'numeric';W.mkdir(exist_ok=True)
VC=P.Path(os.environ.get('ISO532_VCVARS',r'C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat'))
def sha(p):return hashlib.sha256(P.Path(p).read_bytes()).hexdigest()
def run(cmd,cwd=None,label='command'):
 p=S.run(cmd,cwd=cwd,capture_output=True,text=True,encoding='utf8',errors='replace');(O/(label+'.log')).write_text(p.stdout+p.stderr,encoding='utf8');assert p.returncode==0,(cmd,p.stdout[-1000:],p.stderr[-1000:]);return p.stdout
exes={}
for v in ['candidate','round1']:
 d=W/v;d.mkdir(exist_ok=True);(d/'src').mkdir(exist_ok=True);(d/'src/main.rs').write_bytes((O/'numeric-harness.rs.txt').read_bytes());(d/'Cargo.toml').write_text('[package]\nname="acceptance-numeric"\nversion="0.0.0"\nedition="2021"\n[workspace]\n[dependencies]\niso532={path="'+(B/v/'iso532').as_posix()+'"}\n',encoding='utf8');(d/'Cargo.lock').write_bytes((B/v/'Cargo.lock').read_bytes());run(['cargo','build','--offline','--release','--manifest-path',str(d/'Cargo.toml')],label='numeric-build-'+v);exes[v]=d/'target/release/acceptance-numeric.exe'
source=(R/'tmp/c01-tail-root-cause-aa379db-run2/c/ISO_532-1.c').read_bytes();header=(R/'tmp/c01-tail-root-cause-aa379db-run2/c/ISO_532-1.h').read_bytes()
assert hashlib.sha256(source).hexdigest()=='a74b45ed297cd09ac60701a923120341137d227e536f3109ae4ece810d834491'
old=b'{ 0.40f,0.33f,0.26f,0.24f,0.22f,0.22f,0.22f,0.22f}';new=b'{ 0.40f,0.33f,0.26f,0.24f,0.24f,0.22f,0.22f,0.22f}';assert source.count(old)==1;patched=source.replace(old,new);assert hashlib.sha256(patched).hexdigest()=='739af24dee118027cb419fcdb051d8b56b274211d986140d66d7ff4b9d52a7e9'
s=patched.decode();a=s.index('static double ZUP[]');z=s.index('/*  Correction of third octave',a);s=s[:a]+re.sub(r'(?<=\d)f\b','',s[a:z])+s[z:];assert s.count('_ZUP    += .0001f;')==1;s=s.replace('_ZUP    += .0001f;','_ZUP    += 0.0;');diag=s.encode()
(O/'numeric-diagnostic.diff.txt').write_text(''.join(difflib.unified_diff(patched.decode().splitlines(True),s.splitlines(True),fromfile='usl024.c',tofile='diagnostic.c')),encoding='utf8')
libs={};DP=C.POINTER(C.c_double)
for name,src in [('official',source),('patched',patched),('diagnostic',diag)]:
 d=W/name;d.mkdir(exist_ok=True);(d/'ISO_532-1.c').write_bytes(src);(d/'ISO_532-1.h').write_bytes(header);(d/'wrapper.c').write_bytes((O/'numeric-wrapper.c.txt').read_bytes());cmd='call "'+str(VC)+'" >nul && cl /nologo /O2 /fp:precise /LD wrapper.c /link /OUT:wrapper.dll';(d/'build.cmd').write_text(cmd,encoding='utf8');run(['cmd','/c',str(d/'build.cmd')],cwd=d,label='numeric-c-build-'+name);lib=C.CDLL(str(d/'wrapper.dll'));lib.av_signal.argtypes=[DP,C.c_int,DP,DP];lib.av_slopes.argtypes=[DP,C.c_int,DP,DP];lib.av_levels.argtypes=[DP,DP,DP];libs[name]=lib

def cp(x):return x.ctypes.data_as(DP)
def csl(name,nm):
 nm=np.ascontiguousarray(nm);k=nm.size//21;n=np.zeros(k);s=np.zeros((240,k));libs[name].av_slopes(cp(nm),k,cp(n),cp(s));return n,s

def csig(name,x):
 frames=(len(x)+95)//96;k=4*(frames+1);xp=np.zeros(k*24);xp[:len(x)]=x;n=np.zeros(k);s=np.zeros((240,k));assert libs[name].av_signal(cp(xp),len(xp),cp(n),cp(s))==k;return n[:4*frames:4].copy(),s[:,:4*frames:4].copy()
def rust(v,mode,inp,d):
 d.mkdir(parents=True,exist_ok=True);p=S.run([str(exes[v]),mode,str(inp),str(d)],capture_output=True,text=True);assert p.returncode==0,p.stderr
 return tuple(np.fromfile(d/(n+'.bin'),dtype='<f8') for n in ['n','s'])
def bits(x):return f'{np.float64(x).view(np.uint64):016x}'
def compare(a,b):
 assert a.shape==b.shape,(a.shape,b.shape);d=np.abs(a-b);i=np.unravel_index(int(d.argmax()),d.shape);neq=np.argwhere(a.view('u8')!=b.view('u8'));j=tuple(neq[0]) if len(neq) else None
 return {'max_abs':float(d[i]),'max_coordinate':list(map(int,i)),'max_a_bits':bits(a[i]),'max_b_bits':bits(b[i]),'bitwise_differences':len(neq),'first_coordinate':list(map(int,j)) if j is not None else None,'first_a_bits':bits(a[j]) if j is not None else None,'first_b_bits':bits(b[j]) if j is not None else None}
res={'sources':{n:sha(W/n/'ISO_532-1.c') for n in libs},'dlls':{n:sha(W/n/'wrapper.dll') for n in libs},'rust_executables':{v:sha(p) for v,p in exes.items()},'single':{},'sequences':{},'round1':{},'inputs':{}}
text=(B/'candidate/iso532/src/core/calc_slopes.rs').read_text()
for key in ['SIG18_FRAME1564','SIG23_FRAME3893','BAND20_ONLY']:
 if key=='BAND20_ONLY':nm=np.zeros(21);nm[20]=1
 else:nm=np.array([float(v.strip().replace('_','')) for v in re.search(r'const '+key+r': \[f64; 21\] = \[(.*?)\];',text,re.S)[1].split(',') if v.strip()])
 ip=W/(key+'.bin');nm.tofile(ip);rn,rs=rust('candidate','slope',ip,W/key);r={'total':float(rn[0]),'total_bits':bits(rn[0]),'cell35':float(rs[35]),'cell36':float(rs[36]),'nm4':float(nm[4]),'band0_all_zero':bool(np.all(rs[:9]==0)),'C':{}}
 for name in libs:
  cn,cs=csl(name,nm);r['C'][name]={'total':float(cn[0]),'total_delta':float(rn[0]-cn[0]),'specific':compare(rs,cs[:,0])}
 res['single'][key]=r
 print('single',key,flush=True)
for p in sorted((B/'candidate/data/golden-c').glob('*/sig.bin')):
 name=p.parent.name;x=np.fromfile(p,dtype='<f8');res['inputs'][name]=sha(p);d=W/'signals'/name;rn,rs=rust('candidate','stages',p,d);rs=rs.reshape(240,-1);entry={}
 for cv in libs:
  cn,cs=csig(cv,x);entry[cv]={'n':compare(rn,cn),'specific':compare(rs,cs),'tail_total_delta':float(rn[-1]-cn[-1]),'tail_specific_max':float(np.max(abs(rs[:,-1]-cs[:,-1])))}
 nl=np.fromfile(d/'nl.bin',dtype='<f8').reshape(21,-1);sn=np.fromfile(d/'slope-n.bin',dtype='<f8');ss=np.fromfile(d/'slope-s.bin',dtype='<f8').reshape(240,-1);cn,cs=csl('diagnostic',nl);entry['diagnostic_same_nl']={'n':compare(sn,cn),'specific':compare(ss,cs)}
 lev=p.parent/'zwst_levels.bin'
 if lev.exists():
  stn,sts=rust('candidate','levels',lev,d/'stationary');levels=np.fromfile(lev,dtype='<f8');cn=np.zeros(1);cs=np.zeros(240);libs['patched'].av_levels(cp(levels),cp(cn),cp(cs));entry['stationary']={'n':compare(stn,cn),'specific':compare(sts,cs)}
 on,ospec=rust('round1','signal',p,d/'round1');entry['round1_vs_patched']={'n':compare(on,np.fromfile(p.parent/'zwtv_total.bin',dtype='<f8')),'specific':compare(ospec.reshape(240,-1),np.fromfile(p.parent/'zwtv_specific.bin',dtype='<f8').reshape(240,-1))};entry['round1_n_unchanged']=compare(rn,on)
 res['sequences'][name]=entry;(O/'numeric-results.json').write_text(json.dumps(res,indent=2),encoding='utf8');print('sequence',name,entry['patched']['n']['max_abs'],entry['patched']['specific']['max_abs'],flush=True)
# All official Annex B WAVs, using sequential Annex C calibration.
def wav(p):
 with wave.open(str(p),'rb') as w:assert (w.getnchannels(),w.getsampwidth(),w.getframerate())==(1,2,48000);return np.frombuffer(w.readframes(w.getnframes()),'<i2').astype('f8')/32768
cal=wav(R/'tmp/c01-material/official/Annex C/calibration signal sine 1kHz 60dB.wav');intensity=0.
for v in cal:intensity+=float(v)*float(v)
factor=math.sqrt(1e6*4e-10/(intensity/len(cal)));res['calibration_bits']=bits(factor)
paths=sorted((R/'tmp/c01-material/official').glob('Annex B*/*.wav'))
for p in paths+[None]:
 name=p.stem if p else 'contract_3s';x=wav(p)*factor if p else np.array([((i*2654435761)%96001)/96000*.02-.01 for i in range(144000)]);ip=W/'all-annex-input.bin';x.tofile(ip);res['inputs'][name]={'wav_sha256':sha(p) if p else None,'input_sha256':sha(ip),'samples':len(x)};d=W/'round-comparison';mode='signal_diffuse' if name.startswith('Test signal 15 ') else 'signal';rn,rs=rust('candidate',mode,ip,d/'new');on,oss=rust('round1',mode,ip,d/'old');t=np.fromfile(d/'new/t.bin',dtype='<f8');ot=np.fromfile(d/'old/t.bin',dtype='<f8');res['round1'][name]={'n':compare(rn,on),'time':compare(t,ot),'specific':compare(rs.reshape(240,-1),oss.reshape(240,-1))};(O/'numeric-results.json').write_text(json.dumps(res,indent=2),encoding='utf8');print('round',name,res['round1'][name]['n']['bitwise_differences'],res['round1'][name]['specific']['bitwise_differences'],flush=True)
