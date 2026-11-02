import pathlib,subprocess,json,os,hashlib,re,sys
out=pathlib.Path(__file__).resolve().parent;repo=out.parents[2];tmp=repo/'tmp/acceptance-031';dist=repo/'tmp/dist-0.3.1';env=dict(os.environ,CARGO_BUILD_JOBS='2',CARGO_TARGET_DIR=str(tmp/'artifact-baseline-target'))
def run(cmd,log,cwd=repo):
 p=subprocess.run([str(c) for c in cmd],cwd=cwd,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT);s=p.stdout.decode('utf-8',errors='replace');(out/log).write_text(s,encoding='utf-8');return p.returncode,s
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
code,s=run(['cargo','build','--release','--offline','-p','iso532-ffi'],'baseline-ffi-build.log',tmp/'baseline');assert code==0,s
old=tmp/'artifact-baseline-target/release';dump=next(pathlib.Path('C:/Program Files (x86)/Microsoft Visual Studio/2022/BuildTools/VC/Tools/MSVC').glob('*/bin/Hostx64/x64/dumpbin.exe'))
exports={}
for name,p in [('old',old/'iso532_ffi.dll'),('release',dist/'iso532_ffi.dll')]:
 code,s=run([dump,'/exports',p],name+'-exports.log');assert code==0;exports[name]=re.findall(r'^\s+\d+\s+[0-9A-F]+\s+[0-9A-F]+\s+(iso532_\w+)(?:\s+=\s+\w+)?\s*$',s,re.M)
code,compiler=run([dump.parent/'cl.exe'],'compiler.log')
py=tmp/'wheel-venv/Scripts/python.exe';code,s=run([py,out/'wheel_probe.py'],'wheel-install-probe.log');assert code==0,s
r={'status':'passed','exports':exports,'exports_equal':exports['old']==exports['release'],'export_count':len(exports['old']),'baseline_import_library_sha256':sha(old/'iso532_ffi.dll.lib'),'release_import_library_sha256':sha(dist/'iso532_ffi.dll.lib'),'import_library_equal':(old/'iso532_ffi.dll.lib').read_bytes()==(dist/'iso532_ffi.dll.lib').read_bytes(),'baseline_dll_sha256':sha(old/'iso532_ffi.dll'),'clean_wheel_probe':json.loads(s),'compiler':compiler}
assert r['exports_equal'] and r['import_library_equal'] and r['export_count']>0
(out/'artifact-runtime.json').write_text(json.dumps(r,indent=2),encoding='utf-8');print(json.dumps(r,indent=2))
