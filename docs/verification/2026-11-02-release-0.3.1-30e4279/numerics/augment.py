"""Run after run.py and hash-gate command, enrich numeric results."""
import argparse,json,re,struct,subprocess,os,hashlib
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--repo',type=Path,required=True);a=p.parse_args();repo=a.repo.resolve();out=Path(__file__).resolve().parent;work=repo/'tmp/acceptance-031';src=work/'source';tmp=work/'numerics-work';exe=work/'numerics-target-new/release/numeric_acceptance_new.exe'
r=json.loads((out/'results.json').read_text(encoding='utf-8'))
r['controls']=[c for c in r['controls'] if c['name'] not in ['bin_nan','bin_posinf','bin_neginf','bin_negative','bin_empty']]
import scipy
r['tools']['scipy']=scipy.__version__
r['annex_margin_input_hashes']={str(f.relative_to(src)):hashlib.sha256(f.read_bytes()).hexdigest() for f in [src/f'data/golden/annexb_sig{s}/sig.bin' for s in [3,5,10]]+[src/'data/golden/annexb_sig10/tv_nref.bin',src/'data/annexb/test_signal_3.csv',src/'data/annexb/test_signal_5.csv']}
r['available_wav_scope']='All seven WAV files available in data/annexb: three formal named Test signal 3/5/10 WAVs plus four auxiliary/synthetic WAV fixtures; not all 25 official Annex cases.'
r['annex_curve_points']=sum(c['points'] for c in r['margins'])
original=(src/'data/golden/annexb_sig10/tv_nref.bin').read_bytes()
for label,value in [('nan',float('nan')),('posinf',float('inf')),('neginf',-float('inf')),('negative',-1.)]:
 b=bytearray(original);b[8:16]=struct.pack('<d',value);f=tmp/(label+'-copy.bin');f.write_bytes(b)
 v=subprocess.run([str(exe),'bin',str(f)],capture_output=True,text=True);(out/(label+'-bin.log')).write_text(v.stdout+v.stderr,encoding='utf-8');r['controls'].append({'name':'bin_'+label,'passed':'Invalid' in v.stdout,'exit_code':v.returncode,'copy_sha256':hashlib.sha256(b).hexdigest()})
f=tmp/'empty-copy.bin';f.write_bytes(b'');v=subprocess.run([str(exe),'bin',str(f)],capture_output=True,text=True);(out/'empty-bin.log').write_text(v.stdout+v.stderr,encoding='utf-8');r['controls'].append({'name':'bin_empty','passed':'Invalid' in v.stdout,'exit_code':v.returncode})
t=(src/'iso532/tests/annexb.rs').read_text(encoding='utf-8');calls=re.findall(r'assert_annexb\((.*)',t)
r['annexb_call_site_audit']={'source_sha256':hashlib.sha256((src/'iso532/tests/annexb.rs').read_bytes()).hexdigest(),'call_count':len(calls)-1,'helper_calls_annexb_verdict': 'let verdict = annexb_verdict(got, reference);' in t,'helper_asserts_pass':'matches!(verdict, Verdict::Pass { .. })' in t,'calls':calls[1:],'review':'All five official reference comparisons route through assert_annexb and require Verdict::Pass. Additional MoSQITo/time checks do not replace these.'}
h=(src/'iso532/tests/hash_gate.rs').read_text(encoding='utf-8');log=(out/'hash-gate.log').read_text(encoding='utf-8-sig'); frozen={name:tuple(x.lower() for x in re.findall(r'0x[0-9a-f]+',val)) for name,val in re.findall(r'#\[cfg\(target_os = "windows"\)\]\s*const (\w+):.*?=\s*\((.*?)\);',h,re.S)}
labels={'scalar':'EXPECTED_SCALAR','scalar mosqito_tail':'EXPECTED_SCALAR_MOSQITO_TAIL','avx2':'EXPECTED_AVX2','avx2 mosqito_tail':'EXPECTED_AVX2_MOSQITO_TAIL'};comparisons=[]
for label,n,s,t in re.findall(r'^(scalar(?: mosqito_tail)?|avx2(?: mosqito_tail)?): n=(0x[0-9a-f]+) spec=(0x[0-9a-f]+) time=(0x[0-9a-f]+)',log,re.M):
 got=(n,s,t);expected=frozen[labels[label]];comparisons.append({'label':label,'actual':got,'expected':expected,'equal':got==expected,'fields':['n','n_specific','time_axis']})
r['hash_gate']={'command':'CARGO_BUILD_JOBS=2 HASH_GATE_DUMP_ONLY=1 REQUIRE_AVX2=1 cargo test --offline -p iso532 --test hash_gate -- --nocapture','comparisons':comparisons,'status':'passed' if len(comparisons)==4 and all(c['equal'] for c in comparisons) else 'failed','dump_test_passed':'test result: ok. 1 passed' in log,'note':'Dump-only exit zero is not acceptance; these comparisons separately check all frozen Windows constants.'}
r['validator_status']='passed' if all(c['passed'] for c in r['controls']) and all(c['passed'] for c in r['margins']) else 'failed'
r['corrupt_copy_control_count']=len(r['controls']);r['all_control_count']=r['direct_control_count']+len(r['controls'])
(out/'results.json').write_text(json.dumps(r,indent=2,ensure_ascii=False)+'\n',encoding='utf-8');print(json.dumps({'finite':r['finite_status'],'validator':r['validator_status'],'hash_gate':r['hash_gate'],'count':r['compared_f64_count'],'minimum_margin':r['minimum_margin']},indent=2))
