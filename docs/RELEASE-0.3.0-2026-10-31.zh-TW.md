# Release 紀錄：v0.3.0（2026-10-31）

> 對照／Pair: [English](RELEASE-0.3.0-2026-10-31.md) · 來源：en · 同步 2026-11-01

本次 release 的範圍：發現 F-02（批次非線性時間衰減改為自零狀態起算，與
ISO 532-1 Annex A C 程式相同，不再使用 MoSQITo 1.2.1 的末幀種子）。對於訊號結尾
並非靜音的每個時變批次結果，其起始段的數值輸出會改變；串流路徑、穩態路徑，以及
結尾為靜音的訊號，位元逐一不變。公開 Rust API 新增 `NlInit` 與
`ZwtvProcessor::process_with`；低階的 `nl_loudness_avx2` 改為接受明確的
`NlInit`；Python `loudness_zwtv` 新增 `nl_init`；C ABI v1 不變，並沿用新的預設值。

已知未結項目列於文末。本次 release 不宣稱整體符合 ISO 532-1。

## 自 v0.2.0 以來的 commit

| commit | 內容 |
|---|---|
| `437f51c` | F-02 修正：`NlInit`、scalar 與 AVX2 皆以零狀態為預設、`tests/nl_zero_init.rs`、凍結 hash 依預設值重新記錄並在 `MosqitoTail` 下保留舊值 |
| `a0897f0` | Python `nl_init` 關鍵字參數、補靜音的 MoSQITo parity 交叉檢查 |
| `5450d39` | `docs/F02-NL-ZERO-INIT-2026-10-31.md`、README 差異列、CHANGELOG |
| `0207951` | F-02 獨立驗證交付（置於 `docs/verification/`）、證據索引、`tools/redact_paths.py` |
| release commit | 版本 0.3.0、CHANGELOG、README 直接比較列、`compare_mosqito.py --nl-init`、本紀錄 |

## 驗證

### 本機，release commit 狀態

- 工具鏈：rustc / cargo 1.99.1（`rustup default stable`），Windows 10 x64，AVX2+FMA，
  12 個邏輯處理器。
- `cargo fmt --all --check`：乾淨。
- `cargo clippy --all-targets -- -D warnings`（於 `iso532/` 執行，即 CI 指令）與
  `cargo clippy --workspace --all-targets --all-features -- -D warnings`：乾淨。
- `REQUIRE_AVX2=1 cargo test --workspace --all-features`：100 passed、0 failed、
  3 ignored（hash dump、Python contract dump、靜音吞吐量），包含
  `nl_zero_init`（6）、`low_freq_correction`（6）、`stream`（11）、FFI（17）與
  2 個 doctest。第一次以預設建置平行度執行時，測試二進位檔編譯失敗
  （`found invalid metadata files`、`handle_alloc_error`），當時機器的分頁檔已
  全數提交；改以 `-j 3` 重跑後編譯並通過。兩次嘗試均無任何測試失敗。
- `tools/golden_manifest.py --verify`：175 個檔案相符。
- Python：`maturin develop --release`（安裝 0.3.0，`iso532.__version__ == "0.3.0"`），
  接著以 `ISO532_REQUIRE_PARITY=1` 執行 `pytest iso532-py/tests`：47 passed
  （smoke、stream、`nl_init`，以及 27 個 MoSQITo 直接比較案例）。

### CI

- Run 21（`5450d39`）與 run 22（`0207951`）：六個 job 全綠（ubuntu 與 windows 上的
  test、ffi、py），包含依零狀態預設重新記錄的 Linux 凍結 hash 關卡。
- release commit 的 run 結果記錄於 tag 訊息。

### 獨立驗證

[`docs/verification/2026-10-31-F02-5450d39/F02獨立驗證報告.md`](verification/2026-10-31-F02-5450d39/F02獨立驗證報告.md)
（凍結快照 `5450d39`，以 MSVC 重新建置官方 Annex A C 程式）：F-02 在其範圍內 PASS。
前綴因果性 48/48，`N` 與全部 240 個 Bark 列位元逐一相同；批次自第 0 幀起與因果
串流位元逐一相等，36/36；官方 C 的 `f_nl` 階段在同一組 21 頻帶主響度上 28/28，
最大 |delta| 1.78e-14；FFI/Python 預設值 8/8；`MosqitoTail` 負對照仍重現修正前的
數值 4/4。在 2 s / 25 Hz / 119 dB SPL 正弦波上，時變包絡線的例外由 1/1000
（`N`）與 56/240000（`N'`）降為 0/0。因下列未結項目，整體專案狀態仍為 PARTIAL；
其中沒有任何一項是本次 release 造成的回歸。

## 產出物（自 release commit 建置，Windows x64，rustc 1.99.1）

| 檔案 | SHA-256 |
|---|---|
| `iso532-0.3.0-cp39-abi3-win_amd64.whl` | `cb4bc0864392cc66d50cf7268584e833d4a63d8cfeb01bce5c6d7b2e4d3967b4` |
| `iso532_ffi.dll` | `92c2c26803fdf32caf6c1a479c7579e8b92d47fd31ac8d50a438c4e047db9e66` |
| `iso532_ffi.dll.lib` | `e5b7a8f812cd9e6d8be7a22f15dd0493ef3ebda7920757f3858d1e63026c05a9` |
| `iso532.h` | `8f49fe105a6e287736f78b0eea21eb41b7bbeef02edffb89c7750b419e0a79bb` |

`iso532.h` 與 import library 與 v0.2.0 逐位元相同（C ABI v1 不變）。
PE 二進位檔內嵌建置中繼資料，因此在另一台機器重新建置，不預期能逐位元重現
DLL 與 wheel 的 hash；可重現的部分是原始碼與輸入的 hash。

## API 遷移

- `iso532::zwtv::nonlinear_decay::nl_loudness_avx2(core, n_time, mode)` 現為
  `nl_loudness_avx2(core, n_time, mode, init)`。呼叫這個低階函式的程式，要用新預設
  請傳 `NlInit::Zero`，要用先前的行為請傳 `NlInit::MosqitoTail`。`loudness_zwtv`、
  `ZwtvProcessor::process`、`nl_loudness`、`nl_loudness_with_mode`、C ABI 與
  Python 批次函式維持原簽章，並切換為零狀態預設。
- 任何要在 1e-15 等級與 MoSQITo 1.2.1 比較的人，必須傳
  `NlInit::MosqitoTail` / `nl_init="mosqito_tail"`；見下方的比較。

## Release 檢查清單逐項紀錄（`docs/RELEASE-CHECKLIST.md`）

| 項目 | 狀態 |
|---|---|
| README 檔案中的審查草稿引言區塊 | 不存在；無需移除 |
| 重跑 `tools/compare_mosqito.py` | 見下方「MoSQITo 比較」；README 直接比較列已針對兩種初始化更新 |
| 自重新產生的 golden 環境執行「Reproduce the evidence」指令 | 在既有的本機 golden 環境執行（manifest 已驗證，175 個檔案）；本次 release 未從頭重新產生 |
| `docs/GOLDEN-REGEN-SOP.md` 先決條件 | 自 v0.1.0 以來未變 |
| 能力與邊界敘述對照已打 tag 的原始碼 | README 的 F-02 差異列自 `5450d39` 起存在；數值差異表已為本次 release 重新量測；其他能力宣稱未變 |
| `THIRD_PARTY_NOTICES.md`、`CITATION.cff`、`SECURITY.md`、範本 | `CITATION.cff` 版本已更新（日期不變，同一天）；其他未變 |
| release 產出物的防毒掃描 | **待執行的人工步驟**：Avira 為目前啟用的產品；建置機器上的 Windows Defender 已停用。發布二進位檔前，請以 Avira 掃描產出物資料夾，並在此記錄產品、版本、hash 與結果 |
| SHA-256 校驗值 | 如上表 |
| 僅限本機的檔案、壓縮檔、`data/`、憑證、機器路徑未被 stage | `data/` 與壓縮檔已 gitignore；`python tools/redact_paths.py --check docs` 輸出 `clean` |
| 驗證交付已建立索引，含大小、SHA-256 與連結 | 大小與 SHA-256 已記錄於 `docs/verification/README.md`；**下載連結仍為「link pending」**，待壓縮檔上傳至共用雲端硬碟。壓縮檔不進庫 |

## MoSQITo 比較（release commit，rustc 1.99.1）

與 README 表格相同的腳本、訊號與流程（3 s 契約訊號、一次 warm-up、量測 30 次
迭代），Python 3.11.9、NumPy 2.4.6、MoSQITo 1.2.1：

| 實作 | 平均 | 樣本標準差 | 最小／最大 | 相對速度 |
|---|---:|---:|---:|---:|
| ISO532 Rust 經 Python binding，`nl_init="zero"` | 12.210 ms | 0.771 ms | 10.894 / 13.683 ms | 563.36x |
| MoSQITo 1.2.1 `loudness_zwtv` | 6.879 s | 0.109 s | 6.752 / 7.109 s | 1.00x |

同一次執行的直接數值比較：

| 初始化 | max abs dN(t) | max abs dN_specific(t) | 位置 |
|---|---:|---:|---|
| `nl_init="zero"`（預設） | 5.826515e-03 sone | 3.245252e-02 sone/Bark | t = 2 ms；契約訊號沒有前導靜音，因此 MoSQITo 的 `core[-1] / 24` 種子不為零 |
| `nl_init="mosqito_tail"` | 2.664535e-15 sone | 3.455569e-15 sone/Bark | 與 README 2026-07-20 的數值相同 |

第二列顯示共用的衰減迴圈未變；第一列的全部差異都來自初始化。README 效能表維持
2026-07-20 於安靜機器上的量測；上方的計時是 release 當時的快照。

## 已知未結項目（0.3.0 未處理）

- V-01：`tests/annexb.rs::isoclose` 使用加法容差；Annex B workbook 使用
  `max(0.1, 5 %)`。空向量、無限大的參考值與無法解析的 CSV 列未被拒絕。規格：
  `docs/修正報告2.md` 第 12.2 與 15.5 節。僅影響測試，無數值影響；規劃為下一步。
- C-01：對於長度不是 96 個樣本倍數的訊號，批次輸出有 `ceil(ceil(L/24)/4)` 個點，
  比官方 CLI 的總響度寫出器（`floor`）多一個；官方的比響度寫出器本身則使用
  `ceil`。多出的那一點沒有官方參考值。輸出長度契約的決定待定。
- C-02：批次 ZWST/ZWTV 接受 NaN 與無限大樣本，並回傳 `Ok` 與零響度；串流路徑將
  該樣本歸零並舉出 `NONFINITE_INPUT`。拒絕／標記／替代的決定待定。
- 穩態前端：整段訊號 RMS 含濾波器啟動段（MoSQITo 相容）對上附安定窗
  （`TimeSkip`）的參考濾波器組；低頻高位準時的比響度與 C 程式不同
  （TimeSkip = 0.2 s 時 240 個 Bark 值中有 66 個），總響度則維持在容差內。前端
  契約的決定待定。
- 官方參考資料的問題（N5 欄與窗、確切的 1 % 邊界、Rust 與 MoSQITo 的
  `USL[12][4]` 0.24 對上 Annex A C 程式的 0.22，F-03）仍待權威來源
  （ISO 532-1:2017 Table A.9 與條文）。本次 release 不更動該表。
- `N_WARMUP_FRAMES = 580` 與 `WARMUP` 旗標維持其 v1 意義；自 F-02 起，它們不再
  標示批次／串流差異。

## 下游

`iso532-rs-panel` 以 git tag `v0.1.0` 釘住引擎。要採用本次 release，請將
`plugin/Cargo.toml` 中的 tag 改為 `v0.3.0`，執行 `cargo update -p iso532`，並重跑
panel 自己的驗收關卡（P-01 至 P-03）；panel 的產品版本與引擎版本獨立。panel 使用
串流路徑，其數值不受 F-02 影響；F-01（v0.2.0）則確實會影響它。
