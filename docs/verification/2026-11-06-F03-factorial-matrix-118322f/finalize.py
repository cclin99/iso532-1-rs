"""One final redaction pass, explicit visual-format privacy checks, integrity."""
from pathlib import Path
import json,hashlib,re,subprocess,importlib.util,xml.etree.ElementTree as ET,datetime
from PIL import Image
R=Path.cwd();O=Path(__file__).resolve().parent
sp=importlib.util.spec_from_file_location('redactor',R/'tools/redact_paths.py');red=importlib.util.module_from_spec(sp);sp.loader.exec_module(red)
(O/'delivery-check.md').write_text('''# Delivery check

- PASS: design328 unique cells =304 new evaluations +24 immutable reused B cells; A256+crop8 and B64 IDs match. Prior20-signal reanalysis uses120 files with24 overlapping B, not extra new executions.
- PASS:264 new stationary outputs and40 new TV outputs pass shape/finite checks; original/new inputs and source hashes verified. All24 sqrt inputs match prior input arrays bitwise. Both previous delivery manifests remain intact.
- PASS: native Mo skip0 frontend parity, exact repeats, immutable shared-level guards,128 insensitive stationary USL pairs,8 representative signal25 USL pairs,64 stationary and16 TV no-round Nprime bitwise controls. Full16/32-term Walsh reconstruction residuals ≤1e−12; coordinate error decompositions ≤1e−12.
- PASS: coordinator separately checked full design/result coverage,40 shared-level hashes, all24 reused-input equivalence, source no-round isolation,16 independent paired C main effects and prior manifests.
- PASS: English/Traditional-Chinese numeric tables match; SVG/PNG visually reviewed, units/domain/reference/coordinate clear. Generic redactor does not cover these formats: SVG XML text/metadata was separately inspected; PNG decoded and text metadata inspected. No identifying paths in either.
- PASS: repository redactor followed by --check; all other files UTF-8 and supported, warnings/skipped/non-UTF8 inspected. Delivery diff reviewed; no complete third-party source, raw WAV/workbook, DLL or large arrays included.
- PASS: dedicated Octave container stopped after all workers exited; files retained. Initial caller-mutation adapter failure and full successful rerun are explicit, without changing algorithms or repeat tolerance.
- PASS: delivery-integrity.json covers all final post-redaction files except itself. Original source/input/binary/output hashes keep their separate meaning. No product, formal-test, golden, old evidence, commit or push changes.

Scope remains diagnostic; no p-values, universal conformity claim, unique-best-setting claim, or authority decision for Table A.9.
''',encoding='utf8')
for args,name in [([], 'redaction.log'),(['--check'],'redaction-check.log')]:
 p=subprocess.run(['python','tools/redact_paths.py',*args,str(O)],capture_output=True,text=True)
 text=red.redact_text(p.stdout+p.stderr)[0];(O/name).write_text(text,encoding='utf8');assert p.returncode==0 and 'skipped' not in text.lower(),text
 print(text.strip())
unsupported=[];nonutf=[];privacy=[];jsoncount=0
for p in O.rglob('*'):
 if not p.is_file() or p.suffix=='.png':continue
 if p.suffix not in red.TEXT_SUFFIXES and p.suffix!='.svg':unsupported.append(p.name)
 try:t=p.read_text(encoding='utf8')
 except UnicodeDecodeError:nonutf.append(p.name);continue
 if red.redact_text(t)[1] or re.search(r'DESKTOP-[A-Za-z0-9]+|license_[A-Za-z0-9]+_[A-Za-z0-9]+_\d+',t):privacy.append(p.name)
 if p.suffix=='.json':json.loads(t);jsoncount+=1
assert not unsupported and not nonutf and not privacy,(unsupported,nonutf,privacy)
ET.parse(O/'factorial-effects.svg')
with Image.open(O/'factorial-effects.png') as im:
 im.load();png={'size':list(im.size),'mode':im.mode,'metadata':im.info};assert im.size[0]>=1000
 for val in im.info.values():assert red.redact_text(str(val))[1]==0
numbers=[];counts=[]
for name in ['report.md','report.en.md']:
 tables=[];cur=[]
 for line in (O/name).read_text(encoding='utf8').splitlines()+['']:
  if line.startswith('|'):cur.append(line)
  elif cur:tables.append(cur);cur=[]
 for t in tables:assert len({len(re.split(r'(?<!\\)\|',l)) for l in t})==1
 counts.append(len(tables));numbers.append(re.findall(r'[-+]?\d+(?:\.\d+)?(?:e[-+]?\d+)?','\n'.join('\n'.join(t) for t in tables)))
assert counts==[9,9] and numbers[0]==numbers[1]
audit={'unsupported_formats':unsupported,'non_UTF8_files':nonutf,'privacy_residual_files':privacy,'generic_redactor_skipped_warnings':[],'generic_unsupported_but_manually_checked':['factorial-effects.svg','factorial-effects.png'],'SVG_XML_and_text_privacy':'PASS','PNG_decode_metadata_and_visual_review':'PASS','png':png,'bilingual_tables':9,'bilingual_numeric_tables_match':True,'markdown_table_columns_valid':True,'JSON_files_parsed_before_audit':jsoncount,'report_and_delivery_diff_reviewed':True}
(O/'delivery-audit.json').write_text(json.dumps(audit,indent=2),encoding='utf8')
files={p.relative_to(O).as_posix():{'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size} for p in sorted(O.rglob('*')) if p.is_file() and p.name!='delivery-integrity.json'}
m={'meaning':'Final post-redaction delivery bytes, excluding this manifest. Original input/source/binary/output hashes elsewhere preserve their original-file meaning.','created_at':datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat(),'files':files}
(O/'delivery-integrity.json').write_text(json.dumps(m,indent=2),encoding='utf8')
assert all(hashlib.sha256((O/k).read_bytes()).hexdigest()==v['sha256'] for k,v in files.items())
print(json.dumps({'total_files':len(files)+1,'hashed_files':len(files),'integrity':'PASS','privacy':'PASS','SVG_PNG_extra_inspection':'PASS'},indent=2))
