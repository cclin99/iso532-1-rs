"""Supplemental F-07 branch trace, explicitly derived from frozen source.
Independent C comparison is in run-numerics.py; this trace checks change localization.
"""
from pathlib import Path
import subprocess,json,re,hashlib,math,wave
import numpy as np
R=Path.cwd();B=R/'tmp/acceptance-040-astra';O=R/'docs/verification/2026-11-04-release-0.4.0-fca4ccd';D=B/'classification';(D/'src').mkdir(parents=True,exist_ok=True)
for v,mod in [('candidate','new'),('round1','old')]:
 s=(B/v/'iso532/src/core/calc_slopes.rs').read_text().split('#[cfg(test)]')[0].replace('use crate::tables','use iso532::tables')
 if mod=='new':
  s='thread_local! {pub static FLAGS: std::cell::RefCell<[bool;240]> = const {std::cell::RefCell::new([false;240])};}\n'+s
  needle='sample_after(z_array, z2, n2, nm_band, band)';assert s.count(needle)==1;s=s.replace(needle,'FLAGS.with(|f|f.borrow_mut()[(z_array*10.0).round() as usize-1]=true);\n        '+needle)
 (D/'src'/f'{mod}.rs').write_text(s);(O/f'classification-{mod}.rs.txt').write_text(s)
main=r'''
mod new; mod old;
use std::{fs,env};use iso532::{FieldType,zwtv::{third_octave_levels,nonlinear_decay,ParMode,NlInit},core::{calc_slopes::calc_slopes,main_loudness::main_loudness_frames_into}};
fn main(){let a:Vec<String>=env::args().collect();let field=if a.get(2).map(|s|s.as_str())==Some("diffuse"){FieldType::Diffuse}else{FieldType::Free};let x:Vec<f64>=fs::read(&a[1]).unwrap().chunks_exact(8).map(|b|f64::from_le_bytes(b.try_into().unwrap())).collect();let(tol,k)=third_octave_levels::third_octave_levels(&x);let mut tm=vec![0.;28*k];for t in 0..k{for b in 0..28{tm[t*28+b]=tol[b*k+t];}}let mut core=vec![0.;21*k];main_loudness_frames_into(&tm,k,field,&mut core).unwrap();let nl=nonlinear_decay::nl_loudness_with(&core,k,ParMode::Rayon,NlInit::Zero);let mut changes=0usize;let mut outside=0usize;let mut traced=0usize;for t in (0..k).step_by(4){let nm=std::array::from_fn(|b|nl[b*k+t]);new::FLAGS.with(|f|*f.borrow_mut()=[false;240]);let(n,s)=new::calc_slopes(&nm);let(on,os)=old::calc_slopes(&nm);let(pn,ps)=calc_slopes(&nm);assert_eq!(n.to_bits(),pn.to_bits());assert_eq!(n.to_bits(),on.to_bits());new::FLAGS.with(|f|{let flags=f.borrow();for b in 0..240{assert_eq!(s[b].to_bits(),ps[b].to_bits());if flags[b]{traced+=1;}if s[b].to_bits()!=os[b].to_bits(){changes+=1;if !flags[b]{outside+=1;}}}});}println!("{{\"changed\":{},\"outside_after_segment_branch\":{},\"branch_cells\":{},\"output_frames\":{}}}",changes,outside,traced,k.div_ceil(4));}
'''
(D/'src/main.rs').write_text(main);(O/'classification-main.rs.txt').write_text(main);(D/'Cargo.toml').write_text('[package]\nname="classify-f07"\nversion="0.0.0"\nedition="2021"\n[workspace]\n[dependencies]\niso532={path="'+(B/'candidate/iso532').as_posix()+'"}\n');(D/'Cargo.lock').write_bytes((B/'candidate/Cargo.lock').read_bytes());p=subprocess.run(['cargo','build','--offline','--release','--manifest-path',str(D/'Cargo.toml')],capture_output=True,text=True);(O/'classification-build.log').write_text(p.stdout+p.stderr);assert p.returncode==0

def wav(p):
 with wave.open(str(p),'rb') as w:return np.frombuffer(w.readframes(w.getnframes()),'<i2').astype('f8')/32768
cal=wav(R/'tmp/c01-material/official/Annex C/calibration signal sine 1kHz 60dB.wav');s=0.
for v in cal:s+=float(v)*float(v)
factor=math.sqrt(1e6*4e-10/(s/len(cal)));res={}
for p in sorted((R/'tmp/c01-material/official').glob('Annex B*/*.wav'))+[None]:
 x=wav(p)*factor if p else np.array([((i*2654435761)%96001)/96000*.02-.01 for i in range(144000)]);name=p.stem if p else 'contract_3s';ip=D/'input.bin';x.tofile(ip);r=subprocess.run([str(D/'target/release/classify-f07.exe'),str(ip),'diffuse' if name.startswith('Test signal 15 ') else 'free'],capture_output=True,text=True);assert r.returncode==0,r.stderr;res[name]=json.loads(r.stdout);print(name,r.stdout.strip(),flush=True)
(O/'classification-results.json').write_text(json.dumps(res,indent=2))
