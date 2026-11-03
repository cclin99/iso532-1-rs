"""Frozen-snapshot C-01 root-cause experiment; only new scratch and this delivery.
Requires Windows MSVC, Rust and NumPy. CLI arguments identify preserved materials.
"""
from __future__ import annotations
import argparse, ctypes as ct, csv, datetime, difflib, hashlib, json, platform, shutil, subprocess, sys, tarfile
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent
COMMIT='aa379db8f3dc37f5048ac6c8b7a6d4ba2a6c3b76'
CSHA='a74b45ed297cd09ac60701a923120341137d227e536f3109ae4ece810d834491'
DP=ct.POINTER(ct.c_double)
def ptr(x):return x.ctypes.data_as(DP)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def ah(x):return hashlib.sha256(np.asarray(x,dtype='<f8').tobytes()).hexdigest()
def write(p,s):Path(p).write_text(s,encoding='utf8',newline='\n')
def js(p,x):write(p,json.dumps(x,indent=2,ensure_ascii=False,allow_nan=False)+'\n')
def val(x):return {'decimal17':format(float(x),'.17g'),'bits':format(np.float64(x).view('u8').item(),'016x')}
def bits(x,y):return x.shape==y.shape and bool(np.array_equal(x.view('u8'),y.view('u8')))
def metric(a,b):
    if a.shape!=b.shape:raise ValueError('shape mismatch')
    if not np.isfinite(a).all() or not np.isfinite(b).all():raise ValueError('nonfinite')
    delta=a-b;ab=np.abs(delta);bad=a.view('u8')!=b.view('u8');large=ab>1e-14
    def first(mask):
        ix=np.argwhere(mask)
        if not len(ix):return None
        # Chronological first: time is the last axis, then band index.
        if mask.ndim==2:ix=ix[np.lexsort((ix[:,0],ix[:,1]))]
        return list(map(int,ix[0]))
    worst=list(map(int,np.unravel_index(np.argmax(ab),ab.shape)))
    coords={'first_bitwise':first(bad),'first_above_1e_minus14':first(large),'worst':worst}
    if a.ndim==1:target=[a.shape[-1]-1]
    else:target=[int(np.argmax(ab[:,-1])),a.shape[-1]-1]
    coords['target_worst']=target
    samples={k:{'coordinate':c,'left':val(a[tuple(c)]),'right':val(b[tuple(c)]),'signed_diff':float(delta[tuple(c)]),'abs_diff':float(ab[tuple(c)])} for k,c in coords.items() if c is not None}
    return {'shape':list(a.shape),'finite':True,'compared_count':a.size,'bitwise_mismatches':int(bad.sum()),
            'above_1e_minus14':int(large.sum()),'max_abs_diff':float(ab.max()),'target_max_abs_diff':float(ab[...,-1].max()),'samples':samples}

ap=argparse.ArgumentParser();ap.add_argument('--repo',type=Path,default=Path.cwd());ap.add_argument('--work',type=Path,required=True)
ap.add_argument('--prior-work',type=Path,required=True);ap.add_argument('--prior-results',type=Path,required=True)
ap.add_argument('--official',type=Path,required=True);ap.add_argument('--archive',type=Path,required=True);ap.add_argument('--vcvars',type=Path,required=True)
a=ap.parse_args();repo=a.repo.resolve();work=a.work.resolve();prior=a.prior_work.resolve();official=a.official.resolve()
assert not (HERE/'results.json').exists();work.mkdir(parents=True,exist_ok=False)
log=[];r={'tested_commit':COMMIT,'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
 'design_sha256':{p.name:sha(p) for p in HERE.glob('experiment-design*.md')},
 'environment':{'python':sys.version,'numpy':np.__version__,'platform':platform.platform()},'signals':[],
 'encoding':'all .bin arrays little-endian binary64; multiband arrays row-major [band,time]'}
js(HERE/'run-start.json',{k:r[k] for k in ['tested_commit','started_utc','design_sha256']})
def run(cmd,cwd=None,check=True):
    p=subprocess.run(list(map(str,cmd)),cwd=cwd or work,capture_output=True,text=True,encoding='utf8',errors='replace')
    log.append({'command':list(map(str,cmd)),'cwd':str(cwd or work),'exit_code':p.returncode,'stdout':p.stdout,'stderr':p.stderr})
    js(HERE/'run-log.json',log)
    if check and p.returncode:raise RuntimeError(p.stdout+p.stderr)
    return p
try:
    old=json.loads(a.prior_results.read_text(encoding='utf8'));assert old['tested_commit']==COMMIT
    r['prior_evidence']={'results_sha256':sha(a.prior_results),'role':'Frozen inputs and old expected baseline bits; all new results recomputed.'}
    r['worktree_before']=run(['git','status','--short'],repo).stdout
    archive=work/'source.tar';run(['git','archive','--format=tar',f'--output={archive}',COMMIT,'Cargo.toml','Cargo.lock','iso532','iso532-ffi','iso532-py'],repo)
    with tarfile.open(archive) as t:t.extractall(work/'snapshot',filter='data')
    snap=work/'snapshot';before={str(p.relative_to(snap)).replace('\\','/'):sha(p) for p in sorted(snap.rglob('*')) if p.is_file()}
    r['source']={'archive_sha256':sha(archive),'snapshot_before':before,'official_archive_sha256':sha(a.archive)}
    assert sha(a.archive)==old['source_hashes']['official_archive_sha256']
    cdir=work/'c';cdir.mkdir();csrc=official/'Annex A.4/ISO_532-1_LIB/src/ISO_532-1.c';header=official/'Annex A.4/ISO_532-1_LIB/include/ISO_532-1.h'
    assert sha(csrc)==CSHA
    for src in [csrc,header]:shutil.copyfile(src,cdir/src.name)
    shutil.copyfile(HERE/'stages.c.txt',cdir/'stages.c')
    write(cdir/'build.cmd',f'@echo off\ncall "{a.vcvars.resolve()}"\nif errorlevel 1 exit /b %errorlevel%\ncl /nologo /O2 /fp:precise /LD /I. stages.c /link /OUT:stages.dll\nexit /b %errorlevel%\n')
    shutil.copyfile(cdir/'build.cmd',HERE/'build-c.cmd.txt');run(['cmd','/c',cdir/'build.cmd'],cdir)
    write(cdir/'version.cmd',f'@echo off\ncall "{a.vcvars.resolve()}" >nul\ncl /Bv\nexit /b %errorlevel%\n')
    v=run(['cmd','/c',cdir/'version.cmd'],cdir,False);assert v.returncode in [0,2]
    r['environment']['MSVC']={'stdout':v.stdout,'stderr':v.stderr,'exit_code':v.returncode,'note':'No-source /Bv query may exit 2 (D8003).'}
    for tool in ['rustc','cargo']:r['environment'][tool]=run([tool,'--version'],repo).stdout.strip()
    probe=work/'probe';(probe/'src').mkdir(parents=True);shutil.copyfile(HERE/'probe.rs.txt',probe/'src/main.rs')
    src=(snap/'iso532/src/core/calc_slopes.rs').read_text(encoding='utf8')
    rounding='''    if total <= 16.0 {
        total = (total * 1000.0 + 0.5).floor() / 1000.0;
    } else {
        total = (total * 100.0 + 0.5).floor() / 100.0;
    }
'''
    assert src.count(rounding)==1
    raw=src.replace(rounding,'').replace('crate::tables::','iso532::tables::')
    raw22=raw.replace('iso532::tables::','crate::tables22::')
    tables=(snap/'iso532/src/tables.rs').read_text(encoding='utf8');cell='[0.40, 0.33, 0.26, 0.24, 0.24, 0.22, 0.22, 0.22]'
    assert tables.count(cell)==1
    tables22=tables.replace(cell,'[0.40, 0.33, 0.26, 0.24, 0.22, 0.22, 0.22, 0.22]')
    r['transformations']=[]
    for name,base,text in [('slopes_raw.rs',src,raw),('slopes_raw22.rs',src,raw22),('tables22.rs',tables,tables22)]:
        write(probe/'src'/name,text)
        df=''.join(difflib.unified_diff(base.splitlines(True),text.splitlines(True),fromfile=name+'.original',tofile=name+'.diagnostic'))
        write(HERE/(name+'.diff.txt'),df)
        r['transformations'].append({'file':name,'original_text_sha256':hashlib.sha256(base.encode()).hexdigest(),'diagnostic_text_sha256':sha(probe/'src'/name),'diff_file':name+'.diff.txt'})
    write(probe/'Cargo.toml','[package]\nname="c01-root-probe"\nversion="0.0.0"\nedition="2021"\n[workspace]\n[dependencies]\niso532={path="../snapshot/iso532"}\n')
    shutil.copyfile(snap/'Cargo.lock',probe/'Cargo.lock');run(['cargo','build','--release','--offline','--manifest-path',probe/'Cargo.toml'])
    for src,name in [(probe/'Cargo.toml','probe-Cargo.toml'),(probe/'Cargo.lock','probe-Cargo.lock.txt')]:shutil.copyfile(src,HERE/name)
    exe=probe/'target/release/c01-root-probe.exe';dll=cdir/'stages.dll';r['binary_hashes']={p.name:sha(p) for p in [exe,dll]}
    r['harness_hashes_before_redaction']={p.name:sha(p) for p in [HERE/'run_experiment.py',HERE/'probe.rs.txt',HERE/'stages.c.txt']}
    lib=ct.CDLL(str(dll))
    for name in ['rc_filter','rc_main','rc_nl','rc_tw']:
        getattr(lib,name).argtypes=[DP,ct.c_int,DP];getattr(lib,name).restype=ct.c_int
    for name in ['rc_slopes','rc_public']:
        getattr(lib,name).argtypes=[DP,ct.c_int,DP,DP];getattr(lib,name).restype=ct.c_int
    def cstage(name,x,n,shape,folder,tag):
        y=np.full(shape,np.nan);beforehash=ah(x);ret=getattr(lib,'rc_'+name)(ptr(x),n,ptr(y))
        assert ret==0 and ah(x)==beforehash and np.isfinite(y).all(),(name,ret)
        y.tofile(folder/(tag+'.bin'));return y
    def cslopes(x,n,folder,tag):
        total=np.zeros(n);spec=np.full((240,n),np.nan);beforehash=ah(x)
        ret=lib.rc_slopes(ptr(x),n,ptr(total),ptr(spec));assert ret==0 and ah(x)==beforehash and np.isfinite(spec).all() and np.isfinite(total).all()
        total.tofile(folder/(tag+'-total.bin'));spec.tofile(folder/(tag+'-spec.bin'));return total,spec
    def rust(mode,x,folder,tag):
        d=folder/tag;d.mkdir();x.tofile(d/'input.bin');beforehash=ah(x)
        run([exe,mode,d/'input.bin',d]);assert sha(d/'input.bin')==beforehash
        return {p.stem:np.fromfile(p,dtype='<f8') for p in d.glob('*.bin') if p.stem!='input'}
    def rt(x,folder,tag):return rust('tw',x,folder,tag)['tw']
    def ctweight(x,folder,tag):return cstage('tw',x,len(x),(len(x),),folder,tag)
    for s in old['signals']:
        sig=s['signal'];folder=work/f'signal-{sig}';folder.mkdir();K=s['K'];nt=s['L_pad']//24
        raw=prior/f'signal-{sig}-rust/input.bin';assert sha(raw)==s['input']['pressure_f64le_sha256']
        x=np.fromfile(raw,dtype='<f8');x.tofile(folder/'original-pressure.bin');xp=np.r_[x,np.zeros(s['L_pad']-len(x))];xp.tofile(folder/'padded-pressure.bin')
        assert ah(xp)==s['input']['padded_pressure_f64le_sha256']
        wav=next(official.rglob(f'Test signal {sig} (*.wav'));assert sha(wav)==s['input']['WAV_sha256']
        cp=np.full(nt,np.nan);cps=np.full((240,nt),np.nan);ret=lib.rc_public(ptr(xp),len(xp),ptr(cp),ptr(cps));assert ret==nt
        cp.tofile(folder/'C-public-total.bin');cps.tofile(folder/'C-public-specific.bin')
        rr=rust('pipeline',xp,folder,'R-pipeline');ur=rust('public',x,folder,'R-original-public')
        Rtol=rr['tol'].reshape(28,nt);Rcore=rr['core'].reshape(21,nt);Rnl=rr['nl'].reshape(21,nt);Rsp=rr['specific'].reshape(240,nt)
        Ctol=cstage('filter',xp,len(xp),(28,nt),folder,'C-tol')
        Ccore=cstage('main',Ctol,nt,(21,nt),folder,'C-core');Cnl=cstage('nl',Ccore,nt,(21,nt),folder,'C-nl')
        Cpre,Csp=cslopes(Cnl,nt,folder,'C-slope');Ctw=ctweight(Cpre,folder,'C-tw')
        eq={'C_replay_total':bits(cp,Ctw),'C_replay_specific':bits(cps,Csp),
            'Rust_replay_total':bits(rr['public_n'],rr['tw_round'][::4]),'Rust_replay_specific':bits(rr['public_spec'].reshape(240,-1),Rsp[:,::4].copy()),
            'Rust_original_padded_total_prefix':bits(ur['public_n'],rr['public_n'][:len(ur['public_n'])]),
            'old_C_tail_bits':val(cp[K])['bits']==s['total']['C']['bits'],
            'old_Rust_tail_bits':val(ur['public_n'][-1])['bits']==s['total']['Rust']['bits']}
        assert all(eq.values()),eq
        reround=rust('round',rr['slope_raw'],folder,'R-reround')['round'];eq['raw_reround_equals_baseline']=bits(reround,rr['slope_round']);assert eq['raw_reround_equals_baseline']
        # Ordered downstream substitutions, always keeping the stated upstream.
        Csl_Rnl,Csp_Rnl=cslopes(Rnl,nt,folder,'C-slope-on-Rnl');T2=rt(Csl_Rnl,folder,'T2')
        Cnl_Rcore=cstage('nl',Rcore,nt,(21,nt),folder,'C-nl-on-Rcore');pre3,_=cslopes(Cnl_Rcore,nt,folder,'C-slope-on-Cnl-Rcore');T3=rt(pre3,folder,'T3')
        Ccore_Rtol=cstage('main',Rtol,nt,(21,nt),folder,'C-core-on-Rtol');nl4=cstage('nl',Ccore_Rtol,nt,(21,nt),folder,'C-nl-on-Ccore-Rtol');pre4,_=cslopes(nl4,nt,folder,'C-slope-on-Cnl-Ccore-Rtol');T4=rt(pre4,folder,'T4')
        T5=rt(Cpre,folder,'T5')
        tails=[rr['tw_round'][K],rr['tw_raw'][K],T2[K],T3[K],T4[K],T5[K],cp[K]]
        errors=np.array(tails)-cp[K];contributions=errors[:-1]-errors[1:]
        order=['baseline','remove_R_rounding','replace_slopes_C','replace_NL_C','replace_main_C','replace_filter_C','replace_TW_C']
        decomp=[{'step':i,'intervention':name,'tail':val(tails[i]),'signed_residual':float(errors[i]),'abs_residual':float(abs(errors[i])),
                 'within_1e_minus14':bool(abs(errors[i])<=1e-14),
                 'signed_contribution':None if i==0 else float(contributions[i-1]),
                 'signed_explained_fraction':None if i==0 else float(contributions[i-1]/errors[0])} for i,name in enumerate(order)]
        # Both directions for same-input stages; TW uses all relevant histories.
        rmC=rust('main',Ctol,folder,'R-main-on-Ctol')['core'].reshape(21,nt)
        rnC=rust('nl',Ccore,folder,'R-nl-on-Ccore')['nl'].reshape(21,nt)
        rsC=rust('slopes',Cnl,folder,'R-slopes-on-Cnl')
        Ctw_Rraw=ctweight(rr['slope_raw'],folder,'Ctw-Rraw');Ctw_Rround=ctweight(rr['slope_round'],folder,'Ctw-Rround')
        Crounded=rust('round',Cpre,folder,'round-C-history')['round'];Rtw_Crounded=rt(Crounded,folder,'Rtw-Crounded');Ctw_Crounded=ctweight(Crounded,folder,'Ctw-Crounded')
        def upto(x):return np.ascontiguousarray(x[...,:K+1])
        stages={name:metric(upto(left),upto(right)) for name,left,right in [
          ('native_filter_SPL_R_minus_C',Rtol,Ctol),('native_main_R_minus_C',Rcore,Ccore),('native_NL_R_minus_C',Rnl,Cnl),
          ('native_slope_raw_R_minus_C',rr['slope_raw'],Cpre),('native_slope_rounded_R_minus_C',rr['slope_round'],Cpre),
          ('native_specific_R_minus_C',Rsp,Csp),('native_weighted_total_R_minus_C',rr['tw_round'],Ctw),
          ('same_Rtol_main_R_minus_C',Rcore,Ccore_Rtol),('same_Ctol_main_R_minus_C',rmC,Ccore),
          ('same_Rcore_NL_R_minus_C',Rnl,Cnl_Rcore),('same_Ccore_NL_R_minus_C',rnC,Cnl),
          ('same_Rnl_slopes_raw_R_minus_C',rr['slope_raw'],Csl_Rnl),('same_Cnl_slopes_raw_R_minus_C',rsC['slope_raw'],Cpre),
          ('same_Cpre_TW_R_minus_C',T5,Ctw),('same_Rraw_TW_R_minus_C',rr['tw_raw'],Ctw_Rraw),
          ('same_Rround_TW_R_minus_C',rr['tw_round'],Ctw_Rround),('same_Crounded_TW_R_minus_C',Rtw_Crounded,Ctw_Crounded)]}
        # Comparator and causal propagation controls never mutate originals.
        ref=Cpre[:K+1].copy();injected=ref.copy();injected[K-20]+=1e-6
        neg=metric(injected,ref);selfm=metric(ref,ref)
        rejected={}
        for label,bad in [('shape',ref[:-1]),('nonfinite',np.full_like(ref,np.nan))]:
            try:metric(ref,bad);rejected[label]=False
            except ValueError:rejected[label]=True
        tw_inj=Cpre.copy();tw_inj[K-20]+=.01
        piR=rt(tw_inj,folder,'TW-positive-R');piC=ctweight(tw_inj,folder,'TW-positive-C')
        controls={'self_zero':selfm['bitwise_mismatches']==0,'injected_coordinate':K-20,'injected_metric':neg,
           'injection_detected':neg['above_1e_minus14']==1 and neg['samples']['first_above_1e_minus14']['coordinate']==[K-20],
           'invalid_rejected':rejected,'TW_positive_R_tail_delta':float(piR[K]-T5[K]),'TW_positive_C_tail_delta':float(piC[K]-Ctw[K]),
           'TW_positive_passed':bool(abs(piR[K]-T5[K])>1e-14 and abs(piC[K]-Ctw[K])>1e-14)}
        rev={'C_history_rounding_effect_C_TW':float(Ctw_Crounded[K]-Ctw[K]),'C_history_rounding_effect_R_TW':float(Rtw_Crounded[K]-T5[K]),
          'Rust_history_rounding_effect_R_TW':float(rr['tw_round'][K]-rr['tw_raw'][K]),
          'Rust_history_rounding_effect_C_TW':float(Ctw_Rround[K]-Ctw_Rraw[K])}
        quant=rr['slope_round']-rr['slope_raw']
        case={'signal':sig,'L':len(x),'L_pad':len(xp),'K':K,'internal_frames':nt,'input':s['input'],
              'baseline_equivalence':eq,'baseline_C_tail':val(cp[K]),'baseline_Rust_tail':val(tails[0]),
              'baseline_signed_difference':float(errors[0]),'baseline_abs_difference':float(abs(errors[0])),
              'ordered_decomposition':decomp,'decomposition_reconstruction_error':float(sum(contributions)-errors[0]),
              'stage_comparisons':stages,'reverse_rounding_controls':rev,'controls':controls,
              'cell_counterfactual':{'raw24_tail':val(rr['tw_raw'][K]),'raw22_tail':val(rr['tw_raw22'][K]),
                   'cell22_minus_cell24_effect':float(rr['tw_raw22'][K]-rr['tw_raw'][K]),'cell22_residual_vs_C':float(rr['tw_raw22'][K]-cp[K]),
                   'scope':'Rust raw slope single cell 0.24 -> 0.22; other implementation differences unchanged'},
              'quantization':{'frames_through_target':K+1,'changed_frames':int((quant[:K+1]!=0).sum()),'max_abs_per_frame':float(abs(quant[:K+1]).max()),
                              'raw_frames_above_16':int((rr['slope_raw'][:K+1]>16).sum())}}
        r['signals'].append(case)
        print(f"signal {sig}: baseline={errors[0]:.17g}, unrounded residual={errors[1]:.17g}, rounding fraction={contributions[0]/errors[0]:.9g}, TW residual={errors[5]:.17g}",flush=True)
        js(HERE/'results.partial.json',r)
    after={str(p.relative_to(snap)).replace('\\','/'):sha(p) for p in sorted(snap.rglob('*')) if p.is_file()}
    assert before==after
    r['source']['snapshot_after']=after;r['source']['official_C_original']=sha(csrc);r['source']['official_C_used']=sha(cdir/csrc.name);r['source']['official_header']=sha(header)
    r['raw_arrays']=[{'file':str(p.relative_to(work)).replace('\\','/'),'bytes':p.stat().st_size,'sha256':sha(p)} for p in sorted(work.glob('signal-*/**/*.bin'))]
    r['gates']={'source_unchanged':before==after and sha(cdir/csrc.name)==CSHA,
       'baseline_and_replay_bitwise':all(all(s['baseline_equivalence'].values()) for s in r['signals']),
       'decomposition_reconstructs':all(abs(s['decomposition_reconstruction_error'])<=1e-14 for s in r['signals']),
       'final_substitution_within_1e_minus14':all(s['ordered_decomposition'][-1]['within_1e_minus14'] for s in r['signals']),
       'controls':all(s['controls']['self_zero'] and s['controls']['injection_detected'] and all(s['controls']['invalid_rejected'].values()) and s['controls']['TW_positive_passed'] for s in r['signals']),
       'rounding_removal_alone_within_1e_minus14':all(s['ordered_decomposition'][1]['within_1e_minus14'] for s in r['signals'])}
    r['finished_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat();r['worktree_after']=run(['git','status','--short'],repo).stdout
    js(HERE/'results.json',r);js(HERE/'run-log.json',log);(HERE/'results.partial.json').unlink()
    with (HERE/'tail-decomposition.csv').open('w',encoding='utf8',newline='') as f:
        w=csv.writer(f);w.writerow(['signal','step','intervention','tail_decimal17','tail_bits','signed_residual','signed_contribution','signed_fraction'])
        for s in r['signals']:
            for row in s['ordered_decomposition']:w.writerow([s['signal'],row['step'],row['intervention'],row['tail']['decimal17'],row['tail']['bits'],format(row['signed_residual'],'.17g'),'' if row['signed_contribution'] is None else format(row['signed_contribution'],'.17g'),'' if row['signed_explained_fraction'] is None else format(row['signed_explained_fraction'],'.17g')])
    with (HERE/'stage-coordinates.csv').open('w',encoding='utf8',newline='') as f:
        w=csv.writer(f);w.writerow(['signal','comparison','selection','coordinate','left_decimal17','left_bits','right_decimal17','right_bits','signed_diff'])
        for s in r['signals']:
            for name,m in s['stage_comparisons'].items():
                for sel,v in m['samples'].items():w.writerow([s['signal'],name,sel,json.dumps(v['coordinate']),v['left']['decimal17'],v['left']['bits'],v['right']['decimal17'],v['right']['bits'],format(v['signed_diff'],'.17g')])
    print(json.dumps(r['gates'],indent=2),flush=True)
except BaseException as e:
    r['execution_error']=repr(e);js(HERE/'results.partial.json',r);js(HERE/'run-log.json',log);raise
