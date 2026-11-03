"""Review new-file diffs, redact all supported UTF-8 text, hash final delivery.
No source, input or binary hash is rewritten as a delivered-copy hash.
"""
import hashlib, json, subprocess, sys
from pathlib import Path
p=Path(__file__).resolve().parent
repo=p.parents[2]
def write(path,text):path.write_text(text,encoding='utf8',newline='\n')
def js(path,x):write(path,json.dumps(x,indent=2,ensure_ascii=False)+'\n')
def run(cmd):return subprocess.run(list(map(str,cmd)),cwd=repo,capture_output=True,text=True,encoding='utf8',errors='strict')
assert repo.name.lower()=='iso532'
review=[]
for f in sorted(p.rglob('*')):
    if not f.is_file() or f.name in {'diff-review.json','delivery-integrity.json','redaction-final.log','delivery-check.md','artifact-audit.json'}:continue
    rel=f.relative_to(repo)
    ck=run(['git','diff','--no-index','--check','--','NUL',rel]);st=run(['git','diff','--no-index','--numstat','--','NUL',rel])
    assert ck.returncode in [0,1] and not ck.stdout,(rel,ck.stdout,ck.stderr)
    assert st.returncode in [0,1],(rel,st.stdout,st.stderr)
    review.append({'file':str(f.relative_to(p)),'check_exit_code':ck.returncode,'numstat_exit_code':st.returncode,'numstat':st.stdout.strip(),
                   'warnings':sorted(set((ck.stderr+st.stderr).splitlines()))})
js(p/'diff-review.json',{'scope':'All new files compared against NUL; diff --check emits no whitespace diagnostics. Exit 1 under --no-index denotes expected new-file differences.',
 'review':'Narrative/code/commands reviewed; decimal/bits/CSV/JSON checked by audit_artifacts.py; large repeated raw CLI rows checked by parsed shape/serialization and original hashes.',
 'files':review})
write(p/'delivery-check.md','''# Delivery check / 交付檢查

## Scope / 範圍

Only this dated C-01 delivery is finalized. The fixed tested commit, official C and input hashes retain their original meanings. The existing F-03 delivery, DSP/tests/goldens/decision/brief/audit row are untouched. The main agent updates the verification index separately. This check is artifact QA, not another numerical acceptance round. The strict total gate remains FAILED; overall numerical acceptance remains PARTIAL.

## Redaction / 去識別化

Initial `python tools/redact_paths.py <this folder>`: exit 0; 4 files changed (attempt-1-results.json: 1 replacement; history-diagnostic.json: 12; results.json: 1; run-log.json: 129). Initial `--check`: exit 0, `clean`. No skipped/non-UTF-8 warning was emitted.

After all report/script/log/inventory text was written, both commands were rerun. Exact final logs are in redaction-final.log. The finalization script repeats both passes once more after writing that log, requires `0 file(s) changed` and `clean`, and only then generates delivery-integrity.json. Final integrity hashes cover post-redaction bytes and exclude the manifest itself. If anything changes later, repeat both passes and regenerate hashes.

## Coverage / 格式盤點

Every delivered file is decoded strictly as UTF-8, including the final manifest. No binary/WAV is delivered. The file inventory is delivery-integrity.json; artifact-audit.json lists the audited text. All extensions are within the scanner's supported set: .md, .json, .txt, .py, .csv, .toml, .log. Unsupported extensions: none. Non-UTF-8 files: none. Explicit skipped files/directories: none. Native C/Rust/diff/build/lock artifacts deliberately use .txt. Standard MSVC installation paths under Program Files are generic toolchain paths; user/repository identifying paths were replaced by the repository tool. A zero exit alone was not used as a coverage claim.

## Diff and consistency / 差異與一致性

All new-file diffs were checked against NUL; diff-review.json records every checked file and exit code. `git diff --no-index --check` emitted no whitespace diagnostics. Return 1 under --no-index denotes expected new-file differences, including --numstat. The finalizer initially required return 0 and stopped on a clean added-file diff; it was corrected to accept 0/1 only with empty whitespace-diagnostic stdout. Git emitted LF-to-CRLF future-conversion warnings for text files; these are retained in the review log and did not change delivered bytes. Reports, scripts, commands, logs, source/input inventory and primary numerical tables were reviewed. The only numerical-harness correction was the isolated negative-control call, preserved in control-correction.diff.txt with original runner/results.

Artifact audit: 964 C/Rust value pairs pass decimal17/binary64 round-trip, exact error recomputation and CSV/JSON equality. Paired report tables are identical; paired design data rows are identical and both preregistered hashes are unchanged. Final gate counts are 9 passed / 1 failed; 8 boundary rows passed. The first artifact-audit attempt compared translated design headers literally and failed; only that audit assertion was corrected to compare data rows. Its successful rerun does not modify designs or numerical evidence. The main agent separately reviewed the same 964 pairs, bilingual structure and design hashes; that is delivery review, not an additional numerical run.

## Hash semantics / Hash 語意

results.json/source-input-hashes.json retain raw source, WAV, pressure, output-array, binary and executed-harness hashes. attempt-1-run_experiment.py.txt preserves the executed original; run_experiment.py is the corrected reproduction script. control-correction.json/history-diagnostic.json explicitly label hashes taken before redaction. Those hashes need not equal delivered text hashes after path replacement. delivery-integrity.json is the sole final delivered-file integrity inventory and explicitly excludes itself.
''')
audit=run([sys.executable,p/'audit_artifacts.py']);assert audit.returncode==0,audit.stdout+audit.stderr
redactor=repo/'tools/redact_paths.py'
passes=[]
for cmd in [[sys.executable,redactor,p],[sys.executable,redactor,'--check',p]]:
    x=run(cmd);assert x.returncode==0
    passes.append({'command':'python tools/redact_paths.py '+('--check ' if '--check' in cmd else '')+'<delivery>','exit_code':x.returncode,'stdout':x.stdout,'stderr':x.stderr})
assert passes[0]['stdout'].strip()=='0 file(s) changed',passes
assert passes[1]['stdout'].strip()=='clean',passes
write(p/'redaction-final.log',json.dumps({'final_logged_passes':passes,'post_log_confirmation':'Both commands are repeated after this log is written; finalizer requires no changes and clean before hashing.'},indent=2)+'\n')
# No more text edits beyond the final manifest after these confirmation calls.
for cmd,expected in [([sys.executable,redactor,p],'0 file(s) changed'),([sys.executable,redactor,'--check',p],'clean')]:
    x=run(cmd);assert x.returncode==0 and x.stdout.strip()==expected and not x.stderr,(x.returncode,x.stdout,x.stderr)
supported={'.md','.json','.txt','.log','.ps1','.py','.csv','.yml','.yaml','.toml','.sh'}
files=[]
for f in sorted(p.rglob('*')):
    if not f.is_file() or f.name=='delivery-integrity.json':continue
    b=f.read_bytes();b.decode('utf8',errors='strict');assert f.suffix.lower() in supported
    files.append({'file':str(f.relative_to(p)).replace('\\','/'),'size_bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()})
js(p/'delivery-integrity.json',{'meaning':'Final post-redaction UTF-8 delivery bytes; not raw input/source/binary identity.',
 'self_excluded':'delivery-integrity.json','file_count':len(files),'files':files})
(p/'delivery-integrity.json').read_bytes().decode('utf8',errors='strict')
check=run([sys.executable,redactor,'--check',p]);assert check.returncode==0 and check.stdout.strip()=='clean' and not check.stderr
for e in files:assert hashlib.sha256((p/e['file']).read_bytes()).hexdigest()==e['sha256']
print(json.dumps({'delivery_files_including_manifest':len(files)+1,'hashed_files':len(files),'unsupported_extensions':[],
 'non_UTF8_files':[],'final_redaction':'0 file(s) changed','final_check':'clean','all_manifest_hashes_verified':True}))
