"""Create the three isolated source snapshots without overwriting existing trees."""
from pathlib import Path
import subprocess,tarfile,io,hashlib,json
R=Path.cwd();B=R/'tmp/acceptance-040-astra';B.mkdir(parents=True,exist_ok=True)
for name,rev in [('candidate','fca4ccda18a8fbada77031425e5e683f1acd5a8d'),('round1','2fc1708'),('baseline','v0.3.1')]:
 dest=B/name
 if dest.exists():raise SystemExit('Refusing to overwrite '+str(dest))
 b=subprocess.check_output(['git','archive',rev]);dest.mkdir();tarfile.open(fileobj=io.BytesIO(b)).extractall(dest,filter='data');print(name,hashlib.sha256(b).hexdigest())
