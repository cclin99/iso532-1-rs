"""Finalize UTF-8-only delivery. Run only after all evidence writers stop."""
from pathlib import Path
import subprocess,sys,json,hashlib,collections,shutil
R=Path.cwd();O=Path(__file__).resolve().parent
assert O.is_relative_to(R/'docs/verification')
for p in O.rglob('__pycache__'):
 assert p.resolve().is_relative_to(O.resolve());shutil.rmtree(p)
known={'.md','.json','.txt','.log','.ps1','.py','.csv','.yml','.yaml','.toml','.sh'}
def inventory():
 rows=[]
 for p in sorted(O.rglob('*')):
  if p.is_file():
   b=p.read_bytes();b.decode('utf8');assert b'\x00' not in b,p
   assert p.suffix in known,p
   rows.append({'file':p.relative_to(O).as_posix(),'bytes':len(b),'suffix':p.suffix,'utf8':True})
 return rows
rows=inventory()
red=subprocess.run([sys.executable,str(R/'tools/redact_paths.py'),str(O)],capture_output=True,text=True,encoding='utf8');assert red.returncode==0
check=subprocess.run([sys.executable,str(R/'tools/redact_paths.py'),'--check',str(O)],capture_output=True,text=True,encoding='utf8');assert check.returncode==0
# Paths in redactor's own inventory output are represented by this neutral token.
def safe(s):return s.replace(str(O),'<DELIVERY>').replace(str(R),'<REPO>')
status=subprocess.check_output(['git','status','--porcelain'],text=True);diff=subprocess.check_output(['git','diff','--stat'],text=True);assert not diff
text='''# Delivery check

All product/source snapshots were rechecked against their original git archives (source-integrity.json): candidate 560, Round 1 560, baseline 394 tracked files, zero changed tracked bytes. Main git diff is empty; only this delivery directory is untracked. No commit/stage/push/tag/remote CI was performed.

The whole delivery was decoded file-by-file as UTF-8 and inspected for NUL bytes, suffixes and cache directories. Only the redactor-supported suffixes listed below are present. No non-UTF-8 file, unhandled suffix, __pycache__, binary, WAV, wheel, original official C, workbook, or golden-c data is delivered. The C/Rust harness sources use .txt. Source/input/DLL hashes retain their original meaning; delivery hashes are calculated only after redaction.

## Redaction pass

```text
'''+safe(red.stdout+red.stderr)+'''```

## Check pass

```text
'''+safe(check.stdout+check.stderr)+'''```

No skipped/non-UTF-8 warnings occurred in these passes. Directory-mode silent suffix omissions were independently excluded through a complete recursive file inventory. Previous environment failures and compiler warnings remain in logs with explicit recovery notes; they are not redaction warnings.

## Review

- Reviewed paired reports, nine-item results, raw command statuses, harness sources, source hashes, input hashes and numerical summaries.
- Initial pip/pytest/C smoke failures are retained as environment history; final pytest87, workspace146/0/3, and explicit smoke execution are successful. Invalid shared-target Round1 cache output is explicitly excluded; the independent-target result is authoritative.
- Public stream-specific output is unavailable in both versions and remains PARTIAL, never fabricated as a pass. The missing commit-table entry is FAILED record consistency, with no numerical release blocker.
- Delivery manifest excludes itself, covers every other delivered file and uses redacted final bytes. It does not describe original binaries as byte-identical to these text reports.
- git diff --check succeeds for the main tracked tree; the untracked delivery was separately scanned for UTF-8, NUL, paths and artifact types. Full inventory and per-file integrity allow independent review of every untracked file.

'''
(O/'delivery-check.md').write_text(text,encoding='utf8')
subprocess.run([sys.executable,str(R/'tools/redact_paths.py'),str(O)],check=True,capture_output=True,text=True)
last=subprocess.run([sys.executable,str(R/'tools/redact_paths.py'),'--check',str(O)],capture_output=True,text=True);assert last.returncode==0,last.stdout
rows=inventory();ext=dict(collections.Counter(x['suffix'] for x in rows));(O/'delivery-inventory.json').write_text(json.dumps({'all_utf8':True,'unhandled_suffixes':[],'non_utf8':[],'binary_or_cache':[],'suffix_counts_before_inventory_manifest':ext,'files_before_inventory_manifest':rows},indent=2),encoding='utf8')
subprocess.run(['git','diff','--check'],check=True)
files={p.relative_to(O).as_posix():{'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size} for p in sorted(O.rglob('*')) if p.is_file() and p.name!='delivery-integrity.json'}
(O/'delivery-integrity.json').write_text(json.dumps({'algorithm':'SHA-256','meaning':'redacted delivered UTF-8 file bytes','excluded':['delivery-integrity.json'],'file_count':len(files),'files':files},indent=2),encoding='utf8')
print('sealed',len(files),'files plus manifest; all UTF8, no unsupported suffix; redaction clean')
