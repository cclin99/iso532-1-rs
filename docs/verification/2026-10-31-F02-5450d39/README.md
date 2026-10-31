# F-02 獨立驗證交付

本資料夾僅交付 2026-10-31 對 commit `5450d3908cd92f8c17e80133201f0b313c9eb646` 的 F-02 驗證，不追加或覆寫 F-01／前輪報告。

- [獨立驗證報告](F02獨立驗證報告.md)
- [數值摘要與版本](F02獨立驗證-5450d39/f02-summary.json)
- [因果性、C 階段與串流測試](F02獨立驗證-5450d39/f02-independent.json)
- [FFI／Python 比較](F02獨立驗證-5450d39/f02-bindings.json)
- [Annex B 詳細判定](F02獨立驗證-5450d39/AnnexB深入分析.json)
- 完整原始證據 ZIP：`F02獨立驗證證據-5450d39.zip`（335 MB，SHA-256 `9f777b6c9f717a57f6045a1a0c5f37d9ec65c7073d099fd8f9af9ae2c392add0`），由雲端硬碟提供，下載連結與校驗方式見 [docs/verification/README.md](../README.md)
- [移交校驗清單](交付完整性.json)

報告原文逐位元保留。原文「本對話 work／outputs」指驗證當時的位置；此次移交的路徑以本頁及交付完整性清單為準。完整 ZIP 不進 Git，由雲端硬碟分發；複查者先依上層索引核對 SHA-256 再解壓。本資料夾內的報告、JSON、log 與 runner 副本在進庫前經 `tools/redact_paths.py` 去識別化（工作站路徑改為 `<AUDIT_HOME>`、`<REPO>` 等占位符），`交付完整性.json` 同時保留原始檔與去識別化後的 SHA-256。

複查時先核對交付完整性清單與 ZIP 內 evidence-manifest.json，再解壓 ZIP，依根目錄 reproduce-f02.ps1 建立全新的 run 目錄。此資料夾內的 runner 是供閱讀的副本，必須搭配完整證據包中的 source／official／prior-baseline 資料執行。

既有 ZIP 為當時驗證的不可變歷史封存，內含當時混合增補版《修正報告2.md》；本次不拆改 ZIP、不改寫歷史 hashes。複查本輪結論請以本資料夾的獨立《F02獨立驗證報告.md》為主；不將混合增補版移入專案 docs。

## 後續報告規則

每輪驗證建立獨立資料夾與報告，名稱包含日期、議題、被測 commit。每份報告自足列出範圍、版本、方法、結果、限制與證據位置。不得將新輪結果追加到前輪報告；關聯內容以連結引用。未重新執行的檢查須明示為歷史證據。不同輪次的完整性清單與證據包分開保存。