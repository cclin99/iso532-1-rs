"""Independent measurement of the installed wheel versus frozen MoSQITo golden arrays."""
import pathlib,json,hashlib,sys,struct
import numpy as np
import iso532
ROOT=pathlib.Path(__file__).resolve().parents[4]
SRC=ROOT/'tmp/acceptance-040-astra/candidate'; OUT=pathlib.Path(__file__).resolve().parent
sys.path.insert(0,str(SRC/'tools'))
from iso532_testkit import contract_signal,fnv1a_f64

def compare(a,b):
 a=np.asarray(a,dtype='<f8');b=np.asarray(b,dtype='<f8');d=np.abs(a-b);flat=int(d.argmax());idx=np.unravel_index(flat,a.shape);different=np.flatnonzero(a.ravel().view('u8')!=b.ravel().view('u8'))
 first=int(different[0]) if different.size else None
 return {'shape':list(a.shape),'max_abs':float(d.ravel()[flat]),'max_coordinate':[int(i) for i in idx],'bit_differences':int(different.size),'first_coordinate':list(map(int,np.unravel_index(first,a.shape))) if first is not None else None,'first_got_hex':f'{a.ravel().view("u8")[first]:016x}' if first is not None else None,'first_want_hex':f'{b.ravel().view("u8")[first]:016x}' if first is not None else None}
r={}
for p in sorted((SRC/'data/golden').iterdir()):
 if not (p/'sig.bin').exists():continue
 sig=np.fromfile(p/'sig.bin',dtype='<f8');n,s,b,t=iso532.loudness_zwtv(sig,48000.,nl_init='mosqito_tail');sn,ss,sb=iso532.loudness_zwst(sig,48000.)
 r[p.name]={'zwtv_n':compare(n,np.fromfile(p/'N_time.bin',dtype='<f8')),'zwtv_specific':compare(s,np.fromfile(p/'N_spec_time.bin',dtype='<f8').reshape(s.shape)),'zwst_n':compare(np.array([sn]),np.fromfile(p/'N.bin',dtype='<f8')),'zwst_specific':compare(ss,np.fromfile(p/'N_specific.bin',dtype='<f8'))}
h={}
for init in ['zero','mosqito_tail']:
 n,s,b,t=iso532.loudness_zwtv(contract_signal(),48000.,nl_init=init);h[init]={'n':f'{fnv1a_f64(n):016x}','time_axis':f'{fnv1a_f64(t):016x}','first_n_f64_hex':struct.pack('>d',n[0]).hex()}
(OUT/'mosqito-measurements.json').write_text(json.dumps({'comparisons':r,'python_contract_hashes':h,'module':iso532.__file__},indent=2),encoding='utf8')
print(json.dumps({'max_zwtv_n':max(x['zwtv_n']['max_abs'] for x in r.values()),'max_zwtv_specific':max(x['zwtv_specific']['max_abs'] for x in r.values()),'max_zwst_n':max(x['zwst_n']['max_abs'] for x in r.values()),'max_zwst_specific':max(x['zwst_specific']['max_abs'] for x in r.values()),'hashes':h},indent=2))
