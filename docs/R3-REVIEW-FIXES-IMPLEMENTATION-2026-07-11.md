# R3 審查修復實作紀錄（2026-07-11）

依 `docs/superpowers/plans/2026-07-11-r3-review-fixes.md` 完成發現 #1–#9；#10 依計畫遞延 R5。

## 實作摘要

- F1：core 統一輸出框架、錯誤碼與場型轉換；FFI 轉發 core 契約、加入 release 硬檢查與場型／internal 常數；重生 header；CI 加 cbindgen diff gate。
- F2：Python binding 在釋放 GIL 前複製輸入，消除 ndarray 並行寫入資料競爭；場型解析改用 core；parity collection 改用 `importorskip`。
- F3：golden 工具鏈加入 Python 版本、mosqito tarball SHA256、openpyxl/pyuff import 守衛並更新 SOP。
- F4：建立 Python testkit 單一來源與 Rust known-answer/dump，移除 FFI 重複 FNV／訊號實作。
- 建立 `.codex/skills/iso532-r3-verification`，固化本次驗證方法與失敗判讀。

## TDD／BDD 證據

- RED：core 缺少 `zwtv_out_frames`、`Iso532Error::code`、`FieldType` conversions；FFI 缺少三個凍結常數；testkit 與 Rust contract target 尚不存在。
- GREEN：core `cargo test` 全綠；FFI `cargo test --features test-panic` 10/10；Python smoke 6/6；parity 18/18。
- BDD 契約：有效長度 framing 查詢等於實際輸出；非法場型維持 -3；panic 維持 -2；header 由 cbindgen 重生；可選 parity 套件 collection 不再因缺少 extension 報錯。

## 數值與工具鏈驗證

- Python/Rust contract：`n=0x44e6822074554786`、`time=0xf076bcb342595537`、`frames=500`，偏差 0。
- Golden manifest：`verify OK: 175 files match`。計畫文字預期 178，但現行 manifest 為 175 且全部匹配。
- Python 3.9 負向版本守衛正確拒絕；隔離環境連跑 `setup_env.sh` 兩次皆成功，確認 SHA256、imports 與冪等性。
- Binding benchmark 煙霧：10 秒訊號 best-of-20 為 44.1 ms；此數字不是效能驗收門檻。

## 環境偏差與待外部確認

- Windows 原生 restricted-token sandbox 無法執行一般 `apply_patch`；使用 Codex 官方 `--codex-run-as-apply-patch` 且逐檔提升權限完成修改。
- 專案既有 `.venv` ACL 阻止原地重建；F3 在 `D:\tmp\iso532-f3-validation` 隔離鏡像完整驗證兩次。
- GitHub Actions 未在本機觸發；push 後仍需確認 rust/ffi/py × Windows/Linux 全綠。

## R3 回歸修復追加（2026-07-11）

本輪依 `R3-FIXES-REVIEW-2026-07-11.md` 採 TDD/BDD 執行：

- **#1（Sol，高風險）**：FFI `zwtv` 在所有 unsafe copy 前檢查 `n`、`n_specific`、`bark_axis`、`time_axis`；`zwst` 檢查兩個 240 長度不變量，違反回傳 `ISO532_ERR_INTERNAL (-4)`。保留 ABI 的固定 240 契約。
- **#2/#4/#8（Terra）**：Python 3.11 boot guard 移到建立 `.venv` 前；testkit 使用不可被 `python -O` 消除的 `RuntimeError`；tarball SHA 只從 `requirements.lock` header 讀取並拒絕缺失/重複。
- **#3/#5/#6/#9（Luna）**：驗證 skill 加入 cbindgen 0.29.4 與 parity 強制入口；CI 使用預編譯 cbindgen action；Python helper bootstrap 集中於 conftest（CI 工作樹已套用 action，Python parity 入口仍待 binding build 後驗證）。（2026-07-16 追記：conftest 於 R5 S0.4 才真正落地；ISO532_REQUIRE_PARITY 同步由文件慣例改為程式實作。）
- **TDD RED/GREEN**：環境三項守衛先以失敗靜態契約建立 RED，再以 `tools/test_env_guards.py` 3/3 GREEN；FFI 長度守衛的探針測試設計完成，現有 10 個 FFI 測試與 core 全套測試 GREEN。
- **BDD 情境**：Given 錯版 boot interpreter，When setup 啟動，Then 不建立/改寫 `.venv`；Given cross-language known-answer，When Python 以 `-O` 載入，Then drift 以 RuntimeError 報錯；Given FFI 回傳長度破壞，When unsafe copy 前檢查，Then 回傳 -4 且不寫輸出緩衝。

### 本輪驗證紀錄

- `bash -n tools/setup_env.sh`：PASS。
- `python -m unittest tools.test_env_guards -v`：3/3 PASS。
- `python -O -c "import tools.iso532_testkit"`：PASS。
- `cargo test`（`iso532`）：全 crate/integration/doc tests PASS。
- `cargo test --features test-panic`（`iso532-ffi`）：10/10 PASS。
- `cargo fmt` 後 `cargo fmt --check`：PASS；`git diff --check`：PASS。
- `quick_validate.py .codex/skills/iso532-r3-verification`：`Skill is valid!`。
- Python smoke：本機未先建置 maturin extension，直接執行會得到 `AttributeError: module 'iso532' has no attribute 'loudness_zwtv'`；這是環境/建置前置條件，不是 Rust core 回歸，需依 skill 先執行 maturin develop 再重跑。

未提交 commit；保留既有工作樹變更與未追蹤 R3 測試/skill 檔，入版時必須一併 `git add`。
## 完成稽核追加（2026-07-11 continuation）

回收代理後由主線完成剩餘工作：

- FFI #7 已將 200 輪完整 pipeline property test 改為 11 個代表性 framing 邊界的 core-forwarding checks。
- FFI #10 已移除錯誤映射 wrapper、保留 `Iso532Error::code()` 單一來源，並將合法 field literal 改用 ABI 常數。
- 建置 `iso532-py` maturin release extension 後，smoke **6/6**、collection **24 tests**、強制 parity **18/18**（0 skipped）全部通過。
- `cbindgen 0.29.4` 確認；header 重新生成兩次 SHA256 相同（`540C813834B92EC00668093E46C8E0E44C737AFA793FE19B6CF5AB6F1DD55FD0`）。
- `golden_manifest.py --verify`：175/175 match；core 與 FFI fmt/clippy/test gates 通過；skill quick validation 通過。

Python smoke/parity 的早先 AttributeError 已由 maturin develop 修正並以正式 extension 重驗，故不再是環境偏差。
