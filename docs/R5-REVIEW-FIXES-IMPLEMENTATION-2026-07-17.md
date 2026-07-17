# R5 審查修正實作紀錄（2026-07-17）

依 `docs/R5-REVIEW-FIXES-2026-07-17.md` 完成 P0 1–6、P1 7–9，並一併完成兩項 P2 防呆。R5 原始實作與本次審查修正維持同一個 v1 凍結收尾範圍。

## 實作摘要

- FFI v1 契約：補齊 opaque handle、48 kHz/24-sample latency、執行緒限制、out_cap 拒收、panic poison、flush 後生命週期與 frame flags/warmup 文件；`ISO532_ERR_INTERNAL (-4)` 明確涵蓋內部不變量與不足 out_cap 且不部分寫入兩種語意。
- cbindgen 0.29.4 重生 `include/iso532.h`；stream 函式簽名與 `Iso532StreamFrame` 佈局未變，本輪只補契約註解。連續重生 SHA256 均為 `63BBB016CFB7B195D2DDD20D96A6F600D078DBB80593117DF2F9D1D7A6DB1D6D`。
- Rust stream 契約：凍結 `N_WARMUP_FRAMES == 580`；chunk {1,7,24,64,480,4096,LCG} 與 reset 改為逐欄 `to_bits()`/整數位元級比較。
- FFI 測試：補不足 out_cap 拒收但 handle 可續用、`iso532_stream_max_frames` 轉發與 `_reserved` offset 互鎖。
- Python：新增 `iso532.sone2phon`，以 Python 重述兩段公式掃描 0..20 sone（step 0.02、atol 1e-12）並驗 1/2/4 sone anchors。
- C smoke：實際呼叫 `iso532_stream_max_frames(480)` 檢查靜態容量，並輸出前三幀的 index/n/phon/flags。
- P2：auto-dispatch benchmark 每輪明確解除 force-scalar；scalar 測試直接斷言 AVX2 dispatch 已停用。
- 計畫偏差：`main_loudness_clamped` 刻意維持 `pub(crate)`，足供 stream 內部使用且不擴張公開 Rust API。

## TDD／BDD 證據

- RED：先加入 Python 公式互驗，得到 `AttributeError: module 'iso532' has no attribute 'sone2phon'`；確認驗收 6 的缺口可重現。
- Characterization：先加入 warmup 凍結、bitwise chunk/reset、FFI out_cap/max-frames/layout tests；這些測試立即通過，證明既有行為正確，目的為將 v1 契約固定而非修正產品行為。
- GREEN：加入 PyO3 出口並重建 extension 後，focused Python 公式測試 1/1、完整 smoke 7/7；Rust stream 9 passed + 1 ignored timing、scalar 1/1；FFI focused stream 5/5。
- BDD — Given out_cap 小於 max_frames，When push 480 samples，Then 回 -4、written=0，且同一 handle 以足量 cap 再 push 成功。
- BDD — Given 任意支援的 chunk 分割或 reset，When 產生 StreamFrame，Then n/n_phon/index/flags 與基準逐位一致。
- BDD — Given 0..20 sone 與 1/2/4 anchors，When Python 呼叫 Rust `sone2phon`，Then 與 Python 重述公式在 atol 1e-12 內一致。
- BDD — Given C caller only knows chunk_len，When 先查 max_frames 再 push/flush，Then 500 幀完成且前三幀可由 v1 frame 佈局讀取。

## CI 等價驗證結果

- `iso532`: `cargo test` 全部通過（stream 9 passed + 1 ignored manual timing；allocation/no-rayon/scalar 各 1 passed）；`cargo fmt --check`、`cargo clippy --all-targets -- -D warnings` 通過。
- frozen R1 hashes 12/12 逐字相同：
  - `sine_1k_60`: `0b10971021634b4e / 62496b610f7c223d / f076bcb342595537`
  - `pulse_1k_70`: `b92a2b970de3067f / bdab430b961720f0 / f076bcb342595537`
  - `step_60_80`: `40ac75b0dcaed5a8 / 2fdc839b4f702621 / f076bcb342595537`
  - `annexb_sig10`: `83da1e1c06d5296c / 3c2b914686402b54 / f076bcb342595537`
- Python contract：`n=0x44e6822074554786 time=0xf076bcb342595537 frames=500`。
- `iso532-ffi`: `cargo test --features test-panic` 15/15；fmt/clippy all-features 通過；release build 與 VS 2022 x64 MSVC C smoke 通過，輸出前三幀後為 `smoke ok: frames=500 zwtv_n0=3.779000`。
- `iso532-py`: cargo fmt/clippy 通過；maturin release wheel 在乾淨 `D:/tmp/iso532-r5-ci` venv 安裝後 smoke 7/7；collection 25；`ISO532_REQUIRE_PARITY=1` formal parity 18/18、0 skipped。
- golden chain：`golden_manifest.py --verify` 為 175/175；Git Bash `bash -n tools/setup_env.sh` 通過。
- `git diff --check` 通過。

## 環境偏差

- Windows restricted-token 不能直接執行一般 `apply_patch`，依既有 repo SOP 以 Codex 官方 `--codex-run-as-apply-patch` 在工作區權限下套用，並逐次讀回/測試。
- 系統 `bash.exe`（WSL）回 `E_ACCESSDENIED`；Git Bash 在 sandbox 內亦因 CreateFileMapping error 5 失敗，提升權限後唯讀 `bash -n` 通過。
- 未限制 BLAS/OMP 執行緒的 pytest collection 曾在 mosqito/SciPy import 階段異常；依 R5 既有正式驗證條件將 OMP/MKL/OpenBLAS/NumExpr 固定為 1 後，collection 25 與 strict parity 18/18 穩定通過。
- 本輪執行的是與 `.github/workflows/ci.yml` 對齊並加強的本機 Windows CI gates；遠端 Windows/Linux jobs 需在 push 後由 GitHub Actions 觀察，不在 commit 前可觀測範圍。
