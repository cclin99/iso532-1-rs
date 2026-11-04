from pathlib import Path
import subprocess,json,hashlib
r=Path.cwd();s=r/'tmp/acceptance-040-astra/candidate';o=r/'docs/verification/2026-11-04-release-0.4.0-fca4ccd';p=s/'tools/golden-c.sha256';before=p.read_bytes()
cmd=[str(r/'.venv/Scripts/python.exe'),str(s/'tools/gen_golden_c.py'),'--official',str(r/'tmp/c01-tail-root-cause-aa379db-run2/c/ISO_532-1.c'),'--header',str(r/'tmp/c01-tail-root-cause-aa379db-run2/c/ISO_532-1.h'),'--vcvars',r'C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat','--iso-archive',str(r/'tmp/c01-material/official'),'--out',str(s/'data/golden-c')]
p1=subprocess.run(cmd,capture_output=True,text=True);(o/'golden-generation.log').write_text(p1.stdout+p1.stderr,encoding='utf8')
results=[]
for ln in before.decode().splitlines():
 if not ln or ln.startswith('#'):continue
 h,n=ln.split(None,1); f=s/'data/golden-c'/n; actual=hashlib.sha256(f.read_bytes()).hexdigest() if f.exists() else None;results.append(dict(file=n,expected=h,actual=actual,match=h==actual))
p.write_bytes(before)
cmd[cmd.index('--official')+1]=str(s/'Cargo.toml');bad=subprocess.run(cmd,capture_output=True,text=True);(o/'golden-negative.log').write_text(bad.stdout+bad.stderr,encoding='utf8')
(o/'golden-results.json').write_text(json.dumps({'exit':p1.returncode,'negative_exit':bad.returncode,'files':results},indent=2),encoding='utf8')
print(p1.returncode,p1.stdout,p1.stderr,'negative',bad.returncode)

# The optional prior metadata is accepted only if its hash matches the frozen manifest.
prior=r/'data/golden-c/meta.json'
expected=next(x['expected'] for x in results if x['file']=='meta.json')
if prior.exists() and hashlib.sha256(prior.read_bytes()).hexdigest()==expected:
 old=json.loads(prior.read_text());new=json.loads((s/'data/golden-c/meta.json').read_text());diff=[]
 def walk(a,b,path=''):
  if isinstance(a,dict) and isinstance(b,dict):
   for k in sorted(a.keys()|b.keys()):walk(a.get(k),b.get(k),path+'/'+k)
  elif a!=b:diff.append({'field':path,'old':a,'new':b})
 walk(old,new)
 (o/'golden-meta-differences.json').write_text(json.dumps({'old_meta_sha256':expected,'new_meta_sha256':hashlib.sha256((s/'data/golden-c/meta.json').read_bytes()).hexdigest(),'differences':diff},indent=2),encoding='utf8')

a=(r/'tools/golden-c-usl12-4.diff').read_bytes();b=(s/'tools/golden-c-usl12-4.diff').read_bytes()
(o/'golden-diff-line-endings.json').write_text(json.dumps({'checkout_sha256':hashlib.sha256(a).hexdigest(),'archive_sha256':hashlib.sha256(b).hexdigest(),'normalized_equal':a.replace(b'\r\n',b'\n')==b.replace(b'\r\n',b'\n'),'checkout_crlf':a.count(b'\r\n'),'archive_crlf':b.count(b'\r\n')},indent=2),encoding='utf8')
