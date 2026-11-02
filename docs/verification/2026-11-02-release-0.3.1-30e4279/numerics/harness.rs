use std::{path::Path,io::Write};
#[path = "COMMON_PATH"] mod common;
use common::annexb_check::*;
fn save(p:&Path, v:&[f64]) { let mut f=std::fs::File::create(p).unwrap(); for x in v {f.write_all(&x.to_le_bytes()).unwrap();}}
fn main(){
let a:Vec<String>=std::env::args().collect();
if a[1]=="compute" {let x=common::read_bin_path(Path::new(&a[2])); let out=Path::new(&a[3]);std::fs::create_dir_all(out).unwrap();
let s=iso532::loudness_zwst(&x,48000.,iso532::FieldType::Free).unwrap(); let t=iso532::loudness_zwtv(&x,48000.,iso532::FieldType::Free).unwrap();
for (name,v) in [("st_n",vec![s.n]),("st_spec",s.n_specific),("tv_n",t.n),("tv_spec",t.n_specific),("tv_time",t.time_axis)] {save(&out.join(format!("{name}.bin")),&v);} return;}
if a[1]=="verdict"{let g=common::read_bin_path(Path::new(&a[2]));let r=common::read_bin_path(Path::new(&a[3])); println!("{:?}",annexb_verdict(&g,&r));return;}
if a[1]=="csv" {let v=annexb_csv_path(Path::new(&a[2])); assert_eq!(v.len(),240); println!("{:?}",annexb_verdict(&vec![0.;240],&v)); return;}
if a[1]=="bin" {let v=common::read_bin_path(Path::new(&a[2]));println!("{:?}",annexb_verdict(&v,&v));return;}
if a[1]=="controls" {
for (name,g,r) in [("empty_both",vec![],vec![]),("empty_got",vec![],vec![1.]),("empty_reference",vec![1.],vec![]),("shape",vec![1.,1.],vec![1.]),("negative_ref",vec![0.],vec![-1.])]{let v=annexb_verdict(&g,&r);assert!(matches!(v,Verdict::Invalid(_)));println!("{name}: {v:?}");}
for v in [f64::NAN,f64::INFINITY,f64::NEG_INFINITY] {for side in ["got","reference"] {let (g,r)=if side=="got" {(vec![1.,v],vec![1.,1.])}else{(vec![1.,1.],vec![1.,v])};let z=annexb_verdict(&g,&r);assert!(matches!(z,Verdict::Invalid(_)));println!("nonfinite_{side}_{v}: {z:?}");}}
for (g,r,expect) in [(2.1,2.,false),(2.0625,2.,true),(2.125,2.,false),(10.55,10.,false),(8.5,8.,false),(8.375,8.,true),(0.1,0.,true),(0.1000000001,0.,false),(105.,100.,true),(105.0000001,100.,false)] {let z=annexb_verdict(&[g],&[r]);assert_eq!(z.is_pass(),expect);println!("boundary got={g} ref={r} diff_bits={:016x} tolerance_bits={:016x} {z:?}",(g-r).abs().to_bits(),annexb_tolerance(r).to_bits());}
}
}
