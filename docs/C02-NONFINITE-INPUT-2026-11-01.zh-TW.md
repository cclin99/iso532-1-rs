# C-02 批次非有限輸入：契約與完成紀錄

> 對照／Pair: [English](C02-NONFINITE-INPUT-2026-11-01.md) · 來源：zh · 同步 2026-11-01

日期 2026-11-01（Asia/Taipei）。基底 `28f6a49`（v0.3.0 + V-01）。由 Claude 依使用者決定「C02 按照建議做」實作。稽核來源：`docs/修正報告2.md` §12.2 的 C-02 列。

## 1. 發現與契約

本次變更前，批次函式接受 NaN 與無限大樣本並回傳 `Ok` 且響度為零，呼叫端無法分辨壞資料與靜音。串流路徑原本就會把這類樣本歸零並舉 `FrameFlags::NONFINITE_INPUT`；對音訊執行緒而言這是正確的，因為它不能失敗。

本次起的契約：

| 路徑 | 遇到 NaN／±Inf 的行為 | 理由 |
|---|---|---|
| 批次 `loudness_zwst`、`loudness_zwtv`、`ZwtvProcessor::process*` | `Err(Iso532Error::NonFiniteInput { idx })`，穩定錯誤碼 **4**，`idx` 為第一個違規樣本；不計算、不寫出 | 批次拿到的是完整訊號，拒絕才是誠實的契約 |
| C ABI `iso532_loudness_zwst`／`iso532_loudness_zwtv` | 回傳 `ISO532_ERR_NONFINITE_INPUT`（= 4）；輸出緩衝區不動 | 加法式的正值錯誤碼，ABI v1 其餘不變 |
| Python `loudness_zwst`／`loudness_zwtv` | `ValueError`，訊息含 `non-finite sample … index N` | 既有錯誤映射 |
| 串流（`ZwtvStream`、C ABI 串流函式、Python `ZwtvStream`） | 不變：樣本歸零、下一個輸出幀帶 `NONFINITE_INPUT` flag，`flush` 後為殘留 flag | 即時路徑永不失敗、永不配置 |

批次入口的檢查順序：取樣率 → 長度 → 有限性 → 計算。次正規數、精確零（±0.0）與極大有限值（例如 1e300）都是有限輸入，不被此檢查拒絕；極大值仍可能以 `LevelExceeds120dB` 結束，那是既有契約。

## 2. 改了什麼

| 檔案 | 變更 |
|---|---|
| `iso532/src/error.rs` | `Iso532Error::NonFiniteInput { idx }`、`code() = 4`、`check_finite(&[f64])` 輔助函式、單元測試 |
| `iso532/src/zwst/mod.rs`、`iso532/src/zwtv/mod.rs` | 長度檢查後加 `Iso532Error::check_finite(signal)?` |
| `iso532-ffi/src/lib.rs` | `ISO532_ERR_NONFINITE_INPUT = 4` 與文件註解；批次包裝器經既有 `e.code()` 傳遞 |
| `iso532-ffi/include/iso532.h` | 以 cbindgen 0.29.4 重新產生；唯一差異是新 define 與其註解 |
| `iso532/tests/api_errors.rs` | 錯誤碼 4 凍結；兩個批次函式在頭、中、尾的 NaN／+Inf／−Inf；第一個違規 index；取樣率與長度錯誤的優先順序；次正規／零／1e300 不被當成非有限；串流仍以 flag 回報 |
| `iso532-ffi/tests/ffi.rs` | 錯誤映射表加入 zwtv 與 zwst 的錯誤碼 4，並檢查「未寫任何輸出」；常數凍結 |
| `iso532-py/tests/test_smoke.py` | 9 個參數化案例（3 個值 × 3 個位置），兩個批次函式都測 |
| `README.md`、`README.zh-TW.md`、`CHANGELOG.md` | 輸入契約句子與 Unreleased 條目 |

沒有任何數值路徑改變：對有限輸入，所有函式的計算與之前完全相同（golden、hash、parity、SIMD 測試全部不變且通過）。

## 3. 驗收結果

| Gate | 結果 |
|---|---|
| `cargo fmt --all --check` | 通過 |
| `cargo clippy --all-targets -- -D warnings`（在 `iso532/`）與 `--workspace --all-features` | 通過 |
| `REQUIRE_AVX2=1 cargo test --workspace --all-features` | 全部通過，0 failed，3 ignored（既有）；`api_errors` 10、`ffi` 17、錯誤單元測試 2 |
| `tools/golden_manifest.py --verify` | 175 files match |
| `maturin develop --release` + `ISO532_REQUIRE_PARITY=1 pytest iso532-py/tests` | 56 passed（原 47 + 新 9） |

本機備註：分頁檔幾乎用滿，cargo 以 `-j 2` 執行；這是環境限制，不是測試結果。

## 4. 稽核驗收對照（§12.2 C-02 列）

| 驗收項 | 狀態 |
|---|---|
| NaN／±Inf 放在頭中尾 | Rust（3 × 3 × 2 個函式）、FFI（2 案）、Python（9 案）皆測 |
| 次正規、極大有限值、零 | 已測：視為有限輸入接受 |
| FFI／Python／Rust 一致映射 | 錯誤碼 4 ↔ `ISO532_ERR_NONFINITE_INPUT` ↔ `ValueError`；FFI 出錯時不寫輸出 |
| 串流後續恢復與 flag | 行為不變，在 `api_errors.rs` 與既有串流測試再次斷言 |
| 參數／長度錯誤 | 新增優先順序測試 |
| 「不能無聲偽裝正常零響度」 | 批次改為錯誤；串流以 flag 回報（文件標明為刻意的差異） |

## 5. 範圍外

C-01 輸出長度、穩態前端、F-03。串流路徑未動。版號不變；隨下一個 release 出（0.3.1 或 0.4.0 由使用者決定；C ABI 變更是加法式）。
