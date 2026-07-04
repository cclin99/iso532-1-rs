# Phase 8 TDD/BDD：64 軌 VST 插件（即時響度量測）

**對應：** [ROADMAP §2, §3](../../ROADMAP.md)　**狀態：** 🎨 設計（啟動前需 brainstorming → spec → plan；相依 phase-7 串流 API）
**規劃測試檔：** `iso532-vst/tests/realtime.rs`、`iso532-vst/tests/multitrack.rs`、`iso532-vst/tests/panel_values.rs`

> 本 phase 產出 GUI/插件，測試分「引擎側可自動化」與「插件側需宿主/手動」兩層。本文件聚焦可自動化的引擎契約，插件層列為手動驗收清單。

## 1. 測試策略摘要

VST 建於 phase-7 的 `LoudnessStream` 之上。可自動化的核心是**即時效能門檻**與**多軌獨立性**；面板顯示值則對引擎輸出比對：

1. **即時效能門檻**：單軌 10 s 訊號的處理 wall-clock 必須**遠小於** 10 s；64 軌 × 48 kHz = 每秒 3.07M 樣本的 budget 要留餘裕。以 criterion 量單軌 throughput，換算 64 軌是否即時。
2. **多軌獨立性**：N 個 stream 併行處理各自訊號，結果與各自單獨批次計算一致——證明無跨軌狀態污染（承 phase-7 「狀態不放全域」）。
3. **跨軌平行**：每軌一 thread（rayon）時，平行結果 == 序列結果（無資料競爭）。
4. **面板數值**：`third_octave_levels`（dB SPL/帶）、`N(t)`（sone）、`N_specific`（sone/Bark）對引擎輸出一致；phon 面板用 phase-7 的 `sone2phone`。

## 2. BDD 行為情境（Gherkin）

### Feature: 即時效能（realtime.rs / criterion）

```gherkin
Scenario: 單軌處理遠快於即時
  Given 一段 10 秒 48 kHz 訊號
  When 以串流方式跑完整 zwtv pipeline
  Then wall-clock << 10 秒（單軌即時餘裕充足）

Scenario: 64 軌換算仍即時
  Given 單軌 throughput 測量值
  When 換算 64 軌 × 3.07M 樣本/秒
  Then 總處理時間 < 即時 budget（否則觸發 Phase 5 式熱點排查）
```

### Feature: 多軌獨立與平行（multitrack.rs）

```gherkin
Scenario: 多軌併行不互相污染
  Given 64 條不同訊號、各一個 LoudnessStream
  When 交錯 push 各軌 chunk
  Then 每軌 N(t) 等於該軌單獨批次結果，rtol<=1e-12

Scenario: 跨軌 rayon 平行結果等於序列
  Given 64 軌
  When 以 rayon 每軌一 thread 平行處理
  And 另以單 thread 序列處理
  Then 兩者逐軌逐點相等（無資料競爭）
```

### Feature: 顯示面板數值（panel_values.rs）

```gherkin
Scenario: 面板三種數值對齊引擎輸出
  Given 一段訊號經引擎產生 third_octave_levels / N(t) / N_specific
  When 面板讀取顯示資料
  Then dB SPL/帶、sone、sone/Bark 皆等於引擎輸出，rtol<=1e-12
  And phon 顯示 == sone2phone(N)（phase-7）
```

### Feature: 插件層（手動/宿主驗收，非自動化）

```gherkin
Scenario: 於 DAW 載入且不 xrun
  Given nih-plug 打包的插件於宿主（Win/macOS/Linux）
  When 64 軌播放
  Then 無音訊 dropout / xrun，面板即時更新
```

## 3. TDD 測試清單（RED→GREEN，規劃）

| 測試名 | 檔案 | 輸入 | 預期 | 容差 |
|---|---|---|---|---|
| `single_track_faster_than_realtime` | realtime.rs | 10 s 訊號 | wall-clock << 10 s | 門檻 |
| `sixtyfour_track_budget`（bench 換算）| realtime.rs | 單軌 throughput | < 即時 budget | 門檻 |
| `multitrack_no_cross_contamination` | multitrack.rs | 64 訊號 | 各軌對單獨批次 | 1e-12 |
| `rayon_parallel_equals_serial` | multitrack.rs | 64 軌 | 平行==序列 | 1e-12 |
| `panel_values_match_engine` | panel_values.rs | 一段訊號 | 面板==引擎 | 1e-12 |
| （手動）DAW 載入無 xrun | — | 宿主 | 無 dropout | 觀察 |

## 4. 已知差異風險 / 排查順序

1. **相依 phase-7**：VST 建於 `LoudnessStream`；phase-7 的「串流==批次」與「狀態不放全域」不變式若未先立，多軌會出詭異污染。先確認 phase-7 綠。
2. **即時分配**：音訊執行緒不得在 `push` 熱路徑做堆積配置（no alloc in RT thread）；測試/檢查以固定容量緩衝為前提。
3. **加速比不足**：若 64 軌換算不即時，先套 Phase 5 熱點排查（AVX2 路徑是否生效、lane 抽取批次化），再考慮跨軌平行。
4. **平台 SIMD**：x86-64 走 AVX2、Apple M 走 NEON（phase-9）——效能門檻要在各目標平台各量一次，勿以單平台數字宣告全平台即時。

## 5. 驗收對照（規劃）

```bash
cargo test -p iso532-vst              # 多軌獨立、平行==序列、面板數值
cargo bench -p iso532-vst             # 單軌 throughput → 64 軌即時換算
# 手動：於 DAW 載入插件、64 軌播放、觀察無 xrun 與面板即時更新
```

執行順序：ROADMAP 建議在串流 API（phase-7）之後。
