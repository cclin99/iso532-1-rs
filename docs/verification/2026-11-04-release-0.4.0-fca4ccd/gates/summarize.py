import pathlib,json,re
OUT=pathlib.Path(__file__).resolve().parent;ROOT=OUT.parents[3];SRC=ROOT/'tmp/acceptance-040-astra/candidate'
r={'commands':json.loads((OUT/'command-results.json').read_text(encoding='utf8')),'python_commands':json.loads((OUT/'python-command-results.json').read_text(encoding='utf8')) if (OUT/'python-command-results.json').exists() else [],'tests':{},'hashes':{}}
for p in OUT.glob('*.log'):
 t=p.read_text(encoding='utf-8-sig');matches=re.findall(r'test result: (\w+)\. (\d+) passed; (\d+) failed; (\d+) ignored;',t)
 if matches and 'invalid' not in p.stem:r['tests'][p.stem]={'passed':sum(int(a[1]) for a in matches),'failed':sum(int(a[2]) for a in matches),'ignored':sum(int(a[3]) for a in matches),'binaries':len(matches)}
 if p.stem=='pytest':
  m=re.search(r'=+ ([\d]+) passed(?:,.*)? in ([\d.]+)s',t)
  if m:r['tests']['pytest']={'passed':int(m[1]),'failed':0,'xfailed':len(re.findall(r' XFAIL',t)),'seconds':float(m[2])}
source=(SRC/'iso532/tests/hash_gate.rs').read_text()
for os_name,log in [('windows','hash-dump.log'),('linux','linux.log')]:
 if not (OUT/log).exists():continue
 got={m[0]:{'n':m[1],'specific':m[2],'time':m[3]} for m in re.findall(r'^(scalar(?: mosqito_tail)?|avx2(?: mosqito_tail)?): n=0x([0-9a-f]+) spec=0x([0-9a-f]+) time=0x([0-9a-f]+)',(OUT/log).read_text(encoding='utf-8-sig'),re.M)}
 expected={}
 for const,nums in re.findall(r'#\[cfg\(target_os = "'+os_name+r'"\)\]\s*const (\w+): \(u64, u64, u64\) =\s*\(([^)]+)\)',source):
  label=const.removeprefix('EXPECTED_').lower().replace('_mosqito_tail',' mosqito_tail');vals=re.findall('0x([0-9a-f]+)',nums);expected[label]=dict(zip(['n','specific','time'],vals))
 r['hashes'][os_name]={'got':got,'expected':expected,'all_equal':got==expected}

if (OUT/'round1-hash.log').exists():
 t=(OUT/'round1-hash.log').read_text(encoding='utf8');got={m[0]:{'n':m[1],'specific':m[2],'time':m[3]} for m in re.findall(r'^(scalar(?: mosqito_tail)?|avx2(?: mosqito_tail)?): n=0x([0-9a-f]+) spec=0x([0-9a-f]+) time=0x([0-9a-f]+)',t,re.M)}
 source1=(ROOT/'tmp/acceptance-040-astra/round1/iso532/tests/hash_gate.rs').read_text();expected={}
 for const,nums in re.findall(r'#\[cfg\(target_os = "windows"\)\]\s*const (\w+): \(u64, u64, u64\) =\s*\(([^)]+)\)',source1):
  label=const.removeprefix('EXPECTED_').lower().replace('_mosqito_tail',' mosqito_tail');expected[label]=dict(zip(['n','specific','time'],re.findall('0x([0-9a-f]+)',nums)))
 r['round1_hashes']={'got':got,'expected':expected,'all_equal':got==expected,'status':'passed' if got==expected else 'pending' if not got else 'failed'}

if (OUT/'mosqito-measurements.json').exists():r['mosqito']=json.loads((OUT/'mosqito-measurements.json').read_text())
if 'mosqito' in r:
 h=r['mosqito']['python_contract_hashes'];smoke=(SRC/'iso532-py/tests/test_smoke.py').read_text();vals=re.search(r'"win32": \(0x([0-9A-F]+), 0x([0-9A-F]+)\)',smoke);time_expected=re.search(r'TIME_HASH = 0x([0-9A-F]+)',smoke).group(1).lower();r['python_hashes_equal']=all(h[k]['n']==vals.group(i).lower() and h[k]['time_axis']==time_expected for k,i in [('zero',1),('mosqito_tail',2)])
r['invalid_evidence']={'round1-shared-target-invalid.log':'Excluded: shared target reused candidate binary; replaced by isolated round1-hash-target rebuild.'}
r['ffi_extra']=json.loads((OUT/'ffi-extra-results.json').read_text()) if (OUT/'ffi-extra-results.json').exists() else []
r['final_extra']=json.loads((OUT/'final-extra-results.json').read_text()) if (OUT/'final-extra-results.json').exists() else []
r['header_regeneration']=json.loads((OUT/'header-regeneration.json').read_text()) if (OUT/'header-regeneration.json').exists() else {}
r['python_recovery']=json.loads((OUT/'python-recovery-results.json').read_text()) if (OUT/'python-recovery-results.json').exists() else []
r['linux_exit']=int((OUT/'linux-exit.txt').read_text(encoding='utf-8-sig')) if (OUT/'linux-exit.txt').exists() else None
r['environment_recovery']={'initial_pip_failure':'PIP_NO_INDEX=1 inherited; no distributions visible','recovery':'PIP_NO_INDEX=0; pinned packages installed into the same fresh venv; run_python.py builds and installs the candidate wheel','pytest_initial_failure':'MoSQITo undeclared matplotlib import caused collection error; installed matplotlib 3.11.2 and reran pytest without rebuild','docker_initial_failure':'npipe ACL denied; scoped escalation allowed isolated local Linux verification'}
r['final_status']={'required_gates':'passed' if r['tests'].get('workspace',{}).get('passed')==146 and r['tests'].get('pytest',{}).get('passed')==87 else 'pending','windows_hashes':'passed' if r['hashes'].get('windows',{}).get('all_equal') else 'failed','linux_hashes':'passed' if r['hashes'].get('linux',{}).get('all_equal') else 'failed','mosqito_compatibility':'passed' if all(x[k]['max_abs']<=5e-3 for x in r.get('mosqito',{}).get('comparisons',{}).values() for k in ['zwtv_n','zwst_n']) else 'failed','ffi_smoke':'passed' if any(x['name']=='c-smoke-explicit' and x['exit_code']==0 for x in r['final_extra']) else 'pending','header_semantics':'passed' if r['header_regeneration'].get('normalized_lf_equal') else 'failed'}
(OUT/'gates-results.json').write_text(json.dumps(r,indent=2),encoding='utf8')
print(json.dumps({'tests':r['tests'],'hashes':{k:v['all_equal'] for k,v in r['hashes'].items()},'linux_exit':r['linux_exit']},indent=2))

