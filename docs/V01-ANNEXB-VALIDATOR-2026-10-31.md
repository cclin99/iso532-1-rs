# V-01 Annex B 驗證器 fail-closed：完成紀錄

日期：2026-10-31（Asia/Taipei）。基底 `d623d32`（v0.3.0 + V-01 計畫）。執行者：Claude（使用者授權「V-01 如果可以推進就繼續推進」；依 `docs/superpowers/plans/phases/phase-v01-annexb-validator.md` 執行，未交 Codex）。純測試碼與文件變更，`iso532/src/` 零差異。English version follows.

## 做了什麼

| 檔案 | 變更 |
|---|---|
| `iso532/tests/common/annexb_check.rs`（新） | `Verdict { Pass, Fail, Invalid }`、`InvalidReason`、`annexb_tolerance`、`annexb_verdict`；嚴格 CSV 讀取 `annexb_csv_path`／`annexb_csv`；`annexb_dir` |
| `iso532/tests/common/mod.rs` | 導出 `annexb_check`；`read_bin` 拆出 `read_bin_path(&Path)`，行為不變 |
| `iso532/tests/annexb.rs` | 刪除加法容差 `isoclose`；三個 Annex B 測試改用 `annexb_verdict`，失敗訊息印 `Verdict` 的 Debug |
| `iso532/tests/annexb_validator.rs`（新） | 24 個測試：容差規則 7、fail-closed 5、CSV 7、二進位 5 |
| `README.md`、`README.zh-TW.md` | 容差描述改為 max 規則並註明來源是工作簿公式 |
| `docs/ISO-ANNEXB-NUMERICAL-ERROR-2026-07-04.md` | 加一行更正註記，原數據不動 |
| `CHANGELOG.md` | Unreleased → Changed |

## 驗收結果

| Gate | 結果 |
|---|---|
| `cargo fmt --all --check` | 通過 |
| `cargo clippy --all-targets -- -D warnings`（`iso532/`，CI 命令） | 通過 |
| `cargo clippy --workspace --all-targets --all-features -- -D warnings` | 通過（第一次因分頁檔用滿出現 `invalid metadata` 編譯錯誤，`-j 2` 重跑通過；不是 lint 失敗） |
| `REQUIRE_AVX2=1 cargo test --workspace --all-features`（`-j 3`） | 全部通過，0 failed，3 ignored（既有的 hash dump、Python contract dump、silence throughput）；其中 `annexb` 3 個、`annexb_validator` 24 個 |
| `git diff --stat iso532/src/` | 空 |
| `tools/golden_manifest.py --verify` | 175 files match |

**D1 的風險項沒有發生**：三個既有 Annex B 測試在 max 規則下全部通過，沒有新 finding。這與稽核 §11.5 對 25 案的結論一致（max 規則 0 例外）。

## 與計畫的偏差（審閱時請看這裡）

1. **邊界案例的字面值。** 計畫寫 `ref=2.0, got=2.1 → Pass`。IEEE 754 下 `2.1 − 2.0 = 0.10000000000000009 > 0.1`，max 規則會判 Fail，計畫的預期是錯的。改用可精確表示的偏移：`2.0625 → Pass`、`2.125 → Fail`；另加 `ref=8.0`：`8.375 → Pass`、`8.5 → Fail`（8.5 在加法規則下恰好通過，是第二個分辨兩公式的控制）。`ref=10.0, got=10.55`（§6.1 指定控制）、`ref=0.0` 與 `ref=100.0` 的案例維持計畫原值，均已確認浮點行為符合預期。
2. **CSV 讀取函式的位置。** `annexb_csv`／`annexb_csv_path` 放在 `tests/common/annexb_check.rs` 而不是 `annexb.rs`，因為 `annexb_validator.rs` 也要用。名稱式包裝 `annexb_csv(file)` 保持不變。
3. **BOM 檢查。** 依 D4「BOM 只允許在第一列」，資料列若含 `U+FEFF` 直接 panic；計畫沒有列這條負向測試，已補。
4. **239 列的案例。** 讀取器照實回傳 239 點；測試以 `catch_unwind` 重演呼叫端的 `assert_eq!(len, 240)` 並檢查訊息含「240」。
5. **模組層級 `#![allow(dead_code)]`。** `tests/common` 被每個測試二進位各自編譯，不用到判定器的二進位會把它的公開項目視為 dead code，`-D warnings` 下變成錯誤，故在模組頂端一次允許。
6. **單測放在獨立檔** `annexb_validator.rs`（計畫允許兩種放法）。CI 用 `cargo test`（含所有 integration tests），會跑到。
7. 額外提供 `Verdict::is_pass()` 與 `annexb_tolerance()` 兩個小輔助，供日後 C-01 契約測試重用。

## 範圍外（未動）

C-01 輸出長度、C-02 非有限輸入、1 % 例外規則、USL 表、golden、`data/`、版號。本階段落地在 Unreleased，隨下一個 0.3.x 或 0.4.0 發布由使用者決定。

## 建議的後續

- 可交 Astra 做一輪輕量複審（純測試碼；重點是 D1 容差公式與 fail-closed 清單是否與 §12.2 V-01 列一致）。
- 這組判定器就是 C-01 上策「補零 C library 參考值」要用的容差判定。

---

# V-01 Annex B validator fail-closed: completion record

Date: 2026-10-31 (Asia/Taipei). Base `d623d32` (v0.3.0 + the V-01 plan). Executed by Claude, authorised by the user ("push V-01 forward if it can be pushed"); followed `docs/superpowers/plans/phases/phase-v01-annexb-validator.md`, not handed to Codex. Test and documentation changes only; `iso532/src/` has zero diff.

## What changed

| File | Change |
|---|---|
| `iso532/tests/common/annexb_check.rs` (new) | `Verdict { Pass, Fail, Invalid }`, `InvalidReason`, `annexb_tolerance`, `annexb_verdict`; strict CSV reader `annexb_csv_path` / `annexb_csv`; `annexb_dir` |
| `iso532/tests/common/mod.rs` | exports `annexb_check`; `read_bin` split into `read_bin_path(&Path)`, same behaviour |
| `iso532/tests/annexb.rs` | additive `isoclose` removed; the three Annex B tests use `annexb_verdict` and print the `Verdict` on failure |
| `iso532/tests/annexb_validator.rs` (new) | 24 tests: tolerance rule 7, fail-closed 5, CSV 7, binary 5 |
| `README.md`, `README.zh-TW.md` | tolerance wording switched to the max rule, source stated as the workbook formula |
| `docs/ISO-ANNEXB-NUMERICAL-ERROR-2026-07-04.md` | one correction note added, historical numbers untouched |
| `CHANGELOG.md` | Unreleased → Changed |

## Gate results

| Gate | Result |
|---|---|
| `cargo fmt --all --check` | clean |
| `cargo clippy --all-targets -- -D warnings` (from `iso532/`, the CI command) | clean |
| `cargo clippy --workspace --all-targets --all-features -- -D warnings` | clean (the first run hit `invalid metadata` compile errors while the page file was full; the `-j 2` re-run passed; not a lint failure) |
| `REQUIRE_AVX2=1 cargo test --workspace --all-features` (`-j 3`) | all passed, 0 failed, 3 ignored (the existing hash dump, Python contract dump, silence throughput); includes `annexb` 3 and `annexb_validator` 24 |
| `git diff --stat iso532/src/` | empty |
| `tools/golden_manifest.py --verify` | 175 files match |

**The D1 risk did not materialise**: all three existing Annex B tests pass under the max rule, no new finding. This agrees with audit §11.5 (max rule, 0 exceptions over 25 cases).

## Deviations from the plan (reviewers: start here)

1. **Boundary literals.** The plan expected `ref=2.0, got=2.1 → Pass`. Under IEEE 754, `2.1 − 2.0 = 0.10000000000000009 > 0.1`, so the max rule fails it; the plan's expectation was wrong. Replaced by exactly representable offsets: `2.0625 → Pass`, `2.125 → Fail`; added `ref=8.0`: `8.375 → Pass`, `8.5 → Fail` (8.5 passes the additive rule exactly, a second control separating the formulas). The `ref=10.0, got=10.55` control from §6.1 and the `ref=0.0` / `ref=100.0` cases keep the plan's values; their floating-point behaviour was checked.
2. **Location of the CSV readers.** `annexb_csv` / `annexb_csv_path` live in `tests/common/annexb_check.rs`, not `annexb.rs`, because `annexb_validator.rs` needs them too. The name-based wrapper `annexb_csv(file)` is unchanged.
3. **BOM check.** Per D4 ("BOM only on the header line"), a data row containing `U+FEFF` panics; the plan listed no such negative test, one was added.
4. **239-row case.** The reader returns the 239 points it parsed; the test re-enacts the caller's `assert_eq!(len, 240)` under `catch_unwind` and checks that the message names 240.
5. **Module-level `#![allow(dead_code)]`.** `tests/common` is compiled into every test binary; binaries that do not use the verdict would see its public items as dead code, an error under `-D warnings`.
6. **Unit tests in a separate file** `annexb_validator.rs` (the plan allowed either placement). CI runs `cargo test`, which includes all integration tests.
7. Two small helpers, `Verdict::is_pass()` and `annexb_tolerance()`, are exposed for reuse by the future C-01 contract tests.

## Out of scope (untouched)

C-01 output length, C-02 non-finite input, the 1 % exception rule, the USL table, goldens, `data/`, the version number. The change sits in Unreleased; the user decides whether it ships with the next 0.3.x or with 0.4.0.

## Suggested follow-up

- Optional light review by Astra (test-only; the points to check are the D1 formula and the fail-closed list against audit §12.2 row V-01).
- This verdict is the tolerance check the C-01 "best option" (zero-padded C library reference) would use.
