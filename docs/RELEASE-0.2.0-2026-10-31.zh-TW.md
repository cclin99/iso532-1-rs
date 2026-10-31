# Release 紀錄：v0.2.0（2026-10-31）

> 對照／Pair: [English](RELEASE-0.2.0-2026-10-31.md) · 來源：en · 同步 2026-11-01

本次 release 的範圍：發現 F-01（ISO 532-1 Annex A 低頻 RAP/DLL 修正現在會選到表的
最後一列）。公開 Rust API、C ABI v1 與 Python 介面不變。數值輸出僅在低頻帶位準
高於第七個 RAP 門檻時改變；其餘一切與 v0.1.0 位元逐一相同。

已知未結項目列於文末。本次 release 不宣稱整體符合 ISO 532-1。

## 自 v0.1.0 以來的 commit

| commit | 內容 |
|---|---|
| `ae55ca1`、`73d110e`、`8fde6b6`、`603726b` | README、治理檔案、效能量測（僅文件） |
| `3dc420c` | F-01 修正、`low_freq_dll_row`、逐門檻單元測試、`tests/low_freq_correction.rs`、文件 |
| `6aea8b3` | 測試讀取器改用 `as_chunks` 並拒絕結尾不完整的記錄（clippy 1.99） |
| release commit | 版本 0.2.0、CHANGELOG、CI 串流測試、中性措辭、`docs/` 下的審核報告 |

## 驗證

### 本機，release commit 狀態

- 工具鏈：rustc / cargo 1.99.1（`rustup default stable`），Windows 10 x64，AVX2+FMA。
- `cargo fmt --all --check`：乾淨。
- `cargo clippy --all-targets -- -D warnings`（於 `iso532/` 執行，即 CI 指令）與
  `cargo clippy --workspace --all-targets --all-features -- -D warnings`：乾淨。
- `REQUIRE_AVX2=1 cargo test --workspace --all-features`：所有測試套件全綠，包含
  九個 MoSQITo golden fixture、Annex B 訊號 3/5/10、SIMD parity、決定性、
  凍結的 Windows hash 關卡、所有串流套件，以及 FFI（17）。
- `tools/golden_manifest.py --verify`：175 個檔案相符。
- Python：`maturin develop --release`，接著以 `ISO532_REQUIRE_PARITY=1` 執行
  `pytest iso532-py/tests`：36 passed（smoke、stream，以及 MoSQITo 直接 parity）。

### CI

- Run 18（`3dc420c`）：clippy 在兩個 runner 上都失敗，因為託管的 stable 工具鏈已
  移至 1.99.1（既有測試程式碼觸發 `chunks_exact_to_as_chunks`）；測試未執行。
- Run 19（`6aea8b3`）：六個 job 全綠（ubuntu 與 windows 上的 test、ffi、py），包含
  Linux 凍結 hash 關卡與 `low_freq_correction`。
- release commit 將 `stream_alloc`、`stream_no_rayon`、`stream_scalar` 加入 CI 測試
  清單；其 run 結果記錄於 tag 訊息。

### 獨立驗證

`docs/修正後獨立驗證報告.md`（凍結快照 `3dc420c` 與 `6aea8b3`，以 MSVC 重新建置
官方 Annex A C 程式）：F-01 在其範圍內 PASS（337 個原始邊界案例與 1,210 個新的
自由場／擴散場案例，0 個容差失敗；25 個 Annex B 案例不變，188 個儲存輸出與 v0.1.0
位元逐一相同）。因下列未結項目，整體專案狀態仍為 PARTIAL；其中沒有任何一項是本次
release 造成的回歸。

## 產出物（自 release commit 建置，Windows x64，rustc 1.99.1）

| 檔案 | SHA-256 |
|---|---|
| `iso532-0.2.0-cp39-abi3-win_amd64.whl` | `091b605abaab393f2aa73b6257bd0b9090bd7b6a594a2962800f8ba13a244b74` |
| `iso532_ffi.dll` | `f59ab3d4eea6eb8999ada992795cb253420652bdc7d374d2e8d6e79e466fb15d` |
| `iso532_ffi.dll.lib` | `e5b7a8f812cd9e6d8be7a22f15dd0493ef3ebda7920757f3858d1e63026c05a9` |
| `iso532.h` | `8f49fe105a6e287736f78b0eea21eb41b7bbeef02edffb89c7750b419e0a79bb` |

PE 二進位檔內嵌建置中繼資料，因此在另一台機器重新建置，不預期能逐位元重現這些
hash；可重現的部分是原始碼與輸入的 hash。

## Release 檢查清單逐項紀錄（`docs/RELEASE-CHECKLIST.md`）

| 項目 | 狀態 |
|---|---|
| README 檔案中的審查草稿引言區塊 | 不存在；無需移除 |
| 重跑 `tools/compare_mosqito.py` | 見下方「MoSQITo 比較」 |
| 自重新產生的 golden 環境執行「Reproduce the evidence」指令 | 在既有的本機 golden 環境執行（manifest 已驗證）；本次 release 未從頭重新產生 |
| `docs/GOLDEN-REGEN-SOP.md` 先決條件 | 自 v0.1.0 以來未變；所引用的工具（`setup_env.sh`、`gen_golden.py`、`golden_manifest.py`、`requirements.lock`）皆存在 |
| 能力與邊界敘述對照已打 tag 的原始碼 | README 的沿用選擇表已針對 F-01 更新；其他能力宣稱未變 |
| `THIRD_PARTY_NOTICES.md`、`CITATION.cff`、`SECURITY.md`、範本 | `CITATION.cff` 版本與日期已更新；其他未變 |
| release 產出物的防毒掃描 | **待執行的人工步驟**：建置機器上目前啟用的產品是 Avira Security；Windows Defender 已停用（`MpCmdRun` 回傳 0x80004005）。發布二進位檔前，請以 Avira 掃描產出物資料夾，並在此記錄產品、版本、hash 與結果 |
| SHA-256 校驗值 | 如上表 |
| 僅限本機的檔案、壓縮檔、`data/`、憑證、機器路徑未被 stage | `data/` 與壓縮檔已 gitignore。`docs/` 下的審核報告是在本 repository 之外撰寫的，含有來自審核者工作站絕對路徑的重現命令列；它們以審核證據的身分原樣收錄 |

## MoSQITo 比較（release commit，rustc 1.99.1）

與 README 表格相同的腳本、訊號與流程（3 s 契約訊號、一次 warm-up、量測 30 次
迭代），Python 3.11.9、NumPy 2.4.6：

| 實作 | 平均 | 樣本標準差 | 最小／最大 | 相對速度 |
|---|---:|---:|---:|---:|
| ISO532 Rust 經 Python binding | 16.889 ms | 3.594 ms | 13.345 / 30.285 ms | 452.22x |
| MoSQITo 1.2.1 `loudness_zwtv` | 7.637 s | 0.688 s | 7.129 / 9.922 s | 1.00x |

同一次執行的直接數值比較：max |dN(t)| = 2.664535e-15 sone、
max |dN_specific(t)| = 3.455569e-15 sone/Bark，與 README 中為 v0.1.0 記錄的數值相同；
這是預期結果，因為比較訊號並未進入 F-01 的影響範圍。

計時欄位是在機器同時執行獨立驗證與 release 建置時量測的（樣本標準差 3.6 ms，
README 量測為 0.45 ms），因此在此記錄為 release 當時的快照，README 效能表維持
2026-07-20/21 於安靜機器上的量測。引用新的計時數字前，請在閒置機器上重新量測。

## 已知未結項目（0.2.0 未處理）

- F-02：批次非線性衰減狀態以最後一幀作為種子（MoSQITo 相容）；官方 C 程式自零
  起算。串流路徑已經自零起算。規劃為獨立的數值變更（0.3.0），並附自 0 ms 起、
  涵蓋全部 Bark 的回歸測試；25 Hz / 119 dB 的時變起始段可看出此效應。
- V-01：`tests/annexb.rs::isoclose` 使用加法容差；Annex B workbook 使用
  `max(0.1, 5 %)`。空向量、無限大的參考值與無法解析的 CSV 列未被拒絕。
- C-02：批次 ZWST/ZWTV 接受 NaN 與無限大樣本，並回傳 `Ok` 與零響度；串流路徑將
  該樣本歸零並舉出 `NONFINITE_INPUT`。
- 穩態前端：整段訊號 RMS 含濾波器啟動段（MoSQITo 相容）對上附安定窗的參考
  濾波器組；低頻高位準時的比響度與 C 程式不同，總響度則維持在容差內。
- 官方參考資料的問題（N5 欄與窗、確切的 1 % 邊界、USL[12][4] 0.24 對 0.22）仍待
  權威來源。
- `N_WARMUP_FRAMES = 580` 是在合成測試訊號上凍結的；在 25 Hz / 119 dB 正弦波上，
  串流要到第 597 幀起才與批次相符到 1e-9。

## 下游

`iso532-rs-panel` 以 git tag `v0.1.0` 釘住引擎。要採用本次 release，請將
`plugin/Cargo.toml` 中的 tag 改為 `v0.2.0`，執行 `cargo update -p iso532`，並重跑
panel 自己的驗收關卡；panel 的產品版本與引擎版本獨立。
