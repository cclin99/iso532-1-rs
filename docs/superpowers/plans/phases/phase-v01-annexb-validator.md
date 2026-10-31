# V-01 Annex B 驗證器 fail-closed Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 讓 `iso532/tests/annexb.rs` 的判定器在「資料無效」或「結果不符」時一定失敗，並把容差改成官方 Annex B 工作簿實際使用的 `max(0.1, 0.05 × |reference|)`。純測試碼變更，不碰 `iso532/src/`、不改 golden、不改 fixture、不改版號。

**Architecture:** 把 `isoclose` 從單一布林換成一個可單測的小判定模組 `iso532/tests/common/annexb_check.rs`：輸入兩條曲線與選項，輸出 `Verdict { Pass | Fail{..} | Invalid{..} }`。無效資料（空集合、NaN／±Inf、長度不符、負 reference）一律 `Invalid`，絕不折成 `Pass`。既有三個 Annex B 測試改呼叫新判定器並 `assert!(matches!(v, Pass))`。`annexb_csv` 改為嚴格解析：每一列要麼是有效數字，要麼明確 panic 指出行號。`read_bin` 已在 `6aea8b3` 拒絕尾端不足 8 bytes，本階段只補負向測試，不重寫。

**Tech Stack:** Rust 2021 integration tests；不新增依賴。

**上游依據:** `docs/修正報告2.md` §6、§11.5、§12.2（V-01 列）、§15.5；`docs/RELEASE-0.3.0-2026-10-31.md` Known open items。不授權處理 C-01／C-02／穩態前端／F-03。

---

## 先鎖定決策

### D1. 容差規則 = `|got − ref| ≤ max(0.1, 0.05 × |ref|)`，不是相加

官方 XLSX 的公式已由稽核直接讀出為 max 規則（§11.5）。max 規則在每一點都比相加規則嚴格或相等（`max(a,b) ≤ a+b` 對非負 a、b 恆成立），因此既有通過的點不會因「放寬」而通過。**若換成 max 後有既有測試失敗，那是真實發現，必須記錄為 finding，不得調整門檻或改 fixture 讓它通過。**

### D2. 不引入 1% 例外規則

Repo 測試目前是逐點嚴格（0 例外），比 Annex B 的 1% 例外條款更嚴。§15.5 的 `<1%`／`≤1%` 雙計數只在「套用例外規則」時才需要；本階段不套用，維持 0 例外，所以不實作雙計數。判定器輸出 `exceptions: usize` 與 `points: usize` 兩個整數供日後擴充，但 `Pass` 的條件固定為 `exceptions == 0`。

### D3. Invalid 的定義（fail-closed 清單）

以下任一成立即 `Invalid`，不比較數值：

1. `got` 或 `reference` 為空。
2. 長度不同（不取 `min(len)` 共同範圍；共同範圍診斷不是本測試的職責）。
3. 任一 `got` 或 `reference` 值非有限（NaN、±Inf）。
4. 任一 `reference` 值為負（Annex B 響度與比響度參考值皆非負；負值代表讀錯欄或錯檔）。

`Invalid` 與 `Fail` 都讓測試失敗，但訊息不同，便於區分「結果錯」與「資料錯」。

### D4. CSV 嚴格解析

`annexb_csv` 現在用 `filter_map(parse().ok())`，壞列會被無聲丟掉，只靠事後 `len() == 240` 擋住部分情況。改為：跳過第一列標頭後，每列 `trim()`，空列視為錯誤（不是略過），解析失敗 `panic!("{path}:{line_no}: cannot parse {text:?}")`。BOM（`\u{feff}`）只允許出現在第一列標頭。

### D5. 負向測試用外部副本，不碰 `data/`

損壞檔測試一律寫到 `std::env::temp_dir()` 下的唯一子目錄再讀取；`read_bin`／`annexb_csv` 要能接受任意路徑，因此抽出 `read_bin_path(&Path)`／`annexb_csv_path(&Path)` 供負向測試呼叫，原本以名稱為參數的包裝保持不變。

### D6. README 文字同步

`README.md` 與 `README.zh-TW.md` 的「ISO Annex B uses the much broader acceptance expression `abs(error) <= 0.1 + 0.05 * abs(reference)`」改為 max 規則並註明來源是工作簿公式（不是正式條文逐條核對）。`docs/ISO-ANNEXB-NUMERICAL-ERROR-2026-07-04.md` 若有同一句，加一行更正註記，不改寫歷史數據。

---

## Tasks

### Task V1.1 判定器模組（RED → GREEN）

- [ ] 新增 `iso532/tests/common/annexb_check.rs`，`pub enum Verdict { Pass { points: usize }, Fail { exceptions: usize, points: usize, worst_idx: usize, worst_diff: f64 }, Invalid(InvalidReason) }`，`pub enum InvalidReason { Empty, LengthMismatch { got: usize, want: usize }, NonFinite { which: &'static str, idx: usize }, NegativeReference { idx: usize } }`。
- [ ] `pub fn annexb_verdict(got: &[f64], reference: &[f64]) -> Verdict`，容差依 D1。
- [ ] 在同檔 `#[cfg(test)]` 或 `iso532/tests/annexb_validator.rs` 寫單測，先確認 RED 再實作：
  - `max` 與相加規則分歧案例：`ref=10.0, got=10.55` → 相加規則通過（10.55−10 = 0.55 ≤ 0.6）、max 規則失敗（0.55 > 0.5）。這是 §6.1 的指定控制。
  - `ref=0.0, got=0.1` → Pass；`got=0.1000000001` → Fail（絕對下限 0.1 的邊界）。
  - `ref=2.0, got=2.1` → Pass；`got=2.1000001` → Fail（5% 線 0.1，與絕對下限交界）。
  - `ref=100.0, got=105.0` → Pass；`got=105.0000001` → Fail。
  - 空集合、長度不符、`got` 含 NaN、`reference` 含 NaN、`reference` 含 +Inf（§6.1 指出 Inf reference 原本會通過）、`got` 含 −Inf、`reference` 含 −0.5 → 各自對應的 `Invalid`。
  - 1 點與 2 點的極短曲線：正常比較，不特殊處理。
- [ ] `common/mod.rs` 以 `pub mod annexb_check;` 導出。

### Task V1.2 既有 Annex B 測試切換

- [ ] `annexb.rs` 刪除本地 `isoclose`，三個測試改用 `annexb_verdict`，失敗訊息印出 `Verdict` 的 Debug。
- [ ] 跑 `cargo test --test annexb`。**預期全過**（§11.5 已對 25 案例確認 max 規則 0 例外）。若任一失敗：停止，記錄 got／ref／idx／diff，回報為 finding，不改門檻。
- [ ] `sig10 N(t) vs ISO xlsx reference` 這一條另外確認 `iso_ref` 無負值、無 NaN（由判定器自動保證；若出現 `Invalid`，代表 `tv_nref.bin` 內容需查，同樣是 finding）。

### Task V1.3 CSV 嚴格解析與負向測試

- [ ] 依 D4、D5 改 `annexb_csv`，新增 `annexb_csv_path`。
- [ ] 負向測試（寫入 temp 目錄的外部副本）：
  - 中間一列為 `abc` → panic 訊息含行號。
  - 中間一列為空白 → panic。
  - 少一列（239 列）→ 由呼叫端 `assert_eq!(len, 240)` 攔住；測試明確檢查這條訊息。
  - 正常檔（複製 `data/annexb/test_signal_3.csv`）→ 240 點且與原函式結果逐位元相同。
- [ ] `read_bin_path` 負向測試：1、7、9、15、17 bytes 的檔案 panic 且訊息含 `trailing bytes`；8、16 bytes 正常。這些與 `docs/修正後獨立驗證報告.md` §2 的「二進位尾端截斷」列一致。

### Task V1.4 文件同步

- [ ] 依 D6 修 README 兩語言的容差描述。
- [ ] `docs/ISO-ANNEXB-NUMERICAL-ERROR-2026-07-04.md`：若引用相加公式，加註「2026-10-31 更正：官方工作簿為 max 規則，見 V-01」，不改原數據。
- [ ] `CHANGELOG.md` Unreleased → Changed：「Annex B 測試容差改為 `max(0.1, 5 %)`；判定器對空集合、非有限值、長度不符、負參考值 fail-closed；CSV 讀取不再無聲丟列」。

### Task V1.5 Exit gate

- [ ] `cargo fmt --all --check`；`cargo +stable clippy --all-targets -- -D warnings`（在 `iso532/` 下）與 `cargo +stable clippy --workspace --all-targets --all-features -- -D warnings`。
- [ ] `REQUIRE_AVX2=1 cargo test --workspace --all-features`（本機若遇 `invalid metadata` 編譯錯誤，加 `-j 3` 重跑；那是 commit charge 問題，不是測試失敗）。
- [ ] `git diff --stat iso532/src/` 必須為空。
- [ ] `python tools/golden_manifest.py --verify` 仍為 175 files match（證明沒碰 fixture）。
- [ ] 新測試在 CI 的 `cargo test` 清單中被涵蓋（`annexb` 本來就跑；若新增獨立檔 `annexb_validator.rs`，確認 CI workflow 的 test 列表或 `--workspace` 會跑到）。

---

## 驗收總表（逐條複製自 `docs/修正報告2.md` §12.2 V-01 列，未改寫）

| 回歸測試 | 驗收條件 |
|---|---|
| 保留第 11.5 節的 19 個控制；直接測 repo 判斷式；增加 reference/time/bounds 的 NaN、±Inf、空集合、shape 錯誤、反轉界限、錯時間單位、重複／倒退時間、截斷檔與壞列 | 無效資料統一 INVALID／FAIL，不能列 PASS；對非負 reference 使用 max 容差；每條曲線分開計數；共同範圍通過但長度不同必須 PARTIAL；機器結果與總結狀態一致。1% 未裁定時同時列 `<1%` 與 `≤1%`，有分歧不得自動核准 |

本階段對應關係：「19 個控制」中屬於 repo 判定式可直接表達的子集由 V1.1 覆蓋（容差分歧、絕對下限邊界、空集合、NaN／Inf、長度不符、負參考）；time／bounds 的時間軸檢查已由 `annexb_timevarying_signal10` 的 `assert_close(time_axis, 1e-12)` 覆蓋，不重複；「共同範圍通過但長度不同必須 PARTIAL」在 repo 測試語意下等於 `Invalid(LengthMismatch)` 讓測試失敗；1% 雙計數依 D2 不實作。

## 不在範圍（明確排除）

- 不改 `iso532/src/` 任何檔案；不改 C-01 輸出長度、C-02 非有限輸入契約。
- 不重產 golden、不改 `data/`、不改 `tools/gen_golden.py`。
- 不改 USL 表、不碰 N5／1% 的資料或 workbook。
- 不改版號；本階段落地後進 Unreleased，由使用者決定隨 0.3.x 或下一版發布。
