# ISO532 架構、效能、風險與演進整合審查報告

**日期：** 2026-07-10  
**審查基線：** `HEAD 9d8c496` 加目前工作樹中的 R4 頻帶平行化實作  
**目標平台：** AMD Ryzen 5 3600（6C/12T，AVX2+FMA，無 AVX-512）、Windows 10 x86-64  
**工具鏈：** rustc 1.93.0、LLVM 21.1.8、Criterion 0.5.1、Rayon 1.12.0  
**文件性質：** 架構與程式碼唯讀審查、實際測試與 benchmark、演進計畫風險分析；本文不代表尚未完成階段已經實作。

---

## 1. 執行摘要

### 1.1 最終判斷

目前專案可明確分成兩種成熟度完全不同的產品形態：

1. **離線批次 ISO 532-1 引擎：成熟度高。**
   - AVX2/FMA 是真實向量運算，不是僅有 intrinsics 外觀。
   - R1 與 R4 的效能提升可由 Criterion 重跑。
   - 目前 10 秒輸入在 12 logical threads 的 AVX2 中位數為 **51.34 ms**，約 **194.8 倍即時**。
   - 目前輸出 hash 與 R1 既有 12 個快照逐字一致，未發現以降低數值品質換速度的證據。
   - 適合離線量測、批次分析、研究工具與後續 Python/C-ABI 包裝。

2. **即時串流/VST 引擎：設計已具體，但尚未實作。**
   - 現行 `ZwtvProcessor::process` 仍是整段訊號批次處理，不是 chunk-by-chunk stateful engine。
   - 暖機後每次呼叫仍至少約 **14 次明確 heap allocation**，並會使用 Rayon 全域 thread pool。
   - denormal、NaN/Inf 狀態毒化、1 幀前視、初始化語意、mid-stream error、P99 deadline 均尚未由串流程式碼解決。
   - 因此目前不能宣稱 zero-alloc、audio-thread safe、VST-ready 或 64 軌已驗收。

3. **最大效能潛力仍存在，但缺少新的 stage profiler 與硬體 counter，不能給出可信的單一「極限值」。**
   - 現有牆鐘時間足以證明收益，不能證明 L1/L2 命中率、IPC、branch-miss 或 stall 已達硬體極限。
   - 目前沒有 flamegraph、AMD uProf/perf/WPR counter 報告，也沒有 current-R4 的逐階段 benchmark。
   - 本文因此只提供分層上限、條件式推估與驗證門檻，不把推估當成完成數據。

### 1.2 成熟度儀表板

| 能力 | 現況 | 成熟度 | 是否可對外承諾 |
|---|---|---:|---|
| ISO 532-1 stationary batch | 已實作、golden/Annex B 測試 | 高 | 可，需明載 Mosqito parity 與 ISO tolerance 的不同 |
| ISO 532-1 time-varying batch | 已實作、AVX2/Rayon、golden | 高 | 可 |
| AVX2+FMA dispatch | runtime detection + scalar fallback | 高 | 可，僅 x86-64 AVX2/FMA |
| R1 calc_slopes dedup | 已合入 `9d8c496` | 高 | 可 |
| R4 band parallelism | 目前位於未提交工作樹 | 中高 | 先提交、固化 benchmark/hash gate 後再承諾 |
| 自動化 bitwise regression gate | 部分存在，hash helper 仍需人工比對 | 中 | 不可稱完整 CI gate |
| Zero-allocation batch | 不成立 | 低 | 不可 |
| Stateful streaming engine | 有完整 R5 規格，無 `stream.rs` 實作 | 設計階段 | 不可 |
| Real-time audio-thread safety | 尚未滿足 | 低 | 不可 |
| C-ABI / Python binding | R3 計畫完成，尚未實作 | 設計階段 | 不可 |
| VST/CLAP plugin | R6 計畫完成，尚未原型驗證 | 規格階段 | 不可 |
| NEON / Apple Silicon SIMD | R7 計畫完成，尚未實作 | 規格階段 | 不可 |
| 多標準 workspace | R8 計畫完成，尚未啟動 | 規格階段 | 不可 |

---

## 2. 審查範圍與證據分級

### 2.1 審查範圍

- 公開 API 與編排：`iso532/src/lib.rs`、`iso532/src/zwtv/mod.rs`
- DSP 與演算法：`dsp/`、`core/`、`zwst/`、`zwtv/`
- SIMD/dispatch：`simd/mod.rs`、AVX2 filter bank、AVX2 nonlinear decay
- 配置與資料布局：所有 `Vec`、`collect`、`resize`、clone、輸出轉置
- 測試：golden、Annex B、SIMD parity、determinism、dispatch、API error
- 效能：Criterion bench、release assembly、R1/R4 審查紀錄
- 演進：ROADMAP、R1-R8 master plan、R1/R4 phase plan、streaming/VST TDD 文件

### 2.2 證據標籤

| 標籤 | 定義 | 可否作為驗收結論 |
|---|---|---|
| **MEASURED** | 本工作樹實際執行測試或 benchmark | 可以，但需附環境與命令 |
| **ASSEMBLY** | release 組譯碼直接確認 | 可以證明生成指令，不能取代硬體 counter |
| **STATIC** | 由原始碼與型別/控制流直接推出 | 可以證明結構，不可推導實際 CPU miss rate |
| **PLANNED** | Roadmap/phase plan 已規格化但未實作 | 不可視為已完成 |
| **ESTIMATED** | 依既有數據或 Amdahl 模型推估 | 只能用於排程與設門檻 |
| **UNKNOWN** | 缺少 profiler、counter、跨平台或 host 實測 | 必須先補證據 |

本文所有「上限」與「潛力」均使用上述標籤，避免混用。

---

## 3. 現行架構與資料流

### 3.1 分層

```text
Public API
├─ loudness_zwst(signal, fs, field)
└─ loudness_zwtv(signal, fs, field)
   └─ ZwtvProcessor::process
      ├─ third_octave_levels       48 kHz -> 28 bands @ 2 kHz
      ├─ transpose                 band-major -> frame-major
      ├─ main_loudness_frames_into 28 -> 21 critical bands
      ├─ nonlinear_decay           21 bands x 24 virtual substeps
      ├─ calc_slopes               N + 240-point specific loudness
      ├─ temporal_weighting        dual time constants
      └─ output materialization    500 Hz N/N_specific/time axis
```

模組邊界整體合理：

- `dsp/` 放通用 SOS/filter primitives。
- `core/` 放 ISO 532-1 主響度與 Bark slope 邏輯。
- `zwst/`、`zwtv/` 負責模式編排。
- tables 與 runtime dispatch 分離。
- 公開輸出維持扁平 `Vec<f64>`，利於 C-ABI 與 NumPy。

### 3.2 平行軸與向量軸

現行實作正確地把兩種平行方式分開：

| 層次 | 平行維度 | 適用階段 | 限制 |
|---|---|---|---|
| SIMD | 4 個 frequency bands / f64x4 | filter bank、nonlinear decay | 時間遞迴不能切斷 |
| Rayon | bands 或獨立 frames | R4 filter/NL、main loudness、calc slopes | 不適合 audio callback |
| 未來多軌 | tracks / plugin instances | R6 64 軌 | 由 host 排程，不應在每軌內再啟 Rayon |

這個設計沒有把 IIR 的時間依賴錯誤地跨執行緒切割。R4 是將互相獨立的 band group 分工，每個 worker 仍完整順序推進自己的狀態。

### 3.3 資料布局

目前為了讓每個階段連續存取，管線中有數次轉置：

1. Filter bank 輸出：band-major，方便每 band 沿時間順序寫入。
2. Main loudness 輸入：frame-major，讓每幀 28 值連續。
3. NL 輸入/輸出：band-major，方便時間遞迴。
4. calc_slopes 暫存：time-major 240-point chunk，方便幀平行與避免 false sharing。
5. 公開 specific loudness：bark-major，符合 API/golden 既有契約。

這是合理的計算局部性取捨，但轉置與 materialization 會增加 O(n) 記憶體流量。要消除它們必須同時更改上下游 layout，不能單點修改。

---

## 4. 硬核程式碼審查整合結論

### 4.1 SIMD 利用率

**MEASURED/ASSEMBLY：SIMD 真實存在。** release assembly 出現 `ymm`、FMA、compare、blend、broadcast 等指令。

| Kernel | lane 使用 | 覆蓋 | 記憶體模式 | 判斷 |
|---|---:|---:|---|---|
| Third-octave filter | 7 x f64x4 | 28/28 bands | 1 sample broadcast 到 4 bands | lane 無浪費，compute SIMD 有效 |
| Nonlinear decay | 5 x f64x4 + scalar tail | 20/21 bands SIMD | 4 個 band row scalar gather / scalar scatter | 約 95.2% band 覆蓋，load/store 不是連續向量 I/O |
| AVX-512 | 無 | 0 | 無 dispatch/測試 | 目前不可宣稱 |
| NEON | 無 | 0 | R7 規格存在 | 目前不可宣稱 |

Filter kernel 的向量化維度是 bands，而不是連續 samples。NL 也由四個相隔 `n_time` 的位置組成向量；因此它是有效 SIMD，但不是最理想的 contiguous load/store。

### 4.2 分支、bounds check 與 inline

- NL 的演算法條件已用 compare+blend 改為 lane-wise branchless，避免 SIMD lane divergence。
- Filter 每 24 samples 有一次 decimation/store 判斷，規律且通常容易預測。
- release assembly 顯示 NL 每個時間步仍保留多個 slice bounds-check branch。
- 原始碼沒有 `get_unchecked` 或 `#[inline(always)]`。
- `#[inline]` 的 `nl_loudness_load4` 已被 LLVM 實際 inline，證明不需要因風格偏好盲目改成 `inline(always)`。

結論：bounds check 未完全清除，但是否值得引入 unsafe 必須先用 counter 或 microbenchmark 證明。沒有 branch-miss 數據時，不能把每個條件分支都當成 misprediction。

### 4.3 對齊

- `Vec<f64>` 只保證 `f64` 對齊，不保證 32-byte AVX 對齊。
- 實作使用 unaligned load/store 或 scalar load，沒有錯誤使用 aligned intrinsic，因此不存在 misaligned fault 風險。
- unaligned access 是否跨 cache line、是否造成顯著 throughput 損失尚未量測。

### 4.4 Zero-Alloc 稽核

現行 batch path 不是 zero-allocation。`ZwtvProcessor` 暖機後，一次成功處理仍至少包含以下明確配置：

| 來源 | 最低配置數 | 說明 |
|---|---:|---|
| third-octave output | 1 | `28 * n_time` |
| main loudness `collect<Result<Vec<_>>>` | 1 | 每幀 `[f64; 21]` 暫存 |
| NL output | 1 | `21 * n_time` |
| AVX2 NL scalar tail | 3 | `ui_delta`、`uo.clone()`、`u2` |
| temporal weighting | 3 | fast、slow、final collect |
| time axis | 1 | 每次重建 |
| returned N/time/N_specific/bark | 4 | 公開 ownership model |
| **暖機後最低合計** | **14** | 不含 Rayon 內部行為 |

首次呼叫還可能讓 processor 的四個 scratch `Vec` 擴容。Scalar fallback 會對多個 bands 建立大暫存；配合 Rayon 時峰值工作集可能超過 100 MB。現有 scratch-capacity test 只證明四個成員容量重用，不能證明整條路徑沒有配置。

---

## 5. 現行效能與逐項分析

### 5.1 2026-07-10 可重現 Criterion 結果

測試輸入為 10 秒、48 kHz、480,000 samples 的三正弦合成訊號。

| 模式 | Filter scalar | Filter AVX2 | Filter SIMD speedup | ZWTV scalar | ZWTV AVX2 | Pipeline speedup |
|---|---:|---:|---:|---:|---:|---:|
| 12 logical threads | 53.40 ms | 5.10 ms | **10.47x** | 139.98 ms | **51.34 ms** | **2.73x** |
| 1 thread | 244.82 ms | 23.98 ms | **10.21x** | 576.43 ms | **252.83 ms** | **2.28x** |

解讀：

- Filter 的約 10x scalar/AVX2 差異證明 SIMD 收益不依賴 Rayon 才存在。
- 12-thread ZWTV 約 194.8x real-time，適合 batch throughput。
- 1-thread ZWTV 約 39.6x real-time，是估算未來單軌串流成本較合理的上界基線。
- Criterion 的 `change:` 在 MT 與 ST 連續執行時會把 thread-count 差異誤標成 improvement/regression，必須看絕對中位數。

### 5.2 各階段效能狀態

R4 後沒有新的完整 stage profiler，因此下表將「目前可量測」與「舊 profiler 結構資訊」分開。

| 階段 | 現況 | 已知成本/特徵 | 主要潛力 | 缺少的驗證 |
|---|---|---|---|---|
| Filter bank | R4 bands x Rayon + AVX2 | ST 23.98 ms；MT filter 5.10 ms | 預算係數、減少 stack spill、layout/scan 研究 | IPC、L1/L2、每 group scaling |
| TOL transpose | 順序 O(n) copy | 舊 profiler約 1 ms | 融合 producer/consumer 或改 layout | current-R4 stage timing |
| Main loudness | frame-parallel | 會配置 `Vec<[f64;21]>`；pow/log/table branches | caller-provided output、移除中介 collect | 獨立 Criterion、alloc count |
| Nonlinear decay | R4 bands x Rayon + AVX2 | 20 bands SIMD + 1 scalar tail；tail 有 3 allocations | tail state machine、time-major/AoSoA layout、bounds elimination | 獨立 Criterion、branch/cycle counter |
| calc_slopes | R1 已消除重算 | 舊 profiler顯示為 ST 主成本、MT 可良好平行 | 工作粒度、table search、full-spec mode分離 | R1/R4 後 stage timing |
| Temporal weighting | 序列遞迴 | 舊 profiler約 1.8 ms；目前 3 allocations | 兩個低通單 pass + caller output | bitwise/FMA影響測試 |
| Output assembly | 多個 Vec + transpose | batch ownership 明確但有配置/搬移 | caller-allocated API、stream frame output | allocation/copy bytes profile |

### 5.3 為何 pipeline SIMD speedup 小於 filter speedup

Filter 是最適合 SIMD 的規律 IIR kernel，所以可以達約 10x。整體 pipeline 還包含：

- scalar/branch-heavy main loudness 與 slope 計算；
- log/pow 等 libm；
- 多次 transpose/materialization；
- temporal recursion；
- allocation、初始化與輸出組裝；
- NL 的 scalar tail。

因此不能用 filter 的 10.2x 直接外推整條 pipeline。整體單緒 2.28x 是合理結果，不代表 SIMD kernel 利用率只有 22%。

---

## 6. 最大上限與潛力分析

### 6.1 必須區分的三種上限

1. **Batch throughput 上限：** 一次處理長訊號，可使用 Rayon、長迴圈攤提、整段輸出配置。
2. **Single-track real-time 上限：** 不使用 Rayon，chunk 很小，必須 zero-alloc、bounded latency。
3. **64-track product 上限：** 靠 host 在 tracks 間平行，還要支付 plugin、GUI、IPC/SPSC、host scheduling 與 cache contention。

三者不能用同一個 Criterion 數字直接互換。

### 6.2 Batch throughput 上限

**MEASURED：** 51.34 ms / 10 s，即 194.8x real-time。

**ESTIMATED 潛力區間：**

| 層級 | 可能區間 | 條件 | 信心 |
|---|---:|---|---|
| 現況 | 51-53 ms | current R4、12 threads | 高 |
| 低風險工程優化 | 40-48 ms | 移除中介配置、current stage tuning、固定 pool/bench metadata | 中低 |
| 侵入式 layout/fusion | 30-40 ms | AoSoA、跨階段融合、減少 transpose、重新驗證 bitwise | 低 |
| 25-30 ms 歷史推估 | 尚未達成 | 來自 R4 前 Amdahl 模型 | 已被實測修正，不應再當承諾 |

目前無法給出更低且可信的硬體地板，原因是缺少 current-R4 stage profile、cycles/instruction、IPC、cache miss 與 memory bandwidth。AVX-512 即使加入也只加速部分 kernel，不會讓整條 pipeline 自動 2x。

### 6.3 單軌即時潛力

以目前單緒 batch amortized 數字：

```text
252.83 ms / 10 s = 2.528% of one core per track
252.83 ms / 5000 output frames = 50.57 us per 2 ms output frame
```

這是有利的吞吐基線，但仍不是 audio callback 實測：

- batch 使用大連續輸入，分支與呼叫成本充分攤提；
- streaming 需要 carry/lookahead、chunk dispatch、flags、sanitization；
- batch 目前配置很多，streaming 必須完全移除；
- denormal 靜音、NaN、host block size、P99/P99.9 尚未測。

R5 現有 `<= 60 us/frame` 驗收只約等於每軌 3% 單核。若以 64 軌、6 實體核計算：

```text
60 us / 2 ms * 64 / 6 = 32% of total 6-core capacity
```

R6 的 `<35%` 目標只剩約 3 個百分點給 host、GUI、SPSC 與 cache contention，過於緊。建議將 R5 目標拆成：

- median `<= 45 us/frame`；
- P99 `<= 60 us/frame`；
- 靜音/高位準/NaN sanitize 後 P99 不超標；
- 不以平均值取代 deadline distribution。

### 6.4 64 軌上限

以目前 50.57 us/frame 的 batch amortized 基線：

```text
single track = 2.528% of one core
64 tracks = 161.8% of one core
on 6 physical cores = 27.0% aggregate CPU capacity
```

這支持「64 軌在算術上可行」，但不等於產品驗收，因為尚未計入：

- host buffer callback 與 plugin wrapper；
- 每軌 state/cache working set；
- GUI aggregation；
- sandbox/multi-process IPC；
- sample-rate conversion；
- CPU power-state、其他插件與 DAW engine；
- P99 deadline 與 xrun，而非平均 throughput。

合理結論是：**64 軌值得進入 R6a/R6b 原型，不應直接宣稱已可穩定承載。**

### 6.5 硬體與演算法上限

| 方向 | 潛力 | 限制 |
|---|---|---|
| AVX-512 f64x8 | Filter/NL lane 寬可能增加 | 現機不支援；downclock、mask、整體 Amdahl 限制需實測 |
| NEON f64x2 | Apple M 可避免 scalar fallback | lane 比 AVX2 窄，但 Apple core IPC/頻寬不同，不能按 1/2 外推 |
| FMA/branchless | 已使用 | 已接近該局部演算法形式的合理實作 |
| 跨時間平行 | 不適用 IIR/NL recursion | 會破壞狀態鏈或改演算法 |
| 降低 NL 24 substeps | 可能大幅加速 | 屬演算法變更，不能接受為透明優化 |
| 降頻帶/降低 specific rate | 可加速 | 會改輸出契約或標準語意，只能成為顯式模式 |
| 近似 log/pow | 可能加速 | 必須另設 precision mode 與 golden，不可偷偷替換 |

任何會改迭代數、頻帶數、時間網格或 libm 精度的工作，都必須以新模式與新驗收出現，不能納入「數值零變更」優化。

---

## 7. 風險分析

### 7.1 風險矩陣

| ID | 風險 | 機率 | 影響 | 現況 | 必要 gate / 緩解 |
|---|---|---:|---:|---|---|
| R-01 | Batch path 被誤稱 zero-alloc/audio-safe | 已發生 | 高 | 至少 14 個明確配置 | 對外文件分開 batch/stream；R5 counting allocator = 0 |
| R-02 | Denormal 靜音失速 | 中高 | 高 | 無 FTZ/DAZ 或 state flush | 60 s silence vs tone；P99/throughput gate；RAII 還原 MXCSR |
| R-03 | NaN/Inf 永久毒化 IIR state | 中 | 高 | batch GIGO，stream 未實作 | chunk sanitize、flag、1 s recovery test |
| R-04 | 非因果 wraparound/lookahead 無法串流 | 必然 | 高 | batch 忠實 Mosqito | ZeroState reference、24-sample latency、chunk invariance |
| R-05 | Audio thread 觸發 Rayon/pool/scheduling | 必然（若重用 batch） | 高 | batch 預設 Rayon | stream API 型別上無 Rayon；不得只靠文件約定 |
| R-06 | Streaming mid-frame error 中斷整條量測 | 中 | 高 | batch `Result` collect | clamp + frame flags；batch 語意保持 |
| R-07 | FFI panic 穿越 ABI | 中 | 高 | R3 未實作 | 每個 extern C 統一 `catch_unwind`；panic injection |
| R-08 | 48 kHz-only 在實際 DAW 不可用 | 高 | 高 | 係數固定 48 kHz | R6a 先做 host 調查；v1 限制或獨立 resampler phase |
| R-09 | 64-instance registry 在 sandbox host 失效 | 中 | 高 | 僅設計假設 | REAPER/Nuendo/Bitwig 類 host 原型；IPC fallback 成本先估 |
| R-10 | Criterion MT/ST baseline 互相污染 | 高 | 中 | Benchmark ID 無 thread count | ID/`--save-baseline` 分離，記錄 env/toolchain/commit |
| R-11 | 無 flamegraph/counter 卻宣稱硬體極限 | 高 | 中 | 目前只有 wall time | uProf/perf/WPR + stage benchmark，建立可重跑腳本 |
| R-12 | SIMD parity 在不支援平台 silent pass | 高 | 高 | test 直接 return | CI job 必須斷言 SIMD path executed |
| R-13 | Hash snapshot 只列印、不自動 assert | 高 | 中 | 人工 gate | expected constants 入測試或 manifest 比對 |
| R-14 | Golden 再生鏈失效 | 中 | 高 | Mosqito/Scipy 環境未完全固化 | lockfile + SHA256 manifest + CI cache/artifact |
| R-15 | FTZ 破壞 bitwise contract | 高 | 中 | R5 尚未定義 | 在 R5 開工前決定 reference 同樣 FTZ 或容差契約 |
| R-16 | Workspace 搬移混入行為修改 | 中 | 高 | R8 未啟動 | 純移動 commit；golden 全綠後才加標準 |
| R-17 | C-ABI 過早凍結阻礙 stream handle | 中 | 中 | R3 先於 R5 | v0 標記；R5 完成才升 v1 |
| R-18 | VST3/CLAP 授權與發布策略未定 | 中 | 中高 | R6a 待辦 | CLAP first；VST3 法務決策先於發布實作 |
| R-19 | 病態輸入缺少 fuzz/property tests | 中 | 高 | NaN/Inf/huge/DC coverage 不足 | R5 收口加入 property/fuzz corpus |
| R-20 | `ParMode::Rayon` 在 1-thread pool 退化成 Sequential，使測試空洞 | 中 | 中 | `use_rayon` 有 thread-count 判斷 | 測試提供強制分支或明確 assertion |

### 7.2 最高優先風險鏈

真正的 critical path 不是「再多做一個 SIMD kernel」，而是：

```text
可再生 golden / 自動 bitwise gate
    -> R3 外部差分驗證
    -> R5 stateful + zero-alloc + causal semantics
    -> R6a host/sample-rate/registry feasibility
    -> R6b single-track deadline
    -> R6c 64-track aggregation
```

其中任一層未通過，都不應以後一層的 GUI 或產品包裝掩蓋。

---

## 8. 可驗證性分析

### 8.1 現有驗證資產

| 資產 | 能證明 | 不能證明 |
|---|---|---|
| Mosqito stage golden | 各階段數值接近 reference | ISO 官方唯一真值、所有病態輸入 |
| Annex B | ISO 指定案例符合 tolerance | 所有時間訊號、streaming correctness |
| SIMD parity | scalar/AVX2 在指定容差內 | bitwise 相同、非 AVX2 CI 確實執行 SIMD |
| R1 hash dump | current output 與既有 snapshot 相同 | CI 自動阻擋，因 helper 只列印 |
| determinism 20 runs | 同一路徑重跑穩定、模式等價 | scalar vs SIMD 完整黑箱逐位相同 |
| Criterion | wall-clock distribution、throughput | branch miss、cache、alloc count、deadline P99 |
| release assembly | LLVM 確實生成 AVX2/FMA/bounds checks | 實際 instruction mix、stall、cache behavior |
| clippy/fmt | lint 與格式品質 | 數值正確或即時安全 |

### 8.2 2026-07-10 實際驗證結果

- `cargo test`：33 個非忽略測試 + 2 doctests 通過；1 個 manual hash test 預設 ignored。
- AVX2 parity 在本機確實執行並通過。
- 4 組輸入 x 3 輸出，共 12 個 hash 與既有 R1 snapshot 相符。
- `cargo clippy --all-targets -- -D warnings` 通過。
- `cargo fmt --check` 通過。
- Criterion MT/ST 已重跑，數字見 5.1。
- `cargo test --release` 因 Windows linker/測試 exe 產物無法開啟或消失而未完成；先通過 14 項後中止。Release benchmark 與 assembly 生成成功。
- 無 flamegraph、無 hardware counter、無 allocation counter、無跨平台 CI 證據。

### 8.3 建議的驗證金字塔

#### 每個 commit

1. Unit tests。
2. Stage golden。
3. End-to-end golden。
4. 自動 expected hash assertion。
5. Determinism 與 thread-count invariance。
6. fmt/clippy。

#### 每個效能 phase

1. 同日、同機、同 toolchain 的 before/after worktree A/B。
2. MT/ST 使用不同 benchmark ID 或 saved baseline。
3. Stage benchmark，不只量 end-to-end。
4. Allocation count/allocated bytes。
5. profiler + cycles/IPC/cache/branch counters。
6. 數值 gate 全綠後才接受效能數字。

#### 每個即時 phase

1. Chunk-size invariance：`1, 7, 24, 64, 128, 480, 4096, random`。
2. Counting allocator：`push()` 0 allocation。
3. P50/P95/P99/P99.9 latency，不只平均。
4. silence/denormal、NaN/Inf、clipping、DC、huge input。
5. 4 小時 soak，state/counter/memory 不漂移。
6. Host xrun 測試與 buffer size matrix。

### 8.4 位元級 differential testing 的正確契約

必須分成三種，不宜混成一句「bitwise equal」：

1. **Refactor invariance：** 同一路徑重構前後必須 hash/`to_bits()` 相同。
2. **Thread invariance：** Sequential/Rayon 必須相同，因為工作項無 reduction。
3. **Backend parity：** Scalar/AVX2/NEON 可能因 FMA 只捨入一次而有 ULP 差；應保留嚴格 tolerance，另對量化後 `N(t)` 設 bitwise gate。

這比強迫所有 backend 全陣列 bitwise 相同更誠實，也避免為了表面 bitwise 一致而禁用 FMA。

---

## 9. 即時引擎設計狀態

### 9.1 已完成的設計決策

R5 master plan 已具體定義：

- `ZwtvStream` 持有 filter/NL/temporal state。
- `push(chunk, out)` caller-provided output，目標 zero-allocation。
- carry 小於 24 samples。
- 固定 1 幀 lookahead，`latency_samples() = 24`。
- `StreamFrame` 以整數 frame index 避免浮點時間漂移。
- `CLAMPED_120DB`、`NONFINITE_INPUT`、`WARMUP` flags。
- Compute layer 不需要 ring buffer；ring buffer 只存在 audio-to-GUI SPSC。
- Streaming path 不使用 Rayon。
- Specific loudness v1 可不輸出，保留 optional tap/第二 output 的擴充點。

這些決策足以進入 bite-sized TDD phase，架構本身不需要重新發明。

### 9.2 尚未完成的實作

| 即時必要條件 | 現況 | 判斷 |
|---|---|---|
| Stateful chunk processing | 無 | 阻擋 |
| Zero allocation in `push` | 無 counting allocator 證據 | 阻擋 |
| No Rayon/pool creation | batch 預設 Rayon | 阻擋 |
| Denormal protection | 無 | 阻擋 |
| NaN/Inf recovery | 無 | 阻擋 |
| Causal initialization/lookahead | batch 為 wraparound/reference 語意 | 阻擋 |
| Stable 24-sample latency | 僅計畫 | 阻擋 |
| P99 deadline | 無 benchmark | 阻擋 |
| Lock-free GUI transport | 僅 R6 設計 | 後續 |
| 48 kHz host handling | 僅限制策略 | 產品阻擋 |
| Long-run soak/xrun | 無 | 產品阻擋 |

### 9.3 即時引擎完成定義

只有同時滿足以下條件才可標示 realtime-ready：

1. `push` 在所有合法 chunk size 都是 0 allocation、0 lock、0 Rayon。
2. chunk size 不影響輸出 bits/timestamps。
3. silence、NaN、clipping 不造成永久狀態污染或 deadline spike。
4. latency contract 由專屬測試鎖定。
5. P99 <= 60 us/frame，建議 median <= 45 us/frame。
6. 4 小時 soak 無配置增長、無 state drift、無 xrun。
7. 至少一個真實 host 完成單軌與 64 軌驗證。

---

## 10. 擴充性分析

### 10.1 C-ABI 與 Python

優點：

- 扁平 row-major output 已適合 pointer + length。
- `Iso532Error` 可穩定映射錯誤碼。
- Caller-allocated C output 可避免跨 allocator free。
- Python binding 能直接與 Mosqito runtime differential test。

風險：

- 現行 Rust API 內部仍配置大量 Vec；caller-allocated FFI 只解決邊界 ownership，不自動讓核心 zero-copy。
- `catch_unwind` 必須涵蓋所有 extern C 入口。
- R3 interface 應保持 pre-1.0，等 R5 stream handle 完成再凍結 v1。

### 10.2 跨平台 SIMD

| 平台 | 現況 | 演進 |
|---|---|---|
| Windows/Linux x86-64 AVX2 | 已實作 runtime dispatch | CI 必須確保 SIMD test 真執行 |
| x86-64 AVX-512 | 無 | 獨立 backend；不可只改 compile flags |
| aarch64 NEON | scalar fallback | R7 f64x2 mechanical port + parity |
| 非 SIMD 平台 | scalar | 必須保留 correctness baseline |

SIMD dispatch 應演進成 backend abstraction，但不要過早建立複雜 trait object；compile-time module + small runtime enum 已足夠，且可避免 hot path dynamic dispatch。

### 10.3 多心理聲學標準

| 方向 | 可複用 | 新工作 | 阻力 |
|---|---|---|---|
| DIN 45692 sharpness | 240-point `n_specific`、golden framework | weighting/integration | 低，最適合作第二標準 |
| ISO 532-2 | output/error/golden infrastructure | FFT、ERB、全新 loudness path | 中 |
| ECMA-418-2 | DSP primitives、validation method | hearing model、modulation analysis | 中高 |
| Roughness/fluctuation | time-varying specific loudness | 可能需要 2 kHz full-rate spec | 中；不可刪 full-rate能力 |

Workspace 化應在第二個標準真正動工時進行。太早拆 crate 只會增加版本與 feature 管理，太晚則會讓 ISO 532-1 私有邏輯滲入共用 DSP。

### 10.4 Plugin/UI 擴充

- Audio engine 與 GUI 必須以 SPSC、drop-on-full 隔離；音訊執行緒不得等待 GUI。
- 64 軌聚合先驗證同 process registry；若 host sandbox，不得事後才改 IPC。
- dBFS-to-Pa calibration 是產品語意，不是單純 UI 選項；錯誤校準會使所有 sone/phon 系統性錯誤。
- 48 kHz-only 是重大產品限制，必須在 R6a 做 go/no-go，而非留到發行前。

---

## 11. 建議演進順序與驗收門

### G0：證據硬化與 R4 收尾

**目的：** 先讓目前成果可稽核，再擴介面。

- 將 R4 實作形成可 bisect 的 commits。
- expected output hashes 改成自動 assertion/manifest。
- Benchmark ID 納入 thread count/backend；保存 commit/rustc/CPU/env。
- 增加 current stage benchmarks：filter、main、NL、slopes、temporal、output assembly。
- 增加 allocation count/bytes benchmark。
- 建立 uProf/perf/WPR profiler 配方與 flamegraph/counter artifact。

**Exit gate：** 正確性全綠、R4 數字可從乾淨 checkout 重現、報告不依賴人工口述。

### R3：C-ABI + Python batch binding

**目的：** 建立跨語言 differential verification 與實用入口。

- Caller-allocated C output。
- `catch_unwind`、錯誤碼、shape/property tests。
- Python/Mosqito 9-signal direct comparison。

**Exit gate：** C smoke、wheel install、panic injection、Python differential 全通過。

### R5：Streaming core

**目的：** 將數學核心改造成真正 audio-thread-safe state machine。

- 先搬 state/scratch，維持計算順序。
- 再定 ZeroState/lookahead/flush/FTZ semantics。
- Counting allocator、chunk invariance、pathological inputs、P99 benchmark。

**Exit gate：** 本文 9.3 七項全部通過。缺一項不得啟動正式 plugin。

### R6a：Host feasibility spike

**目的：** 用最少程式回答 sample rate、registry/process model、licensing 三個產品風險。

**Exit gate：** 明確 go/no-go、目標 host matrix、IPC fallback 成本與格式策略。

### R6b/R6c：Single-track -> 64-track

- 先完成單軌 calibration、latency、4-hour soak。
- 再做 aggregation、GUI、64-instance xrun test。
- 不把單機平均 CPU 當成跨 host 保證。

### R7/R8：Cross-platform 與多標準

- R7 可在 R5 前後穿插，但 macOS plugin 發行前必須完成。
- R8 在 sharpness 開工時進行純搬移 workspace commit。
- 每個新標準先做 reference gap report、自由度地圖與 parity debt 登記。

---

## 12. 可重現命令

在 `D:\ISO532\iso532`：

```powershell
# Correctness
cargo test
cargo test --test golden_zwtv dump_zwtv_output_hashes -- --ignored --nocapture
cargo clippy --all-targets -- -D warnings
cargo fmt --check

# Multi-thread Criterion
cargo bench --bench loudness

# Single-thread Criterion
$env:RAYON_NUM_THREADS='1'
cargo bench --bench loudness
Remove-Item Env:RAYON_NUM_THREADS

# Release assembly inspection
cargo rustc --release --lib -- --emit=asm
```

建議新增但目前 repo 尚未具備的驗證命令類別：

```text
allocation-count test
stage-level Criterion groups
AMD uProf / Linux perf stat counters
flamegraph or sampled call-stack artifact
stream chunk-size invariance
stream P99/P99.9 deadline benchmark
```

---

## 13. 追溯資料

- `docs/DESIGN-DEVELOPMENT-2026-07-04.md`
- `docs/SYSTEM-DESIGN-QA-2026-07-06.md`
- `docs/MOSQITO-VS-ISO-BASELINE-STRATEGY-2026-07-05.md`
- `docs/ROADMAP.md`
- `docs/superpowers/plans/2026-07-05-roadmap-master-plan.md`
- `docs/superpowers/plans/phases/phase-r1-calc-slopes-dedup.md`
- `docs/superpowers/plans/phases/phase-r4-band-parallel.md`
- `iso532/benches/loudness.rs`
- `iso532/tests/golden_zwtv.rs`
- `iso532/tests/simd_parity.rs`
- `iso532/tests/determinism.rs`

---

## 14. 總結

ISO532 現行架構的最大優勢不是單一 benchmark 數字，而是：演算法分層清楚、跨頻帶 SIMD/Rayon 的平行維度選擇正確、reference/golden 資產完整、輸出布局已為 FFI 與後續標準預留。

目前最大的技術債也很明確：batch 成功不能被誤讀為 realtime 成功。Zero-allocation、stateful causality、denormal/nonfinite recovery、P99 deadline、host sample rate 與 plugin process model，都必須在 R5/R6 以獨立 gate 驗證。

效能提升本身是真實的，沒有發現藉由減少頻帶、迭代或放寬既有輸出換速度；但硬體極限、AVX-512 潛力與 64 軌產品容量尚未被 flamegraph/counter/host test 證實。最穩健的演進方式是先完成 G0 證據硬化，再沿 R3 -> R5 -> R6 的依賴鏈推進，並把 R7/R8 保持為可插入但不干擾核心驗證的獨立工作流。
