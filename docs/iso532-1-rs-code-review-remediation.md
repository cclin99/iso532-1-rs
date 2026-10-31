# iso532-1-rs｜Code Review 修正計畫

> **文件用途**：作為逐項修復、撰寫測試、建立 PR 與驗收的工作清單；可保存為 `docs/CODE-REVIEW-REMEDIATION.md`。  
> **審查目標**：[cclin99/iso532-1-rs](https://github.com/cclin99/iso532-1-rs)  
> **審查基準**：`main`，commit `8fde6b6e18d57245e3e2905d6833a155f5fecc58`（2026-07-21）  
> **文件整理日期**：2026-10-31  
> **審查性質**：已讀取關鍵原始碼、測試與 CI 設定的**靜態 Code Review**；未在本次審查環境執行 Cargo、Clippy、Miri、Benchmark 或 ISO 原始測試資料比對。  
> **修改狀態**：本文件為建議，**尚未對 Repository 寫入任何變更**。

## 0. 執行摘要

### 結論

現有架構具備相當好的工程基礎：Rust core／C ABI／Python binding 分離、`ZwtvStream` 有明確的 `push`／`flush`／`reset` 契約、AVX2 + FMA runtime dispatch、Scalar parity、串流 chunk invariance、FFI panic protection 與跨平台 CI。專案尤其重視數值行為及可重現性。

目前最值得優先處理的是 **Batch API 對非有限輸入值的明確處理**、**CI 沒有完整覆蓋核心串流測試**、以及 **新使用者能否在乾淨環境重現基本測試與數值驗證**。

**注意**：本文件未確認任何 Critical 級記憶體破壞或 ISO 演算法計算錯誤。評估並非正式 ISO 認證、完整安全稽核或第三方數值驗證。以下的「確認」指源碼／配置可直接觀察到的行為，不代表該行為一定已造成外部事故。

### 問題總覽

| ID | 建議優先度 | 類別 | 問題摘要 | 證據狀態 | 修改排序 |
|---|---|---|---|---|---|
| CR-01 | P0 / High | 輸入驗證 | Batch ZWST / ZWTV 未顯式拒絕 NaN、±Infinity | **確認缺少檢查**；實際結果需回歸測試 | 1 |
| CR-02 | P0 / High | CI / 測試 | 核心 Streaming integration tests 沒有全面納入一般 CI | **確認 CI 配置缺口** | 2 |
| CR-03 | P1 / Medium | FFI 安全契約 | C ABI 的 buffer 重疊／指標前置條件記載不足 | **確認文件缺口**；非已證實 UB 漏洞 | 4 |
| CR-04 | P1 / Medium | 可重現性 | README 的 `cargo test` 與本機 Golden 資料依賴不一致 | **確認流程摩擦** | 3 |
| CR-05 | P1 / Medium | API 錯誤處理 | 部分 public DSP helper 以 `assert!` 處理可預期的輸入尺寸錯誤 | **確認 API 行為**；是否更改屬設計決策 | 5 |
| CR-06 | P1 / Medium | 記憶體 / 效能 | Batch 長訊號有多層 `O(N)` 暫存與分配，缺資源契約 | **確認架構特徵**；OOM 閾值未量測 | 6 |
| CR-07 | P2 / Low | 跨平台測試 | Windows 的 frozen hash gate 採 dump-only | **確認配置**；屬可攜性取捨 | 7 |
| CR-08 | P2 / Low | API 契約 | FFI 不足 `out_cap` 與 internal invariant 使用同一錯誤碼 | **確認現況**；屬語意改善 | 8 |

> **Severity 原則**：High / Medium / Low 反映建議的修復優先度，不是 CVSS 分數。尤其 CR-01 的「可能造成錯誤數值」尚需實測，CR-03 不應誤寫為已證實可在遵循契約的合法呼叫中觸發 UB。

---

## 1. 詳細發現與修正規格

### CR-01｜Batch API 缺少非有限值輸入驗證

- **優先度**：P0 / High
- **證據狀態**：已從程式碼確認未顯式檢查；尚未執行反例測試。
- **影響位置**：
  - [`iso532/src/zwst/mod.rs`](https://github.com/cclin99/iso532-1-rs/blob/main/iso532/src/zwst/mod.rs#L36-L53)（`loudness_zwst`）
  - [`iso532/src/zwtv/mod.rs`](https://github.com/cclin99/iso532-1-rs/blob/main/iso532/src/zwtv/mod.rs#L66-L82)（`ZwtvProcessor::process`）
  - [`iso532/src/core/main_loudness.rs`](https://github.com/cclin99/iso532-1-rs/blob/main/iso532/src/core/main_loudness.rs#L5-L15)（`level > 120.0` 對 NaN 不成立）
  - 間接受影響：`iso532-ffi/src/lib.rs`、`iso532-py/src/lib.rs` 的 batch API

**現況與風險**

- 入口目前主要驗證 `fs == 48_000.0` 與最短訊號長度 4800 samples。
- 沒有對 `signal` 全部樣本執行 `is_finite()`；浮點比較不會自動把 NaN 視為錯誤。
- NaN／Infinity 可能沿著濾波、RMS、log、閾值與 Bark 計算路徑傳播或導致非預期分支。**具體輸出需用測試量測**，不能事先假定全部會回傳 NaN、零或 `Ok`。
- **Streaming** 已採用不同且有文件說明的策略：non-finite 樣本以 0 代替並回報 `NONFINITE_INPUT` flag。這個設計可以保留，無須強迫 Batch 與 Streaming 行為相同。

**建議修法**

1. 在兩個 Batch 公開入口完成基本參數驗證後、進行任何 DSP 計算前，顯式拒絕非有限值。
2. 新增 `Iso532Error::NonFiniteInput`（可再決定是否包含 first invalid sample index）。
3. 對應新增 C ABI 錯誤碼，保留既有 0、1、2、3、-1～-4 數值不變；同步更新 C header、Python 例外、README。
4. 不要因為修正 Batch 而改動 Streaming 的零值替代 + flag 契約。

**建議回歸測試**

```rust
#[test]
fn batch_rejects_nonfinite_samples() {
    for invalid in [f64::NAN, f64::INFINITY, f64::NEG_INFINITY] {
        let mut signal = vec![0.0; 48_000];
        signal[1234] = invalid;
        assert!(iso532::loudness_zwst(&signal, 48_000.0, iso532::FieldType::Free).is_err());
        assert!(iso532::loudness_zwtv(&signal, 48_000.0, iso532::FieldType::Free).is_err());
    }
}
```

這是**修復目標的測試草案**，在錯誤型別定案後宜改用 `matches!` 檢查具體 variant，而不僅檢查 `is_err()`；同步覆蓋第一個樣本、最後一個樣本、Python binding 與 C ABI。

**完成條件**

- [ ] ZWST/ZWTV 對 NaN、+Inf、-Inf 均回傳一致、明確的錯誤。
- [ ] Rust、Python 與 C ABI 的錯誤契約一致。
- [ ] Streaming 非有限值補零與 flag 行為不變。
- [ ] 有針對錯誤位置（首／中／尾）的測試，且原有 Golden／parity 測試無變化。

### CR-02｜核心 Streaming 測試未完整納入一般 CI

- **優先度**：P0 / High
- **證據狀態**：CI YAML 可以直接確認。
- **位置**：[`.github/workflows/ci.yml`](https://github.com/cclin99/iso532-1-rs/blob/main/.github/workflows/ci.yml#L32-L45)（路徑前無空白）
- **相關測試**：`iso532/tests/stream.rs`、`stream_alloc.rs`、`stream_no_rayon.rs`、`stream_scalar.rs`

**現況與風險**

CI 執行 `cargo test --lib`、`cargo test --doc`，及指定的 `simd_parity`、`simd_dispatch`、`determinism`、`api_errors`、`hash_gate`、`py_contract_dump`，但沒有把上述 Rust streaming integration tests 逐一列入。`stream.rs` 又混有需要本機 `data/golden` 的測試，使它不能在乾淨 runner 中直接整檔執行。

因此可能出現「CI 成功，但部分 streaming、zero-allocation、Rayon 隔離或 reset 契約未受到檢驗」的情況。既有 Python streaming tests 是加分，卻不能代替 Rust 層的所有測試。

**建議修法**

1. 分拆 `stream.rs`：把不依賴 Golden 的測試搬到 `stream_core.rs`；依賴 `data/golden` 的九組參考訊號放 `stream_golden.rs`。
2. CI 增加 self-contained 的 streaming 整合測試：

```yaml
- run: >
    cargo test
    --test stream_core
    --test stream_alloc
    --test stream_no_rayon
    --test stream_scalar
```

3. 將需要 ISO／MoSQITo 檔案的測試設為獨立的 reference-validation job 或手動 workflow，並說明資料取得及授權條件。
4. 確認 Linux 與 Windows 的測試均有合適的 CPU feature fallback。

**完成條件**

- [ ] 每個 PR 的 CI 會執行 chunk invariance、reset、flush、nonfinite、allocation、Rayon 隔離、scalar stream 測試。
- [ ] 不下載 Golden 檔也可在乾淨 runner 跑完 fast/self-contained 套件。
- [ ] Golden／Annex B 測試入口仍存在且可以依 SOP 執行。
- [ ] 刻意破壞一項核心 stream 契約時，CI 能顯示失敗（可用本地 mutation/temporary change 驗證，不必提交）。

### CR-03｜C ABI 指標與不重疊契約文件不夠精確

- **優先度**：P1 / Medium
- **證據狀態**：程式碼與 header 可確認；**沒有確認守規的呼叫者可以引發 UB**。
- **位置**：
  - [`iso532-ffi/src/lib.rs:131–163`](https://github.com/cclin99/iso532-1-rs/blob/main/iso532-ffi/src/lib.rs#L131-L163)
  - [`iso532-ffi/include/iso532.h`](https://github.com/cclin99/iso532-1-rs/blob/main/iso532-ffi/include/iso532.h)

**現況與風險**

`iso532_stream_push` 將 `chunk` 建立為 `&[f64]`，將 `out` 建立為 `&mut [StreamFrame]`；這些 Rust 借用需要有效、對齊且在借用期間不違反別名規則的記憶體。`out_written` 與其他 mutable output 也要避免不合法重疊。Null 與 `out_cap` 檢查**不能**檢查一般指標的有效範圍或別名；這是 C ABI 的慣常限制，不能用來推論實作已存在可利用漏洞。

**建議修法**

1. 在 `# Safety` 與生成的 C header 補充所有輸入／輸出區間不得以違反 Rust aliasing 規則的方式重疊；呼叫期間不得由其他執行緒修改；指標對齊與長度必須有效。
2. 補充 handle **不可並行使用**、`push` after `flush` 必須先 `reset`（C ABI 目前沒有 reset，因此 C 客戶端需重建 handle）。
3. 建立 **合法 C 呼叫** 的 smoke test / 範例；避免用 UB 的違規指標撰寫一般測試來「確認」檢查機制。
4. 若產品需求是防禦任意不可信 C 指標，須另行設計 API／隔離層；單靠 `is_null()` 無法達成。

**完成條件**

- [ ] C Header、Rustdoc、範例一致註明 caller obligations。
- [ ] 在合法輸入與輸出緩衝區下，C smoke 與 FFI integration tests 全過。
- [ ] 文件不再暗示 API 能自動偵測任意錯誤或重疊的 C 指標。

### CR-04｜乾淨 clone 的測試指令與 Golden 資料依賴不一致

- **優先度**：P1 / Medium
- **位置**：[`README.md`](https://github.com/cclin99/iso532-1-rs/blob/main/README.md) 的 Rust Quick start；`iso532/tests/stream.rs`、`iso532/tests/annexb.rs`、`iso532/tests/golden_*.rs`；[`docs/GOLDEN-REGEN-SOP.md`](https://github.com/cclin99/iso532-1-rs/blob/main/docs/GOLDEN-REGEN-SOP.md)
- **證據狀態**：從測試內容與 `.gitignore`／README 的 `data/` 說明可確認；本次未在 fresh clone 實際執行。

**現況與風險**

README 的 Quick start 展示 `cargo test`，但部分 integration tests 透過 `read_bin()` 直接讀取本機 `data/golden`。Repository 說明這些測試資料刻意未提交。因此首次 clone 者可能不能直接跑完整測試。

**建議修法**

1. 明確提供 `cargo test --lib` 與 self-contained tests 的指令，區分「快速測試」與「Reference validation」。
2. 讓 `docs/GOLDEN-REGEN-SOP.md` 包含環境版本、來源、hash、授權、操作命令、預期結果及排錯方式。
3. 若不能再散布 ISO Annex B 原始測試檔，保持合法來源／手動取得的流程；不應為了方便 CI 而提交受限資料。
4. 考慮用單一 script 執行 Golden 前置檢查並提供有意義的錯誤訊息。

**完成條件**

- [ ] 新使用者能在不具備私有／授權資料的情況下執行明確的 basic test suite。
- [ ] Reference validation 在資料就緒時可用明確命令執行。
- [ ] README 不會讓新使用者誤以為任意環境 `cargo test` 必定全過。

### CR-05｜公開 DSP Helper 用 assert! 處理錯誤輸入

- **優先度**：P1 / Medium
- **位置**：
  - [`iso532/src/core/main_loudness.rs:5–10`](https://github.com/cclin99/iso532-1-rs/blob/main/iso532/src/core/main_loudness.rs#L5-L10)
  - [`iso532/src/core/calc_slopes.rs:9–15`](https://github.com/cclin99/iso532-1-rs/blob/main/iso532/src/core/calc_slopes.rs#L9-L15)
  - [`iso532/src/dsp/filtfilt.rs:5–6`](https://github.com/cclin99/iso532-1-rs/blob/main/iso532/src/dsp/filtfilt.rs#L5-L6)
- **證據狀態**：可直接確認使用 `assert!`／`assert_eq!`；是否構成缺陷取決於公開 API 的契約。

**現況與取捨**

目前這些 helper 透過公開 module 可被外部直接呼叫，傳入錯誤長度會 panic。若預期只供內部、且輸入尺寸為不可破壞的不變條件，使用 assertion 有其合理性；但對第三方呼叫者，`Result`／typed input 會更清楚。

**建議修法（擇一）**

- **A. 保留公開 API**：改 `Result` 或增加 `try_*` 版本，逐步 deprecated 舊版；注意 API 相容性。
- **B. 收窄公開面**：對內部 helper 改 `pub(crate)`，保留真正有意提供給使用者的高階入口。
- **C. 維持 panic 契約**：明確在 rustdoc 的 `# Panics` 註記尺寸前置條件，視為設計選擇而非 Bug。

**完成條件**

- [ ] 逐個 helper 定義 public / internal 身分。
- [ ] panic 或 `Result` 行為有文件與測試。
- [ ] 如果改動 public API，記錄相容性及 versioning 決策。

### CR-06｜Batch ZWTV 長訊號的資源成本缺少明確契約

- **優先度**：P1 / Medium
- **位置**：[`iso532/src/zwtv/mod.rs:82–133`](https://github.com/cclin99/iso532-1-rs/blob/main/iso532/src/zwtv/mod.rs#L82-L133)
- **證據狀態**：可確認存在多份依輸入長度成長的 `Vec`；未量測記憶體峰值或發現特定 OOM 重現案例。

**現況與風險**

Batch 路徑建立 third-octave matrix、frame-major copy、21-band core、nonlinear-decay output、time-series、specific loudness 等資料。這些資料隨時間長度線性增加，部份會同時存活。Rayon 路徑也可能造成額外暫態記憶體，對長時間離線檔案和服務端多工作併行尤其重要。

**建議修法**

1. 用 **RSS peak、allocated bytes、throughput** 測量 10 秒／1 分鐘／10 分鐘／1 小時的輸入。
2. 公布輸入時長與預估 RAM 的表格，並標註 Batch / Streaming 差異。
3. 在產品整合層加入輸入長度或記憶體預算限制；極長訊號建議使用 Streaming，但需留意它與 Batch 的 warm-up／初始條件差異。
4. 視測量結果再考慮減少 `tol`／`nl` 多份資料的生命週期，避免為節省 RAM 破壞 Golden parity。

**完成條件**

- [ ] 有至少三種長度的 peak-memory benchmark。
- [ ] README 說明大型輸入的資源需求與建議 API。
- [ ] 任意優化有 Golden／SIMD／determinism regression gate。

### CR-07｜Windows hash gate 設定為 dump-only

- **優先度**：P2 / Low
- **位置**：[`iso532/tests/hash_gate.rs:14–20, 77–86`](https://github.com/cclin99/iso532-1-rs/blob/main/iso532/tests/hash_gate.rs#L14-L20)、[`.github/workflows/ci.yml:15–20`](https://github.com/cclin99/iso532-1-rs/blob/main/.github/workflows/ci.yml#L15-L20)
- **證據狀態**：明確是為 Windows libm／CPU 差異設置的取捨，**不應簡單視為測試失效**。

**建議修法**

- 保留 Linux frozen hash 作嚴格回歸門檻。
- Windows 增加具容差的 Scalar / AVX2 比較與基本輸出 invariant；避免固定 OS／CPU dependent bit hash 導致誤報。
- 未來新增 macOS aarch64 scalar runner；如實標註 NEON 尚未實作。

**完成條件**

- [ ] Windows 不只有 dump log，也至少有數值與形狀／邊界斷言。
- [ ] README 的跨平台聲明不超出實際測試範圍。

### CR-08｜FFI 錯誤碼混用不足容量與內部異常

- **優先度**：P2 / Low
- **位置**：[`iso532-ffi/src/lib.rs:13–15, 151–153, 191–193`](https://github.com/cclin99/iso532-1-rs/blob/main/iso532-ffi/src/lib.rs#L13-L15)
- **證據狀態**：實作與 API 文件明確說明 `ISO532_ERR_INTERNAL = -4` 同時代表不足 `out_cap` 與內部 invariant；屬 API 語意設計問題。

**建議修法**

- 若目標是穩定 C ABI v1，先不要變更既有錯誤碼；可新增一個 `ISO532_ERR_INSUFFICIENT_CAPACITY` 常數與明確回傳語意（須同時更新測試、Header、CHANGELOG，評估相容性）。
- 如果暫時保持 `-4`，把所需 `out_cap` 的查詢及錯誤診斷寫清楚。
- 加入邊界測試（`out_cap=0`、`out_cap=required-1`、`out_cap=required`、`out_written` 的值）。

**完成條件**

- [ ] 舊 C 客戶端不會因錯誤碼重新編號而失效。
- [ ] C Header 與 Rust/FFI test 一致。

---

## 2. 已確認的優點（不建議無故重寫）

| 面向 | 實際設計／測試證據 | 建議 |
|---|---|---|
| 模組邊界 | `iso532` / `iso532-ffi` / `iso532-py` workspace | 保持分離 |
| Streaming 分段一致性 | `stream.rs::chunk_size_invariance_is_bitwise`，含隨機 chunk 長度 | 作為重構 hard gate |
| Reset / flush | 測試包含非 24 倍數長度及 NaN 後 reset | 避免破壞既有語意 |
| Hot-path allocation | `stream_alloc.rs` 用 counting allocator 驗證 | 將測試納入 CI |
| Rayon 隔離 | `stream_no_rayon.rs` 驗證串流不初始化全域池 | 將測試納入 CI |
| SIMD | runtime 檢查 AVX2 + FMA、`simd_parity` 與 scalar fallback | 保留 scalar oracle |
| FFI panic | `catch_unwind`、panic injection、C smoke | 維持 panic=unwind 契約；不等於全面防止 UB |
| ABI 佈局 | `size_of` / `align_of` / `offset_of` compile-time assertions | 保持 |
| Python binding | 釋放 GIL 前 copy input，`PyZwtvStream` 使用 `Box` | 視為安全取捨，不當作 Bug |
| 對外透明度 | README 陳述 AI-assisted、校正需由整合者負責及非認證限制 | 保留 |

**關鍵避免誤修**：`iso532-py/src/lib.rs` 每次 streaming `push()` 都會複製輸入並產生 NumPy 輸出；文件已把零配置限定於 **Rust core hot path**。不應要求 Python binding 也零配置，除非未來另開明確的 real-time / zero-copy API 設計工作。

---

## 3. 修復順序與 PR 切分

### PR-1｜Batch invalid sample contract（P0）

- [ ] 先建立 NaN／Inf 失敗測試；確認修復前現象。
- [ ] 新增 Rust error variant。
- [ ] 更新 Batch ZWST / ZWTV 入口驗證。
- [ ] 更新 FFI error mapping、Python 例外及 test。
- [ ] 不改變正常 finite input 的結果。

### PR-2｜Self-contained streaming CI（P0）

- [ ] 拆分 `stream_core.rs` 與 `stream_golden.rs`。
- [ ] CI 加入 `stream_core`、`stream_alloc`、`stream_no_rayon`、`stream_scalar`。
- [ ] Windows / Linux 都通過。
- [ ] 保留 Annex B 與 Golden 的獨立驗證入口。

### PR-3｜Reproducibility + docs（P1）

- [ ] README 分成快速測試／完整參考測試。
- [ ] Golden regeneration SOP 標註來源、版本、授權、預期結果。
- [ ] 修正 C Header safety contract 並以 cbindgen 重新產生。

### PR-4｜API / Resource hardening（P1）

- [ ] 決定 low-level helper 公開面與 panic 契約。
- [ ] 建立長訊號記憶體 benchmark。
- [ ] 確認是否需要固定輸入長度或容器記憶體預算。

### PR-5｜Cross-platform + ABI polish（P2）

- [ ] Windows 加容差型數值測試。
- [ ] 視設備／runner 可用性增加 aarch64 scalar CI。
- [ ] 決定 FFI 新增 capacity 專用錯誤碼或保留舊錯誤碼。

---

## 4. 驗收與驗證命令（於完整 Rust / Python 環境執行）

> 下列命令是**建議執行清單**，不代表本次審查已執行。所有改動應先在 branch 上進行。

```bash
# 在 repo 根目錄
cargo fmt --all -- --check
cargo clippy --workspace --all-targets -- -D warnings

# 不依賴 Golden 的測試（拆分 PR-2 後）
cargo test -p iso532 --lib
cargo test -p iso532 --test stream_core --test stream_alloc --test stream_no_rayon --test stream_scalar
cargo test -p iso532 --test simd_parity --test simd_dispatch --test determinism --test api_errors --test hash_gate

# C ABI
cargo test -p iso532-ffi --features test-panic
cargo build -p iso532-ffi --release

# Python：按現有 ci.yml 的 maturin + clean venv 程序建 wheel，再跑
# python -m pytest iso532-py/tests/test_smoke.py iso532-py/tests/test_stream.py -v
```

**Reference validation（僅在合法取得資料並依 SOP 建好 `data/` 後）**

```bash
cargo test -p iso532 --test annexb
cargo test -p iso532 --test golden_zwst
cargo test -p iso532 --test golden_zwtv
cargo test -p iso532 --test golden_core
cargo test -p iso532 --test golden_dsp
```

**可選但重要的額外驗證**

- [ ] Miri／ASan／UBSan（評估 FFI/unsafe 及工具鏈支援；不能單靠它們證明 C 呼叫契約安全）。
- [ ] 跨 x86-64（支援／不支援 AVX2+FMA）與 aarch64 的 build/tests。
- [ ] 長時間 streaming soak test、p99 / p99.9 callback latency 與壓力下 deadline misses。
- [ ] ISO Annex B 原始參考資料與 MoSQITo parity **分開**出報告。
- [ ] Feature / license / dependency review、release artifacts 的 checksum 與 smoke test。

---

## 5. 修改完成後的共同 DoD（Definition of Done）

每個 PR 至少符合：

- [ ] PR 說明附「修正前問題 → 修正後行為 → 測試」三段證據。
- [ ] 正常 finite signal 的核心數值結果沒有非預期漂移；如改動則公開原因與誤差界線。
- [ ] 相關 error code、Header、Python、README 同步更新。
- [ ] 不新增音訊 hot-path 配置或 Rayon pool 初始化。
- [ ] Windows / Linux CI 成功，若平台無法驗證需明確記錄。
- [ ] 檔案位置、測試命令與結果可由其他人重現。
- [ ] 不提交需授權的 ISO test fixtures 或 local golden 資料。

## 6. 本輪仍未證實的事項

以下不應標記為「已確認 Bug」：

1. **ISO 532-1 數學符合性**：已讀到部分公式與 Annex B 驗證程式，但沒有重跑 ISO 資料，也沒有逐一獨立推導所有係數。
2. **Nonfinite 的實際錯誤輸出**：已確認 Batch 無顯式檢查；實際錯誤型態與輸出仍待測試。
3. **FFI 的合法呼叫發生 UB**：目前只有 unsafe caller preconditions 的文件缺口，尚未找到守規用法下的記憶體錯誤。
4. **Streaming 事件旗標時間對齊**：`on_internal_frame()` 有 lookahead，應額外定義旗標表示「事件時間」或「影響的輸出」，目前視為**需驗證的語意風險**。
5. **長訊號 OOM 或 deadline miss**：只有結構性資源成本，尚未量測門檻或 worst-case latency。
6. **完整工具鏈結果**：本次未重新執行 Cargo／Clippy／Miri／Benchmark；GitHub 上可見 2026-07-21 該 SHA 有成功的 workflow run，但只涵蓋當時 CI 有執行的測試。

## 7. 參考原始碼位置

- [Rust 核心入口](https://github.com/cclin99/iso532-1-rs/blob/main/iso532/src/lib.rs)
- [ZWST](https://github.com/cclin99/iso532-1-rs/blob/main/iso532/src/zwst/mod.rs)
- [ZWTV Batch](https://github.com/cclin99/iso532-1-rs/blob/main/iso532/src/zwtv/mod.rs)
- [Streaming](https://github.com/cclin99/iso532-1-rs/blob/main/iso532/src/zwtv/stream.rs)
- [Main loudness](https://github.com/cclin99/iso532-1-rs/blob/main/iso532/src/core/main_loudness.rs)
- [Bark integration](https://github.com/cclin99/iso532-1-rs/blob/main/iso532/src/core/calc_slopes.rs)
- [SOS / filtfilt](https://github.com/cclin99/iso532-1-rs/tree/main/iso532/src/dsp)
- [C ABI](https://github.com/cclin99/iso532-1-rs/blob/main/iso532-ffi/src/lib.rs)
- [Python binding](https://github.com/cclin99/iso532-1-rs/blob/main/iso532-py/src/lib.rs)
- [GitHub Actions CI](https://github.com/cclin99/iso532-1-rs/blob/main/.github/workflows/ci.yml)
- [Golden regeneration SOP](https://github.com/cclin99/iso532-1-rs/blob/main/docs/GOLDEN-REGEN-SOP.md)
- [ISO Annex B 數值誤差紀錄](https://github.com/cclin99/iso532-1-rs/blob/main/docs/ISO-ANNEXB-NUMERICAL-ERROR-2026-07-04.md)

---

**建議起手順序**：先做 CR-01 的 fail-first regression tests，再做 CR-02／CR-04 的測試分層與 CI；確認數值 hash 及 Golden parity 不變後，才進入 FFI 契約與 Batch 記憶體最佳化。這樣最容易定位每個 PR 引入的回歸。
