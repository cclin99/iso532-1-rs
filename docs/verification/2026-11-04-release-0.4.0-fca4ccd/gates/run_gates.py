import subprocess, pathlib, os, json, hashlib, shutil, sys, time
ROOT=pathlib.Path(__file__).resolve().parents[4]
BASE=ROOT/'tmp/acceptance-040-astra'; SRC=BASE/'candidate'; OUT=pathlib.Path(__file__).resolve().parent
ENV=os.environ.copy(); ENV['CARGO_TARGET_DIR']=str(BASE/'gates-target'); ENV['PYTHONIOENCODING']='utf-8'
results=[]
def run(name,args,cwd=SRC,extra=None):
 env=ENV.copy();env.update(extra or {});start=time.time()
 with (OUT/(name+'.log')).open('w',encoding='utf8') as f:
  f.write('COMMAND '+json.dumps([str(x) for x in args])+'\n');f.flush()
  p=subprocess.run([str(x) for x in args],cwd=cwd,env=env,stdout=f,stderr=subprocess.STDOUT)
 results.append(dict(name=name,args=[str(x) for x in args],exit_code=p.returncode,seconds=time.time()-start));(OUT/'command-results.json').write_text(json.dumps(results,indent=2),encoding='utf8');print(name,p.returncode,flush=True)
 return p.returncode
if __name__=='__main__':
 inputs={}
 for kind in ['golden','annexb']:
  src=ROOT/'data'/kind;dest=SRC/'data'/kind
  if not dest.exists():shutil.copytree(src,dest)
  for p in sorted(dest.rglob('*')):
   if p.is_file():inputs[str(p.relative_to(SRC)).replace('\\','/')]=hashlib.sha256(p.read_bytes()).hexdigest()
 (OUT/'input-hashes.json').write_text(json.dumps(inputs,indent=2),encoding='utf8')
 for name,args in [('rustc',['rustc','-Vv']),('cargo',['cargo','-V']),('python',[sys.executable,'--version']),('fmt',['cargo','fmt','--all','--','--check']),('clippy',['cargo','clippy','--workspace','--all-targets','--','-D','warnings']),('clippy-ffi',['cargo','clippy','-p','iso532-ffi','--all-targets','--all-features','--','-D','warnings']),('doc-pairs',[sys.executable,'tools/doc_pairs.py','--check']),('redact-docs',[sys.executable,'tools/redact_paths.py','--check','docs'])]:run(name,args)
 venv=BASE/'fresh-venv';run('venv',[sys.executable,'-m','venv',venv]);py=venv/'Scripts/python.exe'
 run('pip-dependencies',[py,'-m','pip','install','numpy==2.4.6','mosqito==1.2.1','pytest==9.1.1','maturin==1.14.1'])
 run('pip-freeze',[py,'-m','pip','freeze'])
 run('maturin',[py,'-m','maturin','build','--release','--out',BASE/'wheels'],SRC/'iso532-py')
 wheels=list((BASE/'wheels').glob('*.whl'))
 if wheels:
  (OUT/'wheel-hashes.json').write_text(json.dumps({p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in wheels},indent=2),encoding='utf8')
  run('wheel-install',[py,'-m','pip','install',wheels[0]])
  run('pytest',[py,'-m','pytest','iso532-py/tests','-v','-s'],extra={'ISO532_REQUIRE_PARITY':'1'})
 for test in ['hash_gate','output_grid','stream','annexb','annexb_validator','golden_zwtv','golden_zwst']:
  run(test,['cargo','test','-p','iso532','--test',test,'--','--nocapture'])
 run('hash-dump',['cargo','test','-p','iso532','--test','hash_gate','--','--nocapture'],extra={'HASH_GATE_DUMP_ONLY':'1'})
 run('bench-build',['cargo','bench','--workspace','--no-run'])
 print('WAIT GOLDEN',flush=True)
 while not (BASE/'golden-ready').exists():time.sleep(5)
 run('golden_c',['cargo','test','-p','iso532','--test','golden_c','--','--nocapture'])
 run('workspace',['cargo','test','--workspace','--no-fail-fast'])
