"""Final bounded exploratory control: comparison-rounding identity, 2x2 cell/r8."""
import argparse, datetime, difflib, hashlib, json, shutil, subprocess
from pathlib import Path
import numpy as np
p=Path(__file__).resolve().parent
ap=argparse.ArgumentParser();ap.add_argument('--work',type=Path,required=True);a=ap.parse_args();work=a.work.resolve();scratch=work/'r8-control';(scratch/'src').mkdir(parents=True,exist_ok=False)
def sha(f):return hashlib.sha256(Path(f).read_bytes()).hexdigest()
def write(f,s):Path(f).write_text(s,encoding='utf8',newline='\n')
def js(f,x):write(f,json.dumps(x,indent=2,ensure_ascii=False,allow_nan=False)+'\n')
def val(x):return {'decimal17':format(float(x),'.17g'),'bits':format(np.float64(x).view('u8').item(),'016x')}
ts=datetime.datetime.now(datetime.timezone.utc).isoformat()
write(p/'r8-addendum.en.md',f'''# Final exploratory comparison-rounding control

Before execution: {ts}. After epsilon/table controls left a measurable same-input slope gap, test ONLY replacing Rust r8(value)=(value*1e8).round()/1e8 with identity in already unrounded slope modules, both cell24 and cell22. Original Rust/C remain unchanged. Fix R nonlinear history and R TW. Record the 2x2 cell/r8 interaction, tail residual against original C slopes on that history and epsilon-zero/tables-double C diagnostic, full history counts and hashes. This is the last bounded control; afterward stop and report any residual unresolved. No threshold changes or code-fix claim.
''')
write(p/'r8-addendum.md',f'''# 最後一項探索性比較捨入控制

執行前：{ts}。epsilon／table 控制仍留可量測同輸入 slope 差後，只把已移除 total rounding 的 Rust slope 模組中 r8(value)=(value*1e8).round()/1e8 改成 identity，分別測 cell24／cell22。原 Rust／C 不變，固定 R nonlinear 歷史與 R TW。列 2x2 cell／r8 交互項、相對相同歷史原 C slopes 與 epsilon-zero/tables-double C 診斷的尾殘差、完整歷史數量與 hash。此為最後限定控制，之後停止並如實列未解殘差，不改門檻，不冒稱修復。
''')
original='''fn r8(value: f64) -> f64 {
    (value * 100_000_000.0).round() / 100_000_000.0
}'''
trans=[]
for old,new in [('slopes_raw.rs','off24.rs'),('slopes_raw22.rs','off22.rs')]:
    text=(work/'probe/src'/old).read_text(encoding='utf8');assert text.count(original)==1
    changed=text.replace(original,'fn r8(value: f64) -> f64 { value }');write(scratch/'src'/new,changed)
    write(p/(new+'.diff.txt'),''.join(difflib.unified_diff(text.splitlines(True),changed.splitlines(True),fromfile=old,tofile=new)))
    trans.append({'module':new,'before_sha256':sha(work/'probe/src'/old),'after_sha256':sha(scratch/'src'/new)})
shutil.copyfile(work/'probe/src/tables22.rs',scratch/'src/tables22.rs')
write(scratch/'src/main.rs',r'''#![allow(dead_code)]
use std::{env,fs,io::Write,path::Path};mod off24;mod off22;mod tables22;
fn save(d:&Path,name:&str,x:&[f64]){let mut f=fs::File::create(d.join(format!("{name}.bin"))).unwrap();for v in x{f.write_all(&v.to_le_bytes()).unwrap();}}
fn main(){let a:Vec<String>=env::args().collect();let raw=fs::read(&a[1]).unwrap();let x:Vec<f64>=raw.chunks_exact(8).map(|b|f64::from_le_bytes(b.try_into().unwrap())).collect();let n=x.len()/21;let d=Path::new(&a[2]);let mut y24=vec![0.;n];let mut y22=vec![0.;n];for t in 0..n{let frame=std::array::from_fn(|b|x[b*n+t]);y24[t]=off24::calc_slopes_n_only(&frame);y22[t]=off22::calc_slopes_n_only(&frame);}save(d,"slope24",&y24);save(d,"slope22",&y22);save(d,"tw24",&iso532::zwtv::temporal_weighting::temporal_weighting(&y24));save(d,"tw22",&iso532::zwtv::temporal_weighting::temporal_weighting(&y22));}
''')
shutil.copyfile(scratch/'src/main.rs',p/'r8-probe.rs.txt')
write(scratch/'Cargo.toml','[package]\nname="c01-r8-control"\nversion="0.0.0"\nedition="2021"\n[workspace]\n[dependencies]\niso532={path="../snapshot/iso532"}\n')
shutil.copyfile(work/'probe/Cargo.lock',scratch/'Cargo.lock');logs=[]
def run(cmd):
    z=subprocess.run(list(map(str,cmd)),cwd=scratch,capture_output=True,text=True,encoding='utf8',errors='replace');logs.append({'command':list(map(str,cmd)),'exit_code':z.returncode,'stdout':z.stdout,'stderr':z.stderr});js(p/'r8-control-log.json',logs);assert z.returncode==0,z.stdout+z.stderr
original_probe=work/'probe/target/release/c01-root-probe.exe';original_probe_sha=sha(original_probe)
run(['cargo','build','--release','--offline','--manifest-path',scratch/'Cargo.toml','--target-dir',work/'probe/target'])
exe=work/'probe/target/release/c01-r8-control.exe';assert sha(original_probe)==original_probe_sha
shutil.copyfile(scratch/'Cargo.toml',p/'r8-Cargo.toml');shutil.copyfile(scratch/'Cargo.lock',p/'r8-Cargo.lock.txt')
primary=json.loads((p/'results.json').read_text(encoding='utf8'));slopes=json.loads((p/'slopes-controls.json').read_text(encoding='utf8'))
r={'started_utc':ts,'addendum_sha256':{q.name:sha(q) for q in p.glob('r8-addendum*.md')},'transformations':trans,'binary_sha256':sha(exe),'original_probe_unchanged':True,'signals':[]}
for s in primary['signals']:
    sig=s['signal'];K=s['K'];d=scratch/f'signal-{sig}';d.mkdir();src=work/f'signal-{sig}/R-pipeline/nl.bin';run([exe,src,d])
    y24=np.fromfile(d/'tw24.bin',dtype='<f8');y22=np.fromfile(d/'tw22.bin',dtype='<f8')
    on24=float(s['cell_counterfactual']['raw24_tail']['decimal17']);on22=float(s['cell_counterfactual']['raw22_tail']['decimal17']);c=float(s['ordered_decomposition'][2]['tail']['decimal17'])
    cs=next(v for v in slopes['signals'] if v['signal']==sig);cd=float(cs['variants']['epsilon_zero_tables_double']['tail']['decimal17'])
    r['signals'].append({'signal':sig,'r8_on_cell24':val(on24),'r8_on_cell22':val(on22),'r8_off_cell24':val(y24[K]),'r8_off_cell22':val(y22[K]),
      'r8_off_minus_on_cell24':float(y24[K]-on24),'r8_off_minus_on_cell22':float(y22[K]-on22),
      'interaction_cell_by_r8':float((y22[K]-y24[K])-(on22-on24)),
      'off22_residual_vs_original_C_same_history':float(y22[K]-c),'off22_residual_vs_normalized_C_same_history':float(y22[K]-cd),
      'within_1e_minus14_original_C':bool(abs(y22[K]-c)<=1e-14),'within_1e_minus14_normalized_C':bool(abs(y22[K]-cd)<=1e-14),
      'input_nonlinear_sha256':sha(src),'raw_hashes':{f.name:sha(f) for f in d.glob('*.bin')},
      'finite':bool(np.isfinite(y24).all() and np.isfinite(y22).all()),'frames':len(y24)})
r['finished_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat();js(p/'r8-control.json',r)
primary['exploratory_r8_controls']={'artifact':'r8-control.json','signals':r['signals']};js(p/'results.json',primary)
print(json.dumps(r['signals'],indent=2))
