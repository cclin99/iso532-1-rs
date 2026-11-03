# 最後一項探索性比較捨入控制

執行前：2026-11-03T13:11:06.700272+00:00。epsilon／table 控制仍留可量測同輸入 slope 差後，只把已移除 total rounding 的 Rust slope 模組中 r8(value)=(value*1e8).round()/1e8 改成 identity，分別測 cell24／cell22。原 Rust／C 不變，固定 R nonlinear 歷史與 R TW。列 2x2 cell／r8 交互項、相對相同歷史原 C slopes 與 epsilon-zero/tables-double C 診斷的尾殘差、完整歷史數量與 hash。此為最後限定控制，之後停止並如實列未解殘差，不改門檻，不冒稱修復。
