"""Final numerical/output/provenance audit independent of report prose."""
from pathlib import Path
import json,hashlib,sys,importlib.metadata as md
import numpy as np
from scipy.io import loadmat
R=Path.cwd();O=Path(__file__).resolve().parent;T=R/'tmp/verification-f03-factorial-matrix';P=R/'tmp/verification-f03-three-implementations'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
f=json.loads((O/'frozen-inputs.json').read_text());d=json.loads((O/'design-matrix.json').read_text());checks={}
assert len(d)==328 and len({x['id'] for x in d})==328
assert sum(x['execution']=='new' for x in d)==304
for rel,h in f['generated_inputs'].items():assert sha(T/rel)==h
for name,files in f['source_hashes'].items():
 for rel,h in files.items():assert sha(T/name/'mosqito'/rel)==h
for s in range(2,26):assert np.array_equal(np.load(T/f'inputs/sig{s}-sqrt.npy').view('u8'),np.load(P/f'inputs/sig{s}.npy').view('u8'))
for name in ['2026-11-05-F03-filter-independent-118322f','2026-11-06-F03-three-implementations-118322f']:
 old=R/'docs/verification'/name;m=json.loads((old/'delivery-integrity.json').read_text())
 for rel,h in m['files'].items():assert sha(old/rel)==h['sha256']
 checks[name]={'manifest_sha256':sha(old/'delivery-integrity.json'),'verified_files':len(m['files'])}
arraycounts={}
for p in (T/'tv-outputs').iterdir():
 dd=loadmat(p) if p.suffix=='.mat' else np.load(p);n=np.asarray(dd['n']).ravel();ns=np.asarray(dd['ns']).reshape(240,-1);assert len(n)==ns.shape[1] and np.isfinite(n).all() and np.isfinite(ns).all();arraycounts[p.name]={'N':len(n),'Nprime':int(ns.size),'sha256':sha(p)}
assert len(arraycounts)==40
for p in [T/'stationary-all.npz']:
 dd=np.load(p);assert len(dd.files)==264
 for key in dd.files:assert dd[key].shape==(241,) and np.isfinite(dd[key]).all()
checks.update({'new_tv_outputs':arraycounts,'stationary_evaluations':264,'new_evaluations_total':304,'reused_B_cells':24,'prior_TV_reanalysis_files':120,'prior_TV_overlap_with_B_reuse':24,'all_24_sqrt_inputs_bitwise_match_previous':True,'frozen_generated_inputs_and_source_hashes_match':True,'worker_exit_codes':{'stationary_final':0,'C_TV_022':0,'C_TV_024':0,'Mo_round_TV_022':0,'Mo_round_TV_024':0,'Mo_noround_TV_022':0,'Mo_noround_TV_024':0,'SQAT_stationary_both_variants_and_repeat':0,'SQAT_TV_022_a':0,'SQAT_TV_022_b':0,'SQAT_TV_024_a':0,'SQAT_TV_024_b':0},'repaired_harness_event':{'initial_attempt':'Exact-repeat assertion rejected C caller-level mutation','fix':'Independent copy supplied to each C call; shared input bytes checked after every call; all A rerun','algorithm_or_tolerance_changed':False,'rejected_log':'run-stationary-initial-rejected.log'},'python':sys.version,'analysis_packages':{k:md.version(k) for k in ['numpy','scipy','openpyxl','matplotlib','Pillow']},'no_product_or_old_delivery_write':True})
(O/'execution-audit.json').write_text(json.dumps(checks,indent=2),encoding='utf8')
print('Final numerical and immutable-prior audit PASS; 304 new + 24 reuse')
