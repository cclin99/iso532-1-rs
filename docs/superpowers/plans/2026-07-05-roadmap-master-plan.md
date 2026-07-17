# ISO532 Roadmap 主實施計畫(2026-07-05)

> **For agentic workers:** 本文件是**主計畫**(planning-of-plans)。每個階段動工前,必須先依本文件展開成 `docs/superpowers/plans/phases/phase-R<N>-<name>.md` 的 bite-sized TDD 計畫(慣例同 `phases/phase-2-zwst-scalar.md`),再以 superpowers:subagent-driven-development 或 executing-plans 執行。**不要直接拿本文件的 task 清單寫程式**——本文件鎖定的是範圍、介面、驗收與風險,不是逐步驟程式碼。

**Goal:** 將 `ROADMAP.md` 的五個方向與 `DESIGN-DEVELOPMENT-2026-07-04.md` §9 的優先序,整併為八個可獨立交付、順序明確、風險已登記的實施階段。

**Architecture:** 批次 API(現況)→ C-ABI/Python(驗證槓桿)→ 串流核心(`ZwtvStream`)→ VST 產品層,每層只依賴下層已凍結的介面;新標準走 workspace 化後的 `dsp-core` 複用路線。

**Tech Stack:** Rust 2021、std::arch AVX2/NEON、cdylib + pyo3/maturin、nih-plug(CLAP/VST3)、GitHub Actions。

**基準策略:** 全程遵循 `docs/MOSQITO-VS-ISO-BASELINE-STRATEGY-2026-07-05.md`——mosqito golden parity 為主軸,官方值作 gap report 與合規確認。

**工時標示:** 本文件所有工時數字均為**推估**(依 phase 1–5 實績外插),落地後需回填實測。

---

## 0. 階段總覽與依賴圖

```
R1 calc_slopes 修正 ──────────────┐
R2 zwst IsoReference ─────────────┤ (互相獨立,可任意插隊)
R4 離線頻帶平行 ──────────────────┤
                                  ▼
R3 C-ABI + Python binding(批次)──► R5 串流 API + phon ──► R6 VST 插件
                                  │                        ▲
R7 NEON + CI 跨平台 ──────────────┘ (R5 前後皆可;VST 出 macOS 版前必須完成)
                                  
R8 workspace 化 + sharpness → 後續標準 (僅依賴 R1;建議排在 R5 之後避免搬移衝突)
```

| 階段 | 內容 | 工時(推估) | 風險等級 | 前置 |
|---|---|---|---|---|
| R1 | calc_slopes 重複計算修正 | 0.5 天 | 低 | 無 |
| R2 | zwst IsoReference 模式 | 1–2 天 | 低 | 無 |
| R3 | C-ABI + Python binding(批次) | 3–5 天 | 中 | 無 |
| R4 | filter_bank / nl 頻帶平行(離線) | 2–3 天 | 中 | 無 |
| R5 | 串流 API 重構 + phon 轉換 | 8–12 天 | **高** | R1(建議)、R3(介面互鎖) |
| R6 | VST 插件(64 軌 + 面板) | 4–8 週,分 3 子階段 | **高** | R5 必須;R7 出 mac 版前必須 |
| R7 | NEON kernel + CI 三平台 | 3–5 天 | 低-中 | 無(kernel 結構已凍結) |
| R8 | workspace 化 + sharpness → ECMA/532-2 | sharpness 2–3 天起 | 中 | R1;建議 R5 後 |

**順序決策說明**(調和 `ROADMAP.md` 執行順序與 DESIGN §9):採 ROADMAP 的「C-ABI 先於串流」——Python binding 讓 R5 之後的每一步都能用 pytest 直接對 mosqito 互比,驗證槓桿最大;DESIGN §9 把串流排第 2 是就緒度視角,不衝突。R2/R4 為獨立小項,插隊填空檔。

---

## R1:calc_slopes 重複計算修正

**來源:** DESIGN §5.2-1。`calc_slopes_n_only` 跑全部幀、`calc_slopes_into` 對 t%4==0 幀重算——每 4 幀 1 幀算兩遍。

**範圍:**
- Modify: `iso532/src/zwtv/mod.rs`(`ZwtvProcessor::process` 的兩段 calc_slopes 呼叫合併為分流:t%4==0 走 `calc_slopes_into` 並取其回傳 N,其餘走 `calc_slopes_n_only`)
- Modify: `iso532/src/core/calc_slopes.rs`(確認 `calc_slopes_into` 回傳 N;若目前丟棄則補回傳,不改演算法)

**驗收準則:**
1. `cargo test` 全綠,golden 測試(9 組)**逐位不變**——本項是純調度重排,任何數值變化都是 bug。
2. criterion `zwtv_10s` 單執行緒自 285.9 ms 降至 ~250 ms(容許 ±10% 機器噪音);多執行緒不劣化。
> **實測回填(2026-07-08,本機):** 單執行緒 AVX2 285.9 -> 244.1 ms;多執行緒 AVX2 歷史基線 79.1 ms -> 69.6 ms。
> **審查驗證(2026-07-09,同機無負載 A/B,HEAD worktree 對照):** 單執行緒 AVX2 279.1 -> 244.7 ms(**-12.3%**,正中 ~250 ms 目標);多執行緒 AVX2 76.5 -> 69.3 ms(**-9.4%**,優於推估的 -4 ms);多執行緒 scalar 362.9 -> 363.0 ms(無劣化)。單執行緒 scalar 577.1 -> 535.5 ms(-7.2%)。逐位比對:4 訊號 x 3 輸出共 12 個 FNV-1a 雜湊逐字相同(準則 1 達成);clippy/fmt 乾淨(準則 3 達成)。量測注意:機器須閒置——背景負載曾造成多執行緒 scalar +3% 的假性劣化。
3. `cargo clippy --all-targets -- -D warnings`、`cargo fmt --check` 乾淨。

**風險與陷阱:**

| # | 風險 | 機率 | 影響 | 緩解 |
|---|---|---|---|---|
| 1 | `calc_slopes_into` 與 `n_only` 對同一幀的 N 存在捨入路徑差(r8/量化順序不同)→ 分流後 N(t) 在 t%4==0 幀跳動 | 低 | 中 | 動工前先寫「兩函式對同一幀輸出 N 逐位相等」的單元測試;若不等,先修齊再分流 |
| 2 | rayon 分流後兩種工作項混在同一 par 迴圈,槽位寫入錯位 | 低 | 高 | 維持「每工作項寫互斥槽位」不變式;golden 逐位比對會抓到 |

---

## R2:zwst IsoReference 模式

**來源:** DESIGN §10.2(實驗已驗證:Signal 3 偏差 +0.82%→+0.025%、Signal 5 →精確命中)。

**範圍:**
- Modify: `iso532/src/lib.rs`——新增 `pub enum ZwstMode { Mosqito, IsoReference }`,`loudness_zwst` 維持原簽名(內部走 `Mosqito`),新增 `loudness_zwst_with_mode(signal, fs, field_type, mode)`。
- Modify: `iso532/src/zwst/mod.rs`——IsoReference 路徑:呼叫 `zwtv::third_octave_levels` → 跳過穩定暫態窗 → 對頻帶**強度**(非 dB)取時間平均 → 換 dB → 進既有 `main_loudness`/`calc_slopes`。
- Create: 常數 `SETTLE_DISCARD_SECS`,**由最慢頻帶時間常數推導**(25 Hz 帶,τ ~0.1 s 量級,取 5τ)並附推導註解——取代實驗用的 magic number 0.5。
- Test: `iso532/tests/annexb.rs` 加 IsoReference 對 Signal 3(容差:量化步階 + 重採樣殘留,上界 0.05%)與 Signal 5(精確至量化步階)。

**驗收準則:**
1. 預設路徑(Mosqito)golden 逐位不變——**golden 體系不可破壞**是本階段的最高約束。
2. 丟棄窗敏感性測試:`SETTLE_DISCARD_SECS` ×0.5 與 ×2 時 Signal 3/5 結果變化 < 1 個量化步階(證明選值在平坦區)。
3. 文件:丟棄窗推導寫入 rustdoc。

**風險與陷阱:**

| # | 風險 | 機率 | 影響 | 緩解 |
|---|---|---|---|---|
| 1 | API 形狀(enum 參數 vs 新函式)之後被 C-ABI 凍結,反悔成本高 | 中 | 中 | R2 落地前與 R3 的 C 介面草案對照一次;enum 在 C 端映射為 int,天然穩定 |
| 2 | 平均域搞錯:對 dB 取平均而非對強度取平均(常見錯) | 中 | 高 | 驗收測試 Signal 5 精確命中即為看守——平均域錯會偏 >0.1% |
| 3 | 44.1 kHz 輸入殘留 +0.025% 被誤當 bug 追殺 | 中 | 低 | 文件明載成因(FFT resample 漣波)與接受理由;測試容差含此項 |

---

## R3:C-ABI + Python binding(批次 API)

**來源:** ROADMAP §4。扁平 row-major 輸出與具名錯誤已就緒。

**範圍:**
- Create: `iso532-ffi/`(新 crate,`crate-type = ["cdylib", "staticlib"]`),不併入 `iso532`(避免主 crate 揹 cdylib 建置)。
- Create: `iso532-py/`(pyo3 + maturin)。
- Create: `iso532-ffi/include/iso532.h`(手寫或 cbindgen 生成後入 git)。

**C 介面設計決策(本計畫先鎖定,phase 計畫不再重議):**
1. **記憶體模型:caller-allocated 兩段式**——`iso532_zwtv_out_frames(input_len) -> size_t` 查詢尺寸,呼叫端配置後 `iso532_loudness_zwtv(signal, len, field_type, out_n, out_spec, out_time, out_flags) -> int32_t 錯誤碼`。理由:無跨 allocator 釋放問題、VST/嵌入端零拷貝、綁定語言(numpy)可預配。**不要**回傳 Rust 配置的指標 + free 函式(v1 不做 opaque handle;串流 handle 留給 R5 擴充)。
2. **錯誤碼:** `0=OK`,`Iso532Error` 三變體映射 1/2/3,**負值保留給 FFI 層自身錯誤**(null 指標 = -1、panic = -2)。錯誤碼一經發布不得重排。
3. **panic 邊界:** 每個 `extern "C"` 函式體整體包 `catch_unwind`,panic → -2。這是 DESIGN §7-P1-7 的落地點。
4. **執行緒:** rayon 照常參與(批次路徑);文件註明程式庫會使用行程級 thread pool。

**Python 介面:** `iso532.loudness_zwtv(signal: np.ndarray, fs: float, field_type: str) -> (N, N_spec, bark, time)`,`py.allow_threads` 釋放 GIL,回傳值以 `PyArray1/2::from_vec` 零額外拷貝。

**驗收準則:**
1. C 端 smoke test(CI 編一個 `cc` 小程式呼叫 `.h`)。
2. pytest:Rust binding vs mosqito 直跑,9 組 golden 訊號,N(t) atol 1e-12——**這組測試就是之後所有階段的迴歸傘**。
3. `maturin build` 產出 wheel 可在乾淨 venv 安裝。
4. panic 注入測試:故意餵 shape 錯誤觸發內部 assert,確認回 -2 而非行程崩潰。

**風險與陷阱:**

| # | 風險 | 機率 | 影響 | 緩解 |
|---|---|---|---|---|
| 1 | **panic 穿越 FFI = UB**——漏包一個函式就是行程崩潰 | 中 | 高 | 巨集統一包裝(`ffi_guard!`);panic 注入測試逐函式跑 |
| 2 | rayon 工作項 panic 繞過 catch_unwind 傳播路徑差異 | 低 | 高 | rayon panic 會在 join 點 resume——被外層 catch_unwind 接住,寫測試證實而非假設 |
| 3 | Windows 下 MSVC/GNU toolchain 與呼叫端 ABI 不合 | 低 | 中 | 只承諾 MSVC ABI(與 VST host 生態一致);CI 驗 |
| 4 | `FORCE_SCALAR` 行程級全域被 binding 使用者誤用 | 低 | 低 | 不匯出到 C/Python 介面 |
| 5 | 尺寸查詢函式與實際輸出長度不同步(降採樣邊界 off-by-one) | 中 | 中 | 對 1..200 隨機長度做 property test:查詢值 == 實際填入值 |
| 6 | pyo3/numpy 版本矩陣(abi3 vs 非 abi3) | 中 | 低 | 用 `abi3-py39` 單 wheel;CI 裝最舊支援版驗 |

---

## R4:filter_bank / nl 頻帶平行(離線吞吐)

**來源:** DESIGN §5.2-2/3。兩者皆「時間遞迴在帶內、跨帶零依賴」,語意零風險;預估多執行緒 19.6→~4 ms、17.4→~4 ms,合計地板 ~25–30 ms。

**範圍:**
- Modify: `iso532/src/zwtv/third_octave_levels.rs`——7 個 f64x4 群組 rayon 分 7 工,各群組獨立完整掃訊號,寫入互斥的頻帶列。
- Modify: `iso532/src/zwtv/nonlinear_decay.rs`——5 個 4 帶群組 + 1 scalar 尾帶分 6 工。
- **僅離線批次路徑啟用**——為 R5 預留:平行入口收 `enum ParMode { Rayon, Sequential }` 或等效條件,串流路徑編譯期/建構期選 Sequential。

**驗收準則:**
1. golden 逐位不變(頻帶獨立 ⇒ 平行化不得改變任何位元;若變即為實作錯誤,不是可接受誤差)。
2. simd_parity 不變。
3. criterion:多執行緒 zwtv_10s 自 ~79 ms 降至 45–55 ms 區間(推估需實測修正);**單執行緒不得劣化 >2%**。
4. 決定性測試:同輸入跑 20 次,輸出逐位相同。

**風險與陷阱:**

| # | 風險 | 機率 | 影響 | 緩解 |
|---|---|---|---|---|
| 1 | 7 群組同時全速掃 3.84 MB 訊號 → L3 頻寬競爭,加速遠低於 7× | 高 | 低(僅收益縮水) | 預期管理:DESIGN 已標推估;實測後回填,收益 <2× 則考慮群組配對(4 工) |
| 2 | 輸出列跨步寫入造成 false sharing(相鄰群組寫同 cache line) | 中 | 低 | 每群組寫入自己的連續暫存列,結束後一次搬回;或按 64B 對齊切槽位 |
| 3 | rayon 巢狀:外層已在 par 區(未來多軌)再進本平行 → 工作竊取死鎖疑慮 | 低 | 中 | rayon 巢狀是安全的(work-stealing),但 R5/R6 串流路徑必須走 Sequential——用型別強制而非約定 |
| 4 | 群組間 filter 狀態誤共享(重構時把 state 提到群組外) | 低 | 高 | 狀態型別按群組切分(`[BandState; 4]` per group),編譯期隔離 |

> **實測回填(2026-07-10,Ryzen 5 3600,同日 A/B:`git worktree` 檢出 R1 9d8c496 當場重量基線):** 多執行緒 AVX2 74.2 → 52.2 ms(−30%,達 45–55 ms 目標區間);單執行緒 AVX2 249.0 → 252.8 ms(+1.5%)、scalar 553.9 → 558.0 ms(+0.7%),**≤2% 準則達成**。filter_bank_10s 單執行緒 AVX2 21.6 → 24.3 ms(+2.7 ms = tol 迴圈互換成本,攤到管線 +1.1%;風險 #1「回報不重工」適用,不啟動群組配對)。多執行緒 scalar 139.5 ms(無同日基線,歷史參考 ~136.5 ms)。逐位比對 12/12 雜湊相同;determinism 20 次跑逐位相同。審查紀錄見 `phases/phase-r4-band-parallel.md`。

---

## R5:串流 API 重構 + phon 轉換(關鍵階段)

**來源:** DESIGN §7 P0-1..4 + P1-5/6、§9-2;ROADMAP §2/§3。**此階段落地前不動 VST。**

### 範圍與介面(本計畫鎖定)

- Create: `iso532/src/zwtv/stream.rs`
- Modify: `iso532/src/zwtv/{third_octave_levels,nonlinear_decay,temporal_weighting}.rs`——把每呼叫配置移入狀態物件(P1-5),抽出「單幀推進」入口。
- Create: `iso532/src/sone2phon.rs`——`N ≥ 1 → 40 + 10·log2(N)`;`N < 1 → 40·(N + 0.0005)^0.35`(mosqito utils 語意,golden 對比)。
- Create: `iso532/tests/stream.rs`

```rust
pub struct ZwtvStream { /* fb/nl/tw 狀態 + carry([f64;24]) + 1 幀 lookahead 槽 + 相位計數 + 預配 scratch */ }

pub struct StreamFrame {
    pub t_frame_index: u64,      // 自串流起點的 2 ms 幀序號(整數,無浮點累積)
    pub n: f64,                  // sone
    pub n_phon: f64,
    pub flags: FrameFlags,       // CLAMPED_120DB | NONFINITE_INPUT | WARMUP
}

impl ZwtvStream {
    pub fn new(field_type: FieldType) -> Self;
    /// 零配置;回傳寫入 out 的幀數。out 尺寸不足屬呼叫端錯誤(debug_assert)。
    pub fn push(&mut self, chunk: &[f64], out: &mut [StreamFrame]) -> usize;
    pub fn flush(&mut self, out: &mut [StreamFrame]) -> usize;  // 排空 lookahead 尾幀
    pub fn reset(&mut self);
    pub const fn latency_samples() -> usize { 24 }   // 1 幀前視 = 0.5 ms
    pub fn max_frames_for_chunk(chunk_len: usize) -> usize;
}
```

設計不變式(源自 2026-07-05 環形緩衝分析):**計算層只需線性 scratch + 狀態 struct + 1 幀延遲,不引入環形緩衝區**;環形緩衝屬 R6 的 audio→GUI 通道。specific loudness 串流輸出 v1 不做(VST 面板用 N/phon 即可;240 點 spec 留待有需求時以第二 out 參數擴充)。

### P0 逐項落地方式

| P0 | 落地 | 看守測試 |
|---|---|---|
| 1 denormal | AVX 路徑:push 作用域設 MXCSR FTZ+DAZ、離開時**還原原值**(per-thread);scalar 路徑:每幀對濾波器狀態沖洗 `|s|<1e-30 → 0` | 60 s 靜音段吞吐 vs 60 s 正弦吞吐,劣化 <20% |
| 2 NaN/Inf | push 入口 `is_finite` 掃描;非有限樣本置 0 + 該幀 flag `NONFINITE_INPUT` | 注入 NaN 後,後續 1 s 內輸出回到與乾淨串流一致(狀態未毒化) |
| 3 前視/初始化 | lookahead 固定 1 幀;nl 初始化改零初始 + 前 k 幀標 `WARMUP` | 批次核心加 `InitMode::ZeroState`(不公開)生成「串流參考輸出」,串流結果與之**逐位一致**(對齊 1 幀延遲後) |
| 4 錯誤語意 | >120 dB 幀夾限 + flag `CLAMPED_120DB`,不回 Err;批次 API 語意不動 | 注入 130 dB 低頻幀,串流不中斷、flag 正確、後續幀恢復 |

### 驗收準則(全部必須,缺一不收)

1. **chunk 尺寸不變性(本階段最強測試):** 同一訊號以 chunk 尺寸 {1, 7, 24, 64, 480, 4096, 隨機序列} 餵入,輸出**逐位相同**。carry/lookahead/相位的任何 bug 都會在此現形。
2. **批次等價:** 對 9 組 golden 訊號,串流輸出與 `InitMode::ZeroState` 批次參考逐位一致;與現行批次 golden 的差異僅限前 N_warmup 幀(N_warmup 由 nl/tw 時間常數推導,寫入文件)。
3. **零配置:** push 路徑以配置計數 hook(測試 build 換 counting allocator)證明 0 allocation。
4. **無 rayon:** push 路徑不觸發 thread pool 建立(測試:`RAYON_NUM_THREADS` 未初始化下呼叫,查 rayon 全域池未建)。
5. 單幀成本 ≤ 60 µs(單執行緒,對照 DESIGN §4.4 預算 200 µs)。
6. sone2phon 對 mosqito golden atol 1e-12。

> **R5 實作回填（2026-07-16）：** ZwtvStream、sone2phon、P0 硬化、零配置/無 Rayon 看守與 iso532_stream_* C ABI v1 均已落地。Chunk {1,7,24,64,480,4096,LCG} 對 ZeroState 參考逐位一致；scalar/AVX2 兩路皆通過。原 phase 計畫的 N_warmup=363 在實測 frame 363 仍有 1.7133437069e-7 差值，第一個持續 ≤1e-9 的 frame 為 544，因此依 8τ_var + 8τ_slow 修正為 **580 frames**（36-frame margin），未放寬 1e-9 容差。Criterion 10 s/5000 frames median：AVX2 241.78 ms = 48.36 µs/frame，scalar 355.48 ms = 71.10 µs/frame，兩者均達預算。Python smoke 6/6、formal parity 18/18（0 skipped）、FFI Rust tests 13/13；cbindgen 0.29.4 已重生 v1 header。決策細節與偏差證據見 phases/phase-r5-stream-api.md 的實作紀錄。

### 風險與陷阱

| # | 風險 | 機率 | 影響 | 緩解 |
|---|---|---|---|---|
| 1 | **MXCSR 設定洩漏**:push 提前 return / panic 未還原 FTZ,汙染呼叫端執行緒的浮點語意(下游音訊處理全變) | 中 | **高** | RAII guard(`Drop` 還原);測試:push 後讀 MXCSR 斷言復原 |
| 2 | FTZ/DAZ 改變數值:狀態被 flush 為 0 vs 批次的 denormal 尾巴 → 與批次參考差 1 ulp 級 | 高 | 中 | 「逐位一致」驗收改為:批次參考也在 FTZ 環境生成;或容差 atol 1e-15 並文件化。**phase 計畫要先做這個決策,不要寫到一半才發現** |
| 3 | 2 ms 網格相位漂移:chunk 邊界處 t%4 計數錯 1 → 輸出網格整體偏移半格 | 中 | 高 | chunk 不變性測試直接看守;t_frame_index 用整數推導(已設計) |
| 4 | lookahead 語意誤解:誤把「前視 1 幀」實作成「延遲輸出 1 幀但內插仍讀舊值」→ 對不上批次 | 中 | 高 | 先寫「單 chunk 全訊號 push == 批次 ZeroState」的測試再動內插程式碼(TDD 順序強制) |
| 5 | 溫暖化幀數 N_warmup 定義爭議(nl τ 最長 ~? ms、tw 70 ms)→ 驗收模糊 | 中 | 中 | phase 計畫開頭即以時間常數推導定數(5τ_max),寫死進測試 |
| 6 | 每呼叫配置移除時改變計算順序(scratch 重用改變浮點結合順序) | 中 | 中 | 分兩步 commit:先搬配置(數值逐位不變),再動語意;每步跑 golden |
| 7 | `flush()` 尾幀語意與批次結尾不一致(批次有完整訊號,串流結尾少 1 幀前視) | 高 | 低 | 定義:flush 以最後一幀自我外插(重複末幀),文件化;批次等價測試排除最末幀 |
| 8 | C-ABI 串流擴充(handle create/push/destroy)與 R3 的 caller-allocated 慣例接縫 | 低 | 中 | R5 收尾時補 `iso532_stream_*` 四函式,opaque handle 僅此處引入;錯誤碼沿用 |

---

## R6:VST 插件(64 軌 + dB SPL/Sone 面板)

**來源:** ROADMAP §2/§3。**強制分 3 個子階段,每階段有可退出點**——VST 是本 roadmap 不確定性最高的一段,前期決策錯誤的重工成本以週計。

### R6a:可行性原型(1–1.5 週)——先回答三個致命問題再投入

1. **宿主取樣率**:ISO 532-1 全部係數烘焙在 48 kHz;host 跑 44.1/96 kHz 時怎麼辦?
   - v1 決策:**僅原生支援 48 kHz**,其他取樣率插件掛牌「需 48 kHz session」並旁路;v1.1 再評估即時重採樣器(候選 rubato,需驗 realtime-safe 與延遲)。**不要在 v1 就揹重採樣器**——它是另一個需要 golden 驗證的 DSP 元件。
2. **64 軌聚合架構**:單一插件實例在主流 DAW 看不到 64 軌。原型驗證:每軌一實例 + 行程內共享 registry(`static` DashMap 或等效)+ 一個 hub 實例/獨立視窗聚合顯示,在目標 DAW(先選定 1–2 個,建議 REAPER + Nuendo)實測:(a) 同行程性是否成立(部分 host 沙箱化插件);(b) 實例生命週期與 registry 清理。
   - **若同行程 registry 不成立,退路是共享記憶體 IPC——成本 +2 週,原型階段就要知道**。
3. **授權**:VST3(vst3-sys)為 GPLv3 雙授權——閉源發布需 Steinberg 協議;**CLAP 無此限制**(nih-plug 本體 ISC)。v1 決策:CLAP 優先,VST3 視發布策略後補。此為法務決策,原型階段報告即可。

R6a 交付:三個問題的實測答案 + go/no-go 建議。

### R6b:單軌插件(2–3 週)

- Create: `iso532-vst/`(nih-plug,獨立 crate,依賴 `iso532` 的 `ZwtvStream`)
- 音訊執行緒:`ZwtvStream::push`(R5 已保證零配置/無 rayon/denormal 防護);宣告 latency 24 samples。
- audio→GUI:SPSC 環形緩衝(候選 `rtrb`),GUI 端 60 Hz 拉取 StreamFrame;**這是本專案唯一的環形緩衝區**(2026-07-05 分析結論:計算層不需要)。
- GUI(nih_plug_egui):N(t) 走勢、瞬時 sone/phon 數字、28 頻帶 dB SPL 條(來自 filter bank 狀態的頻帶位準輸出——需在 `ZwtvStream` 加選配 tap,R5 時預留欄位)。
- 驗收:REAPER 中 1 kHz 40 dB 校準訊號顯示 1.000 sone / 40 phon(需定義插件內 dBFS→Pa 校準參數,預設 94 dB SPL = 1 Pa @ 0 dBFS,GUI 可調);CPU 單軌 <1%(對照 57 µs/幀 = 2.8%@單核 200µs 預算);4 小時連跑無漂移、無配置增長(對照 DESIGN §6)。

### R6c:64 軌聚合 + 面板(2–3 週)

- hub 視圖:64 軌 N/phon 總覽、排序、峰值保持;軌名從 host 取(CLAP track info 擴充,host 支援度不一——降級為手動命名)。
- 驗收:64 實例 @ 48 kHz,總 CPU <35%(對照 DESIGN §4.4 推估 30%),無 xrun(buffer 128 samples)。

### 風險與陷阱

| # | 風險 | 機率 | 影響 | 緩解 |
|---|---|---|---|---|
| 1 | **取樣率陷阱**:使用者 session 是 44.1 kHz,插件旁路 → 「插件壞了」 | 高 | 高(口碑) | v1 GUI 明示需求 + 文件;v1.1 重採樣器立項(獨立 golden 驗證) |
| 2 | **同行程 registry 不成立**(host 沙箱/多行程插件架構,如部分 Bitwig 設定) | 中 | 高(架構重來) | R6a 原型先驗;退路共享記憶體 IPC 預估 +2 週 |
| 3 | VST3 GPLv3 授權未決就寫 VST3 目標 | 中 | 中(法務) | CLAP 先行;VST3 延後為獨立決策 |
| 4 | GUI 執行緒讀取造成音訊執行緒阻塞(誤用 Mutex 而非 SPSC) | 中 | 高 | 架構規定:音訊執行緒唯一同步原語是 SPSC push(失敗即丟幀,GUI 端容忍) |
| 5 | host 校準語意:dBFS→dB SPL 校準錯,所有 sone 數字系統性偏差 | 高 | 高 | 校準參數顯式化 + GUI 顯示當前假設;文件教學(94/100/114 dB 慣例) |
| 6 | nih-plug API 演進(0.x 版,breaking changes) | 中 | 低 | 鎖 commit;插件層薄,核心都在 `iso532` |
| 7 | 長時運作:DESIGN §6 已審(收縮映射、整數幀計數),但 GUI 端浮點時間軸重犯累積誤差 | 中 | 低 | GUI 時間軸一律由 `t_frame_index` 整數推導 |
| 8 | denormal:host 未設 FTZ 時 GUI/其他插件慢化被歸咎本插件 | 低 | 低 | R5 的 RAII guard 已隔離;釋出說明 |

---

## R7:NEON kernel + CI 三平台

**來源:** ROADMAP §5。結構照抄已凍結的 AVX2 kernel,機械性移植。

**範圍:**
- Modify: `iso532/src/zwtv/third_octave_levels.rs`——NEON:28 帶 = **14×f64x2,無尾帶**;`vfmaq_f64`/`vmaxq_f64`/`vbslq_f64` 與 AVX2 一一對應。
- Modify: `iso532/src/zwtv/nonlinear_decay.rs`——21 帶 = **10×f64x2 + 1 scalar 尾帶**(注意:與 AVX2 的 5×4+1 分組不同,尾帶邏輯可沿用)。
- Modify: `iso532/src/simd/mod.rs`——aarch64 無需 runtime 偵測,`#[cfg(target_arch = "aarch64")]` 直接編入。
- Create: `.github/workflows/ci.yml`——windows-latest / ubuntu-latest(AVX2)/ macos-latest(M 系列)。

**CI 的 golden 資料問題(本階段真正的工作量):** `data/` gitignored,CI 必須重生 → Python venv + mosqito==1.2.1 + 鎖定 numpy/scipy 版本(`tools/requirements.lock`)。用 actions/cache 以 `gen_golden.py`+`requirements.lock` 雜湊為 key 快取 `data/`,避免每次跑 mosqito(其 zwtv 0.45× 即時,9 組訊號生成要數分鐘)。

**驗收準則:**
1. macos runner:`cargo test` 全綠**且 simd_parity 實際執行**(斷言測試非 skip——加一個 `#[cfg(target_arch="aarch64")]` 的存在性測試防 silent skip)。
2. NEON vs scalar parity 容差沿用 AVX2 框架(N(t) 位元一致預期同樣成立——量化吸收)。
3. M 系列 bench 數字記錄(無目標值,建 baseline)。

**風險與陷阱:**

| # | 風險 | 機率 | 影響 | 緩解 |
|---|---|---|---|---|
| 1 | **simd_parity silent skip**:ROADMAP 已警告——M 機器全綠 ≠ 驗過 SIMD | 高 | 高 | 上述存在性測試;CI job 名明示 `neon-parity` |
| 2 | scipy 版本漂移使 CI 重生的 golden 與本機不同(濾波器設計數值差) | 中 | 中 | requirements 全鎖版本;golden 生成後印 SHA256 清單入 repo,CI 比對 |
| 3 | vbslq 分支消除語意與 AVX2 blendv 的 NaN 傳播差異 | 低 | 中 | parity 測試涵蓋含夾限路徑的訊號(step_60_80 已在 golden 集) |
| 4 | 無 M 系列實機,除錯只能在 CI 上迭代 | 高 | 中(效率) | 移植期用 CI 快速迴圈;或 QEMU aarch64 本機先過編譯與 scalar |

---

## R8:workspace 化 + sharpness → 後續標準

**來源:** ROADMAP §1、DESIGN §8、`MOSQITO-VS-ISO-BASELINE-STRATEGY-2026-07-05.md` §4.3。

**時機規則(DESIGN §8 原話):workspace 化在第二個標準動工時做,不提前。** sharpness 就是那個觸發點。

**範圍(sharpness 為首發,DIN 45692):**
- workspace 化:`dsp-core` / `iso532-1` / `sharpness`;現行模組邊界已按此切,是搬移不是重構。搬移 commit 必須零程式碼變更(純 `git mv` + path 修正),golden 全綠後才動 sharpness。
- sharpness 演算法:對 `n_specific`(240 點)做加權重心積分——直接消費現有輸出,無新 DSP。
- **固定前置作業(策略文件 §4.3,每個新標準都做):**
  1. gap report:mosqito sharpness 對 DIN 45692 官方驗證資料的偏差先量;
  2. parity debt 登記:mosqito 實作痕跡逐項記錄;
  3. 自由度地圖:標明規定性 vs 自由度環節。

**後續順序(DESIGN §8 評估):** sharpness → ISO 532-2(FFT 前端,rustfft 進 dsp-core)→ ECMA-418-2(工作量最大,hearing model 全新)。roughness 類需 2 kHz 全速率 spec——**`calc_slopes_into` 的全速率能力不得在任何重構中移除**(DESIGN §8 明文)。

**風險與陷阱:**

| # | 風險 | 機率 | 影響 | 緩解 |
|---|---|---|---|---|
| 1 | workspace 搬移混入行為變更,golden 失效時無法歸因 | 中 | 高 | 鐵律:搬移 commit 零邏輯變更,單獨 commit,golden 全綠才繼續 |
| 2 | sharpness 的 zwst 依賴模式(free field 假設等)與 DIN 驗證資料不合 | 中 | 中 | gap report 先行即為此設 |
| 3 | ECMA-418-2 支援多取樣率,與本專案「48 kHz 烘焙」慣例衝突 | 高 | 中 | ECMA 立項時獨立 spec;dsp-core 濾波器設計走參數化(屆時引入,不回改 ISO 532-1) |
| 4 | 新標準的 mosqito 參考版本與 1.2.1 不同步 | 中 | 中 | 每標準鎖自己的參考版本,golden 目錄按標準分開 |

---

## 9. 跨階段風險登記簿(不屬於單一階段)

| # | 風險 | 影響範圍 | 緩解 |
|---|---|---|---|
| X1 | **golden 再生依賴鏈脆弱**:mosqito 1.2.1 + numpy/scipy 特定版本,上游 yank 或 Python 版本不相容後 golden 不可重生 | 全部 | R7 時鎖 requirements + golden SHA256 清單;考慮把 golden `.bin`(數十 MB)改為 LFS 入庫或 release artifact |
| X2 | **單機基準噪音**:所有效能數字出自同一台 Ryzen 3600,推估外插到其他硬體不成立;**跨日機器條件亦不可比**(R4 教訓:對歷史基線直比產生 ST +3~5% 假警報,連未改動路徑都「劣化」4%) | R4/R5/R6 | 效能驗收一律寫區間不寫點值;**緊預算驗收(如 ST ≤2%)必須同日同機 A/B——`git worktree` 檢出基準 commit 當場重量,不得直接比對歷史數字**;R6b 起加第二台實測 |
| X3 | **介面凍結順序**:R3 凍結 C-ABI → R5 串流擴充 → R6 消費;若 R5 發現批次 C-ABI 設計缺陷,已有下游 | R3→R6 | R3 的 `.h` 標註 `/* v0, pre-1.0: may change */` 直到 R5 收尾;R5 收尾時一併升 v1 凍結 |
| X4 | **Codex 交接損耗**:主計畫→phase 計畫→實作的兩層轉譯,約束(如「逐位不變」)在轉譯中弱化為「誤差很小」 | 全部 | phase 計畫模板固定含「驗收準則」節,逐條複製本文件原文,不改寫 |
| X5 | 規格漂移:DESIGN/ROADMAP/本文件三處記載,更新不同步 | 全部 | 本文件為執行順序的唯一權威;ROADMAP 改指向本文件 |

---

## 10. 下一步

1. 依 X5,`ROADMAP.md` 末節「執行順序建議」改為指向本文件。
2. R1 可立即展開 phase 計畫(`phases/phase-r1-calc-slopes-dedup.md`)交 Codex——半天量級、零風險、首個回血。
3. R6a 的三個致命問題(取樣率、聚合架構、授權)可在 R3–R5 進行期間以低優先背景調研,避免 R6 開工才發現架構性障礙。
