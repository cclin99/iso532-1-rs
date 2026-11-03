"""Reproduce without changing production sources. Windows MSVC + rustc + NumPy.

Run from repo root; --work must not exist. All binaries and preserved-source
copies stay there. --out is a NEW results JSON path. See report for provenance.
"""
from __future__ import annotations
import argparse, ast, difflib, hashlib, json, math, os, platform, re
import shutil, subprocess, sys, tarfile
from decimal import Decimal, localcontext
from fractions import Fraction as F
from pathlib import Path
import numpy as np

COMMIT = "aa379db8f3dc37f5048ac6c8b7a6d4ba2a6c3b76"
HERE = Path(__file__).resolve().parent
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p, s): Path(p).write_text(s.rstrip()+"\n", encoding="utf8", newline="\n")
def exact(x):
    with localcontext() as ctx:
        ctx.prec = 120
        return str(Decimal(x.numerator)/Decimal(x.denominator))
def run(cmd, cwd=None):
    p=subprocess.run(cmd,cwd=cwd,capture_output=True,text=True,encoding="utf8",errors="replace")
    log.append({"command":list(map(str,cmd)),"exit_code":p.returncode,"stdout":p.stdout,"stderr":p.stderr})
    if p.returncode: raise RuntimeError(p.stdout+p.stderr)
    return p.stdout
def patch_once(text,old,new):
    assert text.count(old)==1, (old,text.count(old))
    return text.replace(old,new)
def diff(a,b,name):
    return ''.join(difflib.unified_diff(a.splitlines(True),b.splitlines(True),fromfile=name+".original",tofile=name+".derived"))

ap=argparse.ArgumentParser()
ap.add_argument('--repo',type=Path,default=Path.cwd())
ap.add_argument('--work',type=Path,required=True)
ap.add_argument('--out',type=Path,required=True)
ap.add_argument('--official-c',type=Path,required=True)
ap.add_argument('--official-header',type=Path,required=True)
ap.add_argument('--mosqito-source',type=Path,required=True)
ap.add_argument('--vcvars',type=Path,required=True)
args=ap.parse_args(); repo=args.repo.resolve(); work=args.work.resolve()
assert not args.out.exists(); work.mkdir(parents=True,exist_ok=False)
log=[]; results={"tested_commit":COMMIT,"scope":"synthetic local arithmetic and isolated slope stage; not ISO acceptance"}
results['environment']={"python":platform.python_version(),"numpy":np.__version__,"platform":platform.platform()}
archive=work/'snapshot.tar'
run(['git','archive','--format=tar',f'--output={archive}',COMMIT,'iso532/src/tables.rs','iso532/src/core/calc_slopes.rs'],repo)
with tarfile.open(archive) as tar: tar.extractall(work/'snapshot',filter='data')
tables_path=work/'snapshot/iso532/src/tables.rs'; slopes_path=work/'snapshot/iso532/src/core/calc_slopes.rs'
original_c=args.official_c.read_text(encoding='utf8')
assert sha(args.official_c)=='a74b45ed297cd09ac60701a923120341137d227e536f3109ae4ece810d834491'
tables=tables_path.read_text(encoding='utf8'); slopes=slopes_path.read_text(encoding='utf8')
py_source=args.mosqito_source.read_text(encoding='utf8')
results['source_hashes']={"git_archive":sha(archive),"Rust_tables":sha(tables_path),"Rust_slopes":sha(slopes_path),"preserved_official_C":sha(args.official_c),"official_header":sha(args.official_header),"local_MoSQITo_slopes":sha(args.mosqito_source)}
results['source_locations']={"Rust_tables":"iso532/src/tables.rs:86","Rust_lookup":"iso532/src/core/calc_slopes.rs:207","C_table":"ISO_532-1.c:710","C_lookup":"ISO_532-1.c:869","MoSQITo_table":"mosqito-1.2.1/mosqito/sq_metrics/loudness/loudness_zwst/_calc_slopes.py:80"}
tree=ast.parse(py_source)
usl_node=next(n.value.args[0] for n in ast.walk(tree) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='usl' for t in n.targets))
py_table=ast.literal_eval(usl_node)
c_body=re.search(r'static double USL\[.*?=\s*\{(.*?)\n\};',original_c,re.S).group(1)
c_rows=[[float(v.strip().rstrip('f')) for v in row.split(',')] for row in re.findall(r'\{([^{}]+)\}',c_body)]
rust_body=tables.split('pub const USL:')[1].split('= [',1)[1].split('\n];',1)[0]
rust_rows=ast.literal_eval('['+rust_body+']')
assert np.array(py_table).shape==np.array(c_rows).shape==np.array(rust_rows).shape==(18,8)
results['source_tables']={"C":{"type":"double[18][8], float-suffixed literals","row12":c_rows[12]},"Python":{"type":str(np.array(py_table).dtype),"row12":py_table[12]},"Rust":{"type":"[[f64;8];18]","row12":rust_rows[12]},"target": [12,4],"C_literal":0.22,"Python_literal":0.24,"Rust_literal":0.24}

# Preserved C copy with counting only; the wrapper changes the target at runtime.
c_derived=patch_once(original_c,'void f_calc_slopes( double **CoreLoudness,','static int target_reads = 0;\nvoid f_calc_slopes( double **CoreLoudness,')
c_derived=patch_once(c_derived,'_USL    = USL[IdxRNS][IdxCBN];','_USL    = USL[IdxRNS][IdxCBN];\n                if (IdxRNS == 12 && IdxCBN == 4) target_reads++;')
write(work/'official_instrumented.c',c_derived)
shutil.copyfile(args.official_header,work/args.official_header.name)
write(work/'C-derived.diff',diff(original_c,c_derived,'ISO_532-1.c'))
write(work/'stage.c',r'''#include <stdio.h>
#include "official_instrumented.c"
int main(void) {
    int variant,band,j;
    for(variant=0;variant<2;variant++) for(band=3;band<=4;band++) {
        double nm[21][3]={{0}}, spec[240][3]={{0}}, total[3]={12345,0,12345};
        double *np[21], *sp[240];
        for(j=0;j<21;j++){ nm[j][0]=nm[j][2]=12345; np[j]=&nm[j][1]; }
        for(j=0;j<240;j++){ spec[j][0]=spec[j][2]=12345; sp[j]=&spec[j][1]; }
        nm[band][1]=0.35; target_reads=0;
        USL[12][4]=variant ? (double)0.24f : (double)0.22f;
        f_calc_slopes(np,&total[1],sp,0);
        for(j=0;j<21;j++) if(nm[j][0]!=12345 || nm[j][2]!=12345) return 3;
        for(j=0;j<240;j++) if(spec[j][0]!=12345 || spec[j][2]!=12345) return 4;
        if(total[0]!=12345 || total[2]!=12345) return 5;
        printf("{\"coefficient\":%.2f,\"band\":%d,\"target_reads\":%d,\"total\":%.17g,\"guards\":true,\"specific\":[",variant ? .24:.22,band,target_reads,total[1]);
        for(j=0;j<240;j++) printf("%s%.17g",j?",":"",spec[j][1]);
        printf("]}\n");
    }
    return 0;
}''')
shutil.copyfile(HERE/'numeric.c',work/'numeric.c')
write(work/'build.cmd',f'@echo off\ncall "{args.vcvars.resolve()}"\nif errorlevel 1 exit /b %errorlevel%\ncl /nologo /O2 /fp:strict numeric.c /Fe:numeric.exe\nif errorlevel 1 exit /b %errorlevel%\ncl /nologo /O2 /fp:strict stage.c /Fe:stage.exe\nexit /b %errorlevel%')
run(['cmd','/c',str(work/'build.cmd')],work)
write(work/'version.cmd',f'@echo off\ncall "{args.vcvars.resolve()}" >nul\ncl /Bv\nexit /b %errorlevel%')
version_probe=subprocess.run(['cmd','/c',str(work/'version.cmd')],cwd=work,capture_output=True,text=True,encoding='utf8',errors='replace')
assert version_probe.returncode in [0,2] # cl without an input may report D8003.
log.append({'command':['cmd','/c',str(work/'version.cmd')],'exit_code':version_probe.returncode,'stdout':version_probe.stdout,'stderr':version_probe.stderr,'purpose':'read-only compiler version probe; no source supplied, exit 2 expected'})
results['environment']['MSVC_version_probe']={'exit_code':version_probe.returncode,'text':version_probe.stdout+version_probe.stderr}

# Independent exact fixtures: all decimal inputs are finite exact rationals.
fixtures=[('primary','0.35','0.2'),('inner_low','0.32','0.05'),('inner_high','0.40','0.3'),('inner_short','0.375','0.125')]
records=[]; oracle=[]; c_layout=[]
for name,nn,dd in fixtures:
    n,d=F(nn),F(dd)
    for ss in ['0.22','0.24']:
        s=F(ss); p=n-s*d; area=n*d-s*d*d/2
        assert F('.30')<=p<=n<F('.42')
        decimal_outputs=[]
        for precision in [80,120]:
            with localcontext() as ctx:
                ctx.prec=precision; dn,ds,ddz=Decimal(nn),Decimal(ss),Decimal(dd)
                dp=dn-ds*ddz; da=dn*ddz-ds*ddz*ddz/2
                assert F(dp)==p and F(da)==area
                decimal_outputs.append({"precision":precision,"point":str(dp),"area":str(da)})
        oracle.append({"fixture":name,"n0":nn,"dz":dd,"coefficient":ss,"point_fraction":str(p),"area_fraction":str(area),"point":exact(p),"area":exact(area),"decimal":decimal_outputs})
        outputs=[json.loads(line) for line in run([str(work/'numeric.exe'),nn,dd,str(int(s*100))],work).splitlines()]
        c_layout.append(outputs.pop())
        for mode,typ in [('Python_float',float),('NumPy_float32',np.float32),('NumPy_float64',np.float64)]:
            tn,ts,td=typ(nn),typ(ss),typ(dd)
            outputs.append({"mode":mode,"s":float(ts),"point":float(tn-ts*td),"area":float(tn*td-ts*td*td/typ(2))})
        for row in outputs:
            row.update(fixture=name,coefficient=ss)
            for key,ref in [('point',p),('area',area),('s',s)]:
                err=abs(F.from_float(row[key])-ref)
                row[key+'_abs_error']=float(err); row[key+'_error_exact']=str(err)
                value=row[key]
                spacing=float(np.spacing(np.float32(value))) if 'binary32' in row['mode'] or 'float32' in row['mode'] else math.ulp(value)
                row[key+'_ulp']=spacing; row[key+'_error_ulps']=float(err)/spacing
            records.append(row)
assert len(records)==4*2*6
results['oracle']=oracle; results['arithmetic']=records
primary=[r for r in records if r['fixture']=='primary']
max_error=max(r['point_abs_error'] for r in primary)
results['primary_summary']={"point_effect_exact":exact(F('.004')),"area_effect_exact":exact(F('.0004')),"coefficient_effect_exact":"0.02","max_point_roundoff":max_error,"point_effect_over_max_roundoff":.004/max_error,"max_area_roundoff":max(r['area_abs_error'] for r in primary),"max_all_fixture_point_roundoff":max(r['point_abs_error'] for r in records)}
target=F('.35')-F('.22')*F('.2')
needed_d=(F('.35')-target)/F('.24')
needed_n=target+F('.24')*F('.2')
assert F('.35')-F('.24')*needed_d==target==needed_n-F('.24')*F('.2')
results['compensation_scale']={"purpose":"post-design exact mechanism diagnostic, not historical intent evidence","target_point":exact(target),"if_s24_needed_dz_fraction":str(needed_d),"dz_change_fraction":str(needed_d-F('.2')),"dz_relative_change_fraction":str((needed_d-F('.2'))/F('.2')),"if_s24_needed_n0":exact(needed_n),"n0_change":exact(needed_n-F('.35')),"n0_relative_change_fraction":str((needed_n-F('.35'))/F('.35'))}
# Decision criterion set before results: coefficient effect must exceed every
# sampled point roundoff by >1000, not merely by a marginal tolerance.
assert .004/max_error>1000
for fixture,_,_ in fixtures:
    for coeff in ['0.22','0.24']:
        rows={r['mode']:r for r in records if r['fixture']==fixture and r['coefficient']==coeff}
        for key in ['point','area']:
            assert rows['C_binary64'][key]==rows['Python_float'][key]==rows['NumPy_float64'][key]
            assert rows['C_binary32'][key]==rows['NumPy_float32'][key]

tagged=np.array([[100*r+c for c in range(8)] for r in range(18)])
layout={"expected_tag":1204,"negative_controls":{},"coefficient_variants":[]}
for ss in ['0.22','0.24']:
    nested=[row[:] for row in c_rows]; nested[12][4]=float(ss)
    c_order=np.array(nested,order='C'); f_order=np.array(nested,order='F')
    got=[nested[12][4],c_order[12,4],f_order[12,4],c_order.ravel(order='C')[12*8+4],f_order.ravel(order='F')[4*18+12]]
    assert all(x==float(ss) for x in got)
    assert tagged[12,4]==tagged.ravel(order='C')[100]==np.array(tagged,order='F').ravel(order='F')[84]==1204
    layout['coefficient_variants'].append({"s":ss,"readbacks":list(map(float,got))})
for name,value in [('wrong_row',tagged[11,4]),('wrong_column',tagged[12,3]),('wrong_stride',tagged.ravel(order='F')[12*8+4])]:
    assert value!=1204
    layout['negative_controls'][name]={"observed":int(value),"detected":True}
assert all(r['tagged']==1204 and r['matrix']==r['flat'] and r['wrong_row']!=1204 and r['wrong_col']!=1204 and r['float_mant_dig']==24 and r['double_mant_dig']==53 for r in c_layout)
layout['C_records']=c_layout
results['layout']=layout

# Range selection near boundaries is a separate diagnostic, not error in the
# unbranched local formula. Count corresponds to current implementations.
rns=[21.5,18,15.1,11.5,9,6.1,4.4,3.1,2.13,1.36,.82,.42,.30,.22,.15,.10,.035,0]
boundaries=[]
for bound in [.30,.42]:
    for name,value in [('below',math.nextafter(bound,-math.inf)),('at',bound),('above',math.nextafter(bound,math.inf))]:
        raw=min(17,sum(value<r for r in rns))
        c_initial=min(17,sum(float(np.float32(r))>=value for r in rns))
        r8=lambda x: math.floor(x*1e8+.5)/1e8
        rust_initial=min(17,sum(r8(value)<r8(r) for r in rns))
        rust_next=min(17,sum(r8(value)<=r8(r) for r in rns))
        boundaries.append({"bound":bound,"case":name,"value_hex":value.hex(),"value":value,"raw_lt_index":raw,"C_initial_ge_index":c_initial,"Rust_initial_r8_lt_index":rust_initial,"Rust_next_r8_le_index":rust_next})
results['boundaries']=boundaries
results['stage_C']=[json.loads(line) for line in run([str(work/'stage.exe')],work).splitlines()]

# rustc directly compiles the archived std-only slope/table modules.
rust_slopes=patch_once(slopes,'    USL[rns_idx][band_idx.min(7)]','    if rns_idx == 12 && band_idx.min(7) == 4 { crate::READS.fetch_add(1, std::sync::atomic::Ordering::Relaxed); }\n    USL[rns_idx][band_idx.min(7)]')
write(work/'Rust-derived.diff',diff(slopes,rust_slopes,'calc_slopes.rs'))
write(work/'slopes.rs',rust_slopes)
write(work/'rust_main.rs',r'''mod tables; mod slopes;
static READS: std::sync::atomic::AtomicUsize = std::sync::atomic::AtomicUsize::new(0);
fn main() {
    for band in [3usize,4usize] {
        let mut nm=[0.0;21]; nm[band]=0.35;
        READS.store(0,std::sync::atomic::Ordering::Relaxed);
        let (n,s)=slopes::calc_slopes(&nm);
        println!("{{\"band\":{},\"target_reads\":{},\"total\":{:?},\"specific\":{:?}}}",band,READS.load(std::sync::atomic::Ordering::Relaxed),n,s);
    }
}''')
rust_versions=[]
old='[0.40, 0.33, 0.26, 0.24, 0.24, 0.22, 0.22, 0.22]'
new='[0.40, 0.33, 0.26, 0.24, 0.22, 0.22, 0.22, 0.22]'
for ss in ['0.22','0.24']:
    variant=patch_once(tables,old,new) if ss=='0.22' else tables
    write(work/'tables.rs',variant)
    write(work/f'tables-{ss}.rs',variant)
    if ss=='0.22': write(work/'Rust-table22.diff',diff(tables,variant,'tables.rs'))
    exe=work/f'rust-stage-{ss}.exe'
    run(['rustc','--edition=2021','-O','-A','dead_code','rust_main.rs','-o',str(exe)],work)
    for line in run([str(exe)],work).splitlines():
        row=json.loads(line); row['coefficient']=float(ss);rust_versions.append(row)
results['environment']['rustc']=run(['rustc','--version']).strip()
results['stage_Rust']=rust_versions
comparisons={}
for lang,key in [('C','stage_C'),('Rust','stage_Rust')]:
    data=results[key]
    for band in [3,4]:
        a,b=[r for r in data if r['band']==band]
        assert a['coefficient']==.22 and b['coefficient']==.24
        assert all(math.isfinite(v) for row in [a,b] for v in row['specific'])
        delta=max(abs(x-y) for x,y in zip(a['specific'],b['specific']))
        if band==3: assert delta==0 and a['total']==b['total']
        if band==4: assert delta>0 and a['target_reads']>0 and b['target_reads']>0
        comparisons[f'{lang}_band{band}']={"delta_specific_max":delta,"delta_total":abs(a['total']-b['total']),"reads22":a['target_reads'],"reads24":b['target_reads']}
results['stage_comparisons']=comparisons
# Actual saved MoSQITo stage, isolated from package import side effects. The
# helper's source is executed unchanged; only its package import is removed.
helper_path=args.mosqito_source.with_name('_get_rns_index.py')
helper_source=helper_path.read_text(encoding='utf8')
results['source_hashes']['local_MoSQITo_get_rns_index']=sha(helper_path)
write(work/'_get_rns_index.py',helper_source)
python_stages=[]
package_import='from mosqito.sq_metrics.loudness.loudness_zwst._get_rns_index import _get_rns_index'
for ss in ['0.22','0.24']:
    py_variant=patch_once(py_source,package_import,'# _get_rns_index supplied from the isolated unchanged helper source.')
    if ss=='0.22':
        py_variant=patch_once(py_variant,'(0.40, 0.33, 0.26, 0.24, 0.24, 0.22, 0.22, 0.22)','(0.40, 0.33, 0.26, 0.24, 0.22, 0.22, 0.22, 0.22)')
    write(work/f'python-stage-{ss}.py',py_variant)
    write(work/f'Python-{ss}.diff',diff(py_source,py_variant,'_calc_slopes.py'))
    namespace={}
    exec(compile(helper_source,'isolated_get_rns_index.py','exec'),namespace)
    exec(compile(py_variant,f'isolated_slopes_{ss}.py','exec'),namespace)
    for band in [3,4]:
        nm=np.zeros((21,1));nm[band,0]=.35
        total,specific=namespace['_calc_slopes'](nm)
        assert total.shape==(1,) and specific.shape==(240,1)
        assert np.isfinite(total).all() and np.isfinite(specific).all()
        python_stages.append({'coefficient':float(ss),'band':band,'total':float(total[0]),'specific':specific[:,0].tolist(),'target_reads':None,'note':'actual saved MoSQITo code; no lookup-count instrumentation'})
results['stage_Python']=python_stages
for band in [3,4]:
    a,b=[r for r in python_stages if r['band']==band]
    delta=max(abs(x-y) for x,y in zip(a['specific'],b['specific']))
    if band==3: assert delta==0 and a['total']==b['total']
    if band==4: assert delta>0
    comparisons[f'Python_band{band}']={'delta_specific_max':delta,'delta_total':abs(a['total']-b['total']),'reads22':None,'reads24':None}
results['gates_python_stage']='passed; actual saved stage, two coefficients and band3 negative control, no lookup-count claim'
results['identifiability']={"knowns":["N0","dz"],"unknowns":["s","point","area"],"equations":2,"independent_point_observation":None,"candidate_solutions":[r for r in oracle if r['fixture']=='primary'],"conclusion":"both candidates satisfy their conditional equations exactly; no unique s without independent target/constraint"}
results['gates']={"exact_oracle_fraction_decimal":"passed","full_factorial_48_results":"passed","same_coefficient_language_parity":"passed","layout_positive_and_negative_controls":"passed","boundary_diagnostic":"passed","isolated_C_and_Rust_stage_target_activation":"passed","historical_intent":"inconclusive","authorized_standard_cell":"pending","product_acceptance":"not_run"}
results['gates']['actual_isolated_MoSQITo_stage']='passed'
results['hypotheses']={"H_fp":{"verdict":"not_supported","scope":"four safe local fixtures, tested arithmetic modes only"},"H_layout":{"verdict":"not_supported","scope":"tested correct logical-index mappings only; source literals demonstrably differ"},"H_intent":{"verdict":"inconclusive"},"H_standard":{"verdict":"inconclusive","reason":"no independent identifying target or authorized standard cell"}}
results['derived_hashes']={p.name:sha(p) for p in sorted(work.iterdir()) if p.is_file() and p.suffix in ['.c','.h','.rs','.py','.exe','.diff']}
write(args.out,json.dumps(results,indent=2,ensure_ascii=False))
write(args.out.with_suffix('.run.json'),json.dumps(log,indent=2,ensure_ascii=False))
print(json.dumps(results['primary_summary'],indent=2))
print(json.dumps(results['stage_comparisons'],indent=2))
print('All scoped assertions passed; authority and intent remain unresolved.')
