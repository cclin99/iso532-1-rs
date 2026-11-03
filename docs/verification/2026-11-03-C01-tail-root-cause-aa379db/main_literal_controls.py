"""Exploratory minimal main-literal controls, after frozen primary experiment."""
import argparse, ast, ctypes as ct, datetime, difflib, hashlib, json, shutil, subprocess
from pathlib import Path
import numpy as np
p=Path(__file__).resolve().parent
ap=argparse.ArgumentParser();ap.add_argument('--work',type=Path,required=True);ap.add_argument('--vcvars',type=Path,required=True);a=ap.parse_args()
work=a.work.resolve();scratch=work/'main-literal-controls';scratch.mkdir(exist_ok=False)
primary=json.loads((p/'results.json').read_text(encoding='utf8'));shutil.copyfile(p/'results.json',p/'primary-results.json')
def sha(f):return hashlib.sha256(Path(f).read_bytes()).hexdigest()
def ah(x):return hashlib.sha256(np.asarray(x,dtype='<f8').tobytes()).hexdigest()
def write(f,s):Path(f).write_text(s,encoding='utf8',newline='\n')
def js(f,x):write(f,json.dumps(x,indent=2,ensure_ascii=False,allow_nan=False)+'\n')
ns={'np':np}
tree=ast.parse((p/'run_experiment.py').read_text(encoding='utf8'))
for name in ['val','metric']:
    fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name==name)
    exec(compile(ast.Module(body=[fn],type_ignores=[]),'same-metric','exec'),ns)
val,metric=ns['val'],ns['metric']
logs=[]
def run(cmd,cwd):
    z=subprocess.run(list(map(str,cmd)),cwd=cwd,capture_output=True,text=True,encoding='utf8',errors='replace')
    logs.append({'command':list(map(str,cmd)),'exit_code':z.returncode,'stdout':z.stdout,'stderr':z.stderr})
    js(p/'main-literal-log.json',logs);assert z.returncode==0,z.stderr+z.stdout
source=(work/'c/ISO_532-1.c').read_text(encoding='utf8');wrapper=(p/'stages.c.txt').read_text(encoding='utf8')
assert source.count('MP1 = .0635f *')==1 and source.count('CorrCL = 0.4f + 0.32f *')==1
v1=source.replace('MP1 = .0635f *','MP1 = .0635 *');v2=v1.replace('CorrCL = 0.4f + 0.32f *','CorrCL = 0.4 + 0.32 *')
r={'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'primary_results_sha256_before_redaction':sha(p/'primary-results.json'),
   'addendum_sha256':{q.name:sha(q) for q in p.glob('exploratory-addendum*.md')},'source_original_sha256':sha(work/'c/ISO_532-1.c'),
   'scope':'Exploratory only: MP1 binary32 literal, then additional low-band correction binary32 literals. No normative change.',
   'literals':{s:{'C_binary32_promoted':val(float(np.float32(float(s)))),'Rust_binary64':val(float(s))} for s in ['0.0635','0.4','0.32']},'variants':{},'signals':[]}
DP=ct.POINTER(ct.c_double)
def ptr(x):return x.ctypes.data_as(DP)
def load(path):
    lib=ct.CDLL(str(path))
    for name in ['rc_main','rc_nl','rc_tw']:getattr(lib,name).argtypes=[DP,ct.c_int,DP]
    lib.rc_slopes.argtypes=[DP,ct.c_int,DP,DP]
    return lib
libs={};base=load(work/'c/stages.dll')
for name,text in [('mp1_double',v1),('mp1_and_correction_double',v2)]:
    d=scratch/name;d.mkdir();write(d/'diagnostic.c',text);shutil.copyfile(work/'c/ISO_532-1.h',d/'ISO_532-1.h')
    write(d/'stages.c',wrapper.replace('#include "ISO_532-1.c"','#include "diagnostic.c"'))
    write(p/(name+'.diff.txt'),''.join(difflib.unified_diff(source.splitlines(True),text.splitlines(True),fromfile='ISO_532-1.c.original',tofile=name+'.diagnostic.c')))
    write(d/'build.cmd',f'@echo off\ncall "{a.vcvars.resolve()}"\nif errorlevel 1 exit /b %errorlevel%\ncl /nologo /O2 /fp:precise /LD /I. stages.c /link /OUT:stages.dll\nexit /b %errorlevel%\n')
    run(['cmd','/c',d/'build.cmd'],d);libs[name]=load(d/'stages.dll')
    r['variants'][name]={'diagnostic_source_sha256':sha(d/'diagnostic.c'),'wrapper_sha256':sha(d/'stages.c'),'binary_sha256':sha(d/'stages.dll'),'diff_file':name+'.diff.txt'}
exe=work/'probe/target/release/c01-root-probe.exe';assert sha(exe)==primary['binary_hashes']['c01-root-probe.exe']
for s in primary['signals']:
    sig=s['signal'];n=s['internal_frames'];K=s['K'];folder=work/f'signal-{sig}'
    tol=np.fromfile(folder/'R-pipeline/tol.bin',dtype='<f8').reshape(28,n)
    rcore=np.fromfile(folder/'R-pipeline/core.bin',dtype='<f8').reshape(21,n)
    ccore=np.fromfile(folder/'C-core-on-Rtol.bin',dtype='<f8').reshape(21,n)
    T3=float(s['ordered_decomposition'][3]['tail']['decimal17']);T4=float(s['ordered_decomposition'][4]['tail']['decimal17']);gap=T3-T4
    row={'signal':sig,'original_main_gap_R_minus_C':gap,'variants':{}}
    for name,lib in libs.items():
        d=scratch/name/f'signal-{sig}';d.mkdir();core=np.full((21,n),np.nan);ih=ah(tol)
        assert lib.rc_main(ptr(tol),n,ptr(core))==0 and ih==ah(tol) and np.isfinite(core).all()
        nl=np.full_like(core,np.nan);assert base.rc_nl(ptr(core),n,ptr(nl))==0
        total=np.zeros(n);spec=np.zeros((240,n));assert base.rc_slopes(ptr(nl),n,ptr(total),ptr(spec))==0
        total.tofile(d/'input.bin');core.tofile(d/'core.bin');nl.tofile(d/'nl.bin')
        run([exe,'tw',d/'input.bin',d],d);tail=np.fromfile(d/'tw.bin',dtype='<f8')[K]
        row['variants'][name]={'tail':val(tail),'effect_vs_original_C_main':float(tail-T4),
            'fraction_of_original_main_gap':float((tail-T4)/gap),'remaining_R_main_minus_variant':float(T3-tail),
            'remaining_within_1e_minus14':bool(abs(T3-tail)<=1e-14),
            'core_R_minus_variant':metric(rcore[:,:K+1].copy(),core[:,:K+1].copy()),
            'core_variant_minus_original_C':metric(core[:,:K+1].copy(),ccore[:,:K+1].copy()),
            'raw_hashes':{f.name:sha(f) for f in d.glob('*.bin')}}
    r['signals'].append(row)
r['finished_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat();r['original_C_unchanged']=sha(work/'c/ISO_532-1.c')==r['source_original_sha256']
js(p/'main-literal-controls.json',r)
primary['exploratory_main_literal_controls']={'artifact':'main-literal-controls.json','primary_before_append':'primary-results.json','signals':r['signals']}
js(p/'results.json',primary)
print(json.dumps([{'signal':s['signal'],'original_main_gap':s['original_main_gap_R_minus_C'],
 'variants':{k:{q:v[q] for q in ['effect_vs_original_C_main','fraction_of_original_main_gap','remaining_R_main_minus_variant']} for k,v in s['variants'].items()}} for s in r['signals']],indent=2))
