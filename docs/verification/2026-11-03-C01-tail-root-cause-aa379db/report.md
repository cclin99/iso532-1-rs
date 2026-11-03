# C-01 總響度尾值根因追查

2026-11-03（Asia/Taipei），獨立驗證者 Astra。快照 `aa379db8f3dc37f5048ac6c8b7a6d4ba2a6c3b76`。[English](report.en.md) · [預註冊設計](experiment-design.md)。

## 1. 結論

**已確認主要原因是 Rust 對中間每幀 total 作四捨五入，另有 slope 語意差；不是額外尾點索引錯置。** 固定 nonlinear 歷史與時間加權，僅去除此四捨五入，可解釋四個原始 signed 差的 67.2893%–98.3967%。四例都**仍未達**原定 1e-14 sone。完整階段分解已定量閉合，但尚未把所有剩餘 slope 差追到單一分支／常數。C-01 驗收仍未結案；不宣稱 production 修復，也不裁定規範係數。

| Signal | Baseline R−C (sone) | Rounding contribution % | Residual after removing rounding | Residual after raw cell22 |
|---|---|---|---|---|
| 18 | -2.156775583e-07 | 93.97182728 | -1.300141574e-08 | 1.225633281e-09 |
| 23 | -4.170520259e-07 | 67.28927507 | -1.36420741e-07 | -8.452009531e-09 |
| 24 | -2.99306343e-07 | 97.27845763 | -8.145748935e-09 | 6.027779456e-10 |
| 25 | -2.028349099e-07 | 98.39667769 | -3.252097354e-09 | -3.252097354e-09 |


Rust calc_slopes.rs:161-165 每個 2 kHz total 在 <=16 sone 時捨入至 0.001，較大時至 0.01；官方 C f_calc_slopes 無此捨入。raw Rust 歷史重新套用該規則，可 **bitwise** 重現原 rounded 歷史。這些歷史差再經 TW 傳至尾端，並非僅對最後顯示數字捨入。尾點未加權頻譜已極小且相符，不能消除 weighted total 中的歷史差。

## 2. 證據有效性與有序歸因

本輪相同 hash 聲壓 bytes、新固定 commit 快照、未變官方 C SHA-256 `a74b45ed297cd09ac60701a923120341137d227e536f3109ae4ece810d834491`；MSVC 19.44.35228 `/O2 /fp:precise`、Rust 1.99.1 release／預設 dispatch。四訊號舊 public 尾點基線全部 **bitwise** 重現；C replay 全內部 total／specific 與 public 相同，Rust replay 全抽樣 total／specific 與 public bitwise 相同。完整階段包含 filter/SPL、已校正 main、nonlinear、slope total／specific 與 TW；同輸入階段控制涵蓋雙向上游，首個時間差、最大差與座標詳列 JSON／CSV。

首版 wrapper 的 input-immutability guard 正確抓到官方 C main 會改寫 SPL，引發失敗；attempt-1-* 完整保留。修正為先提供私人工作副本，再呼叫原函式，於全新 run2 重新跑完整實驗；更早的 Python 語法錯誤亦記錄。不將失敗嘗試冒充通過，預註冊設計 hash 不變。

定義 E_i=T_i−T_C，各項貢獻為 E_(i−1)−E_i，最後一步前均保留 Rust TW。事先固定順序為 rounding → slopes → nonlinear → main → filter → TW；signed 貢獻依順序而定，不冒稱唯一獨立百分比，保留抵消。望遠鏡和最大重建誤差為 **0 sone**。把 main 與其下游替換為 C 後，剩餘最多 5.095750210681871e-18 sone；最後全 C 替換精確回到基線。

| Signed contribution (sone) | 18 | 23 | 24 | 25 |
|---|---|---|---|---|
| remove_R_rounding | -2.026761426e-07 | -2.806312849e-07 | -2.911605941e-07 | -1.995828125e-07 |
| replace_slopes_C | -1.296987679e-08 | -1.363086719e-07 | -8.110269432e-09 | -3.212727779e-09 |
| replace_NL_C | 0 | 1.301042607e-18 | 0 | 0 |
| replace_main_C | -3.153894962e-11 | -1.120690893e-10 | -3.54795002e-11 | -3.936957466e-11 |
| replace_filter_C | 5.095750211e-18 | 0 | -3.252606517e-18 | 0 |
| replace_TW_C | 0 | -2.168404345e-18 | 0 | -6.505213035e-19 |


四組比較器自比／finite／shape／已知座標擾動與 TW 傳遞正控制全過。同一 C/Rust rounded/raw 歷史餵送兩套 TW，目標最大差僅 **4.33680869e-18 sone**；TW 算術無法解釋觀察到的 1e-7 級差，它傳遞的是不同上游歷史。原 strict 基線 gate 仍失敗。無關 workspace／binding／package 全套測試刻意 skipped；無素材／建置 blocker。

## 3. 具體 slope 與 main 控制

**USL cell：**只把 raw Rust USL[12][4] 的 0.24 改 0.22，對 18／23／24 有因果數值效果，但 **25 完全零影響**。因此單一 cell 不能解釋四案。這是相同歷史下與保存 C 的反事實對照，不是任何標準版本 cell 權威的證據。

| Signal | 0.22−0.24 effect (sone) | Other same-input slope gap: raw22−C | Gap after C epsilon=0 + tables64 |
|---|---|---|---|
| 18 | 1.422704902e-08 | 1.257172226e-09 | 1.291724238e-09 |
| 23 | 1.279687315e-07 | -8.339940441e-09 | -8.400504273e-09 |
| 24 | 8.748526881e-09 | 6.382574491e-10 | 6.926491861e-10 |
| 25 | 0 | -3.212727779e-09 | -3.178040338e-09 |


C slope 單獨取消 epsilon，以及再累積將 ZUP／RNS／USL 表改成 binary64，皆未消除主要殘差。末欄固定同一 Rust nonlinear 歷史與 Rust TW。這些變體每幀 Bark row 239 未寫，依訊號每變體分別有 4340、5108、4808、5108 個非有限 sentinel；只使用有限 TOTAL，不是有效的 specific 輸出替代。0.1f 格點刻意保留；此偏離如實記錄，未掩蓋。

**Main 常數：**C `.0635f` 先經 binary32 捨入再升位，Rust `0.0635` 直接為 binary64。只改此字面值，可解釋**較小 main-stage 差的 96.9374%–99.5930%**；再累積改 0.4f／0.32f 效果很小。此百分比的分母是 main-stage 差，不是全體原始誤差；未隔離的 main 殘差仍大於 1e-14。

| Signal | Original main-stage gap | MP1-only fraction % | Remaining after MP1 only | Remaining after MP1 + correction |
|---|---|---|---|---|
| 18 | -3.153894962e-11 | 97.85438801 | -6.767034849e-13 | -6.760548068e-13 |
| 23 | -1.120690893e-10 | 99.59296241 | -4.561633189e-13 | -4.561633189e-13 |
| 24 | -3.54795002e-11 | 96.93742981 | -1.086584598e-12 | -1.084293896e-12 |
| 25 | -3.936957466e-11 | 97.88150114 | -8.340439884e-13 | -8.340439884e-13 |


**r8 比較捨入：**最後限定 2×2 控制只在 raw cell24／cell22 變體把 r8 改為 identity，結果大幅惡化一致性且與 cell 有交互作用。此結果排除直接移除 r8 的簡單解法；不能把大幅介入效果冒稱原本微小殘差的歸因。

| Signal | r8 off/cell22 residual vs same-input original C | Cell × r8 interaction |
|---|---|---|
| 18 | -0.0001379427263 | 5.540427184e-07 |
| 23 | -0.0005117469018 | -6.705230238e-06 |
| 24 | -0.0001547866186 | -1.400052247e-08 |
| 25 | -0.0001172302946 | 0 |


## 4. 已確認、目前判斷與未解部分

- **confirmed：**中間 total rounding 為主項；cell 對三例有影響、第四例沒有；main `.0635f` 精度解釋大部分 main-stage 貢獻。有序全階段貢獻可重建四個原始差；baseline／replay／finite／controls 全過，僅去 rounding 的嚴格目標仍失敗。
- **inferred（有證據支持）：**加權尾值主要承載較早上游差異，而非補零索引造成；按宣告順序，filter／nonlinear／TW 替換在這四個尾點只貢獻約 1e-18 sone。
- **unresolved：**cell22、epsilon／table 控制後，同輸入 raw-slope 剩餘絕對差仍為 **6.926491860539258e-10 至 8.400504272667447e-9 sone**，尚未隔離到詳細分段／比較條件；累積 main 常數後剩餘 **4.561633189237302e-13 至 1.0842938959892967e-12 sone**，未逐一拆解表格精度／算術／分支。移除 r8 已證實不是有效捷徑。沒有宣稱任何組合為 production 修正，也未因殘差小就改列可接受。

追加控制均有限定範圍並以附錄明標探索性，不改原門檻或設計。後續若要實作須另行設計／審查；本報告不授權改碼、不關閉 C-01。

## 5. 交付與重現

- [results.json](results.json), [tail-decomposition.csv](tail-decomposition.csv), [stage-coordinates.csv](stage-coordinates.csv): complete primary metrics, signed effects, decimal17/binary64 evidence.
- [main-literal-controls.json](main-literal-controls.json), [slopes-controls.json](slopes-controls.json), [r8-control.json](r8-control.json): bounded exploratory controls and remaining gaps.
- [commands.md](commands.md), [run_experiment.py](run_experiment.py), [run-log.json](run-log.json): reproduction, exact build/execution commands, versions and exit codes. Supplement scripts/logs and all transformation diffs are adjacent.
- [source-input-hashes.json](source-input-hashes.json), [delivery-check.md](delivery-check.md), [delivery-integrity.json](delivery-integrity.json): original-material provenance and final redacted-delivery integrity.

只交付 UTF-8 文字；WAV／binary／完整 raw 階段陣列留 scratch 並列 hash，未改原生來源。原 source／input／binary／harness hash 保留原義；最終清單對應去識別化交付 bytes 且排除自身。舊 C-01／F-03 證據、DSP／測試／golden／決策／audit 列未變，未 commit／push；主代理另維護 index。
