"""Freeze read-only raw material before computation. Run from repository root."""
from pathlib import Path
import hashlib, json, subprocess, datetime
ROOT = Path.cwd()
OUT = Path(__file__).resolve().parent
TAG = '118322f8300dc752f1d38a79db230a2db5ff2870'
sha = lambda b: hashlib.sha256(b).hexdigest()
files = {}
for p in sorted((ROOT/'tmp/c01-material/official').rglob('*')):
    if p.is_file() and p.suffix.lower() in ('.wav','.xlsx','.c','.h','.txt','.pdf'):
        files[p.relative_to(ROOT).as_posix()] = {'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())}
crate = {}
snapshot = ROOT/'tmp/verification-f03-filter-independent/product'
snapshot.mkdir(parents=True,exist_ok=True)
for rel in subprocess.check_output(['git','ls-tree','-r','--name-only',TAG,'iso532']).decode().splitlines():
    raw = subprocess.check_output(['git','show',f'{TAG}:{rel}'])
    current = (ROOT/rel).read_bytes()
    assert raw.replace(b'\r\n',b'\n') == current.replace(b'\r\n',b'\n'), f'working copy differs beyond line endings: {rel}'
    dest=snapshot/rel
    dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_bytes(raw)
    crate[rel] = sha(raw)
o = dict(created_at=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat(),
         product_commit=TAG, orchestration_head=subprocess.check_output(['git','rev-parse','HEAD']).decode().strip(),
         working_crate_equals_tag_after_crlf_normalization=True, tested_crate='git-show extracted byte-exact snapshot', raw_inputs=files, product_files=crate,
         preregistration_sha256=sha((OUT/'preregistration.md').read_bytes()))
p=OUT/'frozen-inputs.json'
with p.open('x',encoding='utf8') as f: json.dump(o,f,indent=2)
print(f'Frozen {len(files)} raw material files and {len(crate)} product files; crate equals tag.')
