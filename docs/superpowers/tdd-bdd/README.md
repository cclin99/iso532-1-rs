# ISO532 TDD / BDD 文件集

本目錄為 `iso532` crate 各階段的**測試設計文件**：以 BDD 行為情境（Gherkin）描述「該做到什麼」，以 TDD 測試清單描述「用哪些測試釘住它」。與 `docs/superpowers/plans/phases/`（範圍＋驗收）並行——plans 說「做什麼、怎麼 commit」，本目錄說「行為規格與測試矩陣」。

## 索引

| 文件 | 對應 | 狀態 | 主要驗證手段 |
|---|---|---|---|
| [phase-1-foundation.md](phase-1-foundation.md) | [plans/phase-1](../plans/phases/phase-1-foundation.md) | ✅ 已實作 | 工具鏈行為 + 常數表轉錄完整性 |
| [phase-2-zwst-scalar.md](phase-2-zwst-scalar.md) | [plans/phase-2](../plans/phases/phase-2-zwst-scalar.md) | ✅ 已實作 | mosqito/scipy 逐階段 golden + Annex B 穩態 |
| [phase-3-zwtv-scalar.md](phase-3-zwtv-scalar.md) | [plans/phase-3](../plans/phases/phase-3-zwtv-scalar.md) | ✅ 已實作 | mosqito 逐階段 golden + Annex B 時變（signal 10）|
| [phase-4-avx2.md](phase-4-avx2.md) | [plans/phase-4](../plans/phases/phase-4-avx2.md) | ✅ 已實作 | AVX2 vs scalar parity + golden 雙路徑重跑 |
| [phase-5-bench-polish.md](phase-5-bench-polish.md) | [plans/phase-5](../plans/phases/phase-5-bench-polish.md) | ✅ 已實作 | criterion 加速比門檻 + CLI 驗收 |
| [phase-6-cabi-python.md](phase-6-cabi-python.md) | [ROADMAP §4](../../ROADMAP.md) | 🎨 設計 | Python binding 對 mosqito golden 互比 |
| [phase-7-streaming-phon.md](phase-7-streaming-phon.md) | [ROADMAP §2,3](../../ROADMAP.md) | 🎨 設計 | 串流逐 chunk == 批次 parity + phon 轉換 |
| [phase-8-vst-plugin.md](phase-8-vst-plugin.md) | [ROADMAP §2](../../ROADMAP.md) | 🎨 設計 | 即時效能門檻 + 多軌正確性 + 面板數值 |
| [phase-9-neon-kernel.md](phase-9-neon-kernel.md) | [ROADMAP §5](../../ROADMAP.md) | 🎨 設計 | NEON vs scalar parity（aarch64）|
| [phase-10-other-standards.md](phase-10-other-standards.md) | [ROADMAP §1](../../ROADMAP.md) | 🎨 設計 | workspace 化 + 新標準沿用 golden 方法 |

## 每份文件的統一結構

1. **測試策略摘要** — 本 phase 用哪種驗證、為什麼。
2. **BDD 行為情境（Gherkin）** — `Feature` / `Scenario` / `Given-When-Then`，Then 一律帶「可觀察結果 + 容差」。
3. **TDD 測試清單（RED→GREEN）** — `測試名 | 檔案 | 輸入 | 預期 | 容差 | 對應 Task`。
4. **已知差異風險 / 排查順序** — 數值型 phase 才有；失敗時照順序處置。
5. **驗收對照** — 連回 plans/phases 或 ROADMAP 的驗收指令。

## 共用慣例

### 容差語意（`tests/common/mod.rs::assert_close`）

`|got − want| ≤ atol + rtol·|want|`，逐元素比對，先斷言長度相等。全文以 `rtol/atol` 標示。

| 比對層級 | rtol | atol | 用在哪 |
|---|---|---|---|
| 位元級結構相同 | `1e-12`~`1e-9` | `1e-15`~`1e-12` | sosfilt、spec_to_db、main_loudness、temporal_weighting |
| 濾波／冪運算鏈 | `1e-7`~`1e-6` | `1e-12`~`1e-9` | noct_spectrum、calc_slopes、nl_loudness、third_octave_levels、E2E |
| ISO 合規（Annex B）| `0.05`（5%）| `0.1` | `isoclose` / `isoclose`，對照 ISO 官方參考值 |
| AVX2 vs scalar | `1e-10`~`1e-12` | `1e-12`~`1e-14` | FMA 改變捨入，只容許極小漂移 |

### golden 資料語意

- `data/golden/<signal>/<stage>.bin`：little-endian f64、C order，由 `tools/gen_golden.py` 從 mosqito 1.2.1 逐階段產生（見主計畫 Task 2）。
- 二維陣列（如 `third_octave_level` = `[28, n_time]`、`N_specific` = `[240]`）以 row-major 攤平；讀取端用 `chunks_exact` 還原。
- golden 缺檔時 `read_bin` panic 並提示 `run tools/gen_golden.py`——測試前置條件，不是 test 本身的斷言。

### Gherkin 約定

- 一個 `Feature` 對應一個模組／公開函式；一個 `Scenario` 對應一條可獨立失敗的行為。
- `Given` 描述輸入 golden 或建構的輸入；`When` 描述呼叫的函式；`Then` 描述斷言與容差。
- 每條 `Scenario` 都能對映到「TDD 測試清單」中的一列（同名或註明）。

### 排查鐵律（沿用主計畫）

golden 失敗時：① 先查 `tables.rs` 轉錄錯字 → ② 再查比較運算子方向（`<` vs `<=`）與 mosqito 的 `round(x, 8)` 語意 → ③ 最後才考慮容差。**以 golden 為準**，放寬容差必須在測試註解寫明是哪個浮點運算順序差異造成。
