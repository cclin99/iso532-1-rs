# C-01 獨立驗證報告

日期：2026-11-03（Asia/Taipei）。驗證者：Astra。受驗 commit：`aa379db8f3dc37f5048ac6c8b7a6d4ba2a6c3b76`（`aa379db`）。對照：[English](report.en.md)。

## 1. 判定

**PARTIAL — 本輪 C-01 數值缺口不得結案。** 已取得獨立官方 C 參考值。960 個目標 specific 比較全部滿足 <=1e-14 sone/Bark，但 4 個 total 絕對差全部超過 <=1e-14 sone。每個合併目標點因此皆為 **WITHIN TOLERANCE**，不是 AGREES。total 最大差為 4.1705202592388566e-7 sone。Annex B 備援 `max(0.1,0.05*abs(reference))` 通過，但不能取代預註冊門檻。

最終十個 gates 中九個通過，four-rounding-agreements 失敗。必要素材／建置／精度均取得：**blocked：無**。**skipped：**全 workspace／binding／package／效能驗收，以及另行完整 audit 條件審查。7 個 output-grid 測試僅是輔證，不是 reset／flush／短輸入的完整驗收。不改 DSP、測試、golden、決策 memo、brief 或 audit closure 列；未 commit／push。

## 2. 固定素材與執行

雙語[預註冊設計](experiment-design.md)在開跑前寫入。run-start.json 記錄開始時間 `2026-11-03T00:18:45.230682+00:00` 與兩份設計 hash，設計至今未變；主要執行結束於 `2026-11-03T00:25:01.520303+00:00`。從固定 commit 解出獨立 scratch 快照，受驗來源前後 hash 相符；保留原有未追蹤 F-03 交付資料夾。

從本機保存的歷史證據 ZIP 取回官方 archive 素材，本輪重新建置，未沿用歷史數字。ISO_532-1.c 未變，SHA-256 `a74b45ed297cd09ac60701a923120341137d227e536f3109ae4ece810d834491`；原 header、CLI main/helper、archive hash 均列清單。MSVC 19.44.35228 x64 使用 `/nologo /O2 /fp:precise`；`_CRT_SECURE_NO_WARNINGS` 僅抑制 CRT 診斷。Rust 使用 `rustc 1.99.1 (58cf8f9c3 2026-10-13)`、release profile、預設 runtime dispatch（AVX2 可用）。Rust harness 有獨立 Cargo manifest/lock，呼叫固定快照公開 loudness_zwtv。

所有 WAV 均為單聲道 48 kHz little-endian 有號 PCM16，以整數 / 32768 解碼，使用官方 Annex C 60 dB 校準檔與 CLI 相同逐樣本累加方式。聲壓倍率為 **2.8357977163914438**，bits `4006afb6b68fc829`。C/Rust 取得相同 little-endian binary64 聲壓 bytes；官方 C helper／CLI 等式解碼器對每份補零及邊界 WAV 產生的 bytes 亦相同。補零僅附加零值。原 WAV、解碼 PCM、聲壓、補零 WAV／聲壓與校準檔 hash 均保留。decoder-wrapper.c.txt 不改 DSP 本體，只呼叫官方 reader 並匯出校準輸入；rust-probe.rs.txt 匯出完整陣列並列印目標 bits。

C／CLI 建置及所有計算子程序退出碼均為 0。cl /Bv 未帶來源檔，預期回報 D8003 並退出 2；環境的 vswhere.exe 查找警告保留且非致命。兩者均未被隱藏或冒充數值通過。

| Binary | SHA-256 |
|---|---|
| c01-probe.exe | f9a538f6c346e59c36ed6f8e9da1bafa9ad1072855b2fc4f5fc65b6e33a5e256 |
| reference.dll | fb1ef5be897b1230b6c0aae62fae125b64a9d7080ee00d70cc59b134086a7e5d |
| reference_cli.exe | 598b224790d6c7c28ed16e95ce4e2d8f01973f2380f67451d2df5bf226f6d854 |


## 3. 目標點與主要結果

零起算：K=floor(L/24)、L_pad=96*(ceil(L/96)+1)、j=K/4=Rust frames-1。參考值是補零 C 在 CLI 序列化之前、未抽樣的第 K 幀。比較前已驗完整陣列形狀與全部有限值；每個 total 與全部 240 specific 均保留 decimal17 與 binary64 bits 於 JSON／CSV。下表時間保留 Rust 精確格點的 binary64 十進位表示。

| Signal | L | K | L_pad | j | Rust frames | t (s) |
|---|---|---|---|---|---|---|
| 18 | 103969 | 4332 | 104160 | 1083 | 1084 | 2.1659999999999999 |
| 23 | 122401 | 5100 | 122592 | 1275 | 1276 | 2.5499999999999998 |
| 24 | 115202 | 4800 | 115392 | 1200 | 1201 | 2.3999999999999999 |
| 25 | 122401 | 5100 | 122592 | 1275 | 1276 | 2.5499999999999998 |

| Signal | C total (sone) | Rust total (sone) | Total abs diff | Max specific abs diff | Verdict |
|---|---|---|---|---|---|
| 18 | 0.00095543263901191108 | 0.00095521696145359593 | 2.1567755831514244e-07 | 9.1113381304915761e-24 | WITHIN TOLERANCE |
| 23 | 0.0034913530909121875 | 0.0034909360388862636 | 4.1705202592388566e-07 | 3.2598605043503344e-23 | WITHIN TOLERANCE |
| 24 | 0.0010659327175432183 | 0.0010656334112001788 | 2.9930634303952305e-07 | 2.1604372979486025e-23 | WITHIN TOLERANCE |
| 25 | 0.0011947790020081512 | 0.0011945761670982473 | 2.0283490990394455e-07 | 4.6742163950249433e-24 | WITHIN TOLERANCE |


specific 欄是全部 240 Bark 值的最大差，不是抽樣子集。4 個 total 均未達捨入門檻，960 個 specific 全過。CLI total／specific 資料列 j 均存在、時間相符、specific 各 240 欄，四位小數序列化差皆 <=0.000050000001；高精度參考不是取自 CLI 文字。

## 4. 對照與最終 gates

C 原長與補零之間全部 19,332 個原始內部 total 幀與 4,639,680 個 specific 值 bitwise 相同，涵蓋未抽樣到 CLI 的內部幀。這是實測全量比較，不是從 CLI 格點推論。

| Signal | C total comparisons | C specific comparisons | Bitwise mismatches (total/spec) | Max abs diff (total/spec) | First mismatch |
|---|---|---|---|---|---|
| 18 | 4332 | 1039680 | 0 / 0 | 0 / 0 | none |
| 23 | 5100 | 1224000 | 0 / 0 | 0 / 0 | none |
| 24 | 4800 | 1152000 | 0 / 0 | 0 / 0 | none |
| 25 | 5100 | 1224000 | 0 / 0 | 0 / 0 | none |


比較器負對照：首輪把注入後參考副本與 Rust 比較，但既存 total 差已超門檻，first failure 因此為 total，干擾指定座標檢查。已完整保留首輪結果及 runner。修正後以**同一個未變的比較器**，比較原 C 參考與 specific[137] 加 1e-6 的副本。4 組自比皆 AGREES；4 組注入皆非 AGREES 並精確指出該座標。有限值／形狀拒絕路徑亦通過。原始數值與門檻均未改；交付修正版重現 runner，本輪僅重新執行這個隔離對照，時間與前後 harness hash 見 control-correction.json。

| Gate | Status |
|---|---|
| official_source_identity | passed |
| source_snapshot_unchanged | passed |
| four_rounding_agreements | failed |
| all_internal_prefix_invariance | passed |
| comparator_negative_control | passed |
| finite_shape_rejection_controls | passed |
| CLI_target_serialization_grid | passed |
| eight_boundary_rows | passed |
| identical_pressure_input | passed |
| supporting_output_grid_contract | passed |


固定快照 `cargo test -p iso532 --test output_grid --locked --offline` **7/7 passed**（0 failed、0 ignored），涵蓋 16 長度、時間軸、零補／真實延續的前綴決定性與 stream chunking；保留編譯日誌及退出碼。

## 5. 長度邊界實測

基底為 Annex B 18 的前 4897 個校準樣本，hash 見 boundary_base；各列為其精確前綴。C library 幀數來自實際回傳值，CLI 為解析資料列數，Rust 為讀出陣列長度。每列均符合預註冊表。

| L | C frames | CLI total | CLI specific | Rust n | Rust spec elements | Rust time | Status |
|---|---|---|---|---|---|---|---|
| 4800 | 200 | 50 | 50 | 50 | 12000 | 50 | passed |
| 4801 | 200 | 50 | 50 | 51 | 12240 | 51 | passed |
| 4823 | 200 | 50 | 50 | 51 | 12240 | 51 | passed |
| 4824 | 201 | 50 | 51 | 51 | 12240 | 51 | passed |
| 4825 | 201 | 50 | 51 | 51 | 12240 | 51 | passed |
| 4895 | 203 | 50 | 51 | 51 | 12240 | 51 | passed |
| 4896 | 204 | 51 | 51 | 51 | 12240 | 51 | passed |
| 4897 | 204 | 51 | 51 | 52 | 12480 | 52 | passed |


## 6. 發現與目前判斷

補充唯讀診斷確認：每個訊號 C/Rust total 差早在共同輸出 **j=54（0.108 s）** 已超過 1e-14，早於額外尾點。Rust 原長與補零的**全部原始 total／specific（含目標尾點）均 bitwise 相同**。合併 C 不變性對照，可確認此次補零操作沒有引入這項跨實作差異。

| Signal | Common points | First total diff >1e-14 (j) | Max common total abs diff | Max common specific abs diff | Rust original/padded total/spec mismatches |
|---|---|---|---|---|---|
| 18 | 1083 | 54 | 0.0030368413726424848 | 0.043772852817229202 | 0 / 0 |
| 23 | 1275 | 54 | 0.0015480181402631743 | 0.035081930844496512 | 0 / 0 |
| 24 | 1200 | 54 | 0.0034863683542534218 | 0.034851647205261127 | 0 / 0 |
| 25 | 1275 | 54 | 0.0006434225633227264 | 0.026392651762537689 | 0 / 0 |


來源證據：官方 C ISO_532-1.c:1002-1015 先算 slope total／specific，再僅對 total 作時間加權；:553-574 保留低通歷史狀態，:607-614 合併 3.5 ms／70 ms 分支。固定 Rust iso532/src/zwtv/mod.rs:130-150 與 temporal_weighting.rs:40-55 亦分開處理並保留歷史狀態。因此，接近消失的尾點 specific 頻譜一致，仍可能伴隨 total 中較早差異的加權殘留。這是有狀態結構支持的目前判斷；**尚未隔離上游數值根因**，不歸因 F-03 係數。較早 specific 也存在差異，已在診斷中分列。

決策 memo 從同一實作的前綴決定性，延伸至跨 C/Rust total 的 1e-14 一致，是待證假說；本輪**未證實**。本輪支持維持 ceil 的前綴性及補零參考有效性，但不支持關閉較嚴格數值 gate。後續若另行追查，需對齊時間加權前 total 歷史與時間加權後輸出，才能定位根因或提出變更。本報告不修改既有決策或 audit 列。

## 7. 證據、重現與界線

- [results.json](results.json): final results, all 241 C/Rust values per signal, bits/decimal17, both controls, input/output hashes, boundaries and gates.
- `signal-*-target.csv`: 964 value pairs with round-trip decimal17 and binary64 bits. `*-Loudness.csv` / `*-SpecLoudness.csv`: original CLI serialization.
- [run-start.json](run-start.json), [run-log.json](run-log.json): preregistration hashes, commands, versions, stdout/stderr, exit codes and library return values.
- [attempt-1-results.json](attempt-1-results.json), [attempt-1-run_experiment.py.txt](attempt-1-run_experiment.py.txt), [control-correction.json](control-correction.json), [control-correction.diff.txt](control-correction.diff.txt): original attempt and explicit comparator-control correction.
- [history-diagnostic.json](history-diagnostic.json), [diagnose_history.py](diagnose_history.py): same-round follow-up, separate from primary acceptance.
- [source-input-hashes.json](source-input-hashes.json), [delivery-check.md](delivery-check.md), [delivery-integrity.json](delivery-integrity.json): material provenance and post-redaction integrity.

依 [commands.md](commands.md) 與交付腳本，使用清單中的原始素材，在新 scratch／輸出目錄重現。只交付 UTF-8 文字；WAV／binary／完整原始陣列留 scratch 並以 hash 識別。去識別化前 harness hash 識別當時實跑原檔，最終交付 hash 識別去識別化文字，兩者不宣稱 bytes 相同。delivery-integrity.json 明確排除自身。

本輪為指定快照／工具鏈、四個訊號及八個形狀邊界的數值驗證，不是全面 ISO 認證、F-03 獨立結論、跨平台驗證或完整 C-01 audit closure。嚴格 total gate 仍未通過。
