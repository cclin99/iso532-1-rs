"""Independent full-precision C controls and factorial analysis, after replay.py."""
from pathlib import Path
import ctypes as C, json, re, hashlib
import numpy as np
ROOT=Path.cwd(); OUT=Path(__file__).resolve().parent; TMP=ROOT/'tmp/verification-f03-filter-independent'
def write(n,o): (OUT/n).write_text(json.dumps(o,indent=2,allow_nan=False,default=lambda v:v.item() if isinstance(v,np.generic) else str(v)),encoding='utf8')
refs=np.load(TMP/'workbook-refs.npz',allow_pickle=True)['refs'].item()
cal=json.loads((OUT/'calibration.json').read_text())['factors']
P=C.POINTER(C.c_double); PP=C.POINTER(P)
class Input(C.Structure): _fields_=[('NumSamples',C.c_int),('SampleRate',C.c_double),('pData',P)]
class Reference:
    def __init__(self,v):
        self.lib=C.CDLL(str(TMP/f'c{v}'/'reference.dll'))
        self.lib.f_loudness_from_signal.argtypes=[C.POINTER(Input),C.c_int,C.c_int,C.c_double,P,PP,C.c_int]
        self.lib.f_loudness_from_signal.restype=C.c_int
        self.lib.f_calc_third_octave_levels.argtypes=[C.POINTER(Input),PP,C.c_int,C.c_int,C.c_double]
        self.lib.f_calc_third_octave_levels.restype=C.c_int
        self.lib.f_loudness_from_levels.argtypes=[PP,C.c_int,C.c_int,C.c_int,P,PP]
        self.lib.f_loudness_from_levels.restype=C.c_int
    @staticmethod
    def ptrs(a): return (P*len(a))(*(row.ctypes.data_as(P) for row in a))
    def signal(self,x,tv=False,skip=.2,field=0):
        x=np.ascontiguousarray(x,dtype=np.float64); inp=Input(len(x),48000,x.ctypes.data_as(P)); k=len(x)//24 if tv else 1
        n=np.zeros(k); ns=np.zeros((240,k))
        rc=self.lib.f_loudness_from_signal(C.byref(inp),field,int(tv),skip,n.ctypes.data_as(P),self.ptrs(ns),k)
        return rc,n,ns
    def frontend(self,x,skip):
        x=np.ascontiguousarray(x,dtype=np.float64); inp=Input(len(x),48000,x.ctypes.data_as(P)); levels=np.zeros((28,1))
        rc=self.lib.f_calc_third_octave_levels(C.byref(inp),self.ptrs(levels),len(x),0,skip)
        assert rc==0
        return levels.ravel()
    def backend(self,l):
        l=np.array(l,dtype=np.float64).reshape(28,1); n=np.zeros(1); ns=np.zeros((240,1))
        rc=self.lib.f_loudness_from_levels(self.ptrs(l),1,0,0,n.ctypes.data_as(P),self.ptrs(ns))
        assert rc==1
        return n[0],ns.ravel()
cs={v:Reference(v) for v in ['022','024']}
data=[json.loads(l) for l in (OUT/'frontend-results.jsonl.txt').read_text().splitlines()]
factorial={}; ccontrols={}; skip_sensitivity={}; boundary=[]
for s in range(2,6):
    r=refs[s]['n']; rs=np.array(refs[s]['specific']); factorial[s]={}; ccontrols[s]={}; skip_sensitivity[s]={}
    for calibration in ['sqrt','cal']:
        x=np.fromfile(TMP/'inputs'/f'sig{s}-{calibration}.bin','<f8')
        sel=[a for a in data if a.get('signal')==s and a.get('calibration')==calibration]
        states={}
        for frontend,skip in [('noct',0),('annex',9600)]:
            a=next(a for a in sel if a.get('frontend')==frontend and a['skip_samples']==skip)
            n=a['n']; ns=np.array(a['specific'])
            states[frontend]={'n':n,'signed_error_sone':n-r,'signed_error_percent':100*(n-r)/r,
                'abs_error_sone':abs(n-r),'specific_max_abs_error':float(np.max(np.abs(ns-rs))),
                'specific_first_over_1e4_bark':next((round((i+1)/10,1) for i,v in enumerate(abs(ns-rs)) if v>.0001+1e-10),None)}
        states['frontend_method_delta_sone']=states['annex']['n']-states['noct']['n']
        matched={}
        for sk in [0,9600]:
            nd={front:next(a['n'] for a in sel if a.get('frontend')==front and a['skip_samples']==sk) for front in ['noct','annex']}
            matched[str(sk/48000)]={'noct_n':nd['noct'],'annex_n':nd['annex'],'filter_only_delta_sone':nd['annex']-nd['noct'],
                'noct_error_percent':100*(nd['noct']-r)/r,'annex_error_percent':100*(nd['annex']-r)/r,
                'abs_error_improvement_factor':abs(nd['noct']-r)/abs(nd['annex']-r)}
        states['matched_skip_filter_effects']=matched
        states['abs_error_improvement_factor']=states['noct']['abs_error_sone']/states['annex']['abs_error_sone']
        factorial[s][calibration]=states
        primary=next(a for a in sel if a.get('frontend')=='annex' and a['skip_samples']==9600)
        levels=cs['022'].frontend(x,.2)
        z={}
        for v,c in cs.items():
            rc,n,ns=c.signal(x);assert rc==1
            bn,bns=c.backend(primary['levels'])
            z[v]={'direct_n':n[0],'candidate_minus_c_n':primary['n']-n[0],
                'candidate_minus_c_specific_max_abs':float(np.max(abs(np.array(primary['specific'])-ns[:,0]))),
                'specific_max_error_bark':(int(np.argmax(abs(np.array(primary['specific'])-ns[:,0])))+1)/10,
                'specific_max_error_candidate':primary['specific'][int(np.argmax(abs(np.array(primary['specific'])-ns[:,0])))],
                'specific_max_error_c':float(ns[int(np.argmax(abs(np.array(primary['specific'])-ns[:,0]))),0]),
                'same_levels_c_n':bn,'candidate_backend_minus_c_n':primary['n']-bn,
                'candidate_backend_minus_c_specific_max_abs':float(np.max(abs(np.array(primary['specific'])-bns)))}
        z['candidate_vs_c_levels_max_abs_db']=float(np.max(abs(np.array(primary['levels'])-levels)))
        z['usl_024_minus_022_n']=z['024']['direct_n']-z['022']['direct_n']
        ccontrols[s][calibration]=z
        sens={}
        for front in ['noct','annex']:
            dd={str(a['skip_samples']/48000):a['n'] for a in sel if a.get('frontend')==front}
            sens[front]={'n_by_skip_s':dd,'delta_0_to_0p2_sone':dd['0.2']-dd['0.0'],
                         'delta_0_to_0p2_percent_of_primary':100*(dd['0.2']-dd['0.0'])/dd['0.2']}
        sens['noct_cropped_reset_n']=next(a['noct_crop_reset_0p2'] for a in sel if 'noct_crop_reset_0p2' in a)
        sens['noct_crop_vs_full_rms_skip_delta']=sens['noct_cropped_reset_n']-sens['noct']['n_by_skip_s']['0.2']
        swaps=next(a['band_swap_dn'] for a in sel if 'band_swap_dn' in a)
        sens['sum_band_swap_dn']=sum(swaps)
        sens['joint_noct_minus_annex']=states['noct']['n']-states['annex']['n']
        sens['nonadditivity_sone']=sum(swaps)-sens['joint_noct_minus_annex']
        skip_sensitivity[s][calibration]=sens
    factorial[s]['calibration_effect_noct']=factorial[s]['cal']['noct']['n']-factorial[s]['sqrt']['noct']['n']
    factorial[s]['calibration_effect_annex']=factorial[s]['cal']['annex']['n']-factorial[s]['sqrt']['annex']['n']
    factorial[s]['frontend_method_calibration_interaction_sone']=factorial[s]['cal']['frontend_method_delta_sone']-factorial[s]['sqrt']['frontend_method_delta_sone']
    factorial[s]['matched_skip_0p2_filter_calibration_interaction_sone']=factorial[s]['cal']['matched_skip_filter_effects']['0.2']['filter_only_delta_sone']-factorial[s]['sqrt']['matched_skip_filter_effects']['0.2']['filter_only_delta_sone']
    factorial[s]['annex_sqrt_claim_le_0p001_percent']=abs(factorial[s]['sqrt']['annex']['signed_error_percent'])<=.001
write('factorial.json',factorial);write('c-fullprecision-controls.json',ccontrols);write('skip-and-band-sensitivity.json',skip_sensitivity)

# Prefix boundary means use real signal prefixes, not a new public API claim.
x=np.fromfile(TMP/'inputs'/'sig3-sqrt.bin','<f8')
for a in data:
    if 'boundary_length' not in a: continue
    b=dict(a); rc,n,ns=cs['022'].signal(x[:a['boundary_length']],skip=a['skip_samples']/48000)
    b['official_c_return']=rc; b['official_c_n']=float(n[0]) if rc==1 else None
    b['harness_rejects_empty_rms']=a['n'] is None
    if rc==1: b['candidate_minus_c']=a['n']-n[0]
    boundary.append(b)
write('length-boundaries.json',boundary)

# Frequency-input bypass: no WAV calibration or frontends involved.
off=ROOT/'tmp/c01-material/official';p=next(off.rglob('Test signal 1.txt'))
l=[float(line.split(':')[1]) for line in p.read_text().splitlines() if ':' in line and not line.lstrip().startswith('#')]
bypass={}
for name,lev in [('annex_b_signal1',l),('all_zero_db',[0.]*28),('one_khz_sixty_db',[-60.]*16+[60.]+[-60.]*11)]:
    vals={v:c.backend(lev) for v,c in cs.items()}
    bypass[name]={'n022':vals['022'][0],'n024':vals['024'][0],
                 'delta_n':vals['024'][0]-vals['022'][0],
                 'specific_delta_max':float(np.max(abs(vals['024'][1]-vals['022'][1])))}
    if name=='annex_b_signal1':
        import openpyxl
        wb=openpyxl.load_workbook(next(off.rglob('*third octave*.xlsx')),read_only=True,data_only=True)
        rows=list(wb.worksheets[0].values); rn=float(rows[7][1]); rs=np.array([float(row[6]) for row in rows[7:247]])
        bypass[name].update(workbook_n=rn,n_error=vals['022'][0]-rn,
            specific_workbook_max_abs=float(np.max(abs(vals['022'][1]-rs))),
            rounded4_all_241_equal_workbook=bool(np.rint(vals['022'][0]*10000)==np.rint(rn*10000) and np.array_equal(np.rint(vals['022'][1]*10000),np.rint(rs*10000))))
write('bypass-negative-controls.json',bypass)

# Representative float32 quantization control: match the CLI's 2 ms sampling,
# and compare raw float64-input C against fresh float32-input C and workbooks.
precision={}
import wave
for s in [6,9,14,15]:
    p=next(off.rglob(f'Test signal {s} (*.wav'))
    with wave.open(str(p)) as w: raw=np.frombuffer(w.readframes(w.getnframes()),'<i2').astype(float)/32768
    x=raw*cal['sqrt']; xf=x.astype(np.float32).astype(float)
    ix=np.array(refs[s]['time_ticks'])//5; r=np.array(refs[s]['n']); results={}
    arrays={}
    for k,xx in [('f64',x),('f32',xf)]:
        rc,n,ns=cs['022'].signal(xx,tv=True,skip=0,field=int(s==15));assert rc==len(x)//24
        assert ix.max()<rc
        ar=n[ix];arrays[k]=ar
        results[k]={'max_abs_vs_workbook':float(np.max(abs(ar-r))),
            'rounded4_exact_workbook':int((np.rint(ar*10000)==np.rint(r*10000)).sum()),'points':len(r)}
    delta=abs(arrays['f64']-arrays['f32'])
    results['f64_minus_f32_max_abs']=float(np.max(delta))
    mi=int(delta.argmax())
    results['max_input_quantization_error_pa']=float(np.max(abs(x-xf)))
    results['max_output_delta_coordinate']={'time_s':refs[s]['time_ticks'][mi]/10000,'f64_n':float(arrays['f64'][mi]),'f32_n':float(arrays['f32'][mi]),'reference_n':float(r[mi])}
    results['round4_changes']=int((np.rint(arrays['f64']*10000)!=np.rint(arrays['f32']*10000)).sum())
    # Ensure the newly computed direct f32 path reproduces fresh CLI 4-decimal N.
    text=(TMP/'cli022'/f'sig{s}'/'Loudness.csv').read_text()
    cli=np.array([[float(v) for v in line.split(';')] for line in text.splitlines() if re.match(r'^\d',line)])
    cli_ix=np.searchsorted(np.rint(cli[:,0]*10000).astype(int),np.array(refs[s]['time_ticks']))
    results['direct_f32_round4_equals_cli']=bool(np.array_equal(np.rint(arrays['f32']*10000),np.rint(cli[cli_ix,1]*10000)))
    precision[s]=results
    print('Full-precision control complete',s,flush=True)
write('float-precision-controls.json',precision)

comparison=json.loads((OUT/'workbook-comparison.json').read_text())
for ss,scores in comparison.items():
    s=int(ss)
    for key,score in scores.items():
        for v in ['022','024']:
            old=f'annex_5percent_exceptions_{v}'
            if old in score: score[f'exploratory_shared_threshold_exceptions_{v}']=score.pop(old)
            fn='Loudness.csv' if key=='N' else 'SpecLoudness.csv'
            text=(TMP/f'cli{v}'/f'sig{s}'/fn).read_text()
            a=np.array([[float(x) for x in ln.split(';') if x.strip()] for ln in text.splitlines() if re.match(r'^\d',ln)])
            if s<=5:
                if key=='N':
                    vals=np.array([float(re.search(r'N / sone \((?:free|diffuse) field\);\s*([\d.]+)',text)[1])]); ref=np.array([refs[s]['n']]);coord=lambda i:{'signal':s,'quantity':'N'}
                else: vals=a.ravel()[-240:];ref=np.array(refs[s]['specific']);coord=lambda i:{'signal':s,'bark':round((i+1)/10,1)}
            else:
                ix=np.searchsorted(np.rint(a[:,0]*10000).astype(int),refs[s]['time_ticks'])
                col=1 if key=='N' else round(refs[s]['bark']*10)
                vals=a[ix,col];ref=np.array(refs[s]['n' if key=='N' else 'specific'])
                coord=lambda i:{'signal':s,'time_s':refs[s]['time_ticks'][i]/10000,**({'bark':refs[s]['bark']} if key=='Nprime' else {})}
            delta=np.abs(vals-ref);bad=np.flatnonzero(delta>.0001+1e-10);mi=int(delta.argmax())
            score[f'first_over_1e4_{v}']=None if not len(bad) else {**coord(int(bad[0])),'reference':float(ref[bad[0]]),'observed':float(vals[bad[0]])}
            score[f'max_error_coordinate_{v}']={**coord(mi),'reference':float(ref[mi]),'observed':float(vals[mi])}
write('workbook-comparison.json',comparison)
totals={}
for label,include in [('opus_original_coverage',lambda s,k:k=='N' or int(s)<=5),('expanded_coverage',lambda s,k:True),('added_time_specific',lambda s,k:k=='Nprime' and 6<=int(s)<=13)]:
    rows=[z for s,ss in comparison.items() for k,z in ss.items() if include(s,k)]
    totals[label]={'points':sum(z['points'] for z in rows), 'max_abs022':max(z['max_abs_022'] for z in rows),
        'max_abs024':max(z['max_abs_024'] for z in rows),'022_over_1e4':sum(z['022_over_1e4'] for z in rows),
        '024_over_1e4':sum(z['024_over_1e4'] for z in rows),
        'thresholds':{str(t):{k:sum(z['thresholds'][str(t)][k] for z in rows) for k in ['points','equal022','equal024','closer022','ties','closer024']} for t in [1,2,3,5,10]}}
write('summary.json',{'totals':totals,'stationary_0p001_percent_gate':all(x['annex_sqrt_claim_le_0p001_percent'] for x in factorial.values()),
    'stationary_frontend_c_same_input_gate_1e4':all(abs(y[v]['candidate_minus_c_n'])<=.0001 and y[v]['candidate_minus_c_specific_max_abs']<=.0001 for x in ccontrols.values() for y in x.values() for v in ['022','024']),
    'authority':'PENDING','generalization':'UNMEASURED','product_mutations':False})
print(json.dumps(totals,indent=2))
