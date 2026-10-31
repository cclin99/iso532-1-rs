# 交付檢查

- 資料夾：`docs/verification/2026-10-31-F03-authority-d623d32/`。
- 五份交付檔案為 `report.md`、`sources.md`、`acquisition-checklist.md`、`literature-followup.md`、`delivery-check.md`，均為 UTF-8 Markdown；沒有 PDF、影像、binary、非 UTF-8 或不支援副檔名。
- 去識別化命令：`python tools/redact_paths.py docs/verification/2026-10-31-F03-authority-d623d32`。
- 再檢查命令：`python tools/redact_paths.py --check docs/verification/2026-10-31-F03-authority-d623d32`。
- 執行結果：redact 退出碼 0、`0 file(s) changed`；check 退出碼 0、`clean`；均沒有 skipped 或警告。逐檔確認全部為工具支援的 `.md` 與 UTF-8，沒有因副檔名或解碼而漏掃的交付檔。
- 不附交付完整性 hash 清單。報告中的原始預覽 PDF hash 僅識別受閱來源，不能解讀為去識別化副本 hash。
