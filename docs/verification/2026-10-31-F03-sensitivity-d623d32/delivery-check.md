# 交付檢查

此資料夾僅交付 UTF-8 `.md`、`.py`、`.txt`、`.json`，均受 `tools/redact_paths.py` 支援；未交付來源付費文件、binary或非UTF-8。Rust probe 以 `.rs.txt` 保存以納入文字檢查。

去識別化命令：`python tools/redact_paths.py docs/verification/2026-10-31-F03-sensitivity-d623d32`，隨後 `python tools/redact_paths.py --check docs/verification/2026-10-31-F03-sensitivity-d623d32`。執行結果為 `0 file(s) changed`、`clean`，退出碼均0，沒有 skipped／警告。另逐檔核對副檔名與 UTF-8，沒有漏掃格式。不以原始來源 hash 充作交付文字 hash。

`run.log` 是第二輪實際 stdout；`build-notes.log` 是工具回傳編譯結果的摘錄，不冒稱完整shell transcript。tmp 實驗目錄 `tmp/f03-sensitivity-probe/` 不屬本交付，沒有把相依cache、exe、DLL或全部nm/spec binary加入驗證資料夾。主方最後進庫前仍應只stage本交付路徑。
