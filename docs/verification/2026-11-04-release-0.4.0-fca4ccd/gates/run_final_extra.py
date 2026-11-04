import pathlib,subprocess,os,json,time
OUT=pathlib.Path(__file__).resolve().parent;ROOT=OUT.parents[3];BASE=ROOT/'tmp/acceptance-040-astra';env=os.environ.copy();env.update(CARGO_TARGET_DIR=str(BASE/'round1-hash-target'),HASH_GATE_DUMP_ONLY='1');rows=[]
for name,args,cwd in [('c-smoke-explicit',[BASE/'ffi-smoke/smoke.exe'],BASE/'ffi-smoke'),('round1-hash',['cargo','test','-p','iso532','--test','hash_gate','--','--nocapture'],BASE/'round1')]:
 t=time.time()
 with (OUT/(name+'.log')).open('w',encoding='utf8') as f:
  f.write('COMMAND '+json.dumps(list(map(str,args)))+'\n');f.flush();p=subprocess.run(list(map(str,args)),cwd=cwd,env=env,stdout=f,stderr=subprocess.STDOUT)
 rows.append(dict(name=name,exit_code=p.returncode,seconds=time.time()-t));(OUT/'final-extra-results.json').write_text(json.dumps(rows,indent=2),encoding='utf8');print(name,p.returncode,flush=True)
