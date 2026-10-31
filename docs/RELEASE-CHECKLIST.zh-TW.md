# Release 檢查清單

> 對照／Pair: [English](RELEASE-CHECKLIST.md) · 來源：en · 同步 2026-11-01

發布 release 或公開 README 之前，請立即執行這份檢查清單。

- [ ] 移除或改寫 `README.md` 與 `README.zh-TW.md` 兩檔開頭附近的審查草稿引言區塊；任何公開的 README 都不得寫「not yet announced as a public release」或「尚未對外宣布發布」。
- [ ] 重跑 `tools/compare_mosqito.py`，並一併更新日期、環境、計時與直接 parity 數值。
- [ ] 從本機重新產生的 golden 環境執行「Reproduce the evidence」／「重現驗證」下的指令。
- [ ] 確認 `docs/GOLDEN-REGEN-SOP.md` 仍涵蓋全新 clone 所需的每一項先決條件。
- [ ] 逐一核對每條能力與邊界敘述是否與已打 tag 的原始碼及公開產出物相符。
- [ ] 對照 release tag 與目前的 repository 設定，檢視 `THIRD_PARTY_NOTICES.md`、`CITATION.cff`、`SECURITY.md` 與社群範本。
- [ ] 在正常的防毒保護啟用下，建置並掃描 release 的 DLL／靜態函式庫、wheel 與任何外掛套件；任何偵測都要記錄產品、版本、產出物 hash 與確切的建置指令。不得將停用防毒下的建置當作 release 證據。
- [ ] 為每個 release 產出物產生並發布 SHA-256 校驗值；smoke test 之前，先以這些校驗值驗證下載的產出物。
- [ ] 確認僅限本機的檔案、壓縮檔、產生的 `data/`、憑證與機器特定路徑未被 stage。
- [ ] 審核與驗證交付：執行 `python tools/redact_paths.py --check docs`（必須輸出 `clean`）；報告所引用的每個證據壓縮檔都列於 `docs/verification/README.md`，含大小、SHA-256 與可用的下載連結；壓縮檔本身不進庫。
