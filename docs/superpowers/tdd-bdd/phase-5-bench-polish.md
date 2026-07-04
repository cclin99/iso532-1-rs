# Phase 5 TDD/BDD：基準測試與收尾

**對應計畫：** [plans/phases/phase-5-bench-polish.md](../plans/phases/phase-5-bench-polish.md)（主計畫 Task 16–17）　**狀態：** ✅ 已實作
**測試檔：** `benches/loudness.rs`（criterion）、`examples/cli.rs`（端到端驗收）、`cargo doc`/`clippy`/`fmt`

## 1. 測試策略摘要

收尾 phase 的「測試」是**效能門檻**與**可用性驗收**，非正確性 golden（正確性已由 Phase 1–4 鎖定）：

1. **效能門檻（criterion）**：AVX2 vs scalar（`set_force_scalar` 切換）跑 zwtv 全 pipeline 與 filter bank 單獨。門檻：**filter bank AVX2 >= 2.5× scalar**；若 <1.5× 視為未達標須排查。
2. **CLI 端到端驗收**：`cargo run --example cli` 讀真實 48 kHz WAV、輸出響度，數字對得上 golden。
3. **品質門檻**：`cargo doc --no-deps`（crate-level rustdoc）、`cargo clippy -- -D warnings`、`cargo fmt --check` 皆乾淨。

> 效能是「門檻斷言」不是「精確值」——benchmark 數字每機不同，斷言的是**加速比達標**與 README 只填**真實測量值**。

## 2. BDD 行為情境（Gherkin）

### Feature: criterion 基準（benches/loudness.rs）

```gherkin
Scenario: filter bank AVX2 相對 scalar 達加速門檻
  Given 一段固定長度測試訊號
  When 以 set_force_scalar(true)/(false) 分別 bench third_octave_levels
  Then AVX2 中位時間 <= scalar 的 1/2.5（>= 2.5× 加速）
  And 結果寫入 docs/bench-results.txt

Scenario: zwtv 全 pipeline 有可比較的 scalar/AVX2 兩組數字
  When bench loudness_zwtv 於 scalar 與 AVX2 兩路徑
  Then 兩組時間皆記錄，供加速比評估

Scenario: 加速比不足時觸發排查（非通過）
  Given filter bank AVX2 加速 < 1.5×
  When 檢視 bench 結果
  Then 依主計畫 Task 16 排查（store 分支移出內迴圈、批次化 lane 抽取）後重測
```

### Feature: CLI 範例端到端（examples/cli.rs）

```gherkin
Scenario: 讀 48 kHz WAV 輸出穩態響度且對得上 golden
  Given Annex B Test signal 5 (pinknoise 60 dB) 的 wav
  When cargo run --example cli -- "<wav>" --calib 2.8284271247461903
  Then 印出 N ≈ 10.42 sone（CLI WAV/calib 路徑實測 10.417；ISO 參考 10.498 由 Annex B 測試以容差驗證）

Scenario: 非 48 kHz 或過短輸入給出清楚錯誤
  Given 一個 44.1 kHz 或過短的 WAV
  When 執行 CLI
  Then 回報對應 Iso532Error（UnsupportedSampleRate / SignalTooShort），非 panic
```

### Feature: 品質門檻（doc / clippy / fmt）

```gherkin
Scenario: 文件、lint、格式皆乾淨
  When 執行 cargo test && cargo doc --no-deps && cargo clippy -- -D warnings
  Then 全部成功、無警告

Scenario: 生成檔不被 rustfmt 弄髒
  Given tables_noct.rs 為 gen_tables.py 生成物
  When cargo fmt --check
  Then 生成檔以 #[rustfmt::skip] 標註（在 gen_tables.py 輸出的兩個 pub const 前），不需手改
  And src/lib.rs 檔尾有換行
```

## 3. TDD 測試清單（驗收項，非 assert 型）

| 驗收項 | 手段 | 門檻／預期 | 對應 Task |
|---|---|---|---|
| filter bank 加速比 | `cargo bench` | AVX2 >= 2.5× scalar | 16 |
| zwtv pipeline scalar/AVX2 | `cargo bench` | 兩組時間入 `docs/bench-results.txt` | 16 |
| CLI 穩態輸出 | `cargo run --example cli`（sig5）| N = 10.417000（約 10.42）| 17 |
| rustdoc | `cargo doc --no-deps` | 成功、crate-level 文件齊 | 17 |
| clippy | `cargo clippy -- -D warnings` | 無警告 | 17 |
| fmt | `cargo fmt --check` | 乾淨（生成檔 skip）| 17 |
| 全測試回歸 | `cargo test` | 全綠 | 16–17 |

## 4. 已知差異風險 / 排查順序

1. **加速比不足（<1.5×）**：主計畫 Task 16 排查方向——store 分支移出內迴圈、批次化 lane 抽取；修完重測再記錄，不填估計值。
2. **README 數字**：只用真實測量值，禁止估計。
3. **`cargo fmt` 與生成檔衝突**：`tables_noct.rs` 非 rustfmt 格式——在 `gen_tables.py` 輸出的生成常數前加 `#[rustfmt::skip]` 後重新生成；勿手動 fmt 生成檔（下次重生又髒）。另補 `src/lib.rs` 檔尾換行。
4. **bench 機器一致性**：加速比要在支援 AVX2+FMA 的機器上量；否則 `set_force_scalar(false)` 也走 scalar，兩組數字無意義。

## 5. 驗收對照

```bash
cd iso532
cargo bench 2>&1 | tee ../docs/bench-results.txt   # filter bank AVX2 >= 2.5x scalar
cargo run --example cli -- "../data/annexb/Test signal 5 (pinknoise 60 dB).wav" \
    --calib 2.8284271247461903                     # N ≈ 10.42 sone
cargo test && cargo doc --no-deps && cargo clippy -- -D warnings
```

完成後對照主計畫底部「驗收清單（對照 spec）」逐項打勾。後續擴充見 [ROADMAP](../../ROADMAP.md) 與 phase-6~10。詳見 [plans/phase-5](../plans/phases/phase-5-bench-polish.md)。
