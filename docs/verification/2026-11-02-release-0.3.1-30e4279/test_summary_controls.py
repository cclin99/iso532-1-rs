"""Lightweight fail-closed controls for the actual report generator; no DSP."""
import pathlib,json,tempfile,shutil,subprocess,sys,copy
out=pathlib.Path(__file__).resolve().parent;repo=out.parents[2];results=[]
for case in ['missing_log','failed_exit','skipped_pytest','missing_record','incomplete_run']:
 with tempfile.TemporaryDirectory(dir=repo/'tmp',prefix='summary-control-') as d:
  dst=pathlib.Path(d)
  for p in out.rglob('*'):
   if p.is_file() and p.suffix in ['.json','.log'] and p.name not in ['results.json','delivery-integrity.json']:
    target=dst/p.relative_to(out);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,target)
  # Independent sub-results are required even though the root output starts absent.
  for sub in ['contracts','numerics']:shutil.copyfile(out/sub/'results.json',dst/sub/'results.json')
  f=json.loads((dst/'formal-gates.json').read_text());p=dst/f['gates']['pytest']['log']
  if case=='missing_log':p.unlink()
  if case=='failed_exit':f['gates']['pytest']['exit_code']=1;f['gates']['pytest']['status']='failed'
  if case=='skipped_pytest':
   p.write_text(p.read_text().replace('69 passed','68 passed, 1 skipped'));f['gates']['pytest']['counts']['passed']=68;f['gates']['pytest']['counts']['skipped']=1
  if case=='missing_record':del f['gates']['maturin']
  if case=='incomplete_run':f['completed']=False
  (dst/'formal-gates.json').write_text(json.dumps(f))
  proc=subprocess.run([sys.executable,str(out/'summarize.py'),'--evidence-root',str(dst)],capture_output=True,text=True)
  decision=json.loads((dst/'results.json').read_text())['decision'] if (dst/'results.json').exists() else None
  passed=decision!='ACCEPT';assert passed,case
  results.append({'case':case,'exit_code':proc.returncode,'decision':decision,'passed':passed})
(out/'summary-negative-controls.json').write_text(json.dumps(results,indent=2),encoding='utf-8');print(json.dumps(results))
