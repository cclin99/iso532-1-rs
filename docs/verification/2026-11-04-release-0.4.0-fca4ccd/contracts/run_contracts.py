"""Independent contracts/ABI/Annex B verifier. Run with project venv Python.
Usage: python run_contracts.py REPOSITORY_ROOT
No product sources or fixtures are modified. Official workbook data are read-only.
"""
import pathlib,sys,subprocess,hashlib,json,os,math,wave,re,struct
import numpy as np
import openpyxl
ROOT=pathlib.Path(sys.argv[1]).resolve(); BASE=ROOT/'tmp/acceptance-040-astra'; OUT=pathlib.Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def run(cmd,cwd=ROOT,env=None,log='command.log'):
 p=subprocess.run(cmd,cwd=cwd,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT);(OUT/log).write_text(p.stdout.decode('utf8',errors='replace'),encoding='utf8');assert p.returncode==0,(cmd,p.returncode);return p.stdout.decode('utf8',errors='replace')
def wav(p):
 with wave.open(str(p)) as w:
  assert(w.getnchannels(),w.getsampwidth(),w.getframerate())==(1,2,48000)
  return np.frombuffer(w.readframes(w.getnframes()),dtype='<i2').astype('float64')/32768.
official=ROOT/'tmp/c01-material/official'; inputs=BASE/'contracts-inputs';inputs.mkdir(exist_ok=True)
cal=official/'Annex C/calibration signal sine 1kHz 60dB.wav'; x=wav(cal);ss=0.
for v in x.tolist():ss+=v*v
factor=math.sqrt(1e6*4e-10/(ss/len(x)))
input_hashes={'calibration':sha(cal),'calibration_factor':factor,'calibration_factor_bits':struct.pack('>d',factor).hex()}
for s in range(1,26):
 p=next(official.rglob(f'Test signal {s} (*wav')) if s>1 else official/'Annex B.2/Test signal 1.txt'
 x=wav(p)*factor if s>1 else np.array([float(l.split(':')[1]) for l in p.read_text().splitlines() if ':' in l and not l.startswith('#')])
 dest=inputs/f'sig{s}.bin';x.astype('<f8').tofile(dest);input_hashes[str(s)]={'source_name':p.name,'source_sha256':sha(p),'decoded_sha256':sha(dest),'samples':len(x)}
harness=BASE/'contracts-harness';(harness/'src').mkdir(parents=True,exist_ok=True);(harness/'src/main.rs').write_bytes((OUT/'harness.rs.txt').read_bytes())
results={'input_hashes':input_hashes,'versions':{},'annexb':{},'stream':{},'grid':{},'abi':{},'static':{}}
for ver in ['candidate','baseline']:
 (harness/'Cargo.toml').write_text('[package]\nname="contract-acceptance"\nversion="0.1.0"\nedition="2021"\n[workspace]\n[dependencies]\niso532={path="'+(BASE/ver/'iso532').as_posix()+'"}\n',encoding='utf8')
 (harness/'Cargo.lock').write_bytes((BASE/ver/'Cargo.lock').read_bytes())
 env=dict(os.environ,CARGO_TARGET_DIR=str(BASE/('contracts-target-'+ver)))
 log=run(['cargo','run','--release','--manifest-path',str(harness/'Cargo.toml'),'--',str(inputs),str(BASE/('contracts-output-'+ver))],env=env,log=ver+'-harness.log')
 (OUT/(ver+'-harness-Cargo.lock.txt')).write_bytes((harness/'Cargo.lock').read_bytes())
 results['grid'][ver]=[{'samples':int(a),'frames':int(b),'expected':((int(a)+23)//24+3)//4} for a,b in re.findall(r'GRID,(\d+),(\d+)',log)]
 run(['cargo','build','--locked','--release','-p','iso532-ffi','--manifest-path',str(BASE/ver/'Cargo.toml')],env=env,log=ver+'-ffi-build.log')
 hdr=BASE/ver/'iso532-ffi/include/iso532.h';dll=BASE/('contracts-target-'+ver)/'release/iso532_ffi.dll';results['abi'][ver]={'header_sha256':sha(hdr),'dll_sha256':sha(dll)}
 # PE export parser avoids dependence on localized dumpbin output.
 b=dll.read_bytes();u16=lambda p:struct.unpack_from('<H',b,p)[0];u32=lambda p:struct.unpack_from('<I',b,p)[0];pe=u32(0x3c);opt=pe+24;secs=opt+u16(pe+20); exp=u32(opt+112)
 def offset(rva):
  for i in range(u16(pe+6)):
   pos=secs+40*i;va=u32(pos+12)
   if va<=rva<va+max(u32(pos+8),u32(pos+16)):return u32(pos+20)+rva-va
  raise ValueError(rva)
 e=offset(exp);names=offset(u32(e+32));exports=[]
 for i in range(u32(e+24)):
  p=offset(u32(names+4*i));exports.append(b[p:b.index(b'\0',p)].decode())
 results['abi'][ver]['exports']=exports
 for s in [10,18,23,25]:
  d=BASE/('contracts-output-'+ver);r={}
  for field in ['n','time']:
   a=np.fromfile(d/f'sig{s}-{field}.bin',dtype='<u8');c=np.fromfile(d/f'sig{s}-stream-{field}.bin',dtype='<u8');ix=np.flatnonzero(a!=c) if len(a)==len(c) else np.array([-1]);r[field]={'count':len(a),'stream_count':len(c),'mismatches':len(ix),'first':None if not len(ix) else {'index':int(ix[0]),'batch_bits':f'{a[ix[0]]:016x}','stream_bits':f'{c[ix[0]]:016x}'}}
  results['stream'][f'{ver}-{s}']=r
results['stream_specific']={'status':'partial','release_blocker':False,'reason':'Both candidate and v0.3.1 Public StreamFrame have no n_specific output and use calc_slopes_n_only. This is a pre-existing API limitation, not a regression. No source instrumentation or product modification performed.'}
results['stream_frame_source']={v:re.search(r'pub struct StreamFrame \{[^}]+\}',(BASE/v/'iso532/src/zwtv/stream.rs').read_text()).group() for v in ['candidate','baseline']}
results['raw_output_sha256']={v:{p.name:sha(p) for p in sorted((BASE/('contracts-output-'+v)).glob('*.bin'))} for v in ['candidate','baseline']}
refs={}
for p in official.rglob('*.xlsx'):
 w=openpyxl.load_workbook(p,data_only=True,read_only=True)
 for sh in w:
  s=int(re.search(r'\d+',sh.title).group()); rows=list(sh.values)
  if s<=5:refs[s]={'n':[float(rows[7][1])],'sp':[float(r[6]) for r in rows[7:247]],'workbook_sha256':sha(p)}
  else:
   r=[row for row in rows[10:] if isinstance(row[0],(int,float)) and isinstance(row[1],(int,float))]
   refs[s]={'time':[row[0] for row in r],'n':[row[1] for row in r],'workbook_sha256':sha(p)}
   if s<=13:
    label=str(rows[8][11]);refs[s]['bark_label']=label;refs[s]['bark_index']=round(float(re.search(r'[\d]+[.,]?[\d]*',label).group().replace(',','.'))*10)-1;refs[s]['sp']=[row[11] for row in r]
for s in refs:
 refs[s]['field']='diffuse' if s==15 else 'free'
 refs[s]['worksheet']='Test signal '+str(s)+('.txt' if s==1 else '')
 refs[s]['reference_cells']='B8;G8:G247' if s<=5 else 'A11:B'+str(10+len(refs[s]['n']))
for ver in ['candidate','baseline']:
 d=BASE/('contracts-output-'+ver);rr={}
 for s,ref in refs.items():
  rr[str(s)]={}
  for field in ['n','sp']:
   if field not in ref:continue
   got=np.fromfile(d/f'sig{s}-{field}.bin',dtype='<f8');want=np.asarray(ref[field]);indices=None
   if s>5:
    times=np.fromfile(d/f'sig{s}-time.bin',dtype='<f8');indices=np.rint(np.array(ref['time'])*500).astype(int)
    assert np.max(np.abs(times[indices]-ref['time']))<1e-10
    if field=='sp':got=got.reshape(240,-1)[ref['bark_index']]
    got=got[indices]
   assert len(got)==len(want)
   tol=np.maximum(.1,.05*np.abs(want));diff=np.abs(got-want);margin=tol-diff;i=int(np.argmin(margin));bad=np.flatnonzero(margin<0)
   rr[str(s)][field]={'points':len(got),'passed':int(np.sum(margin>=0)),'failed':len(bad),'minimum_margin':float(margin[i]),'minimum_margin_index':i,'got':float(got[i]),'reference':float(want[i]),'got_bits':f'{got.view(np.uint64)[i]:016x}','reference_bits':f'{want.astype("float64").view(np.uint64)[i]:016x}','minimum_margin_time':None if s<=5 else ref['time'][i],'first_failure':None if not len(bad) else {'index':int(bad[0]),'time':None if s<=5 else ref['time'][int(bad[0])],'got_bits':f'{got.view(np.uint64)[bad[0]]:016x}','reference_bits':f'{want.astype("float64").view(np.uint64)[bad[0]]:016x}'}}
 results['annexb'][ver]=rr
results['annexb_reference_metadata']={str(s):{k:v for k,v in r.items() if k not in ['n','sp','time']} for s,r in refs.items()}
results['annexb_summary']={v:{'points':sum(f['points'] for s in rr.values() for f in s.values()),'passed':sum(f['passed'] for s in rr.values() for f in s.values()),'failed':sum(f['failed'] for s in rr.values() for f in s.values()),'minimum_margin':min(f['minimum_margin'] for s in rr.values() for f in s.values())} for v,rr in results['annexb'].items()}
results['comparator_negative_controls']={'bitwise_one_bit_mutation_detected':bool(np.count_nonzero(np.array([0x3ff0000000000000],dtype='<u8')!=np.array([0x3ff0000000000001],dtype='<u8'))==1),'max_tolerance_rejects_10p55_vs_10':abs(10.55-10)>max(.1,.05*10)}
src=BASE/'candidate'
for name in ['iso532','iso532-ffi','iso532-py']:
 text=(src/name/'Cargo.toml').read_text();results['versions'][name]=re.search(r'^version = "([^"]+)"',text,re.M).group(1)
lock=(src/'Cargo.lock').read_text();results['static']['lock_versions']={n:re.search(r'name = "'+n+r'"\nversion = "([^"]+)"',lock).group(1) for n in results['versions']}
results['static']['citation_version']=re.search(r'^version: (.+)',(src/'CITATION.cff').read_text(),re.M).group(1)
ch=(src/'CHANGELOG.md').read_text();section=ch.split('## 0.4.0')[1].split('\n## ')[0];results['static']['changelog_markers']={s:s in section for s in ['F-04','F-05','F-06','F-07','Annex A']}
ci=(src/'.github/workflows/ci.yml').read_text();results['static']['ci_py_dump_only']='HASH_GATE_DUMP_ONLY' in ci.split('\n  py:')[1]
commits=run(['git','log','--format=%h %s','5cb036a..fca4ccd'],log='release-commits.log').splitlines();release=(src/'docs/RELEASE-0.4.0-2026-11-04.zh-TW.md').read_text();results['static']['commit_table']=[{'commit':c.split()[0],'present':c.split()[0] in release or c.startswith('fca4ccd')} for c in commits]
(OUT/'contracts-results.json').write_text(json.dumps(results,indent=2,ensure_ascii=False),encoding='utf8')
print(json.dumps({'annexb':{v:{'points':sum(f['points'] for s in rr.values() for f in s.values()),'failed':sum(f['failed'] for s in rr.values() for f in s.values()),'minimum_margin':min(f['minimum_margin'] for s in rr.values() for f in s.values())} for v,rr in results['annexb'].items()},'abi':results['abi'],'stream':results['stream']},indent=2))
