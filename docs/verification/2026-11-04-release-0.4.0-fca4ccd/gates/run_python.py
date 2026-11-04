import pathlib,subprocess,os,json,hashlib,time,sys
OUT=pathlib.Path(__file__).resolve().parent; ROOT=OUT.parents[3]; BASE=ROOT/'tmp/acceptance-040-astra'; SRC=BASE/'candidate';PY=BASE/'fresh-venv/Scripts/python.exe'
env=os.environ.copy();env.update(CARGO_TARGET_DIR=str(BASE/'gates-py-target'),PYTHONIOENCODING='utf-8',ISO532_REQUIRE_PARITY='1')
results=[]
def run(name,args,cwd=SRC):
 t=time.time()
 with (OUT/(name+'.log')).open('w',encoding='utf8') as f:
  f.write('COMMAND '+json.dumps(list(map(str,args)))+'\n');f.flush();p=subprocess.run(list(map(str,args)),cwd=cwd,env=env,stdout=f,stderr=subprocess.STDOUT)
 results.append(dict(name=name,args=list(map(str,args)),exit_code=p.returncode,seconds=time.time()-t));(OUT/'python-command-results.json').write_text(json.dumps(results,indent=2),encoding='utf8');print(name,p.returncode,flush=True)
 return p.returncode
run('pip-freeze-final',[PY,'-m','pip','freeze'])
if run('maturin-retry',[PY,'-m','maturin','build','--release','--out',BASE/'wheels'],SRC/'iso532-py')==0:
 wheels=list((BASE/'wheels').glob('*.whl'));(OUT/'wheel-hashes.json').write_text(json.dumps({p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in wheels},indent=2),encoding='utf8')
 if run('wheel-install',[PY,'-m','pip','install',wheels[0]])==0:
  run('pytest',[PY,'-m','pytest','iso532-py/tests','-v','-s'])
  run('measure-mosqito',[PY,OUT/'measure_mosqito.py'])
