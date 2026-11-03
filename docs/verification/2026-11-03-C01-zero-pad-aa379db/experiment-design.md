# C-01 實驗設計 — 開跑前登錄

日期：2026-11-03（Asia/Taipei）。獨立驗證者：Astra。受驗 commit：`aa379db8f3dc37f5048ac6c8b7a6d4ba2a6c3b76`（`aa379db`）。本設計寫於數值實跑之前。對照：[English](experiment-design.en.md)。

## 1. 問題與假說

H1：Annex B 18、23、24、25 原長 Rust batch 最後一點，與補零後官方 C 先前未輸出的內部第 K 幀一致。H2：補零不改變任何較早 C 內部幀的位元。H3：library／CLI／Rust 的實測形狀符合三種不同輸出格點公式。本輪驗證剩餘數值缺口，不代表完整 ISO 合規，也不裁定 F-03 係數。

## 2. 固定素材與方法

在 tmp 從固定 commit 解出隔離快照；建置前、執行後列來源 hash，harness 分開列。從本機保存的官方 archive 取出 Annex A 原始碼及 Annex B WAV；記錄 archive／WAV／header／CLI／library hash。要求 ISO_532-1.c SHA-256 為 `a74b45ed297cd09ac60701a923120341137d227e536f3109ae4ece810d834491`。使用與 2026-10-31 相同 MSVC `/nologo /O2 /fp:precise` 建置未修改的 C 與 CLI；`_CRT_SECURE_NO_WARNINGS` 僅為 CRT 診斷定義。獨立 wrapper 僅呼叫及匯出官方函式，不變動 DSP 常數、計算本體或迴圈邊界。

單聲道 48 kHz PCM16，以 little-endian 有號整數 / 32768 解碼。使用 Annex C 60 dB 校準檔與官方 CLI 相同的逐樣本強度累加及聲壓倍率。一次匯出校準後 binary64 樣本，將相同 bytes 提供 C 與 Rust；記錄解碼、校準、補零樣本與原 WAV hash、有限值、聲道、取樣率、位深、倍率及編碼。CLI 獨立讀取 PCM WAV 並套用相同校準；要求其解碼／校準聲壓 bytes 與 library 輸入相同。CLI 補零僅附加 PCM 零值，library 僅附加 binary64 零值。

## 3. 主要比較與固定門檻

每個原始長度 L，K=floor(L/24)、L_pad=96*(ceil(L/96)+1)、j=K/4。先驗 K mod 4=0、L mod 24>0。官方 C 分別執行原長與補零聲壓輸入，48 kHz、時變、自由場。參考為補零 C 未抽樣的 total[K] 與全部 b=0..239 的 specific[b,K]；對照原長 Rust loudness_zwtv 的 j=frames-1。先檢查形狀及全部有限值，再作減法。雙方 241 值均保留 17 位有效數字字串及 binary64 bits，逐值列差值與最大值。

AGREES 要求 total 絕對差 <=1e-14 sone 且全部 specific 差 <=1e-14 sone/Bark。僅當所有差值滿足 max(0.1,0.05*abs(reference)) 時，才可使用備援 WITHIN TOLERANCE；否則 DIFFERS。無法取得官方參考為 NOT OBTAINABLE。不得事後調門檻。CLI 文字僅檢查序列化／格點：補零 total/spec 均須有資料列 j、時間 j*0.002、240 specific 欄，四位小數與 library 一致（絕對差 <=0.000050000001）；不得用它判定 1e-14。

## 4. 對照與預期邊界表

逐訊號比較所有 C 內部 0<=k<K，包含未輸出到 CLI 的幀。total 與 specific 分別列比較數、bitwise 不同數、最大絕對差與第一不同座標；H2 要求零差異。在參考副本一個有限 specific 值加 1e-6，同一主要比較器須判非 AGREES 並回報注入座標；保留原始陣列。另測非有限值／形狀拒絕路徑，避免無效輸入誤過關。

使用 Annex B 18 前 4897 樣本為共同基底並列 hash，各取下表前 L 樣本。實測 C 回傳幀數、CLI 資料列數、Rust n/spec/time 長度，不能以公式冒充量測。

| L | C 幀數 | CLI total | CLI specific | Rust n/time | Rust specific 元素 |
|---:|---:|---:|---:|---:|---:|
|4800|200|50|50|50|12000|
|4801|200|50|50|51|12240|
|4823|200|50|50|51|12240|
|4824|201|50|51|51|12240|
|4825|201|50|51|51|12240|
|4895|203|50|51|51|12240|
|4896|204|51|51|51|12240|
|4897|204|51|51|52|12480|

執行固定快照 `cargo test -p iso532 --test output_grid --locked --offline` 作契約輔證。不改程式、不重生 golden，不作效能、binding／package／全套驗收，不改 audit 列，不 commit／push。

## 5. 判定與交付

四組主要比較、全部前綴對照、比較器對照、finite／shape／相同輸入 gates 與八列邊界全過，才能建議關閉本輪數值缺口。清楚區分 passed／failed／blocked／skipped／partial。完整 C-01 audit（含 reset／flush／短輸入）另行決定；任何必要 gate 失敗，即使 Annex B 備援通過亦不得結案。

交付雙語設計／報告、results.json、腳本、完整目標點 CSV、命令／日誌／退出碼／版本、來源／輸入／binary hash、delivery-check.md 及最終 delivery-integrity.json。只交付 UTF-8 文字，WAV／binary 留 tmp。執行路徑去識別化與 --check，逐項檢查未涵蓋格式及警告、檢視交付 diff；文字完成後重跑兩次，再算最終 hash，清單明確排除自身。原始素材 hash 保留原義。
