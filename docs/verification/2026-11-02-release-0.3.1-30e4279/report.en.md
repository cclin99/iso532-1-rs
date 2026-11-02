# 0.3.1 Independent release acceptance

**ACCEPT** — No tag blocker within this brief.

2026-11-02 (Asia/Taipei). Execution is one day after the planned 2026-11-01; delivery uses the actual date and does not overwrite another round.

## Item results

| §2 | Item | Result | Evidence summary |
|---|---|---|---|
| 1 | Freeze | PASSED | Fixed archive 30e427963da88db8b23e82cf612f047f36cd164b; baseline peeled commit 62e46ca7d6ac65df7c4a4db8df8380e30234e267. 275 tracked source files hashed. |
| 2 | Repository gates | PASSED | Rust 138 passed / 0 failed / 3 ignored; manifest 175 files; formal pytest 69 passed. fmt, both clippy commands, doc pairs and docs redaction pass. |
| 3 | C-02 | PASSED | Combined C01/C02 independent cases: Rust 66, C 52, Python 48; all pass. First bad index, precedence, C sentinels, finite boundaries and streaming next-frame/residual flags verified. |
| 4 | C-01 | PASSED | 16 lengths; official signals [3, 5, 10], prefixes [4801, 24013, 47927]; n/time/all 240 Bark rows bitwise equal. Custom stream chunks include 1 and >96 samples. |
| 5 | V-01 | PASSED | 21 direct + 19 corrupt-copy controls pass. 5 curves / 982 points; minimum margin 0.08513610649320266 sone/Bark at signal 3 specific row 66 (zero based). |
| 6 | Finite-input stability | PASSED | 8 inputs, 40 arrays, 4,720,928 binary64 values equal; first difference null. All 12 frozen Windows hash values match. |
| 7 | Artifacts | PASSED | All 4 artifact hashes match record and SHA256SUMS; committed header bytes match. 9 exports match baseline; import library bytes match. Clean wheel version 0.3.1, both NaN calls raise ValueError. |
| 8 | Record consistency | PASSED | Version/date/changelog/commit table match; CI 41278186406 at fixed SHA has 6 successful jobs. Validation counts match release record. |

## Findings and current interpretation

- Initial Windows tar.exe extraction mangled Unicode document paths and failed doc pairing. Re-extraction of the same archive with Python tarfile and git-tree inventory resolved it; doc pairing passes with 10 existing unpaired-backlog warnings. Rust/C/Python source bytes did not change.
- core.autocrlf=true produced a CRLF archive header. The distributed header differs from that archive copy but is byte-identical to the fixed commit's Git blob. The archive difference is EOL-only; normalization did not substitute for the committed-blob comparison.
- Initial maturin failed because the isolated venv lacked its console script; copying the same-version executable enabled the release build. Formal pytest was rerun after that build; initial pytest is not formal evidence. Dependencies came through a .pth to the existing golden venv, while the tested extension resides in the isolated venv. A separate fresh wheel venv without .pth verified installation.
- Subnormals and ±0 succeed; 1e300 returns LevelExceeds120dB (C code 1), not the nonfinite rejection. The C ABI exposes no index; Rust/Python verify index semantics.
- The initial full Rust run used Windows dump-only mode. A separate HASH_GATE_DUMP_ONLY=0 strict hash test passes, and the independent script compares all 12 constants. The reproduction runner now uses strict mode.
- C environment setup emitted a missing-vswhere message; subsequent MSVC compilation and execution succeeded.

## Scope and delivery

There are 7 available WAVs: official signals 3/5/10 plus 4 auxiliary fixtures; the 3 s contract is additional. This is not requalification of all 25 signals. Signal 3's 44.1→48 kHz preprocessing and hashes are recorded. V-01 margins cover the 5 available official reference curves, not unavailable curves. These boundaries do not block this brief's tag acceptance.

Commands, harnesses, per-case hex/first differences, and raw input/binary/source hashes are in results.json, contracts/ and numerics/. Versions are in freeze.json and sub-results: Rust/cargo 1.99.1, Python 3.11.9, MSVC 19.44.35228; gate NumPy 2.4.6, numerics NumPy 2.4.4. Shared HEAD is 4e615bfb3b5be39db8074f34e7c6208feaa35aab; initially clean, with only this round's untracked folder afterward. The v0.3.0 annotated tag object and peeled commit are separate fields.

F-03, stationary frontend, zero-padding official C reference, MoSQITo timing, manual antivirus, all-25-signal requalification and a new Linux run are outside scope. Existing pytest parity executes as required, but independent numerical acceptance does not use MoSQITo as oracle. Historical reports do not supply passed results. No tested source/tests/goldens changed; no stage, commit, push or tag was performed.

Formal gates use actual process exits in formal-gates.json, with pytest counts parsed from terminal summaries. All 5 missing/failed/skipped and related negative controls reject ACCEPT (summary-negative-controls.json). Delivery text uses LF. See delivery-check.md for redaction/text inventory. delivery-integrity.json hashes post-redaction delivery text only and excludes itself; raw binary/WAV/source hashes retain their original meaning. Main-agent review follows; update the release record's independent-verification section from this English report before tagging.
