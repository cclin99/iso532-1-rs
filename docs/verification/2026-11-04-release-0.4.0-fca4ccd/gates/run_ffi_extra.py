import pathlib,subprocess,os,json,hashlib,shutil,time
OUT=pathlib.Path(__file__).resolve().parent;ROOT=OUT.parents[3];BASE=ROOT/'tmp/acceptance-040-astra';SRC=BASE/'candidate';WORK=BASE/'ffi-smoke';WORK.mkdir(exist_ok=True);env=os.environ.copy();env['CARGO_TARGET_DIR']=str(BASE/'gates-target');rows=[]
def run(name,args,cwd=SRC):
 t=time.time()
 with (OUT/(name+'.log')).open('w',encoding='utf8') as f:
  f.write('COMMAND '+json.dumps(list(map(str,args)))+'\n');f.flush();p=subprocess.run(list(map(str,args)),cwd=cwd,env=env,stdout=f,stderr=subprocess.STDOUT)
 rows.append(dict(name=name,exit_code=p.returncode,seconds=time.time()-t));(OUT/'ffi-extra-results.json').write_text(json.dumps(rows,indent=2),encoding='utf8');print(name,p.returncode,flush=True)
 return p.returncode
run('cbindgen-version',['cbindgen','--version'])
if run('header-regen',['cbindgen','--config','cbindgen.toml','--crate','iso532-ffi','--output',WORK/'iso532.h'],SRC/'iso532-ffi')==0:
 a=(WORK/'iso532.h').read_bytes();b=(SRC/'iso532-ffi/include/iso532.h').read_bytes();(OUT/'header-regeneration.json').write_text(json.dumps({'equal':a==b,'normalized_lf_equal':a.replace(b'\r\n',b'\n')==b.replace(b'\r\n',b'\n'),'regenerated_crlf_count':a.count(b'\r\n'),'committed_crlf_count':b.count(b'\r\n'),'regenerated_sha256':hashlib.sha256(a).hexdigest(),'committed_sha256':hashlib.sha256(b).hexdigest()},indent=2),encoding='utf8')
vc=pathlib.Path(os.environ.get('VCVARS64',r'C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat'))
lib=BASE/'contracts-target-candidate/release'
if vc.exists() and (lib/'iso532_ffi.dll').exists():
 shutil.copy2(lib/'iso532_ffi.dll',WORK/'iso532_ffi.dll')
 (WORK/'smoke.cmd').write_text('@echo off\ncall "'+str(vc)+'"\nif errorlevel 1 exit /b %errorlevel%\ncl /nologo /W3 /I"'+str(SRC/'iso532-ffi/include')+'" "'+str(SRC/'iso532-ffi/tests/smoke.c')+'" /Fe:smoke.exe /link /LIBPATH:"'+str(lib)+'" iso532_ffi.dll.lib\nif errorlevel 1 exit /b %errorlevel%\n"%~dp0smoke.exe"\nexit /b %errorlevel%\n',encoding='utf8')
 run('c-smoke',['cmd','/c',WORK/'smoke.cmd'],WORK)
 (OUT/'c-smoke-hashes.json').write_text(json.dumps({p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [WORK/'iso532_ffi.dll',WORK/'smoke.exe',SRC/'iso532-ffi/tests/smoke.c'] if p.exists()},indent=2),encoding='utf8')
run('ffi-test-panic',['cargo','test','-p','iso532-ffi','--features','test-panic','--','--nocapture'])
