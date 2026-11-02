import os,sys,subprocess,json,pathlib,re,hashlib,time,uuid
from gate_evidence import pytest_counts
repo=pathlib.Path(__file__).resolve().parents[3]; out=pathlib.Path(__file__).resolve().parent
src=repo/'tmp/acceptance-031/source'; venv=repo/'tmp/acceptance-031/venv'; py=venv/'Scripts/python.exe'
env=os.environ.copy();env.update(CARGO_BUILD_JOBS='2',CARGO_TARGET_DIR=str(repo/'tmp/acceptance-031/gate-target'),VIRTUAL_ENV=str(venv),REQUIRE_AVX2='1',ISO532_REQUIRE_PARITY='1',HASH_GATE_DUMP_ONLY='0');env['PATH']=str(venv/'Scripts')+os.pathsep+env['PATH']
commands=[('fmt',['cargo','fmt','--all','--check'],src),('clippy',['cargo','clippy','--all-targets','--','-D','warnings'],src/'iso532'),('clippy_all',['cargo','clippy','--workspace','--all-features','--all-targets','--','-D','warnings'],src/'iso532'),('rust_tests',['cargo','test','--workspace','--all-features'],src/'iso532'),('golden',[str(py),'tools/golden_manifest.py','--verify'],src),('maturin',[str(py),'-m','maturin','develop','--release'],src/'iso532-py'),('pytest',[str(py),'-m','pytest','iso532-py/tests','-ra'],src),('doc_pairs',[str(py),'tools/doc_pairs.py','--check'],src),('redact_docs',[str(py),'tools/redact_paths.py','--check','docs'],src),('ffi_release',['cargo','build','--release','-p','iso532-ffi'],src)]
formal_path=out/'formal-gates.json'
if formal_path.exists(): raise SystemExit('Refusing to overwrite a prior formal round; use a new delivery folder.')
commands.append(('hash_gate_strict',['cargo','test','-p','iso532','--test','hash_gate','--','--nocapture'],src))
results={}
formal={'run_id':str(uuid.uuid4()),'source_commit':'30e427963da88db8b23e82cf612f047f36cd164b','completed':False,'gates':results,'provenance':'captured subprocess return codes in this run'}
formal_path.write_text(json.dumps(formal,indent=2),encoding='utf-8')
for name,cmd,cwd in commands:
 print('START',name,flush=True);t=time.time();p=subprocess.run(cmd,cwd=cwd,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT);s=p.stdout.decode('utf-8',errors='replace');(out/(name+'.log')).write_text(s,encoding='utf-8');results[name]={'status':'passed' if p.returncode==0 else 'failed','exit_code':p.returncode,'command':cmd,'cwd':str(cwd),'elapsed_seconds':time.time()-t,'log':name+'.log'}
 if name=='rust_tests':
  counts=re.findall(r'test result: \w+\. (\d+) passed; (\d+) failed; (\d+) ignored',s);results[name]['counts']={k:sum(int(c[i]) for c in counts) for i,k in enumerate(['passed','failed','ignored'])}
 if name=='pytest':
  results[name]['summary']=s.splitlines()[-1:]
  try:results[name]['counts']=pytest_counts(s)
  except ValueError:results[name]['counts']={};results[name]['status']='failed'
 if name=='golden':results[name]['summary']=s.splitlines()[-1:]
 formal_path.write_text(json.dumps(formal,indent=2),encoding='utf-8');(out/'gates.json').write_text(json.dumps(results,indent=2),encoding='utf-8');print('END',name,p.returncode,flush=True)

formal['completed']=True
formal_path.write_text(json.dumps(formal,indent=2),encoding='utf-8')
if any(x['exit_code']!=0 or x['status']!='passed' for x in results.values()):sys.exit(1)
