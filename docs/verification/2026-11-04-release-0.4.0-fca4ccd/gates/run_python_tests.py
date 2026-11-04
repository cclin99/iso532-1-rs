import pathlib,subprocess,os,json,time
OUT=pathlib.Path(__file__).resolve().parent;ROOT=OUT.parents[3];BASE=ROOT/'tmp/acceptance-040-astra';SRC=BASE/'candidate';PY=BASE/'fresh-venv/Scripts/python.exe';env=os.environ.copy();env.update(ISO532_REQUIRE_PARITY='1',PYTHONIOENCODING='utf-8')
rows=[]
for name,args in [('pip-freeze-complete',[PY,'-m','pip','freeze']),('pytest',[PY,'-m','pytest','iso532-py/tests','-v','-s'])]:
 t=time.time()
 with (OUT/(name+'.log')).open('w',encoding='utf8') as f:
  f.write('COMMAND '+json.dumps(list(map(str,args)))+'\n');f.flush();p=subprocess.run(list(map(str,args)),cwd=SRC,env=env,stdout=f,stderr=subprocess.STDOUT)
 rows.append(dict(name=name,exit_code=p.returncode,seconds=time.time()-t));(OUT/'python-recovery-results.json').write_text(json.dumps(rows,indent=2),encoding='utf8');print(name,p.returncode,flush=True)
