"""Prepare coefficient-only SQAT copy and exact native stage extraction."""
from pathlib import Path
import shutil,hashlib,json,datetime
ROOT=Path.cwd();OUT=Path(__file__).resolve().parent;TMP=ROOT/'tmp/verification-f03-three-implementations'
src=TMP/'sqat-v2.0';alt=TMP/'sqat022';shutil.copytree(src,alt,dirs_exist_ok=True)
rel='psychoacoustic_metrics/Loudness_ISO532_1/Loudness_ISO532_1.m';raw=(src/rel).read_bytes()
old=b'0.40 0.33 0.26 0.24 0.24 0.22 0.22 0.22';new=b'0.40 0.33 0.26 0.24 0.22 0.22 0.22 0.22'
assert raw.count(old)==1
(alt/rel).write_bytes(raw.replace(old,new))
stages={}
for v,d in [('024',src),('022',alt)]:
    source=(d/rel).read_text(encoding='utf8')
    begin=source.index('% Upper limits of the approximated critical bands in Bark')
    end=source.index('% Specific loudness as a function of Bark number.')
    body=source[begin:end]
    wrapper='function [N_mat, ns] = sqat_slope_'+v+'(CoreL)\nNumSamplesLevel=size(CoreL,1);method=2;\n'+body+'\nend\n'
    p=TMP/f'sqat_slope_{v}.m';p.write_text(wrapper,encoding='utf8')
    stages[v]={'body_sha256':hashlib.sha256(body.encode()).hexdigest(),'source_first_line':source[:begin].count('\n')+1,'source_end_exclusive_line':source[:end].count('\n')+1,'wrapper_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'algorithm_body_unchanged':True}
shutil.copyfile(OUT/'run_sqat.m.txt',TMP/'run_sqat.m')
obj={'frozen_at':datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat(),'commit':'94f489c053d1366da05d5e62838c3f54ac7715c3','baseline':{p.relative_to(src).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in src.rglob('*.m')},'counterfactual':{p.relative_to(alt).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in alt.rglob('*.m')},'extraction':stages,'coefficient_change_only':raw.replace(old,new)==(alt/rel).read_bytes()}
(OUT/'sqat-freeze.json').write_text(json.dumps(obj,indent=2),encoding='utf8')
print('SQAT frozen and ready')
