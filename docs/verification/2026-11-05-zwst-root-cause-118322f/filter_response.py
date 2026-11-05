"""Frequency responses of the two third-octave filter banks actually used by iso532:
NOCT_SOS (MoSQITo-compatible ZWST front end, applied at 48 kHz / NOCT_DECIM_Q) and the
ISO 532-1 Annex A reference filters (TOB_B, TOB_DELTA, TOB_GAIN), both parsed from the sources."""
import re, sys, json, pathlib, numpy as np
from scipy.signal import sosfreqz
ROOT = pathlib.Path(sys.argv[1])
num = r"-?\d+\.?\d*(?:[eE][-+]?\d+)?"
def floats(txt): return [float(x) for x in re.findall(num, txt)]
noct_src = (ROOT / "iso532/src/tables_noct.rs").read_text()
q = [int(x) for x in re.search(r"NOCT_DECIM_Q: \[usize; 28\] = \[([^\]]+)\]", noct_src).group(1).split(",")]
body = noct_src.split("pub const NOCT_SOS")[1].split("pub const CHEBY_QS")[0]
nv = floats(body.split("=", 1)[1]); 
# each Sos: b[3], a[2] (a0 implicit 1) -> 5 numbers per section, 3 sections per band
assert len(nv) == 28 * 3 * 5, len(nv)
noct = np.array(nv).reshape(28, 3, 5)
tab = (ROOT / "iso532/src/tables.rs").read_text()
dv = floats(tab.split("pub const TOB_DELTA")[1].split("=", 1)[1].split(";")[0])[ : 28 * 3 * 2]
delta = np.array(dv).reshape(28, 3, 2)
gain = np.array(floats(tab.split("pub const TOB_GAIN")[1].split("=", 1)[1].split(";")[0])[:28])
TOB_B = np.array([[1, 2, 1], [1, 0, -1], [1, -2, 1]], float)
FS = 48000.0
out = {}
for band in range(28):
    fc = 10 ** ((band - 16) / 10) * 1000
    iso = np.array([[*TOB_B[s], 1.0, -2 - delta[band, s, 0], 1 - delta[band, s, 1]] for s in range(3)])
    iso[0, :3] *= gain[band]
    nsos = np.array([[*noct[band, s, :3], 1.0, *noct[band, s, 3:]] for s in range(3)])
    fsn = FS / q[band]
    f = np.geomspace(fc / 8, min(fc * 8, 0.49 * fsn), 20000)
    _, hi = sosfreqz(iso, worN=f, fs=FS); _, hn = sosfreqz(nsos, worN=f, fs=fsn)
    pi_, pn = np.abs(hi) ** 2, np.abs(hn) ** 2
    enbw_i = np.trapezoid(pi_, f); enbw_n = np.trapezoid(pn, f)
    exact = fc * (2 ** (1 / 6) - 2 ** (-1 / 6))
    at = lambda p, x: float(10 * np.log10(np.interp(x, f, p)))
    out[band] = {"fc": fc, "decim_q": q[band],
                 "gain_at_fc_dB": {"iso": at(pi_, fc), "noct": at(pn, fc)},
                 "enbw_over_exact_third_octave": {"iso": enbw_i / exact, "noct": enbw_n / exact},
                 "enbw_ratio_noct_over_iso_dB": float(10 * np.log10(enbw_n / enbw_i)),
                 "atten_at_lower_neighbour_centre_dB": {"iso": at(pi_, fc / 10 ** 0.1), "noct": at(pn, fc / 10 ** 0.1)},
                 "atten_at_upper_neighbour_centre_dB": {"iso": at(pi_, fc * 10 ** 0.1), "noct": at(pn, fc * 10 ** 0.1)}}
json.dump(out, open(sys.argv[2], "w"), indent=1)
print("band   fc     q | ENBW/exact iso  noct  (noct-iso dB) | response at lower-neighbour centre iso / noct dB | upper iso / noct")
for b, o in out.items():
    if b < 6: continue
    e = o["enbw_over_exact_third_octave"]; lo = o["atten_at_lower_neighbour_centre_dB"]; up = o["atten_at_upper_neighbour_centre_dB"]
    print(f"{b:3d} {o['fc']:8.1f} {o['decim_q']:2d} | {e['iso']:.4f} {e['noct']:.4f} ({o['enbw_ratio_noct_over_iso_dB']:+.3f}) | {lo['iso']:7.2f} / {lo['noct']:7.2f} | {up['iso']:7.2f} / {up['noct']:7.2f}")
