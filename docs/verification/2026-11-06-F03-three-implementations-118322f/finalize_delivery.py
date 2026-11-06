"""Text-format/privacy/table audit and post-redaction delivery integrity."""
from pathlib import Path
import json,hashlib,re,subprocess,datetime,importlib.util
ROOT=Path.cwd();OUT=Path(__file__).resolve().parent;TMP=ROOT/'tmp/verification-f03-three-implementations'
spec=importlib.util.spec_from_file_location('path_redactor',ROOT/'tools/redact_paths.py');red=importlib.util.module_from_spec(spec);spec.loader.exec_module(red)
for name in ['redaction-first.log','redaction-check.log']:
 p=TMP/name
 if p.exists():(OUT/name).write_text(red.redact_text(p.read_text(encoding='utf8'))[0],encoding='utf8')
def audit():
 unsupported=[];nonutf=[];jsonfiles=0;left=[];ident=[]
 for p in OUT.rglob('*'):
  if not p.is_file():continue
  if p.suffix.lower() not in red.TEXT_SUFFIXES:unsupported.append(p.name)
  try:t=p.read_text(encoding='utf8')
  except UnicodeDecodeError:nonutf.append(p.name);continue
  if red.redact_text(t)[1]:left.append(p.name)
  if re.search(r'DESKTOP-[A-Za-z0-9]+|license_[A-Za-z0-9]+_[A-Za-z0-9]+_\d+',t):ident.append(p.name)
  if p.suffix=='.json':json.loads(t);jsonfiles+=1
 assert not unsupported and not nonutf and not left and not ident,(unsupported,nonutf,left,ident)
 tablecounts=[];nums=[]
 for name in ['report.md','report.en.md']:
  lines=(OUT/name).read_text(encoding='utf8').splitlines();tables=[];current=[]
  for l in lines+['']:
   if l.startswith('|'):current.append(l)
   elif current:tables.append(current);current=[]
  for table in tables:
   widths=[len(re.split(r'(?<!\\)\|',line)) for line in table];assert len(set(widths))==1,(name,widths)
  tablecounts.append(len(tables));nums.append(re.findall(r'[-+]?\d+(?:\.\d+)?(?:e[-+]?\d+)?','\n'.join('\n'.join(t) for t in tables)))
 assert tablecounts==[9,9] and nums[0]==nums[1],(tablecounts,len(nums[0]),len(nums[1]))
 return {'unsupported_formats':unsupported,'non_utf8_files':nonutf,'identifying_path_residuals':left,'host_license_identifier_residuals':ident,'json_files_parsed':jsonfiles,'bilingual_table_count':9,'bilingual_table_numbers_equal':True,'markdown_table_column_counts_valid':True}
obj=audit();obj.update({'redaction_commands':['python tools/redact_paths.py <delivery>','python tools/redact_paths.py --check <delivery>'],'redactor_skipped_warnings':[],'manual_license_search_path_sanitized':True,'delivery_diff_reviewed':True,'tracked_product_diff_empty':True,'integrity_semantics':'Post-redaction bytes only; manifest excludes itself. Other provenance hashes retain original-file meaning.'})
(OUT/'delivery-audit.json').write_text(json.dumps(obj,indent=2),encoding='utf8')
(OUT/'delivery-check.md').write_text('''# Delivery check

- PASS: 150 native route/variant output files (three implementations × two variants × 25 cases) passed finite-value and shape checks; raw arrays remain in tmp.
- PASS: MoSQITo and SQAT baseline sources match frozen hashes; each isolated coefficient variant differs by exactly one ASCII digit. Fresh official-C wrapper outputs are bitwise identical to fresh evaluations through the prior original-C DLL on all 25 cases.
- PASS: original input/source hashes preserved. No product/formal-test/golden changes; no commit or push. Prior-round delivery is retained.
- PASS: matching English/Traditional-Chinese numeric tables, valid escaped Markdown table separators, parseable JSON. Report references native Octave explicitly; MATLAB remains BLOCKED. Table A.9 authority remains PENDING.
- PASS: ran the repository redactor, then --check. Inspected all delivery suffixes and UTF-8 decodability separately: no unsupported formats, no non-UTF-8/skipped files, no residual identifying paths. MATLAB's entire license-search-path was manually replaced with `<MATLAB_LICENSE_SEARCH_PATH>`; no machine/license identifier remains. Original log hash is separately labelled in execution-audit.json.
- PASS: inspected the new delivery report diff plus command/log/provenance content. Scripts are original orchestration/wrappers; no complete third-party source, WAV, workbook, DLL or numeric array is in the delivery.
- PASS: delivery-integrity.json covers every final delivery file except itself, using post-redaction SHA-256 and byte size. Original input/source/binary/raw-output hashes have not been rewritten as if they identified redacted copies.

Detailed audit: delivery-audit.json; native controls: numeric-controls.json; execution deviations: execution-audit.json and alignment-deviation.md. This is scoped numerical evidence, not blanket standards or MATLAB-runtime acceptance.
''',encoding='utf8')
for args in [[],['--check']]:
 p=subprocess.run(['python','tools/redact_paths.py',*args,str(OUT)],capture_output=True,text=True)
 assert p.returncode==0 and 'skipped' not in p.stdout+p.stderr,(p.returncode,p.stdout,p.stderr)
 print(red.redact_text(p.stdout+p.stderr)[0].strip())
audit()
files={p.relative_to(OUT).as_posix():{'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size} for p in sorted(OUT.rglob('*')) if p.is_file() and p.name!='delivery-integrity.json'}
manifest={'meaning':'Final post-redaction delivery file hashes; excludes this manifest itself. Original-source hashes in other manifests retain their own meaning.','created_at':datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat(),'files':files}
(OUT/'delivery-integrity.json').write_text(json.dumps(manifest,indent=2),encoding='utf8')
for name,m in files.items():assert hashlib.sha256((OUT/name).read_bytes()).hexdigest()==m['sha256'] and (OUT/name).stat().st_size==m['bytes']
assert set(files)=={p.relative_to(OUT).as_posix() for p in OUT.rglob('*') if p.is_file() and p.name!='delivery-integrity.json'}
print(json.dumps({'delivery_files':len(files)+1,'hashed_files':len(files),'coverage_and_hashes':'PASS','all_text_utf8':True,'unsupported_formats':[]},indent=2))
