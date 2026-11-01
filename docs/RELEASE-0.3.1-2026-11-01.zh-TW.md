# Release 紀錄：v0.3.1（2026-11-01）

> 對照／Pair: [English](RELEASE-0.3.1-2026-11-01.md) · 來源：en · 同步 2026-11-01

本次範圍：批次輸入契約（稽核項 C-02：NaN 或無限大樣本以新的穩定錯誤碼拒絕，不再回傳零響度）、凍結的輸出格線契約（C-01：保留 `ceil`，寫入文件並以測試釘住）、fail-closed 的 Annex B 驗證器（V-01，僅測試碼），以及雙語文件組。對有限輸入沒有任何數值輸出改變：所有 golden、凍結 hash、parity 與 Annex B 測試原樣通過。C ABI 多一個正值錯誤碼、仍為 ABI v1；Python 批次函式遇非有限輸入丟 `ValueError`。

依本專案 2026-11-01 的版號規則採 patch 版：文件、測試、加法式 API／ABI 與小修正升 patch；數值或破壞性變更才升 minor。

## 自 v0.3.0 以來的 commit

| commit | 內容 |
|---|---|
| `d623d32` | V-01 phase 計畫（Annex B 驗證器，fail-closed） |
| `4f03530` | V-01：`tests/common/annexb_check.rs` 採工作簿規則 `max(0.1, 0.05·|ref|)`、`tests/annexb_validator.rs`（24 測試）、嚴格 CSV／bin 讀取 |
| `8920e25` | F-03 獨立驗證交付（sensitivity、authority、SQAT）與狀態文件 |
| `28f6a49` | C-01 決策備忘 |
| `d7f438d` | C-02：`Iso532Error::NonFiniteInput { idx }`（錯誤碼 4）、`ISO532_ERR_NONFINITE_INPUT`、Python `ValueError`；Rust／FFI／Python 測試 |
| `a2c0410` | 文件語言政策、20 份 en／zh-TW 配對文件、`tools/doc_pairs.py`、文件索引、F-03 選項 B 簡報 |
| `d0bd38b` | C-01：輸出格線契約寫入 README、文件註解、C header 與 CHANGELOG；`tests/output_grid.rs`（7 測試）與 Python 形狀測試；C-01 驗證簡報 |
| release commit | 版號 0.3.1、CHANGELOG、CITATION、README 直接比對列、稽核方對 C-01 簡報的補強、本紀錄 |

## 使用者看到的變化

| 路徑 | 之前 | 自 0.3.1 起 |
|---|---|---|
| 批次 `loudness_zwst`、`loudness_zwtv`、`ZwtvProcessor::process*` 含 NaN 或 ±Inf 樣本 | `Ok` 且響度為零 | `Err(Iso532Error::NonFiniteInput { idx })`，錯誤碼 4，第一個違規 index，不計算 |
| C ABI 批次函式 | 回傳 0 並寫零 | 回傳 `ISO532_ERR_NONFINITE_INPUT`（4）；輸出緩衝區不動 |
| Python `loudness_zwst`／`loudness_zwtv` | 全零陣列 | 帶 index 的 `ValueError` |
| 串流（`ZwtvStream`、C ABI 串流、Python `ZwtvStream`） | 樣本歸零、`NONFINITE_INPUT` flag | 不變 |
| `loudness_zwtv` 與串流的輸出格線 | `ceil(ceil(L/24)/4)` 點（未成文） | 點數相同，現為凍結契約：第 `j` 點恰在 `96j/48000` 秒，值只取決於 samples `≤ 96j`；CLI 格線是前綴 |
| Annex B 測試 | 加法容差 `0.1 + 0.05·|ref|` | 工作簿規則 `max(0.1, 0.05·|ref|)`，無效資料 fail-closed |

批次入口的檢查順序：取樣率 → 長度 → 有限性 → 計算。次正規數、零與極大有限值仍是合法輸入。

## 驗證

### 本機，release commit 狀態

- 工具鏈：rustc／cargo 1.99.1，Windows 10 x64，AVX2+FMA，12 邏輯處理器。因分頁檔幾乎用滿，建置以 `-j 2` 執行；這是環境限制，不是測試結果。
- `cargo fmt --all --check`：通過。
- `cargo clippy --all-targets -- -D warnings`（在 `iso532/`，與 CI 同命令）與 `cargo clippy --workspace --all-features --all-targets -- -D warnings`：通過。
- `REQUIRE_AVX2=1 cargo test --workspace --all-features`：138 通過、0 失敗、3 ignored（hash dump、Python contract dump、靜音吞吐）。較 0.3.0 新增：`annexb_validator`（24）、`output_grid`（7）、`api_errors` +6、`ffi` +2 案、錯誤單元測試 +2。
- `tools/golden_manifest.py --verify`：175 files match。
- Python：`maturin develop --release`，再以 `ISO532_REQUIRE_PARITY=1` 跑 `pytest iso532-py/tests`：69 通過（0.3.0 為 47，+9 非有限案例，+13 輸出格線案例）。
- `python tools/doc_pairs.py --check`：ok。`python tools/redact_paths.py --check docs`：clean。

### CI

- Run 41216048341（`28f6a49`）、41219574093（`a2c0410`）、41257789141（`d0bd38b`）：六個 job 全綠（ubuntu-latest 與 windows-latest 的 test、ffi、py），含本次未變動的 Linux 凍結 hash gate。
- release commit 的 run 結果記在 tag 訊息。

### 獨立驗證

本次沒有新的獨立驗證輪。C-02 變更由 `docs/修正報告2.md` §12.2 C-02 列的驗收項覆蓋（對照見 `docs/C02-NONFINITE-INPUT-2026-11-01.zh-TW.md` §4）。C-01 的數值驗收（Annex B 訊號 18／23／24／25 尾端點的官方 C library 值）已交辦於 `docs/verification/briefs/2026-11-01-C01-zero-pad-reference.zh-TW.md`，將在本次發布後交付到 `docs/verification/`；它不會改變格線，只決定稽核列是否結案。

## 產出物（自 release commit 狀態建置，Windows x64，rustc 1.99.1）

| 檔案 | SHA-256 |
|---|---|
| `iso532-0.3.1-cp39-abi3-win_amd64.whl` | `841584a2741029f23d8f66b5ff8ba72af0061a5d948248a61a7ef155c095f747` |
| `iso532_ffi.dll` | `c2d1b9d310733ebd49208050213b41a16a0bc8acbd3c7527485ee2f9e160102e` |
| `iso532_ffi.dll.lib` | `e5b7a8f812cd9e6d8be7a22f15dd0493ef3ebda7920757f3858d1e63026c05a9` |
| `iso532.h` | `0f548fd348cb0e3999ce8892bec05d4a5afd53740eb695428ad0eca9a45b709b` |

Import library 與 v0.2.0、v0.3.0 位元相同（匯出符號未變）。`iso532.h` 與 v0.3.0 只差 `ISO532_ERR_NONFINITE_INPUT` define、其註解，以及 `iso532_zwtv_out_frames` 的輸出格線註解。PE 二進位內嵌建置資訊，在另一台機器重建不期望逐位元重現 DLL 與 wheel 的 hash。

## API 遷移

- 窮舉比對 `Iso532Error` 的 Rust 呼叫端多一個 `NonFiniteInput { idx }` 分支。之前依賴壞輸入得到零響度的呼叫端，須在批次呼叫前過濾或修補訊號，或改用保留 flag 語意的串流路徑。
- C 呼叫端：處理回傳值 4（`ISO532_ERR_NONFINITE_INPUT`）；與其他錯誤碼相同，出錯時不寫輸出緩衝區。
- Python 呼叫端：接住 `loudness_zwst`／`loudness_zwtv` 的 `ValueError`。
- 沒有簽名改變。`zwtv_out_frames`／`iso532_zwtv_out_frames` 仍是配置緩衝區唯一正確的方法；公式現已成文，但不應手抄。

## Release 檢查清單逐項紀錄（`docs/RELEASE-CHECKLIST.md`）

| 項目 | 狀態 |
|---|---|
| README 的審稿草稿引言 | 不存在 |
| 重跑 `tools/compare_mosqito.py` | 見下方「MoSQITo 比較」；README 直接比對列已更新 |
| 從重生的 golden 環境跑「重現驗證」命令 | 在既有本機 golden 環境執行（manifest 已驗證，175 檔）；本次未從零重生 |
| `docs/GOLDEN-REGEN-SOP.md` 前置條件 | 未變 |
| 能力與邊界敘述對照 tag 原始碼 | 新增 README 輸入契約句（C-02）、輸出格線段（C-01）與 Annex B max 規則措辭（V-01）；其他敘述未變 |
| `THIRD_PARTY_NOTICES.md`、`CITATION.cff`、`SECURITY.md`、範本 | `CITATION.cff` 版號 0.3.1、日期 2026-11-01；其他未變 |
| 產出物防毒掃描 | **待手動**：建置機的防毒為 Avira；發布二進位前請掃描產出物資料夾並在此記錄產品、版本、hash 與結果 |
| SHA-256 校驗 | 如上表 |
| 本機檔案、封存、`data/`、憑證、機器路徑未 stage | `data/`、`tmp/` 與封存已 gitignore；`redact_paths.py --check docs` clean |
| 驗證交付含大小、SHA-256 與連結 | 自 0.3.0 未變；封存下載連結仍待上傳 |

## MoSQITo 比較（release commit 狀態，rustc 1.99.1）

與 README 表格相同的腳本、訊號與流程（3 s contract signal、一次 warm-up、30 次量測），Python 3.11.9、NumPy 2.4.6、MoSQITo 1.2.1：

| 實作 | 平均 | sample SD | min／max | 相對速度 |
|---|---:|---:|---:|---:|
| ISO532 Rust 經 Python binding，`nl_init="zero"` | 13.480 ms | 0.840 ms | 11.696 / 15.501 ms | 500.57x |
| MoSQITo 1.2.1 `loudness_zwtv` | 6.747 s | 0.333 s | 6.555 / 8.144 s | 1.00x |

同一次執行的直接數值比較：

| 初始化 | max abs dN(t) | max abs dN_specific(t) | 備註 |
|---|---:|---:|---|
| `nl_init="zero"`（預設） | 5.826515e-03 sone | 3.245252e-02 sone/Bark | 與 0.3.0 發布值相同：與 MoSQITo 的唯一差異是 F-02 初始化 |
| `nl_init="mosqito_tail"` | 2.664535e-15 sone | 3.455569e-15 sone/Bark | 與 2026-07-20 及 0.3.0 的值相同 |

README 效能表維持 2026-07-20 安靜機器量測；上表時間是發版當時快照。

## 已知未結項目（0.3.1 未處理）

- C-01 數值驗收：Annex B 訊號 18／23／24／25 尾端點的官方 C library 值（簡報已發出；格線本身已凍結、不會再改）。
- F-03：`USL[12][4]` 本專案／MoSQITo／SQAT 為 0.24，Annex A C 程式與 1991 論文為 0.22；仍需 ISO 532-1:2017 Table A.9；選項 B（經 AARAE 2015／2014 C 的血緣追溯）已交辦。本次不改表。
- 穩態前端（ROADMAP R2）：全訊號 RMS（MoSQITo 相容）對參考濾波器組加安定窗；待決。
- N5 欄與窗、精確 1% 邊界：待權威來源。
- `N_WARMUP_FRAMES = 580` 維持 v1 含義。

## 下游

`iso532-rs-panel` 以 git tag 釘住引擎。要採用本次發布，把 `plugin/Cargo.toml` 的 tag 改為 `v0.3.1`，執行 `cargo update -p iso532`，再跑面板自己的驗收（P-01～P-03）。面板使用串流路徑，其數值與 flag 不受本次影響；只有批次呼叫端會看到新錯誤。
