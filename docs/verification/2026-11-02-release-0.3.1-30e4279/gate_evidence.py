"""Strict gate record loading. A successful substring never replaces process status."""
import json,re,pathlib
REQUIRED=('fmt','clippy','clippy_all','rust_tests','golden','maturin','pytest','doc_pairs','redact_docs','ffi_release','hash_gate_strict')
def pytest_counts(text):
 summaries=[x for x in text.splitlines() if re.search(r'=+ .*\bin \d',x)]
 if not summaries:raise ValueError('pytest terminal summary missing')
 counts={k:0 for k in ('passed','failed','skipped','errors','xfailed','xpassed','deselected')}
 for count,key in re.findall(r'(\d+) (passed|failed|skipped|errors?|xfailed|xpassed|deselected)',summaries[-1]):counts['errors' if key=='error' else key]=int(count)
 if not any(counts.values()):raise ValueError('pytest count missing')
 return counts
def validate(document,root):
 if not document.get('completed'):raise ValueError('incomplete formal gate execution')
 if document.get('source_commit')!='30e427963da88db8b23e82cf612f047f36cd164b':raise ValueError('unexpected snapshot')
 records=document['gates'];missing=set(REQUIRED)-set(records)
 if missing:raise ValueError('missing gate records: '+str(sorted(missing)))
 ok=True
 for name in REQUIRED:
  r=records[name];text=(root/r['log']).read_text(encoding='utf-8-sig')
  if not isinstance(r.get('exit_code'),int):raise ValueError('missing actual process exit code')
  ok=ok and r['exit_code']==0 and r['status']=='passed'
  if name=='pytest':
   observed=pytest_counts(text)
   if observed!=r['counts']:raise ValueError('pytest stored counts differ from terminal summary')
   ok=ok and observed['passed']>0 and all(observed[k]==0 for k in observed if k!='passed')
 return ok
def load(root):
 d=json.loads((root/'formal-gates.json').read_text(encoding='utf-8-sig'));return d,validate(d,root)
