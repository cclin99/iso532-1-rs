# Phase 6 TDD/BDD：C-ABI 與 Python 對接

**對應：** [ROADMAP §4](../../ROADMAP.md)　**狀態：** 🎨 設計（尚未有計畫文件；本文件為 phase 啟動前的測試策略草案）
**規劃測試檔：** `iso532-ffi/tests/abi.rs`、`iso532-ffi/tests/roundtrip.py`（pytest）

> 本 phase 尚未進入實作。正式開工前應先跑一次 brainstorming → spec → writing-plans；本文件先釘住「要驗什麼行為、用什麼當基準」，讓計畫有測試骨架可掛。

## 1. 測試策略摘要

新增 `iso532-ffi`（`cdylib` + `#[no_mangle] extern "C"`）與 Python binding（pyo3 + maturin）。正確性**不重驗演算法**——直接複用既有 golden 與 mosqito：

1. **C-ABI 契約**：扁平 `f64*` + 長度參數進出，錯誤碼映射 `Iso532Error`；記憶體所有權/釋放不洩漏。以 Rust 整合測試從 FFI 邊界呼叫，對 crate 內部函式 parity。
2. **Python↔mosqito 互比**：Python 端同時跑 mosqito 與 Rust binding，對同一訊號比 `N`/`N_specific`，複用 Annex B 與合成訊號——這是最強驗證（跨語言、跨實作）。
3. **錯誤碼往返**：非 48 kHz、過短、>120 dB 都要在 FFI 端回可辨識的非零錯誤碼，Python 端轉為例外。

## 2. BDD 行為情境（Gherkin）

### Feature: C-ABI 邊界契約（iso532-ffi）

```gherkin
Scenario: 透過 C-ABI 計算穩態響度對齊 crate 內部
  Given 一段 48 kHz f64 訊號（扁平陣列 + len）
  When 呼叫 extern "C" iso532_loudness_zwst(ptr, len, fs, field, out_n, out_spec)
  Then 回傳碼 0（成功）
  And out_n / out_spec 對 loudness_zwst 內部結果 rtol<=1e-12（同一路徑，應位元一致）

Scenario: 錯誤映射為非零碼且不寫出結果
  Given 44100 Hz 或過短訊號
  When 呼叫 iso532_loudness_zwst
  Then 回傳非零錯誤碼（對應 UnsupportedSampleRate / SignalTooShort）
  And 輸出緩衝區不被部分寫入（呼叫端可安全忽略）

Scenario: 輸出佈局為 row-major 扁平陣列
  Given n_specific 為 [bark_idx * n_frames + frame]
  When 讀取時變 specific loudness
  Then 佈局與文件宣告一致（不得改為巢狀）
```

### Feature: Python binding 對 mosqito 互比（roundtrip.py）

```gherkin
Scenario: Rust binding 與 mosqito 對同訊號給相同響度
  Given Annex B signal 3/5/10 與合成訊號
  When Python 分別呼叫 mosqito 與 iso532 binding
  Then N 逐點 isclose(rtol=1e-6, atol=1e-9)（binding 應等同 crate、逼近 mosqito）
  And 回傳為 numpy array（非 list）

Scenario: binding 錯誤轉為 Python 例外
  When 以 44100 Hz 呼叫 binding
  Then 拋出對應例外（訊息含 UnsupportedSampleRate）
```

## 3. TDD 測試清單（RED→GREEN，規劃）

| 測試名 | 檔案 | 輸入 | 預期 | 容差 |
|---|---|---|---|---|
| `abi_zwst_matches_internal` | ffi/tests/abi.rs | 扁平訊號 | 對內部 loudness_zwst | 1e-12 |
| `abi_zwtv_matches_internal` | ffi/tests/abi.rs | 扁平訊號 | 對內部 loudness_zwtv | 1e-12 |
| `abi_error_codes` | ffi/tests/abi.rs | 44100 / 過短 / >120dB | 非零碼、不寫出 | 精確 |
| `test_binding_vs_mosqito` | roundtrip.py | Annex B + 合成 | isclose mosqito | 1e-6/1e-9 |
| `test_binding_raises_on_bad_input` | roundtrip.py | 44100 Hz | 拋例外 | — |
| `test_returns_numpy` | roundtrip.py | 任一訊號 | `isinstance(out, np.ndarray)` | — |

## 4. 已知差異風險 / 排查順序

1. **輸出佈局鎖定**：現行 crate 已刻意用扁平 row-major `Vec<f64>`（`n_specific = bark_idx*n_frames+frame`）就是為 FFI 鋪路——**不得改成巢狀 Vec**，否則 ABI 契約破裂。
2. **記憶體所有權**：決定 caller-allocates（傳入 out 緩衝 + 容量）或 callee-allocates（配一個 free 函式）；測試須涵蓋緩衝不足的回報路徑，且 valgrind/asan 下無洩漏。
3. **f64 端序**：golden `.bin` 為 LE，x86-64 與 aarch64 皆 LE，跨平台共用；FFI 不做端序轉換。
4. **錯誤碼枚舉穩定性**：`Iso532Error` → 錯誤碼的映射一旦發佈即為 ABI 的一部分，新增變體只能追加不可重排。

## 5. 驗收對照（規劃）

```bash
cargo test -p iso532-ffi                     # ABI 邊界 parity + 錯誤碼
maturin develop && pytest iso532-ffi/tests/  # Python↔mosqito 互比
```

執行順序：ROADMAP 建議此為現行 5 phases 之後的**第一項**（驗證便利、立即可用）。
