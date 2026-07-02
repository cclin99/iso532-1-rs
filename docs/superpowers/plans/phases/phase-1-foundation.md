# Phase 1：基礎建設（骨架、工具鏈、常數表）

**主計畫：** `docs/superpowers/plans/2026-07-03-iso532-rust-avx.md` 的 **Task 1–3**。本文件只定義範圍與驗收；實作細節（完整程式碼、指令、commit 訊息）一律照主計畫執行。

## 範圍

| 主計畫任務 | 內容 |
|---|---|
| Task 1 | `iso532/` crate 骨架、`Iso532Error`、`FieldType` |
| Task 2 | Python venv（本地 mosqito-1.2.1.tar.gz）、`tools/setup_env.sh` 抓 ISO Annex B 測試資料、`tools/gen_golden.py` 產生逐階段 golden |
| Task 3 | `tables.rs`（手工轉錄 ISO 常數）、`tools/gen_tables.py` 生成 `tables_noct.rs`（scipy 烘焙 SOS 係數） |

## 前置條件

- 無（第一個 phase）。repo 根為 `D:\ISO532`，參考原始碼在 `mosqito-1.2.1/`（唯讀）。
- 需要網路（clone MoSQITo repo 抓 Annex B wav/csv/xlsx）。失敗就停下回報，不得造假資料。

## 驗收（全部通過才算完成）

```bash
bash tools/setup_env.sh                      # data/annexb/ 有 wav+csv+xlsx
.venv/Scripts/python tools/gen_golden.py     # data/golden/<signal>/ 齊全
.venv/Scripts/python tools/gen_tables.py     # iso532/src/tables_noct.rs 生成且可編譯
cd iso532 && cargo test                      # 含 tables spot-check 全過
```

抽查：`data/golden/sine_1k_60/N.bin` 值約 4.2（sone）；`tables_noct.rs` 的 `NOCT_DECIM_Q` 前 10 帶 >1。

## 注意事項

- `tables.rs` 的數值錯字不會在本 phase 被抓到（會在 Phase 2/3 的 golden 測試爆出）——轉錄時逐值對照 mosqito 原始檔。
- 每個 Task 完成即 commit（訊息照主計畫）。
