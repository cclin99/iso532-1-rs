"""One-time provenance reconstruction for the observed 2026-11-02 run.
The return codes below were returned by exec/write_stdin, not inferred from logs.
New rounds use run_gates.py and never this historical recorder.
"""
import json,pathlib,sys
sys.dont_write_bytecode=True
from gate_evidence import pytest_counts,validate
out=pathlib.Path(__file__).resolve().parent
if (out/'formal-gates.json').exists():raise SystemExit('formal record already exists')
g=json.loads((out/'gates.json').read_text())
for name,r in g.items():r['log']=name+'.log'
retries={
 'maturin':('maturin-retry.log',0,'exec session 33216 completion','python -m maturin develop --release'),
 'pytest':('pytest-formal.log',0,'exec session 63174 completion','python -m pytest iso532-py/tests -ra'),
 'doc_pairs':('doc_pairs-retry.log',0,'exec chunk d3df70 returned0; stdout ok','python tools/doc_pairs.py --check'),
 'redact_docs':('redact_docs-retry.log',0,'exec chunk d3df70 returned0; stdout clean','python tools/redact_paths.py --check docs'),
 'hash_gate_strict':('hash-gate-strict.log',0,'exec session 29922 completion','cargo test -p iso532 --test hash_gate -- --nocapture')}
for key,(log,code,origin,cmd) in retries.items():
 g[key]={'status':'passed' if code==0 else 'failed','exit_code':code,'command':cmd,'log':log,'exit_provenance':origin}
g['pytest']['counts']=pytest_counts((out/g['pytest']['log']).read_text())
g['rust_tests']['environment_note']='Initial full run HASH_GATE_DUMP_ONLY=1; independent strict hash_gate_strict record closes this gate.'
f={'run_id':'2026-11-02-observed-acceptance-031','source_commit':'30e427963da88db8b23e82cf612f047f36cd164b','completed':True,'provenance':'Original gates.json actual subprocess exits plus observed separately completed retry command exits. Historical reconstruction; no new DSP run.','gates':g}
assert validate(f,out)
(out/'formal-gates.json').write_text(json.dumps(f,indent=2),encoding='utf-8')
