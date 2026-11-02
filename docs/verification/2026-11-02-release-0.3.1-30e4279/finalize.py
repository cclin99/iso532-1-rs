"""Redact every text file, audit unknown suffixes, then hash post-redaction bytes."""
import pathlib,sys,subprocess,json,hashlib,collections,runpy
out=pathlib.Path(__file__).resolve().parent;repo=out.parents[2];tool=repo/'tools/redact_paths.py';ns=runpy.run_path(str(tool));suffixes=ns['TEXT_SUFFIXES'];redact=ns['redact_text']
def files():return sorted(p for p in out.rglob('*') if p.is_file() and p.name!='delivery-integrity.json')
def call(args):
 p=subprocess.run([sys.executable,str(tool),*map(str,args)],stdout=subprocess.PIPE,stderr=subprocess.STDOUT);text=p.stdout.decode('utf-8');assert p.returncode==0,text;return redact(text)[0]
# Canonical LF and one terminal newline for nonempty text define delivered bytes.
# Original source/input/binary object hashes stay unchanged.
for p in files():
 text=p.read_bytes().decode('utf-8');text=text.replace('\r\r\n','\n').replace('\r\n','\n').replace('\r','\n')
 if text:text=text.rstrip('\n')+'\n'
 p.write_bytes(text.encode('utf-8'))
# The required directory redaction is first. Direct-file redaction covers suffixes
# silently omitted by directory mode (.rs/.c/.cmd/.jsonl/.lock/.exit, etc.).
first=call([out]);unknown=[p for p in files() if p.suffix.lower() not in suffixes];extra=call(unknown) if unknown else 'none\n'
check=call(['--check',out]);allcheck=call(['--check',*files()])
for p in files():
 s=p.read_bytes().decode('utf-8');assert '\0' not in s,(p,'NUL byte');assert redact(s)[1]==0,p
p=out/'delivery-check.md';p.write_text('# Delivery audit\n\n- Line endings: all delivered text is normalized to LF before redaction/hashing; original source/input/binary hashes retain their raw-object meaning.\n- Status: PASS. All delivered files decode as UTF-8; no binary/WAV/wheel payloads are included.\n- Required directory redaction followed by --check completed. Unknown suffixes were passed explicitly as individual files and checked again.\n- No non-UTF8 skipped files or tool warnings. Directory mode silently omits unknown suffixes; the explicit-file pass closes this gap.\n- Post-redaction integrity covers all delivery files except delivery-integrity.json itself. Original source/input/binary hashes retain their raw-object meaning.\n\n## Redactor output\n\n```text\n'+first+extra+check+allcheck+'```\n',encoding='utf-8')
inventory=[{'path':p.relative_to(out).as_posix(),'suffix':p.suffix.lower(),'utf8':True,'directory_redactor_supported':p.suffix.lower() in suffixes} for p in files()]
summary=collections.Counter(x['suffix'] for x in inventory)
with (out/'delivery-check.md').open('a',encoding='utf-8') as h:
 h.write('\n## Complete text inventory\n\n'+f'Files (excluding integrity manifest): {len(inventory)}. Suffix counts: '+json.dumps(dict(sorted(summary.items())))+'. Non-UTF8: 0. NUL-containing files: 0. Residual identifying paths: 0.\n\n')
 h.write('| File | UTF-8 | Directory mode |\n|---|---|---|\n')
 for row in inventory:h.write('| '+row['path']+' | yes | '+('covered' if row['directory_redactor_supported'] else 'explicit file pass')+' |\n')
# Verify the generated audit and every other file again before final hashing.
for p in files():
 s=p.read_bytes().decode('utf-8').replace('\r\r\n','\n').replace('\r\n','\n').replace('\r','\n');assert '\0' not in s;assert redact(s)[1]==0
 p.write_bytes(s.encode('utf-8'))
manifest={'scope':'post-redaction UTF-8 delivery files','excluded':['delivery-integrity.json'],'files':[{'path':p.relative_to(out).as_posix(),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in files()]}
(out/'delivery-integrity.json').write_bytes(json.dumps(manifest,ensure_ascii=False,indent=2).encode('utf-8'));print('PASS',len(manifest['files']),'files; manifest excludes itself')
