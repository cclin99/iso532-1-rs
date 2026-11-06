"""Fresh builds and numeric runs. Run from repository root; retains large outputs in tmp.
Dependencies: Python 3, numpy, openpyxl; MSVC 2022 BuildTools; cargo (cached dependencies).
Input provenance is frozen by freeze.py. This script never reads prior numeric results.
"""
from pathlib import Path
import ctypes as ct, datetime, hashlib, json, os, re, shutil, struct, subprocess, sys, wave
import numpy as np
import openpyxl
ROOT=Path.cwd(); OUT=Path(__file__).resolve().parent
TMP=ROOT/'tmp/verification-f03-filter-independent'; OFF=ROOT/'tmp/c01-material/official'
SHA=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(name,obj): (OUT/name).write_text(json.dumps(obj,indent=2,allow_nan=False),encoding='utf8')
def run(args,cwd,log):
    p=subprocess.run(args,cwd=cwd,capture_output=True)
    (OUT/log).write_text(p.stdout.decode(errors='replace')+p.stderr.decode(errors='replace'),encoding='utf8')
    if p.returncode: raise RuntimeError((args,p.returncode,log))
    return p.stdout
frozen=json.loads((OUT/'frozen-inputs.json').read_text())
for path,meta in frozen['raw_inputs'].items(): assert SHA(ROOT/path)==meta['sha256'],path
for path,h in frozen['product_files'].items(): assert SHA(TMP/'product'/path)==h,path
def pcm(p):
    with wave.open(str(p)) as w:
        assert (w.getnchannels(),w.getsampwidth(),w.getframerate())==(1,2,48000)
        return np.frombuffer(w.readframes(w.getnframes()),'<i2').astype(float)/32768
calraw=pcm(next(OFF.rglob('calibration signal sine 1kHz 60dB.wav')))
factors={'sqrt':float(2*np.sqrt(2)),'cal':float(.02/np.sqrt(np.mean(calraw**2)))}
inputs={}; (TMP/'inputs').mkdir(exist_ok=True)
for s in range(2,26):
    path=next(OFF.rglob(f'Test signal {s} (*.wav')); x=pcm(path); inputs[s]=x
    for cal,f in factors.items():
        if cal=='cal' and s>5: continue
        data=(x*f).astype('<f4').tobytes()
        hdr=b'RIFF'+struct.pack('<I',36+len(data))+b'WAVEfmt '+struct.pack('<IHHIIHH',16,3,1,48000,192000,4,32)+b'data'+struct.pack('<I',len(data))
        (TMP/'inputs'/f'sig{s}-{cal}.wav').write_bytes(hdr+data)
        if s<=5: (x*f).astype('<f8').tofile(TMP/'inputs'/f'sig{s}-{cal}.bin')
builds={}
vcvars=r'C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat'
assert Path(vcvars).exists()
for variant in ['022','024']:
    d=TMP/f'c{variant}'; d.mkdir(exist_ok=True)
    for p in OFF.rglob('*'):
        if p.is_file() and p.suffix in ('.c','.h'): shutil.copyfile(p,d/p.name)
    c=d/'ISO_532-1.c'; raw=c.read_bytes()
    old=b'0.40f,0.33f,0.26f,0.24f,0.22f,0.22f,0.22f,0.22f'
    new=b'0.40f,0.33f,0.26f,0.24f,0.24f,0.22f,0.22f,0.22f'
    assert raw.count(old)==1
    if variant=='024': c.write_bytes(raw.replace(old,new))
    cmd='@echo off\ncall "'+vcvars+'" >nul\nif errorlevel 1 exit /b %errorlevel%\ncl /nologo /O2 /fp:precise /D_CRT_SECURE_NO_WARNINGS /I. ISO_532-1.c ISO_532-1_main.c ISO_532-1_helper.c /Fe:cli.exe\nif errorlevel 1 exit /b %errorlevel%\ncl /nologo /O2 /fp:precise /LD /I. ISO_532-1.c /link /OUT:reference.dll /EXPORT:f_loudness_from_signal /EXPORT:f_loudness_from_levels /EXPORT:f_calc_third_octave_levels\nexit /b %errorlevel%\n'
    (d/'build.cmd').write_text(cmd); (OUT/f'build-{variant}.cmd.txt').write_text(cmd)
    run(['cmd','/c',str(d/'build.cmd')],d,f'build-{variant}.log')
    builds[variant]={p.name:SHA(p) for p in d.iterdir() if p.suffix in ('.c','.h','.dll','.exe')}
write('builds.json',builds)
rd=TMP/'rust'; (rd/'src').mkdir(parents=True,exist_ok=True)
shutil.copyfile(OUT/'frontend.rs.txt',rd/'src/main.rs')
manifest='[package]\nname="independent-frontend"\nversion="0.0.0"\nedition="2021"\n[workspace]\n[dependencies]\niso532={path="../product/iso532"}\n'
(rd/'Cargo.toml').write_text(manifest); (OUT/'frontend.Cargo.toml.txt').write_text(manifest)
run(['cargo','build','--release','--offline'],rd,'rust-build.log')
shutil.copyfile(rd/'Cargo.lock',OUT/'frontend.Cargo.lock.txt')
run([str(rd/'target/release/independent-frontend.exe'),str(TMP/'inputs')],ROOT,'frontend-results.jsonl.txt')
print('Fresh C and Rust builds complete; frontend factorial done.',flush=True)
for variant in ['022','024']:
    for s in range(2,26):
        d=TMP/f'cli{variant}'/f'sig{s}'; d.mkdir(parents=True,exist_ok=True)
        args=[str(TMP/f'c{variant}'/'cli.exe'),'Stationary' if s<=5 else 'Time_varying','D' if s==15 else 'F',str(TMP/'inputs'/f'sig{s}-sqrt.wav')]
        if s<=5: args+=['0.2']
        p=subprocess.run(args,cwd=d,capture_output=True); (d/'stdout.txt').write_bytes(p.stdout+p.stderr)
        assert p.returncode==0,(variant,s,p.returncode)
    print('Fresh CLI complete',variant,flush=True)

def csv(variant,s,spec=False):
    name='SpecLoudness.csv' if spec else 'Loudness.csv'
    txt=(TMP/f'cli{variant}'/f'sig{s}'/name).read_text()
    rows=[[float(v) for v in l.split(';') if v.strip()] for l in txt.splitlines() if re.match(r'^\d',l)]
    if s<=5 and not spec: return np.array([[float(re.search(r'N / sone \((?:free|diffuse) field\);\s*([\d.]+)',txt)[1])]])
    return np.array(rows)
def ticks(x):
    y=np.rint(np.array(x)*10000).astype(np.int64)
    assert np.max(np.abs(np.array(x)-y/10000))<1e-10
    return y
def stats(r,a,b):
    # All reference/CSV values have four decimal places. Compare integer units.
    ri=ticks(r); ai=ticks(a); bi=ticks(b); d=np.abs(ai-bi); ea=np.abs(ai-ri); eb=np.abs(bi-ri)
    o={'points':len(ri),'max_abs_022':float(np.max(ea)/10000),'max_abs_024':float(np.max(eb)/10000),
       'exact_022':int((ea==0).sum()),'exact_024':int((eb==0).sum()),'differ':int((d>0).sum()),
       '022_over_1e4':int((ea>1).sum()),'024_over_1e4':int((eb>1).sum()),
       'exploratory_shared_threshold_exceptions_022':int((np.abs(a-r)>np.maximum(.1,.05*np.abs(r))+1e-10).sum()),
       'exploratory_shared_threshold_exceptions_024':int((np.abs(b-r)>np.maximum(.1,.05*np.abs(r))+1e-10).sum()),
       'thresholds':{}}
    for threshold in [1,2,3,5,10]:
        m=d>=threshold
        o['thresholds'][str(threshold)]={'points':int(m.sum()),'equal022':int((m&(ea==0)).sum()),'equal024':int((m&(eb==0)).sum()),
             'closer022':int((m&(ea<eb)).sum()),'ties':int((m&(ea==eb)).sum()),'closer024':int((m&(ea>eb)).sum())}
    return o
refs={}; comparisons={}; alignment={}; negatives={}
for path in sorted(OFF.rglob('*.xlsx')):
    w=openpyxl.load_workbook(path,read_only=True,data_only=True)
    for sh in w:
        s=int(re.search(r'\d+',sh.title)[0]); rows=list(sh.values)
        if s==1: continue
        if s<=5:
            r=np.array([float(rows[7][1])]); ns=np.array([float(row[6]) for row in rows[7:247]])
            refs[s]={'n':r[0],'specific':ns.tolist()}
            comparisons[s]={'N':stats(r,csv('022',s).ravel(),csv('024',s).ravel()),
                            'Nprime':stats(ns,csv('022',s,True).ravel()[-240:],csv('024',s,True).ravel()[-240:])}
        else:
            rows=[row for row in rows[10:] if isinstance(row[0],(int,float)) and isinstance(row[1],(int,float))]
            t=ticks([row[0] for row in rows]); r=np.array([row[1] for row in rows]); assert np.all(np.diff(t)==20)
            nsref=np.array([row[11] for row in rows],float) if s<=13 else None
            vals={}; specs={}
            for v in ['022','024']:
                a=csv(v,s); at=ticks(a[:,0]); assert len(np.unique(at))==len(at)
                ix=np.searchsorted(at,t); assert ix.max()<len(at) and np.array_equal(at[ix],t)
                vals[v]=a[ix,1]
                if s<=13:
                    a2=csv(v,s,True); assert np.array_equal(ticks(a2[:,0]),at)
                    bark=float(str(list(sh.values)[8][11]).split()[1].replace(',','.')); bi=round(bark*10)-1
                    specs[v]=a2[ix,bi+1]
                if v=='022':
                    alignment[s]={'input_samples':len(inputs[s]),'duration_s':len(inputs[s])/48000,'cli_rows':len(at),'workbook_rows':len(t),
                       'workbook_first_s':float(t[0]/10000),'workbook_last_s':float(t[-1]/10000),'cli_last_s':float(at[-1]/10000),
                       'unmatched_cli_rows':len(at)-len(t),'time_match_exact':True,'first_cli_frame':int(ix[0]),'last_cli_frame':int(ix[-1])}
                    negatives[s]={'one_frame_shift_max_abs':float(np.max(np.abs(a[ix[:-1]+1,1]-r[:-1]))),
                       'one_frame_shift_over_1e4':int((np.abs(a[ix[:-1]+1,1]-r[:-1])>.0001+1e-10).sum())}
            comparisons[s]={'N':stats(r,vals['022'],vals['024'])}
            if s<=13: comparisons[s]['Nprime']=stats(nsref,specs['022'],specs['024']); comparisons[s]['Nprime']['bark']=bark
            refs[s]={'time_ticks':t.tolist(),'n':r.tolist()}
            if s<=13: refs[s].update(specific=nsref.tolist(),bark=bark)
write('workbook-comparison.json',comparisons);write('alignment.json',alignment);write('negative-time-shift.json',negatives)
np.savez(TMP/'workbook-refs.npz',refs=np.array(refs,dtype=object))
write('calibration.json',{'factors':factors,'ratio':factors['cal']/factors['sqrt'],'db_delta':float(20*np.log10(factors['cal']/factors['sqrt'])),
      'calibration_pcm_peak_lsb':float(np.max(np.abs(calraw))*32768),'calibration_pcm_rms_lsb':float(np.sqrt(np.mean(calraw**2))*32768)})
write('generated-input-hashes.json',{p.name:SHA(p) for p in (TMP/'inputs').iterdir()})
write('raw-output-hashes.json',{p.relative_to(TMP).as_posix():SHA(p) for p in TMP.glob('cli*/sig*/*') if p.is_file()})
write('tools.json',{'python':sys.version,'numpy':np.__version__,'openpyxl':openpyxl.__version__,
      'rustc':subprocess.check_output(['rustc','-Vv']).decode(),'cargo':subprocess.check_output(['cargo','-V']).decode(),
      'rust_binary_sha256':SHA(rd/'target/release/independent-frontend.exe'),
      'completed_at':datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat()})
print('All fresh workbook comparisons written.',flush=True)
