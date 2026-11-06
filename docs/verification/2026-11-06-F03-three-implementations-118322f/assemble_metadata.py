"""Collect provenance and distinguish original logs from sanitized delivery copies."""
from pathlib import Path
import json,hashlib,re,shutil,datetime
ROOT=Path.cwd();OUT=Path(__file__).resolve().parent;TMP=ROOT/'tmp/verification-f03-three-implementations'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
rawlogs={}
for name in ['sqat-acquisition.json','octave-package-versions.txt','octave-readiness.log']:
 p=TMP/name;rawlogs[name]=sha(p);shutil.copyfile(p,OUT/name)
p=TMP/'matlab-readiness.log';rawlogs[p.name]=sha(p)
t=p.read_text(encoding='utf8');t=re.sub(r'License path:.*?(?=Licensing error:)', 'License path: <MATLAB_LICENSE_SEARCH_PATH>\n',t,flags=re.S)
assert 'DESKTOP-' not in t and 'R2021a_licenses' not in t
(OUT/'matlab-readiness.redacted.log').write_text(t,encoding='utf8')
audit={'started_date_asia_taipei':'2026-11-05','completed_date_asia_taipei':'2026-11-06','all_native_output_routes':150,'signals_per_variant':list(range(1,26)),
 'native_worker_exit_codes':{'c022':0,'c024':0,'mos022':0,'mos024':0,'sqat022_shard_a':0,'sqat022_shard_b':0,'sqat024_shard_a':0,'sqat024_shard_b':0},
 'intentional_scheduling_restart':{'initial_sqat_worker_exit_codes':[1,1],'completed_and_preserved_signals':[1,2,3,4,5,6,9],'terminated_container_pids':[3325,3332],'reason':'Partition remaining inputs into four disjoint jobs on four available CPUs; no algorithm change','new_threads':{'OPENBLAS_NUM_THREADS':'1','OMP_NUM_THREADS':'1'}},
 'environment_and_harness_events':[
  {'event':'MATLAB R2021a readiness','status':'BLOCKED','reason':'License Manager Error -10, license expired','resolution':'Native unchanged SQAT .m run in GNU Octave 8.4.0; MATLAB acceptance not claimed'},
  {'event':'Initial signal 1 preparation','status':'REPAIRED BEFORE RUN','reason':'Generic regex incorrectly included header/frequency numbers; assertion rejected input','resolution':'Read only noncomment text after colon, as official format specifies'},
  {'event':'Initial shard argument shape','status':'REPAIRED BEFORE SHARD NUMERICS','reason':'Column argv vector made one vector loop iteration; nonexistent concatenated input filename rejected','resolution':'reshape signals to row vector; four initial logs preserved'},
  {'event':'Exact returned-time matching','status':'PROTOCOL DEVIATION DOCUMENTED','reason':'MoSQITo endpoint-inclusive linspace labels differ from physical decimation grid','resolution':'Preserve reported labels, fixed source-defined sample indices, report drift; no fitting/interpolation'},
  {'event':'openpyxl conditional formatting warning','status':'INSPECTED','reason':'Unsupported formatting extension, no data-value read failure','resolution':'Read original cell values only; no workbook saved or modified'}],
 'original_raw_log_sha256':rawlogs,
 'raw_hash_semantics':'Hashes above refer to original tmp files, not sanitized delivery copies. Final delivery hashes appear only in delivery-integrity.json.',
 'third_party_full_sources_in_delivery':False,'raw_wav_workbooks_in_delivery':False,'product_changes':False,'commit_or_push':False,
 'reported_time_grid':'Original MoSQITo returned time arrays retained; analysis maps source sample indices to physical 2ms grid per alignment-deviation.md',
 'table_a9_authority':'PENDING'}
(OUT/'execution-audit.json').write_text(json.dumps(audit,indent=2),encoding='utf8')
print('Metadata collected; MATLAB license path manually sanitized')
