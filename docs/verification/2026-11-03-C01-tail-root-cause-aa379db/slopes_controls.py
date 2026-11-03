"""Exploratory TOTAL-only C slope epsilon/table precision controls."""
import argparse, ast, ctypes as ct, datetime, difflib, hashlib, json, re, shutil, subprocess
from pathlib import Path
import numpy as np
p=Path(__file__).resolve().parent
ap=argparse.ArgumentParser();ap.add_argument('--work',type=Path,required=True);ap.add_argument('--vcvars',type=Path,required=True);a=ap.parse_args()
work=a.work.resolve();scratch=work/'slopes-controls';scratch.mkdir(exist_ok=False)
primary=json.loads((p/'results.json').read_text(encoding='utf8'))
def sha(f):return hashlib.sha256(Path(f).read_bytes()).hexdigest()
def ah(x):return hashlib.sha256(np.asarray(x,dtype='<f8').tobytes()).hexdigest()
def write(f,s):Path(f).write_text(s,encoding='utf8',newline='\n')
def js(f,x):write(f,json.dumps(x,indent=2,ensure_ascii=False,allow_nan=False)+'\n')
ns={'np':np};tree=ast.parse((p/'run_experiment.py').read_text(encoding='utf8'))
for name in ['val','metric']:
    fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name==name)
    exec(compile(ast.Module(body=[fn],type_ignores=[]),'same-metric','exec'),ns)
val,metric=ns['val'],ns['metric'];logs=[]
def run(cmd,cwd):
    z=subprocess.run(list(map(str,cmd)),cwd=cwd,capture_output=True,text=True,encoding='utf8',errors='replace')
    logs.append({'command':list(map(str,cmd)),'exit_code':z.returncode,'stdout':z.stdout,'stderr':z.stderr});js(p/'slopes-controls-log.json',logs);assert z.returncode==0,z.stdout+z.stderr
source=(work/'c/ISO_532-1.c').read_text(encoding='utf8');wrapper=(p/'stages.c.txt').read_text(encoding='utf8')
assert source.count('_ZUP    += .0001f;')==1
v1=source.replace('_ZUP    += .0001f;','_ZUP    += 0.0;')
start=v1.index('static double ZUP[]');end=v1.index('void f_corr_third_octave_intensities')
segment=v1[start:end];normalized,norm_count=re.subn(r'(?<=[0-9.])f\b','',segment)
v2=v1[:start]+normalized+v1[end:]
r={'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'addendum_sha256':{q.name:sha(q) for q in p.glob('slopes-addendum*.md')},
   'source_original_sha256':sha(work/'c/ISO_532-1.c'),'scope':'TOTAL ONLY; specific coverage deviations explicitly reported',
   'table_literal_suffixes_removed':norm_count,'grid_0_1f_unchanged':True,'variants':{},'signals':[]}
DP=ct.POINTER(ct.c_double)
def ptr(x):return x.ctypes.data_as(DP)
libs={}
for name,text in [('epsilon_zero',v1),('epsilon_zero_tables_double',v2)]:
    d=scratch/name;d.mkdir();write(d/'diagnostic.c',text);shutil.copyfile(work/'c/ISO_532-1.h',d/'ISO_532-1.h')
    write(d/'stages.c',wrapper.replace('#include "ISO_532-1.c"','#include "diagnostic.c"'))
    write(p/(name+'.diff.txt'),''.join(difflib.unified_diff(source.splitlines(True),text.splitlines(True),fromfile='ISO_532-1.c.original',tofile=name+'.diagnostic.c')))
    write(d/'build.cmd',f'@echo off\ncall "{a.vcvars.resolve()}"\nif errorlevel 1 exit /b %errorlevel%\ncl /nologo /O2 /fp:precise /LD /I. stages.c /link /OUT:stages.dll\nexit /b %errorlevel%\n')
    run(['cmd','/c',d/'build.cmd'],d);lib=ct.CDLL(str(d/'stages.dll'));lib.rc_slopes.argtypes=[DP,ct.c_int,DP,DP];libs[name]=lib
    r['variants'][name]={'source_sha256':sha(d/'diagnostic.c'),'wrapper_sha256':sha(d/'stages.c'),'binary_sha256':sha(d/'stages.dll'),'diff_file':name+'.diff.txt'}
exe=work/'probe/target/release/c01-root-probe.exe';assert sha(exe)==primary['binary_hashes']['c01-root-probe.exe']
for s in primary['signals']:
    sig=s['signal'];n=s['internal_frames'];K=s['K'];folder=work/f'signal-{sig}'
    nl=np.fromfile(folder/'R-pipeline/nl.bin',dtype='<f8').reshape(21,n)
    raw22=np.fromfile(folder/'R-pipeline/slope_raw22.bin',dtype='<f8')
    rust_tail=float(s['cell_counterfactual']['raw22_tail']['decimal17']);c_tail=float(s['ordered_decomposition'][2]['tail']['decimal17'])
    row={'signal':sig,'Rust_raw22_tail':val(rust_tail),'original_C_same_history_tail':val(c_tail),'original_raw22_minus_C_gap':rust_tail-c_tail,'variants':{}}
    for name,lib in libs.items():
        d=scratch/name/f'signal-{sig}';d.mkdir();total=np.zeros(n);spec=np.full((240,n),np.nan);ih=ah(nl)
        assert lib.rc_slopes(ptr(nl),n,ptr(total),ptr(spec))==0 and ih==ah(nl) and np.isfinite(total).all()
        bad=np.argwhere(~np.isfinite(spec));total.tofile(d/'input.bin');spec.tofile(d/'specific.bin')
        run([exe,'tw',d/'input.bin',d],d);tail=np.fromfile(d/'tw.bin',dtype='<f8')[K]
        row['variants'][name]={'tail':val(tail),'effect_vs_original_C_slopes':float(tail-c_tail),'remaining_Rust_raw22_minus_variant':float(rust_tail-tail),
            'remaining_within_1e_minus14':bool(abs(rust_tail-tail)<=1e-14),
            'total_history_Rust_raw22_minus_variant':metric(raw22[:K+1],total[:K+1]),
            'specific_coverage':{'elements':spec.size,'unwritten_nonfinite_count':len(bad),'first_unwritten_coordinate':None if not len(bad) else list(map(int,bad[0])),
                'not_a_specific_equivalence_claim':True},'raw_hashes':{f.name:sha(f) for f in d.glob('*.bin')}}
    r['signals'].append(row)
r['finished_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat();r['original_C_unchanged']=sha(work/'c/ISO_532-1.c')==r['source_original_sha256']
js(p/'slopes-controls.json',r)
primary['exploratory_slopes_controls']={'artifact':'slopes-controls.json','signals':r['signals']};js(p/'results.json',primary)
print(json.dumps([{'signal':s['signal'],'original_gap':s['original_raw22_minus_C_gap'],'variants':{k:{q:v[q] for q in ['effect_vs_original_C_slopes','remaining_Rust_raw22_minus_variant','specific_coverage']} for k,v in s['variants'].items()}} for s in r['signals']],indent=2))
