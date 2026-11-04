"""Audit frozen archives and their materialized tracked files; no git mutation."""
import subprocess,tarfile,io,hashlib,json,pathlib
R=pathlib.Path.cwd();B=R/'tmp/acceptance-040-astra';O=R/'docs/verification/2026-11-04-release-0.4.0-fca4ccd';res={}
for name,rev in [('candidate','fca4ccda18a8fbada77031425e5e683f1acd5a8d'),('round1','2fc1708'),('baseline','v0.3.1')]:
 b=subprocess.check_output(['git','archive',rev]);tar=tarfile.open(fileobj=io.BytesIO(b));files=[]
 for m in tar.getmembers():
  if not m.isfile():continue
  original=tar.extractfile(m).read();p=B/name/m.name;current=p.read_bytes() if p.exists() else None
  files.append({'path':m.name,'source_sha256':hashlib.sha256(original).hexdigest(),'materialized_matches':current==original})
 res[name]={'commit':subprocess.check_output(['git','rev-parse',rev],text=True).strip(),'archive_sha256':hashlib.sha256(b).hexdigest(),'tracked_file_count':len(files),'differences':[x['path'] for x in files if not x['materialized_matches']],'files':files}
(O/'source-integrity.json').write_text(json.dumps(res,indent=2),encoding='utf8');print({k:(v['tracked_file_count'],v['differences']) for k,v in res.items()})
