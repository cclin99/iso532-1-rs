# F-03 係數補償假說：預先定義實驗設計

日期：2026-11-03（Asia/Taipei）。Astra 獨立實驗。固定來源快照 `aa379db8f3dc37f5048ac6c8b7a6d4ba2a6c3b76`。本文件先於 harness 執行建立；正式 source、tables、goldens 不變。

1. H_fp：0.22 與 0.24 的差異可由 C/Python 浮點精度補償解釋。用精確有理數與 Decimal 80/120 位作獨立局部線性公式 oracle；將兩個係數與 C binary32、binary64、float 字面值提升至 double、Python float、NumPy float32/float64 完整交叉。不得將官方 C 本身當作數學真值。
2. 主單點 `N0=7/20`、`Δz=1/5`，公式 `N'=N0-sΔz`、`A=N0Δz-sΔz²/2`。先驗證所有線段端點在 `[0.30,0.42)`。加三個安全內點；總響度全鏈與 ISO 認證不在此局部模型範圍。記錄精確差、絕對誤差、ULP 及點值差/最大浮點誤差比；若浮點誤差遠小於係數效應且兩係數各自都近其獨立 oracle，則在受測情境不支持 H_fp。這不是全算法誤差上界。
3. H_layout：資料排列/索引造成該格差異。驗證 18×8 二維、row-major flat、Python nested、NumPy C/F-order 相同邏輯索引；使用 `100*row+col` 標記表，錯行、錯欄、錯 stride 為負面控制。成功只證明受測路徑，不能排除其他實作錯誤。來源 literal 不同與 storage 轉換誤差分開報告。
4. 邊界另測 `0.30/0.42` 及其 binary64 nextafter，比較未四捨五入比較、C 的 float 常數閾值、Rust r8 閾值邏輯，絕不把分支差異與安全內點混合。
5. 若工具允許，隔離 C 原始斜率函式及固定 Rust 算子做 stage trace，人工 `nm[4]=0.35`、其餘零，0.22/0.24 各執行；插樁記錄目標查表確實發生。另以 `nm[3]=0.35` 作不應受目標格影響的負控。保存派生 diff/hashes，binary 留 tmp。
6. H_intent：作者刻意補償屬歷史動機，僅數值實驗不能證明；沒有作者/commit 證據即 inconclusive。H_standard：標準係數唯一值需授權 Table A.9 或獨立可識別的約束；同公式帶入兩係數不構成標準裁決。不得將模擬值冒稱 ISO 真值。

交付包含雙語報告、精確結果、原始/派生 source hashes、可重現 harness、負控、去識別化與完整性證據。每項 gate 分開報告；無 commit/push/tag，無全套 cargo tests/benchmark，因本輪是研究而非正式產品修改。
