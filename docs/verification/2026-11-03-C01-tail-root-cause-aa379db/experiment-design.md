# C-01 總響度尾值根因實驗設計 — 開跑前登錄

2026-11-03（Asia/Taipei）。獨立驗證者：Astra。固定 commit aa379db8f3dc37f5048ac6c8b7a6d4ba2a6c3b76。寫於本輪計算前。對照：[English](experiment-design.en.md)。

## 1. 固定輸入與基線

使用 Annex B 18/23/24/25 與下表完全相同的校準聲壓 bytes，自前輪 scratch 唯讀複製（單聲道 PCM16 48 kHz、Annex C 60 dB 校準）；亦核對原 WAV／archive hash。明確重用固定輸入，不把前輪計算結果冒充新證據。重新計算原長 Rust public 與補零 C public，要求四個舊 total bits 完全重現，否則先查明原因再作歸因。K=floor(L/24)、L_pad=96*(ceil(L/96)+1)、目標 j=K/4。相同補零輸入的雙方完整內部格點皆為 L_pad/24 幀；階段比較聚焦 0..K（含），scratch 保留完整陣列及 hash。

|Signal|L|Pressure f64le SHA-256|C padded tail|Rust original tail|
|---|---|---|---|---|
|18|103969|b16a82ee3b9f3eeec6261da60083d4de9af6a85c373b7f96a4ae024a5d5aef7a|0.00095543263901191108|0.00095521696145359593|
|23|122401|c67d32d7146dbf2a83791ff439973642f0089a9c17e1ae133502b80827837433|0.0034913530909121875|0.0034909360388862636|
|24|115202|2f20c961bb76b3f29e8d36a3a80edddfc56336c4784bfefece75831e474d1298|0.0010659327175432183|0.0010656334112001788|
|25|122401|0f2ecae2a233732ad0763da35c20168aaa19db3af8298f88539b1faf358babcb|0.0011947790020081512|0.0011945761670982473|

官方 C SHA-256 a74b45ed297cd09ac60701a923120341137d227e536f3109ae4ece810d834491；未改原始編譯單元，MSVC /O2 /fp:precise。固定 Rust 隔離快照與獨立 harness；不改工作樹來源／測試／golden／決策／audit 列，不 commit／push。本輪使用新交付／scratch，舊證據完全不動。

## 2. 可反駁假說與控制

H1（優先）：Rust 每幀 slope total 四捨五入（N<=16 時 0.001 sone，較大時 0.01）對尾端 total 差有貢獻；官方 C slope total 僅截斷負值。以同一 nonlinear 上游歷史、同一 TW，比較 rounded/raw 歷史。要求 raw Rust 重新四捨五入後 bitwise 重現 rounded 歷史，不只看原始碼作結論。

H2：TW 不同算術造成差異。把同一 C/Rust rounded/raw 歷史分別送入官方 C TW 與 Rust TW，對比全歷史與尾點。H3：殘差在上游或 slope 語意（USL cell、float 常數、格點／比較）產生。實測完整階段、同輸入階段比較、固定順序跨管線分解。Rust raw slopes 的單 cell 0.24->0.22 僅為反事實，不作規範權威／修正決定；整段 slope 替換不能單獨把殘差歸給該 cell。

解讀前，C 階段 replay 必須與未修改 C public API 的全部內部 total／240 specific bitwise 相同；Rust replay 必須與未修改 public API 全部抽樣輸出 bitwise 相同。Rust baseline 呼叫未改 crate 公開階段；raw 與 cell 變體為從固定 slope／table 來源生成的獨立模組，交付完整轉換／diff 與改前改後 hash。C wrapper 僅呼叫／匯出原階段，不重寫原計算本體。若等價控制失敗，先停止歸因、修查 harness 並保留失敗痕跡。

## 3. 固定介入順序與定量門檻

定義目標內部 K 的 E_i=T_i-T_C（Rust 方向減官方 C），T_0 為原始 Rust。開跑前固定順序：

1. T_1：只取消 Rust slope-total rounding，保留 Rust 上游與 TW。
2. T_2：相同 Rust nonlinear 歷史，改官方 C slopes，保留 Rust TW。
3. T_3：相同 Rust core 歷史，改 C nonlinear，後接 C slopes／Rust TW。
4. T_4：相同 Rust filter/SPL 歷史，改 C main，後接 C nonlinear／slopes 與 Rust TW。
5. T_5：改 C filter/SPL（得到完整 C pre-weighting 歷史），保留 Rust TW。
6. T_6：改 C TW，回到未修改官方 C 基線。

列 signed contribution E_(i-1)-E_i、剩餘 E_i、絕對殘差、signed fraction contribution/E_0 與望遠鏡和重建誤差。負數或 >100% 貢獻照實列；此為依順序分解，不冒稱唯一獨立因果分配。另對 C pre-weighting 歷史注入 Rust rounding，再送兩套 TW 作反向對照，並比較 Rust raw 0.24／0.22 單 cell 變體。必要時僅沿殘差追到可區分演算法語意／浮點算術，不無限擴張或修程式。

舊絕對門檻 1e-14 sone／sone-Bark 不變；基線／等價控制要求 bitwise，運算前驗 finite／shape。分解要求 |sum(contributions)-E_0|<=1e-14、最後殘差 <=1e-14；每個中間殘差亦各自列是否達 1e-14，不以解釋百分比冒充通過。目標、首差、最大差座標均留至少 17 位十進位字串與 binary64 bits，並列原始階段／輸入／來源／binary hash。

## 4. 正負控制與量測

比較器自比應零差；對一個有限參考副本已知階段座標加 1e-6，同一 finite／shape／error 比較器須指出該座標超過 1e-14；拒絕非有限值與錯形狀。因果傳遞正控制：時間加權前 K-20 幀 total 加 0.01，兩套 TW 的目標變化均須 >1e-14；不改原陣列。不需新增無關全量測試。

filter/SPL（28 bands）、已校正 main（21）、nonlinear（21）、raw／rounded slope total、specific（240）、weighted total：各列比較數、依時間排序首個 bitwise／門檻差、最大差與座標、目標差及精度值；同時比較原生上游與同輸入階段。完整 raw 陣列留 scratch，交付精簡 stage／target CSV，不交付 binary。

## 5. 判定與交付

區分 confirmed、inferred、unresolved。定量主要原因不自動等於完整 1e-14 解法、規範 bug 判決或改碼許可；不關閉 C-01。交付一致雙語設計／報告、results.json、完整 harness／變換 diff、stage／target CSV、命令／版本／日誌／退出碼、來源 hash、delivery-check.md、最終完整性清單。交付僅 UTF-8；執行兩次去識別化，逐項列 skipped／不支援／非 UTF-8，檢視 diff，文字完成後重跑再計交付 hash，清單排除自身，原始素材 hash 不改義。
