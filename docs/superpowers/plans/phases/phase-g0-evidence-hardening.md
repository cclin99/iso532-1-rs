# G0' 證據硬化 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 R3(C-ABI/Python)開工前,把 2026-07-10 架構風險報告中仍然成立的三個小型證據缺口收口:hash gate 自動化(R-13)、benchmark baseline 分離(R-10)、最小 CI 與 SIMD silent-skip 防護(R-12)。

**Architecture:** 不改任何 DSP/演算法程式碼。新增兩個 hash assertion 測試(golden 輸入版鎖定既有 R4 snapshot、合成輸入版供 CI 使用)、把 Criterion group 名稱依 rayon 執行緒數分離、新增 GitHub Actions workflow 只跑不需要 `data/`(164 MB,gitignored)的測試集,並以 `REQUIRE_AVX2` 環境變數把 SIMD 測試的 silent skip 變成 CI 上的硬失敗。

**Tech Stack:** Rust 1.93 / cargo test / Criterion 0.5 / rayon 1.12 / GitHub Actions / PowerShell。

**背景事實(執行前不需重新驗證):**

- 工作目錄:`D:\ISO532`,crate 在 `iso532/`(所有 cargo 命令在 `iso532/` 下執行)。
- `data/` 整個目錄被 `.gitignore` 排除,golden 測試(`golden_*.rs`、`annexb.rs`)在沒有本機資料的環境會 panic,因此 **CI 只能跑** `--lib`、`--doc` 與 `simd_parity`、`simd_dispatch`、`determinism`、`api_errors`、`hash_gate` 這些不讀 `data/` 的測試。
- `iso532::simd::set_force_scalar` 是 **process-global** 旗標;同一個 test binary 內多個 `#[test]` 平行執行會互相污染。慣例見 `iso532/tests/determinism.rs:77-79`(一個 binary 只放一個 `#[test]`)。
- R4 已合入 main(`a16b41f`/`0aff1bf`/`9158f98`/`e96dffa`),bitwise snapshot hash 記錄在 `docs/superpowers/plans/phases/phase-r4-band-parallel.md:69-72`,是 **auto dispatch(AVX2)** 路徑的值。determinism 測試已保證 Rayon/Sequential 逐位相同,所以這些 hash 不受執行緒數影響。
- 目前 `cargo test` 為 33 個非忽略測試 + 2 doctests 全綠;`cargo clippy --all-targets -- -D warnings` 與 `cargo fmt --check` 全綠。

---

### Task 1: 工作樹清理與基線 commit

**Files:**
- Modify: `.gitignore`
- Delete: `target-bench-before/`、`target-bench-beforeoSAJNC/`(未追蹤的 benchmark 殘留)
- Commit: `docs/ARCHITECTURE-PERFORMANCE-RISK-REPORT-2026-07-10.md`、`docs/MOSQITO-VS-ISO-BASELINE-STRATEGY-2026-07-05.md`、`docs/SYSTEM-DESIGN-QA-2026-07-06.md`、`docs/ISO532-SYSTEM-OVERVIEW-QA.html`、`docs/DESIGN-DEVELOPMENT-2026-07-04.md`(已修改)

- [ ] **Step 1: 刪除 benchmark 殘留目錄**

在 repo 根目錄 `D:\ISO532` 執行:

```powershell
Remove-Item -Recurse -Force target-bench-before, target-bench-beforeoSAJNC
```

- [ ] **Step 2: 更新 .gitignore**

把 `.gitignore` 全文改為(補結尾換行、加 bench 殘留樣式與 `.claude/`):

```gitignore
*.tar
*.tar.gz
mosqito-1.2.1/
.venv/
target/
target-bench-*/
data/
AGENTS.md
.claude/
```

- [ ] **Step 3: 確認 git status 乾淨度**

Run: `git status --short`
Expected: 只剩 `M .gitignore`、`M docs/DESIGN-DEVELOPMENT-2026-07-04.md` 與四個 `?? docs/...` 檔案(`.claude/`、`target-bench-*` 不再出現)。

- [ ] **Step 4: Commit**

```powershell
git add .gitignore docs/
git commit -m "docs: commit review reports, ignore bench leftovers and .claude"
```

---

### Task 2: golden 輸入 hash 自動 assertion(R-13,鎖定 R4 snapshot)

把只會列印、預設 `#[ignore]` 的 hash helper 升級成自動 assert 的常數比對測試。既有 12 個 hash 是 AVX2 auto-dispatch 路徑的值,所以測試以 AVX2 gate 保護;`golden_zwtv.rs` 這個 binary 內沒有任何測試翻動 `FORCE_SCALAR`,平行執行安全。

**Files:**
- Modify: `iso532/tests/common/mod.rs`(新增 `require_avx2_or_skip`)
- Modify: `iso532/tests/golden_zwtv.rs`(新增常數與測試;保留原 `dump_zwtv_output_hashes` helper 供未來更新 snapshot)

- [ ] **Step 1: 在 common/mod.rs 加入 AVX2 gate helper**

在 `iso532/tests/common/mod.rs` 檔案結尾加入:

```rust
/// Returns true when AVX2 is available. When it is not: fails hard if the
/// REQUIRE_AVX2 env var is set (CI anti-silent-skip gate), otherwise logs
/// and returns false so the caller can skip.
#[allow(dead_code)]
pub fn require_avx2_or_skip(ctx: &str) -> bool {
    if iso532::simd::avx2_available() {
        return true;
    }
    assert!(
        std::env::var_os("REQUIRE_AVX2").is_none(),
        "{ctx}: REQUIRE_AVX2 is set but AVX2 is unavailable on this runner"
    );
    eprintln!("{ctx}: AVX2 not available; skipping");
    false
}
```

- [ ] **Step 2: 在 golden_zwtv.rs 加入 snapshot 常數與測試**

在 `iso532/tests/golden_zwtv.rs` 的 `dump_zwtv_output_hashes` 之前加入(hash 值取自 `phase-r4-band-parallel.md:69-72`,逐字轉錄):

```rust
/// Bitwise output snapshot recorded after R4 (commit e96dffa) on the AVX2
/// auto-dispatch path. Rayon/Sequential are bitwise-equal (see determinism
/// tests), so these values do not depend on thread count. Regenerate with
/// `cargo test --test golden_zwtv dump_zwtv_output_hashes -- --ignored --nocapture`.
const R4_SNAPSHOT_AVX2: [(&str, u64, u64, u64); 4] = [
    (
        "sine_1k_60",
        0x0b10971021634b4e,
        0x62496b610f7c223d,
        0xf076bcb342595537,
    ),
    (
        "pulse_1k_70",
        0xb92a2b970de3067f,
        0xbdab430b961720f0,
        0xf076bcb342595537,
    ),
    (
        "step_60_80",
        0x40ac75b0dcaed5a8,
        0x2fdc839b4f702621,
        0xf076bcb342595537,
    ),
    (
        "annexb_sig10",
        0x83da1e1c06d5296c,
        0x3c2b914686402b54,
        0xf076bcb342595537,
    ),
];

#[test]
fn zwtv_output_hashes_match_r4_snapshot() {
    if !require_avx2_or_skip("zwtv_output_hashes_match_r4_snapshot") {
        return;
    }
    for (sig, want_n, want_spec, want_time) in R4_SNAPSHOT_AVX2 {
        let x = read_bin(sig, "sig.bin");
        let r = loudness_zwtv(&x, 48000.0, FieldType::Free).unwrap();
        assert_eq!(fnv1a_f64(&r.n), want_n, "{sig}: N hash drifted");
        assert_eq!(
            fnv1a_f64(&r.n_specific),
            want_spec,
            "{sig}: N_specific hash drifted"
        );
        assert_eq!(fnv1a_f64(&r.time_axis), want_time, "{sig}: time hash drifted");
    }
}
```

`use common::*;` 已存在(檔案第 2 行),`require_avx2_or_skip`、`read_bin`、`fnv1a_f64` 都經由它引入,不需要新增 import。

- [ ] **Step 3: 執行新測試確認通過**

Run(在 `iso532/`): `cargo test --test golden_zwtv zwtv_output_hashes_match_r4_snapshot`
Expected: `test zwtv_output_hashes_match_r4_snapshot ... ok`(1 passed)。若 FAIL,表示現行 main 輸出與 R4 snapshot 不符——**停止並回報**,不得更新常數蒙混。

- [ ] **Step 4: 全套測試回歸**

Run: `cargo test`
Expected: 34 個非忽略測試通過(原 33 + 本測試),0 failed。

- [ ] **Step 5: Commit**

```powershell
git add iso532/tests/common/mod.rs iso532/tests/golden_zwtv.rs
git commit -m "test: assert zwtv output hashes against frozen R4 snapshot"
```

---

### Task 3: 合成訊號 hash gate(R-13 的 CI 可執行版)

golden 輸入的 hash 測試在 CI 上跑不了(沒有 `data/`)。此 task 新增一個用合成訊號的 bitwise gate,scalar 與 AVX2 兩條 backend 路徑各自凍結常數,CI 與本機都能執行。因為要翻動 `FORCE_SCALAR`,必須放在**獨立的 test binary**,且整個檔案只有一個非忽略 `#[test]`(同 `determinism.rs` 的慣例)。

**Files:**
- Create: `iso532/tests/hash_gate.rs`

- [ ] **Step 1: 建立 hash_gate.rs(常數先填 0 作為佔位,下一步凍結)**

```rust
#[allow(dead_code)]
mod common;

use iso532::{loudness_zwtv, simd, FieldType};

const FS: f64 = 48_000.0;

// Frozen bitwise snapshots of (fnv1a(n), fnv1a(n_specific), fnv1a(time_axis))
// for the synthetic signal below, one per backend. Scalar and AVX2 differ in
// ULP because FMA rounds once; each path must stay bitwise-stable against
// its own snapshot (refactor invariance, see risk report §8.4).
// Regenerate: set both to (0, 0, 0), run
// `cargo test --test hash_gate -- --nocapture`, copy the printed values.
const EXPECTED_SCALAR: (u64, u64, u64) = (0, 0, 0);
const EXPECTED_AVX2: (u64, u64, u64) = (0, 0, 0);

fn synth_signal() -> Vec<f64> {
    (0..48_000)
        .map(|i| {
            let t = i as f64 / FS;
            0.25 * (2.0 * std::f64::consts::PI * 440.0 * t).sin()
                + 0.10 * (2.0 * std::f64::consts::PI * 1_760.0 * t).sin()
                + 0.04 * (2.0 * std::f64::consts::PI * 6_400.0 * t).sin()
        })
        .collect()
}

fn run_hashes(signal: &[f64]) -> (u64, u64, u64) {
    let r = loudness_zwtv(signal, FS, FieldType::Free).unwrap();
    (
        common::fnv1a_f64(&r.n),
        common::fnv1a_f64(&r.n_specific),
        common::fnv1a_f64(&r.time_axis),
    )
}

// FORCE_SCALAR is process-global. Keep this integration test file to one
// #[test] so flag changes cannot race another test in this binary.
#[test]
fn zwtv_backend_hashes_match_frozen_snapshot() {
    let signal = synth_signal();

    simd::set_force_scalar(true);
    let scalar = run_hashes(&signal);
    simd::set_force_scalar(false);
    eprintln!(
        "scalar: n={:#018x} spec={:#018x} time={:#018x}",
        scalar.0, scalar.1, scalar.2
    );
    assert_eq!(scalar, EXPECTED_SCALAR, "scalar backend hash drifted");

    if common::require_avx2_or_skip("zwtv_backend_hashes avx2") {
        let avx2 = run_hashes(&signal);
        eprintln!(
            "avx2:   n={:#018x} spec={:#018x} time={:#018x}",
            avx2.0, avx2.1, avx2.2
        );
        assert_eq!(avx2, EXPECTED_AVX2, "avx2 backend hash drifted");
    }
}
```

- [ ] **Step 2: 執行一次取得實際 hash(預期失敗)**

Run: `cargo test --test hash_gate -- --nocapture`
Expected: FAIL 於 `scalar backend hash drifted`,stderr 印出 `scalar: n=0x... spec=0x... time=0x...`。記下 scalar 三個值;然後把 `EXPECTED_SCALAR` 填入後**再跑一次**取得 avx2 三個值(第一次執行會在 scalar assert 就中止,看不到 avx2 輸出)。

- [ ] **Step 3: 凍結兩組常數**

把 Step 2 取得的實際值填入 `EXPECTED_SCALAR` 與 `EXPECTED_AVX2`(保持 `0x` 十六進位字面值)。

- [ ] **Step 4: 執行確認通過與穩定性**

Run: `cargo test --test hash_gate`(連跑兩次)
Expected: 兩次都 `test zwtv_backend_hashes_match_frozen_snapshot ... ok`。

- [ ] **Step 5: 全套回歸**

Run: `cargo test`
Expected: 35 個非忽略測試通過,0 failed。

- [ ] **Step 6: Commit**

```powershell
git add iso532/tests/hash_gate.rs
git commit -m "test: add per-backend bitwise hash gate on synthetic signal"
```

---

### Task 4: simd_parity 的 silent skip 加上 REQUIRE_AVX2 硬失敗(R-12)

`simd_parity.rs` 兩個測試在無 AVX2 機器直接 `return`,CI 上會綠得毫無意義。改用 Task 2 的 `require_avx2_or_skip`:本機無 AVX2 仍可 skip,但 CI 設 `REQUIRE_AVX2=1` 時必須硬失敗。

**Files:**
- Modify: `iso532/tests/simd_parity.rs:9-14` 與 `iso532/tests/simd_parity.rs:33-38`

- [ ] **Step 1: 替換兩處 skip 判斷**

`filter_bank_avx2_matches_scalar` 開頭(原 11-14 行):

```rust
    if !common::require_avx2_or_skip("filter_bank_avx2_matches_scalar") {
        return;
    }
```

`nl_loudness_avx2_matches_scalar` 開頭(原 35-38 行)同樣替換:

```rust
    if !common::require_avx2_or_skip("nl_loudness_avx2_matches_scalar") {
        return;
    }
```

檔案第 4 行 `use common::assert_close;` 保持不變(`require_avx2_or_skip` 以 `common::` 路徑呼叫,不需額外 import)。

- [ ] **Step 2: 驗證兩種模式**

Run: `cargo test --test simd_parity`
Expected: 2 passed(本機有 AVX2,走正常路徑)。

Run(驗證 gate 在本機不誤觸,因為 AVX2 可用時 REQUIRE_AVX2 不生效):

```powershell
$env:REQUIRE_AVX2='1'; cargo test --test simd_parity; Remove-Item Env:REQUIRE_AVX2
```

Expected: 仍 2 passed。

- [ ] **Step 3: 全套回歸 + lint**

Run: `cargo test && cargo clippy --all-targets -- -D warnings && cargo fmt --check`
Expected: 全綠。

- [ ] **Step 4: Commit**

```powershell
git add iso532/tests/simd_parity.rs
git commit -m "test: fail simd parity hard when REQUIRE_AVX2 is set"
```

---

### Task 5: benchmark baseline 依執行緒數分離(R-10)

Criterion 的 group/ID 目前不含執行緒數,MT 與 ST 連跑會共用 baseline,`change:` 欄位把執行緒差異誤報成 regression/improvement。把 group 名稱加上 `t{N}` 後綴(`rayon::current_num_threads()`,rayon 已在 `[dependencies]`,bench 可直接使用),兩種模式的歷史彼此隔離。

**Files:**
- Modify: `iso532/benches/loudness.rs`

- [ ] **Step 1: 加入 thread suffix helper 並改兩個 group 名稱**

在 `auto_dispatch_label()`(第 22-28 行)之後加入:

```rust
fn thread_suffix() -> String {
    format!("t{}", rayon::current_num_threads())
}
```

第 32 行改為:

```rust
    let mut group = c.benchmark_group(format!("filter_bank_10s_{}", thread_suffix()));
```

第 60 行改為:

```rust
    let mut group = c.benchmark_group(format!("zwtv_10s_{}", thread_suffix()));
```

- [ ] **Step 2: 編譯驗證(不必等完整 bench)**

Run: `cargo bench --bench loudness -- --test`
Expected: 以 test 模式快速執行,輸出的 benchmark 名稱形如 `filter_bank_10s_t12/scalar/480000`、`zwtv_10s_t12/avx2/480000`(t 後數字依機器而定),exit 0。

- [ ] **Step 3: ST 模式名稱驗證**

```powershell
$env:RAYON_NUM_THREADS='1'; cargo bench --bench loudness -- --test; Remove-Item Env:RAYON_NUM_THREADS
```

Expected: 名稱變為 `..._t1/...`,exit 0。

- [ ] **Step 4: Commit**

```powershell
git add iso532/benches/loudness.rs
git commit -m "bench: separate criterion baselines by rayon thread count"
```

---

### Task 6: bench 執行腳本與環境 metadata(R-10 的環境紀錄半邊)

風險報告要求效能數字附 commit/rustc/CPU/env。新增一個 PowerShell wrapper,跑 bench 前後把 metadata 寫進 `iso532/target/criterion/`,讓每次量測都可追溯。

**Files:**
- Create: `tools/bench.ps1`

- [ ] **Step 1: 建立 tools/bench.ps1**

```powershell
# Runs the loudness Criterion benchmark and records environment metadata
# alongside the results. Usage:
#   powershell -File tools/bench.ps1            # default thread pool (MT)
#   powershell -File tools/bench.ps1 -Threads 1 # single-thread baseline
param([int]$Threads = 0)
$ErrorActionPreference = 'Stop'

Set-Location (Join-Path $PSScriptRoot '..\iso532')

if ($Threads -gt 0) { $env:RAYON_NUM_THREADS = "$Threads" }
try {
    cargo bench --bench loudness
    if ($LASTEXITCODE -ne 0) { throw "cargo bench failed with exit code $LASTEXITCODE" }
}
finally {
    Remove-Item Env:RAYON_NUM_THREADS -ErrorAction SilentlyContinue
}

$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$metaDir = 'target\criterion'
New-Item -ItemType Directory -Force -Path $metaDir | Out-Null
@(
    "date: $(Get-Date -Format o)"
    "commit: $(git rev-parse HEAD)"
    "dirty: $([bool](git status --porcelain))"
    "rustc: $(rustc -V)"
    "cpu: $((Get-CimInstance Win32_Processor).Name)"
    "logical_processors: $((Get-CimInstance Win32_ComputerSystem).NumberOfLogicalProcessors)"
    "rayon_threads_arg: $(if ($Threads -gt 0) { $Threads } else { 'default' })"
) | Out-File (Join-Path $metaDir "bench-meta-$stamp.txt") -Encoding utf8

Write-Host "metadata written to $metaDir\bench-meta-$stamp.txt"
```

- [ ] **Step 2: 冒煙測試**

Run(在 repo 根目錄): `powershell -File tools/bench.ps1 -Threads 1`
Expected: bench 完整跑完(約數分鐘),結尾印出 `metadata written to ...`;開啟該 txt 確認七個欄位都有值。

- [ ] **Step 3: Commit**

```powershell
git add tools/bench.ps1
git commit -m "bench: add wrapper script recording env metadata per run"
```

---

### Task 7: 最小 CI workflow(R-12 收口)

repo 目前完全沒有 CI。新增 GitHub Actions:Windows + Ubuntu 矩陣,跑 fmt/clippy 與**不需要 `data/` 的測試集**,並設 `REQUIRE_AVX2=1` 讓 SIMD 測試不可 silent skip(GitHub hosted runner 均支援 AVX2)。golden 測試維持本機執行,待 R3 完成 golden 再生鏈(R-14)後再入 CI。

**Files:**
- Create: `.github/workflows/ci.yml`

- [ ] **Step 1: 建立 workflow**

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:

jobs:
  test:
    strategy:
      fail-fast: false
      matrix:
        os: [windows-latest, ubuntu-latest]
    runs-on: ${{ matrix.os }}
    env:
      REQUIRE_AVX2: "1"
    defaults:
      run:
        working-directory: iso532
    steps:
      - uses: actions/checkout@v4
      - uses: dtolnay/rust-toolchain@stable
        with:
          components: rustfmt, clippy
      - uses: Swatinem/rust-cache@v2
        with:
          workspaces: iso532
      - run: cargo fmt --check
      - run: cargo clippy --all-targets -- -D warnings
      - run: cargo test --lib
      - run: cargo test --doc
      # golden_* / annexb tests need data/ (164 MB, not in repo) and stay
      # local-only until R3 hardens the golden regeneration chain (R-14).
      - run: >
          cargo test
          --test simd_parity
          --test simd_dispatch
          --test determinism
          --test api_errors
          --test hash_gate
```

- [ ] **Step 2: 本機模擬 CI 測試集**

Run(在 `iso532/`):

```powershell
$env:REQUIRE_AVX2='1'
cargo fmt --check
cargo clippy --all-targets -- -D warnings
cargo test --lib
cargo test --doc
cargo test --test simd_parity --test simd_dispatch --test determinism --test api_errors --test hash_gate
Remove-Item Env:REQUIRE_AVX2
```

Expected: 全部 exit 0;最後一條命令 5 個 test target 全綠。

- [ ] **Step 3: Commit 並推送觸發 CI**

```powershell
git add .github/workflows/ci.yml
git commit -m "ci: add fmt/clippy/test workflow with REQUIRE_AVX2 gate"
git push
```

- [ ] **Step 4: 確認兩個平台的 CI 結果**

Run(repo 根目錄): `gh run watch`(或 `gh run list --limit 1` 後 `gh run view <id>`)
Expected: windows-latest 與 ubuntu-latest 兩個 job 都綠。

- [ ] **Step 5(條件步驟): ubuntu 若只在 hash_gate 失敗——libm 位元差異的既定處置**

`hash_gate` 的合成訊號與 pipeline 會呼叫 `sin`/`powf`/`log10`,Windows CRT 與 glibc 的 libm 可能有 ULP 級差異,導致 ubuntu 上 hash 不同。這**不是 bug**,是平台差異(風險報告 §8.4 的 per-path 契約)。若發生:

1. 從 ubuntu job 的失敗 log 讀出實際印出的 `scalar:`/`avx2:` hash 值。
2. 把 `hash_gate.rs` 的常數改為依 OS 分組:

```rust
#[cfg(target_os = "windows")]
const EXPECTED_SCALAR: (u64, u64, u64) = (/* Windows 實測值 */);
#[cfg(target_os = "windows")]
const EXPECTED_AVX2: (u64, u64, u64) = (/* Windows 實測值 */);

#[cfg(target_os = "linux")]
const EXPECTED_SCALAR: (u64, u64, u64) = (/* ubuntu CI log 值 */);
#[cfg(target_os = "linux")]
const EXPECTED_AVX2: (u64, u64, u64) = (/* ubuntu CI log 值 */);

#[cfg(not(any(target_os = "windows", target_os = "linux")))]
const EXPECTED_SCALAR: (u64, u64, u64) = (0, 0, 0);
#[cfg(not(any(target_os = "windows", target_os = "linux")))]
const EXPECTED_AVX2: (u64, u64, u64) = (0, 0, 0);
```

   並在最後一組(其他 OS)上方加註 `// unfrozen: regenerate per §regenerate note above`,同時把測試開頭加上:

```rust
    if EXPECTED_SCALAR == (0, 0, 0) {
        eprintln!("no frozen snapshot for this OS; dump-only run");
    }
```

   ——注意:此分支仍要跑完 `run_hashes` 並印出值,但跳過 assert(把兩處 `assert_eq!` 各包在 `if EXPECTED_* != (0, 0, 0)` 內)。
3. commit 訊息:`test: freeze per-OS hash gate snapshots (windows/linux libm differ)`,再 push 確認全綠。

若 ubuntu 失敗的不是 hash_gate 而是其他測試,**停止並回報**,那超出本計畫預期。

---

## Exit Gate(全部滿足才算 G0' 完成)

1. `cargo test`(本機)35 個非忽略測試全綠,其中包含 `zwtv_output_hashes_match_r4_snapshot` 與 `zwtv_backend_hashes_match_frozen_snapshot` 兩個自動 hash assertion——R-13 收口。
2. `cargo bench --bench loudness -- --test` 的名稱含 `_t{N}` 執行緒後綴;MT/ST baseline 不再共用——R-10 收口。
3. GitHub Actions 在 windows-latest 與 ubuntu-latest 全綠,且 `REQUIRE_AVX2=1` 生效(SIMD 測試不可能 silent skip)——R-12 收口。
4. `git status --short` 乾淨(無未追蹤殘留)。
5. 未動任何 `iso532/src/` 檔案(本計畫是純測試/基礎設施工作;`git diff <start>..HEAD --stat -- iso532/src` 應為空)。

完成後主計畫依 2026-07-10 風險報告 §11 推進 R3(C-ABI + Python binding),golden 再生鏈固化(R-14)併入 R3 第一個 phase。

---

## 收尾註記(2026-07-10)

**G0' 已完成,Exit Gate 5/5 達成。** Task 1–7 對應 commit `07aed08`…`249f0dd`,
CI 上線後經三輪迭代全綠(`e49de49`/`d67c5e6`/`fa728e7`)。

與計畫的偏差:

1. Task 7 Step 5 的「ubuntu libm 差異」如預期發生,但處置比計畫更進一步:改用本機
   Docker `ubuntu:24.04` 直接取值凍結(不走 CI log 來回),並重構測試為「先印全部
   backend 再 assert」。
2. **計畫外發現**:GitHub windows runner 的 UCRT libm 按 CPU/OS build 分派,連 scalar
   hash 都與開發機不同——「per-OS 凍結」假設在 Windows 不成立。處置:Linux CI 硬
   assert、Windows CI 以 `HASH_GATE_DUMP_ONLY=1` 降級為 dump-only、本機維持硬 assert。
3. 正面發現:`n` 與 `time_axis` 跨全部環境 bitwise 相同,libm 噪音只存在於
   `n_specific`。R3 跨平台驗收可據此對主輸出用 bitwise 比對。

完整除錯紀錄:`docs/CI-HASH-GATE-DEBUG-2026-07-10.md`。
