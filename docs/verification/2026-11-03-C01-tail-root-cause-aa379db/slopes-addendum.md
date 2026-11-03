# 探索性 slope 邊界與常數控制

時間：2026-11-03T13:08:05.503571+00:00

本附錄寫於主要實驗之後、以下控制之前。固定既有 Rust nonlinear 歷史與 Rust TW，比較相同歷史的 raw Rust cell22 與原 C slopes。兩個獨立生成的 C 診斷副本：(A) 只把 `_ZUP += .0001f` 改零；(B) 再去掉 ZUP／RNS／USL 表常數的 f 後綴。保留 C slope 演算法、USL cell 0.22 與 0.1f specific 格點累進。完整列 diff／hash，官方原檔不變。此為探索性，不修改預註冊驗收門檻，也不作規範選擇。

列目標 total 效果／殘差與完整 total 歷史差。本控制只分析 TOTAL：移除 epsilon 可能改變 specific 格點覆蓋，故 specific 緩衝先填 NaN，逐列記未寫／非有限值數與首座標，不宣稱 specific 等價；不得默默調格點或替換 NaN 以取得完整管線通過。兩控制後殘差保留未隔離 slope 實作影響，除非另有獨立證據。本小組控制完成後停止擴張並交付，1e-14 不變。
