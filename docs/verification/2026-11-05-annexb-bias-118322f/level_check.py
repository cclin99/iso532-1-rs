"""Calibrated RMS level of the calibration signal and the stationary test tones (steady part vs whole file)."""
import wave, sys, pathlib, json, numpy as np
ROOT = pathlib.Path(sys.argv[1]); OFF = ROOT / "tmp/c01-material/official"
def wav(p):
    with wave.open(str(p)) as w:
        return np.frombuffer(w.readframes(w.getnframes()), "<i2").astype(float) / 32768.0, w.getframerate()
cal, fs = wav(OFF / "Annex C/calibration signal sine 1kHz 60dB.wav")
I_REF = 4e-10
factor = np.sqrt(10 ** (60 / 10) * I_REF / np.mean(cal ** 2))       # official CLI: whole-file mean square
lvl = lambda x: 10 * np.log10(np.mean(x ** 2) / I_REF)
nz = np.flatnonzero(cal)
env = np.abs(cal)
out = {"calibration": {"samples": len(cal), "seconds": len(cal) / fs, "first_nonzero": int(nz[0]), "last_nonzero": int(nz[-1]),
       "peak": float(env.max()), "factor": float(factor),
       "level_whole_after_cal_dB": float(lvl(cal * factor)),
       "level_middle_80pct_after_cal_dB": float(lvl(cal[len(cal)//10: -len(cal)//10] * factor)),
       "level_first_100ms_dB": float(lvl(cal[:fs//10] * factor)), "level_last_100ms_dB": float(lvl(cal[-fs//10:] * factor))}}
for s, name in [(2, "250 Hz 80 dB"), (3, "1 kHz 60 dB"), (4, "4 kHz 40 dB"), (5, "pinknoise 60 dB")]:
    x, _ = wav(OFF / f"Annex B.3/Test signal {s} ({name}).wav")
    x = x * factor
    q = len(x) // 10
    out[f"sig{s}"] = {"nominal": name, "level_whole_dB": float(lvl(x)), "level_middle_80pct_dB": float(lvl(x[q:-q])),
                      "first_nonzero": int(np.flatnonzero(x)[0]), "seconds": len(x) / fs}
json.dump(out, open(ROOT / "tmp/bias-2026-11-05/level-check.json", "w"), indent=1)
print(json.dumps(out, indent=1))
