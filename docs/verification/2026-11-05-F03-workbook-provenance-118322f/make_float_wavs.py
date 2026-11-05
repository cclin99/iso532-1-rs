"""Write Annex B signals 2-25 as 32-bit IEEE-float WAVs in pascals, scale int16/32768 * 2*sqrt(2)."""
import wave, struct, sys, pathlib, json, hashlib, numpy as np
ROOT = pathlib.Path(sys.argv[1]); OUT = pathlib.Path(sys.argv[2]); OUT.mkdir(parents=True, exist_ok=True)
OFF = ROOT / "tmp/c01-material/official"; meta = {}
for s in range(2, 26):
    src = next(OFF.rglob(f"Test signal {s} (*.wav"))
    with wave.open(str(src)) as w:
        assert (w.getnchannels(), w.getsampwidth(), w.getframerate()) == (1, 2, 48000)
        x = np.frombuffer(w.readframes(w.getnframes()), "<i2").astype(np.float64) / 32768.0 * 2 * np.sqrt(2)
    data = x.astype("<f4").tobytes()
    hdr = b"RIFF" + struct.pack("<I", 36 + len(data)) + b"WAVE" + b"fmt " + struct.pack("<IHHIIHH", 16, 3, 1, 48000, 48000 * 4, 4, 32) + b"data" + struct.pack("<I", len(data))
    p = OUT / f"sig{s}.wav"; p.write_bytes(hdr + data)
    meta[s] = {"source": src.name, "source_sha256": hashlib.sha256(src.read_bytes()).hexdigest(), "float_wav_sha256": hashlib.sha256(p.read_bytes()).hexdigest(), "samples": len(x)}
json.dump(meta, open(OUT / "float-wavs.json", "w"), indent=1); print(len(meta), "written")
