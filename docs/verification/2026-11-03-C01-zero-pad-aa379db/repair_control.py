"""Preserve first attempt; independently rerun only the comparator control.
The primary C/Rust numbers and all thresholds remain untouched.
"""
import ast, datetime, difflib, hashlib, json, shutil
from pathlib import Path
import numpy as np
p=Path(__file__).resolve().parent
def sha(x):return hashlib.sha256(x).hexdigest()
def dump(path,x):path.write_text(json.dumps(x,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf8',newline='\n')
r=json.loads((p/'results.json').read_text(encoding='utf8'))
assert not (p/'attempt-1-results.json').exists()
shutil.copyfile(p/'results.json',p/'attempt-1-results.json')
shutil.copyfile(p/'run_experiment.py',p/'attempt-1-run_experiment.py.txt')
original=(p/'run_experiment.py').read_text(encoding='utf8')
old='neg=compare(perturbed,got)';new='neg=compare(ref,perturbed)'
assert original.count(old)==1
corrected=original.replace(old,new)
(p/'run_experiment.py').write_text(corrected,encoding='utf8',newline='\n')
(p/'control-correction.diff.txt').write_text(''.join(difflib.unified_diff(original.splitlines(True),corrected.splitlines(True),fromfile='attempt-1-run_experiment.py',tofile='run_experiment.py')),encoding='utf8',newline='\n')
tree=ast.parse(corrected);fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='compare')
ns={'np':np};exec(compile(ast.Module(body=[fn],type_ignores=[]),'same-comparator','exec'),ns)
compare=ns['compare']
control={'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
 'reason':'Original injected-reference-vs-Rust comparison was confounded by a real baseline total mismatch. Isolate comparator capability by comparing original C reference against its injected copy.',
 'original_runner_sha256':sha(original.encode()),'corrected_reproduction_runner_sha256':sha(corrected.encode()),
 'original_results_sha256_before_redaction':sha((p/'attempt-1-results.json').read_bytes()),
 'same_comparator_source_sha256':sha(ast.get_source_segment(corrected,fn).encode()),
 'threshold_unchanged':1e-14,'primary_numerics_reused_without_modification':True,'cases':[]}
def f(bits):return np.array([int(bits,16)],dtype=np.uint64).view(np.float64)[0]
for s in r['signals']:
    ref=np.array([f(s['total']['C']['bits'])]+[f(v['C']['bits']) for v in s['specific']])
    baseline=compare(ref,ref);perturbed=ref.copy();perturbed[138]+=1e-6;actual=compare(ref,perturbed)
    result={'injected_coordinate':'specific[137]','injected_offset':float(perturbed[138]-ref[138]),
        'reference_copy_baseline':baseline,'result':actual,
        'passed':baseline['verdict']=='AGREES' and actual['verdict']!='AGREES' and actual['first_failure']=='specific[137]' and actual['rounding_failure_count']==1}
    control['cases'].append({'signal':s['signal'],'original_control':s['comparator_negative_control'],'isolated_control':result})
    s['comparator_negative_control']=result
r['gates']['comparator_negative_control']=all(c['isolated_control']['passed'] for c in control['cases'])
r['numeric_gap_closure_recommended']=all(r['gates'].values())
r['control_correction']={'artifact':'control-correction.json','original_results':'attempt-1-results.json',
    'executed_original_runner':'attempt-1-run_experiment.py.txt','corrected_reproduction_runner':'run_experiment.py',
    'scope':'Only comparator-negative-control fields/gate updated from independent isolated control; all original primary arrays, errors, prefix controls, builds and boundaries retained.'}
control['finished_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
dump(p/'control-correction.json',control);dump(p/'results.json',r)
print(json.dumps({'all_isolated_controls_passed':r['gates']['comparator_negative_control'],'numeric_gap_closure_recommended':r['numeric_gap_closure_recommended']}))
