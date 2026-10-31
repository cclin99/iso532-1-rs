# V-01 Annex B 驗證器 fail-closed：完成紀錄

> 對照／Pair: [English](V01-ANNEXB-VALIDATOR-2026-10-31.md) · 來源：zh · 同步 2026-11-01

日期：2026-10-31（Asia/Taipei）。基底 `d623d32`（v0.3.0 + V-01 計畫）。執行者：Claude（使用者授權「V-01 如果可以推進就繼續推進」；依 `docs/superpowers/plans/phases/phase-v01-annexb-validator.md` 執行，未交 Codex）。純測試碼與文件變更，`iso532/src/` 零差異。

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

## 浮點邊界案例的原因追查（2026-11-01 補）

使用者要求追查「計畫寫 `ref=2.0, got=2.1 → Pass`，實作時卻必須改值」的原因。結論：**不是判定器算錯，是測試字面值在 IEEE 754 下不可精確表示；真實資料離容差邊界極遠，不受影響。**

1. **十進位字面值的表示誤差。** `2.1` 在 binary64 存成 `2.100000000000000088817841970012523…`，`0.1` 存成 `0.1000000000000000055511151231257827…`，`2.0` 精確。
2. **減法是精確的。** `2.1 − 2.0` 兩操作數在 2 倍以內（Sterbenz 引理），結果不再捨入，得 `0.100000000000000088817841970012523…`。
3. **比較。** 容差 `max(0.1, 0.05 × 2.0)`：`0.05 × 2.0` 精確等於存起來的 `0.1`，所以容差是 `0.1000000000000000055…`。差值比容差大 `8.33e-17`，約 6 個 `ulp(0.1)`（`1.39e-17`）。判定器依規格判 Fail，是正確行為。
4. **計畫為何寫錯。** 計畫是用十進位心算寫的；凡是小數部分為 .1、.05 這類的字面值都會捨入。已改用二進位可精確表示的偏移（`2.0625`、`2.125`），其他案例逐一用 Python 的 `decimal` 展開確認：`10.55 − 10.0 = 0.5500000000000007` 對容差 `0.5`（如預期 Fail，餘裕 0.05）；`105.0 − 100.0 = 5.0` 精確、`0.05 × 100.0` 也精確等於 `5.0`，所以恰在邊界上通過；`0.1 − 0.0` 與容差是同一個字面值，精確相等。
5. **對真實判定的影響：無。** 三個 Annex B 測試的最小餘裕（容差減差值）：訊號 3 的 `N′` 0.0851 sone/Bark（第 66 格）、訊號 5 的 `N′` 0.0901、訊號 10 的 `N(t)` 0.0998 sone（第 77 幀）、訊號 3 的 `N` 0.168、訊號 5 的 `N` 0.445。最小餘裕是 `ulp(0.1)` 的 6×10¹⁵ 倍，任何表示誤差都翻不動。官方工作簿在 Excel 的 double 算術下有完全相同的性質，判定器與它一致。
6. **決定：不加 epsilon。** D1 維持嚴格 `≤`；加 epsilon 會偏離工作簿公式且沒有實益。測試撰寫規則新增一條：邊界案例用二進位可精確表示的值（`k/2ⁿ`），或在邊界兩側各留 ≥ 1e-12 的餘裕。
