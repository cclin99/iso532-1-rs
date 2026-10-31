# Golden data regeneration SOP (R-14)
> 對照／Pair: [中文版](GOLDEN-REGEN-SOP.zh-TW.md) · source: zh · synced 2026-11-01

`data/` is gitignored. This document is the only procedure for changing machines, recovering from a broken venv, or regenerating the golden data.
**Core idea: `tools/golden.sha256` is a per-environment contract.** The golden bytes depend on the libm of the generating machine (underneath scipy/numpy). A different SHA256 on a different machine is expected behaviour, not an error (evidence: `docs/CI-HASH-GATE-DEBUG-2026-07-10.md`).

## A. Regenerating on the same machine (broken venv / data deleted by mistake)

Prerequisite: `mosqito-1.2.1.tar.gz` in the repo root (sha256 in the header of `tools/requirements.lock`).

    bash tools/setup_env.sh                                   # 建 .venv(從 requirements.lock 安裝)+ 抓 Annex B
    .venv/Scripts/python.exe tools/gen_golden.py              # 重生 data/golden(約 5–15 分鐘)
    .venv/Scripts/python.exe tools/golden_manifest.py --verify
    cd iso532 && cargo test --test golden_core --test golden_dsp --test golden_zwst --test golden_zwtv --test annexb

All four steps passing = the chain is intact. A `--verify` failure means the environment has drifted (check the Python minor version, whether `requirements.lock` was modified, and the mosqito tarball sha256).

## B. Moving to a new machine (SHA256 mismatch expected)

1. Run the first two steps of A.
2. `--verify` is **expected to fail** (different libm). Run the golden tests instead:
   `cargo test --test golden_core --test golden_dsp --test golden_zwst --test golden_zwtv --test annexb`
3. All tests green ⇒ the golden data of the new environment is valid. Re-freeze the contract:
   `.venv/Scripts/python.exe tools/golden_manifest.py --generate`
   commit `tools/golden.sha256`; record the new environment (OS/CPU) in the commit message.
4. Any test red ⇒ this is not environment noise; it is a real regression or upstream version drift. Stop and investigate. Do not re-freeze directly.

## C. What breaks the chain (maintenance list)

| Dependency | How it is pinned |
|---|---|
| numpy/scipy versions | `tools/requirements.lock` (full pip freeze lock) |
| mosqito 1.2.1 | local tarball + sha256 (lock header) |
| Annex B wav/xlsx | SHA256 in `tools/golden.sha256`; source is the MoSQITo GitHub repo tag v1.2.1 (setup_env.sh) |
| Python minor version | 3.11 (noted in the lock header) |
| golden bytes | `tools/golden.sha256` (per-environment) |
| contract enforcement | `setup_env.sh` script guards: Python == 3.11, tarball SHA256, sanity import including openpyxl/pyuff |
