# 探索性 main-loudness 常數控制

Time / 時間: 2026-11-03T13:05:30.974700+00:00
Primary results SHA-256 (before redaction): c8e8915c6902c8896c40ae1c728e311563ba59089bdf1cbb3c9331605f228d31

本附錄寫於預註冊六步實驗完成後、以下追加計算之前。明確屬探索性，原設計與 1e-14 gate 不變。主要分解已將額外 3.15e-11 至 1.12e-10 sone 尾差定位到 main-loudness 實作。

假說：官方 C `.0635f`（先 binary32 捨入再升 binary64）與 Rust `0.0635`（binary64）可解釋該階段部分或全部貢獻。第二個累積變體另只把最低頻帶修正的 `0.4f`、`0.32f` 改成 double 字面值，其餘表格、常數、分支與算術不動。在新 scratch 生成兩份 C 診斷副本，交付完整 diff／hash，官方原檔不變。使用已修正、會私下複製 SPL 工作緩衝的 wrapper。

四個訊號均使用已固定的相同 Rust SPL 歷史，依序跑各變體 main、原始 C nonlinear／slopes、原始 Rust TW。把變體尾值與相同上／下游的原 C-main、Rust-main 路徑比較，列 signed 常數效果、對原 main-stage 差的比例、剩餘差與是否達 1e-14；記錄完整 core 歷史 metrics 及陣列／binary hash。未另測的表格精度／順序／分支效果保留 unresolved。這些介入不授權改 production，也不作規範判決。
