"""Freeze and prepare isolated third-party sources; run before numerical workers."""
from pathlib import Path
import hashlib,json,shutil,subprocess,datetime,wave,re
import numpy as np
from scipy.io import savemat
import openpyxl
ROOT=Path.cwd(); OUT=Path(__file__).resolve().parent; TMP=ROOT/'tmp/verification-f03-three-implementations'; OFF=ROOT/'tmp/c01-material/official'
SHA=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(n,o): (OUT/n).write_text(json.dumps(o,indent=2),encoding='utf8')
mos=ROOT/'tmp/acceptance-040-astra/fresh-venv/Lib/site-packages/mosqito'
for variant in ['024','022']:
    dest=TMP/f'mos{variant}'/'mosqito'
    shutil.copytree(mos,dest,ignore=shutil.ignore_patterns('__pycache__'),dirs_exist_ok=True)
    if variant=='022':
        p=dest/'sq_metrics/loudness/loudness_zwst/_calc_slopes.py'; t=p.read_bytes()
        old=b'(0.40, 0.33, 0.26, 0.24, 0.24, 0.22, 0.22, 0.22)'
        assert t.count(old)==1
        p.write_bytes(t.replace(old,b'(0.40, 0.33, 0.26, 0.24, 0.22, 0.22, 0.22, 0.22)'))
builds={}
vcvars=r'C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat'
for variant in ['022','024']:
    d=TMP/f'c{variant}'; d.mkdir(exist_ok=True)
    for p in OFF.rglob('*'):
        if p.is_file() and p.suffix in ['.c','.h']:shutil.copyfile(p,d/p.name)
    p=d/'ISO_532-1.c'; raw=p.read_bytes()
    assert SHA(p)=='a74b45ed297cd09ac60701a923120341137d227e536f3109ae4ece810d834491'
    old=b'0.40f,0.33f,0.26f,0.24f,0.22f,0.22f,0.22f,0.22f';assert raw.count(old)==1
    if variant=='024':p.write_bytes(raw.replace(old,b'0.40f,0.33f,0.26f,0.24f,0.24f,0.22f,0.22f,0.22f'))
    shutil.copyfile(OUT/'core-wrapper.c.txt',d/'core-wrapper.c')
    cmd='@echo off\ncall "'+vcvars+'" >nul\nif errorlevel 1 exit /b %errorlevel%\ncl /nologo /O2 /fp:precise /LD /I. core-wrapper.c /link /OUT:reference.dll /EXPORT:f_loudness_from_signal /EXPORT:f_loudness_from_levels /EXPORT:f_calc_slopes\nexit /b %errorlevel%\n'
    (d/'build.cmd').write_text(cmd); (OUT/f'build-{variant}.cmd.txt').write_text(cmd)
    p=subprocess.run(['cmd','/c',str(d/'build.cmd')],cwd=d,capture_output=True)
    (OUT/f'build-{variant}.log').write_text(p.stdout.decode(errors='replace')+p.stderr.decode(errors='replace'))
    assert p.returncode==0
    builds[variant]={p.name:SHA(p) for p in d.iterdir() if p.suffix in ['.c','.h','.dll']}
write('builds.json',builds)
(TMP/'inputs').mkdir(exist_ok=True)
refs={}
for p in OFF.rglob('*.xlsx'):
    for sh in openpyxl.load_workbook(p,data_only=True,read_only=True):
        s=int(re.search(r'\d+',sh.title)[0]); rr=list(sh.values)
        if s<=5:refs[s]={'n':[float(rr[7][1])],'specific':[[float(r[6])] for r in rr[7:247]],'time':[0.]}
        else:
            rows=[r for r in rr[10:] if isinstance(r[0],(int,float)) and isinstance(r[1],(int,float))]
            refs[s]={'n':[r[1] for r in rows],'time':[r[0] for r in rows]}
            if s<=13:
                refs[s]['specific']=[[r[11] for r in rows]]
                refs[s]['bark']=float(str(rr[8][11]).split()[1].replace(',','.'))
levelsfile=next(OFF.rglob('Test signal 1.txt'))
print('levels:',levelsfile.read_text(),flush=True)
nums=[float(line.split(':')[1]) for line in levelsfile.read_text().splitlines() if line.strip() and not line.lstrip().startswith('#')]
assert len(nums)==28,nums
levels=np.array(nums);savemat(TMP/'inputs/sig1.mat',{'x':levels}); np.save(TMP/'inputs/sig1.npy',levels)
for s in range(2,26):
    p=next(OFF.rglob(f'Test signal {s} (*.wav'))
    with wave.open(str(p)) as w:
        assert (w.getnchannels(),w.getsampwidth(),w.getframerate())==(1,2,48000)
        x=np.frombuffer(w.readframes(w.getnframes()),'<i2').astype(float)/32768*(2*np.sqrt(2))
    np.save(TMP/'inputs'/f'sig{s}.npy',x);savemat(TMP/'inputs'/f'sig{s}.mat',{'x':x.reshape(-1,1)})
(TMP/'refs.json').write_text(json.dumps(refs))
write('frozen-inputs.json',{'frozen_at':datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat(),
 'head':subprocess.check_output(['git','rev-parse','HEAD']).decode().strip(),
 'raw_inputs':{p.relative_to(OFF).as_posix():SHA(p) for p in OFF.rglob('*') if p.is_file() and p.suffix.lower() in ['.c','.h','.wav','.xlsx','.txt']},
 'mosqito_version':'1.2.1','mosqito_source':{p.relative_to(mos).as_posix():SHA(p) for p in mos.rglob('*.py')},
 'generated_inputs':{p.relative_to(TMP).as_posix():SHA(p) for p in (TMP/'inputs').iterdir()},
 'preregistration_sha256':SHA(OUT/'preregistration.md')})
print('Prepared and frozen',flush=True)
