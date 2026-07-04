# Phase 7 TDD/BDD：串流 API 重構 + phon 轉換

**對應：** [ROADMAP §2, §3](../../ROADMAP.md)　**狀態：** 🎨 設計（啟動前需 brainstorming → spec → plan）
**規劃測試檔：** `tests/streaming_parity.rs`、`tests/phon.rs`

> 本 phase 為 VST（phase-8）的前置重構。核心風險是「串流 == 批次」，本文件把該不變式定為第一等測試。

## 1. 測試策略摘要

抽出 `struct LoudnessStream { push(&mut self, chunk: &[f64]) -> ... }`，把逐樣本狀態（biquad z0/z1、平滑、nl uo/u2）從函式區域變數提升為 struct 欄位。這是**重構非重寫**——現行 kernel 本就逐樣本推進 + 顯式狀態。驗證主軸：

1. **串流 parity 不變式**：把整段訊號切成任意大小的 chunk 逐一 `push`，累積結果**必須逐位元等於**一次性批次 `loudness_zwtv`。這是本 phase 的正確性支柱。
2. **chunk 邊界不變性**：不同切法（固定 480、隨機大小、單樣本）給相同結果——證明狀態沒有埋在區域變數或依賴 chunk 對齊。
3. **phon 轉換**：`sone2phone`（N≥1 → 40 + 10·log2(N)）對 mosqito utils 參考值。
4. **zwst 不可串流的明確界線**：`sosfiltfilt`（零相位、需完整訊號）**不提供** stream API——測試/文件明示即時場景只走 zwtv。

## 2. BDD 行為情境（Gherkin）

### Feature: 串流 API（LoudnessStream）

```gherkin
Scenario: 逐 chunk 串流結果等於一次性批次
  Given annexb_sig10 訊號
  When 以 480 樣本為 chunk 逐一 push 到 LoudnessStream，收集 N(t)
  And 另以 loudness_zwtv 一次算完整段
  Then 兩者 N(t) 逐元素 rtol<=1e-12, atol<=1e-14（同運算、同順序）

Scenario: 結果與 chunk 切法無關
  Given 同一訊號
  When 分別以 [固定480]、[隨機大小]、[逐樣本] 三種切法串流
  Then 三者輸出彼此 rtol<=1e-12（狀態不依賴 chunk 對齊）

Scenario: 持續濾波器狀態跨 chunk 保持
  Given 濾波器有暫態
  When 在暫態中途切 chunk 邊界
  Then 邊界前後 biquad/平滑/nl 狀態連續（無 reset、無重複暖機）

Scenario: zwst 零相位路徑不提供串流
  Given LoudnessStream 只涵蓋 zwtv
  When 查詢是否有穩態串流入口
  Then 無（文件明示 sosfiltfilt 需完整訊號、不可串流）
```

### Feature: phon 轉換（sone2phone）

```gherkin
Scenario: sone 轉 phon 對齊 mosqito 參考
  Given 一組 N（含 N>=1 與 N<1 兩段）
  When 呼叫 sone2phone(N)
  Then N>=1 段 == 40 + 10*log2(N)，rtol<=1e-12
  And N<1 段用低響度分支公式，對 mosqito 參考 rtol<=1e-9
```

## 3. TDD 測試清單（RED→GREEN，規劃）

| 測試名 | 檔案 | 輸入 | 預期 | 容差 |
|---|---|---|---|---|
| `stream_equals_batch` | streaming_parity | annexb_sig10 分 480 chunk | 對 loudness_zwtv | 1e-12/1e-14 |
| `stream_invariant_to_chunking` | streaming_parity | 三種切法 | 彼此相等 | 1e-12 |
| `stream_state_continuous_across_boundary` | streaming_parity | 暫態中切 chunk | 狀態連續 | 1e-12 |
| `zwst_has_no_stream_api`（編譯期/文件）| streaming_parity | — | 不存在穩態 stream 入口 | — |
| `sone2phone_matches_mosqito` | phon | N 陣列 | mosqito 參考 | 1e-12/1e-9 |

## 4. 已知差異風險 / 排查順序

1. **狀態提升不得改變運算順序**：`push` 內每樣本的運算序必須與批次逐樣本迴圈完全相同；parity 破時先查是否在 chunk 邊界多做/漏做一次狀態更新。
2. **抽樣/抽取對齊**：`third_octave_levels` 的 2 kHz 抽樣（`DEC_FACTOR`）在串流下要正確處理「跨 chunk 的抽樣相位」——不可每 chunk 重置抽樣計數。
3. **nl 24× 虛擬升採樣**：非線性衰減的 24× 內插狀態要跨 chunk 保留（`uo_last`/`u2_last`），這是最易在邊界出錯處。
4. **避免全域狀態**：狀態放 struct 欄位，不放 thread-local/static（ROADMAP 明示）——否則多軌（phase-8）會互相污染。

## 5. 驗收對照（規劃）

```bash
cargo test --test streaming_parity   # 串流 == 批次、切法不變、狀態連續
cargo test --test phon               # sone2phone parity
cargo test                           # 全綠（批次路徑不回歸）
```

執行順序：ROADMAP 建議在 C-ABI（phase-6）之後、VST（phase-8）之前。
