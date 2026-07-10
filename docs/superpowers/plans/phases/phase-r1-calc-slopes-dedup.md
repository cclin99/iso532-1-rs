# Phase R1: calc_slopes 重複計算修正 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 消除 `ZwtvProcessor::process` 中每 4 幀 1 幀被 `calc_slopes` 算兩遍的浪費(`calc_slopes_n_only` 跑全部幀 + `calc_slopes_into` 對 t%4==0 幀重算),輸出逐位不變。

**Architecture:** 純調度重排——把 `zwtv/mod.rs` 的兩個 rayon 平行迴圈合併為一個:每個工作項負責 4 幀(1 幀走 `calc_slopes_into` 同時取回 N,3 幀走 `calc_slopes_n_only`),寫入互斥槽位。`calc_slopes.rs` 演算法零改動(`calc_slopes_into` 已回傳 N,見 `calc_slopes.rs:9-16`)。

**Tech Stack:** Rust 2021、rayon(par_chunks_mut + zip)、criterion、既有 golden 測試框架。

**來源:** `docs/superpowers/plans/2026-07-05-roadmap-master-plan.md` R1 節(範圍、驗收、風險以該文件為準)。

---

## 前置條件(執行前確認,缺一不動工)

1. `data/golden/` 存在且含 `sine_1k_60`、`pulse_1k_70`、`step_60_80`、`annexb_sig10` 等訊號目錄(此目錄被 gitignore;若缺失,先以 `tools/gen_golden.py` 重生,需 Python venv + mosqito==1.2.1)。
2. `cargo test` 目前全綠(以乾淨基線起步)。
3. 本機為 AVX2 機器(基準數字對照 Ryzen 5 3600;非此機器時效能驗收只看相對變化,不看絕對值)。

## 驗收準則(逐字複製自主計畫 R1,不得改寫)

1. `cargo test` 全綠,golden 測試(9 組)**逐位不變**——本項是純調度重排,任何數值變化都是 bug。
2. criterion `zwtv_10s` 單執行緒自 285.9 ms 降至 ~250 ms(容許 ±10% 機器噪音);多執行緒不劣化。
3. `cargo clippy --all-targets -- -D warnings`、`cargo fmt --check` 乾淨。

> 逐位不變的操作化:golden 測試本身帶容差(對 mosqito),無法偵測 Rust 端重構前後的位元級變化。因此本計畫以 Task 2 的 FNV-1a 雜湊快照(重構前)對 Task 3 的重跑雜湊(重構後)**逐位比對**作為準則 1 的實際看守。

## 已知風險(來自主計畫,對應緩解已排入 task)

| # | 風險 | 緩解(本計畫落點) |
|---|---|---|
| 1 | `calc_slopes_into` 與 `n_only` 對同一幀的 N 存在捨入路徑差 → 分流後 N(t) 在 t%4==0 幀跳動 | Task 1 先寫「兩入口對同一幀輸出 N 逐位相等」的擴充測試(既有 `calc_slopes.rs:218-238` 已覆蓋單一合成幀,擴充至邊界幀 + 200 組決定性隨機幀);**若此測試失敗,停工回報,不得繼續 Task 3** |
| 2 | rayon 分流後兩種工作項混在同一 par 迴圈,槽位寫入錯位 | 合併迴圈維持「每工作項寫互斥槽位」不變式(每工作項獨占 `loudness` 的 4 元素 chunk 與 `spec` 的 240 元素 chunk);Task 3 雜湊比對會抓到任何錯位 |

---

### Task 1: 看守測試——calc_slopes 兩入口 N 逐位一致

**Files:**
- Modify: `iso532/src/core/calc_slopes.rs`(僅 `#[cfg(test)] mod tests` 區塊,約 214 行以後)

- [ ] **Step 1: 在 tests 模組新增擴充看守測試**

在 `calc_slopes.rs` 的 `mod tests` 內、`sample_main_loudness()` 之前加入:

```rust
    #[test]
    fn n_only_matches_into_for_edge_and_random_frames() {
        let mut frames: Vec<[f64; 21]> = vec![
            [0.0; 21],
            spike(0, 8.0),
            spike(10, 8.0),
            spike(20, 8.0),
            ramp(0.0, 10.0),
            ramp(10.0, 0.0),
            alternating(6.0, 0.05),
        ];
        let mut state = 0x1234_5678_9abc_def0_u64;
        for _ in 0..200 {
            let mut frame = [0.0; 21];
            for value in frame.iter_mut() {
                state = state
                    .wrapping_mul(6364136223846793005)
                    .wrapping_add(1442695040888963407);
                *value = (state >> 11) as f64 / (1u64 << 53) as f64 * 12.0;
            }
            frames.push(frame);
        }

        for (idx, nm) in frames.iter().enumerate() {
            let mut spec = [f64::NAN; 240];
            let with_spec = calc_slopes_into(nm, &mut spec);
            let n_only = calc_slopes_n_only(nm);
            assert_eq!(
                n_only.to_bits(),
                with_spec.to_bits(),
                "frame {idx}: n_only={n_only} with_spec={with_spec}"
            );
        }
    }

    fn spike(band: usize, value: f64) -> [f64; 21] {
        let mut frame = [0.0; 21];
        frame[band] = value;
        frame
    }

    fn ramp(from: f64, to: f64) -> [f64; 21] {
        std::array::from_fn(|i| from + (to - from) * i as f64 / 20.0)
    }

    fn alternating(high: f64, low: f64) -> [f64; 21] {
        std::array::from_fn(|i| if i % 2 == 0 { high } else { low })
    }
```

說明:LCG 常數與決定性做法沿用 `tests/simd_parity.rs` 慣例,不引入外部 rng 依賴。`ramp(10.0, 0.0)`(下降斜坡)與 `spike` 會觸發 `mask_n1_bigger_nm` 的斜率延伸分支,這正是兩入口唯一可能分歧的路徑。

- [ ] **Step 2: 執行測試,預期直接通過**

Run: `cargo test -p iso532 --lib calc_slopes`
Expected: PASS(含既有 3 個測試 + 新測試共 4 個)。

依 `calc_slopes_impl` 的結構(`calc_slopes.rs:22-168`),`total` 的累加算式完全不觸碰 `n_specific: Option<…>`,兩入口理論上必然逐位一致——本測試是把這個前提固化為看守。**若 FAIL:主計畫風險 #1 成立,停工回報,先修齊兩入口再回來。**

- [ ] **Step 3: Commit**

```bash
git add iso532/src/core/calc_slopes.rs
git commit -m "test: guard bitwise N equality between calc_slopes entry points"
```

---

### Task 2: 位元級快照工具 + 記錄重構前基線

**Files:**
- Modify: `iso532/tests/golden_zwtv.rs`(檔尾追加)

- [ ] **Step 1: 新增 ignored 雜湊快照測試**

在 `golden_zwtv.rs` 檔尾(`zwtv_end_to_end_matches_mosqito` 之後)加入:

```rust
#[test]
#[ignore = "manual helper: bitwise output snapshot for refactor verification"]
fn dump_zwtv_output_hashes() {
    for sig in ["sine_1k_60", "pulse_1k_70", "step_60_80", "annexb_sig10"] {
        let x = read_bin(sig, "sig.bin");
        let r = loudness_zwtv(&x, 48000.0, FieldType::Free).unwrap();
        println!(
            "{sig}: n={:016x} spec={:016x} time={:016x}",
            fnv1a_f64(&r.n),
            fnv1a_f64(&r.n_specific),
            fnv1a_f64(&r.time_axis),
        );
    }
}

fn fnv1a_f64(values: &[f64]) -> u64 {
    let mut hash = 0xcbf2_9ce4_8422_2325_u64;
    for value in values {
        for byte in value.to_le_bytes() {
            hash ^= u64::from(byte);
            hash = hash.wrapping_mul(0x0000_0100_0000_01b3);
        }
    }
    hash
}
```

此測試永久保留(標 ignore,不進常規測試時間),R4 頻帶平行化等後續「逐位不變」重構同樣受用。輸出逐位決定性已由三個 rayon 平行點皆為純 map 保證,雜湊不受執行緒數影響。

- [ ] **Step 2: 執行快照,記錄重構前雜湊(4 行,共 12 個雜湊值)**

Run: `cargo test -p iso532 --test golden_zwtv dump_zwtv_output_hashes -- --ignored --nocapture`
Expected: PASS,stdout 印出 4 行 `sig: n=… spec=… time=…`。**把 4 行完整貼進工作筆記**,Task 3 Step 3 要逐字比對。

- [ ] **Step 3: 記錄重構前 bench 基線(單執行緒 + 多執行緒)**

Run(單執行緒): `RAYON_NUM_THREADS=1 cargo bench -p iso532 --bench loudness -- zwtv_10s`
Run(多執行緒): `cargo bench -p iso532 --bench loudness -- zwtv_10s`
Expected: 各印出 `zwtv_10s/scalar` 與 `zwtv_10s/avx2` 兩行時間。記錄 avx2 行數字(參考值:單執行緒 ~285.9 ms、多執行緒 ~79.1 ms @ Ryzen 5 3600)。

- [ ] **Step 4: Commit**

```bash
git add iso532/tests/golden_zwtv.rs
git commit -m "test: add ignored bitwise hash snapshot helper for zwtv output"
```

---

### Task 3: 合併兩個平行迴圈,消除重複計算

**Files:**
- Modify: `iso532/src/zwtv/mod.rs:51-70`(`ZwtvProcessor::process` 內)

- [ ] **Step 1: 以合併迴圈取代原本兩段**

將 `zwtv/mod.rs` 中這一整段(第 51–70 行):

```rust
        let nl = nonlinear_decay::nl_loudness(&self.core, n_time);
        self.loudness.resize(n_time, 0.0);
        self.loudness
            .par_iter_mut()
            .enumerate()
            .for_each(|(t, loudness)| {
                let frame: [f64; 21] = std::array::from_fn(|band| nl[band * n_time + t]);
                *loudness = calc_slopes_n_only(&frame);
            });

        let n_out = n_time.div_ceil(4);
        self.spec_time_major.resize(240 * n_out, 0.0);
        self.spec_time_major
            .par_chunks_mut(240)
            .enumerate()
            .for_each(|(out_idx, spec)| {
                let t = out_idx * 4;
                let frame: [f64; 21] = std::array::from_fn(|band| nl[band * n_time + t]);
                calc_slopes_into(&frame, spec);
            });
```

替換為:

```rust
        let nl = nonlinear_decay::nl_loudness(&self.core, n_time);
        let n_out = n_time.div_ceil(4);
        self.loudness.resize(n_time, 0.0);
        self.spec_time_major.resize(240 * n_out, 0.0);
        self.loudness
            .par_chunks_mut(4)
            .zip(self.spec_time_major.par_chunks_mut(240))
            .enumerate()
            .for_each(|(out_idx, (loudness_chunk, spec))| {
                let t0 = out_idx * 4;
                let frame: [f64; 21] = std::array::from_fn(|band| nl[band * n_time + t0]);
                loudness_chunk[0] = calc_slopes_into(&frame, spec);
                for (offset, loudness) in loudness_chunk.iter_mut().enumerate().skip(1) {
                    let frame: [f64; 21] =
                        std::array::from_fn(|band| nl[band * n_time + (t0 + offset)]);
                    *loudness = calc_slopes_n_only(&frame);
                }
            });
```

設計要點(實作時不可偏離):
- `loudness.par_chunks_mut(4)` 的 chunk 數 = `n_time.div_ceil(4)` = `spec_time_major.par_chunks_mut(240)` 的 chunk 數,zip 對齊無截斷;最後一個 loudness chunk 可能不足 4 元素,`iter_mut().skip(1)` 自然處理。
- 每工作項獨占自己的 loudness 4 元素 chunk 與 spec 240 元素 chunk——「每工作項寫互斥槽位」不變式維持(主計畫風險 #2 的緩解)。
- **不得**改動 `calc_slopes.rs` 任何非測試程式碼;`calc_slopes_n_only` 仍被使用,不得移除。
- 兩個 `use` 匯入(`calc_slopes_into`, `calc_slopes_n_only`)維持不變(`zwtv/mod.rs:5`)。

- [ ] **Step 2: 全量測試**

Run: `cargo test -p iso532`
Expected: 全綠(單元 + golden + simd_parity + annexb;其中 `processor_matches_free_function_and_reuses_scratch_capacity` 同時看守 scratch 容量穩定與兩次執行位元一致)。

- [ ] **Step 3: 位元級比對(準則 1 的實際看守)**

Run: `cargo test -p iso532 --test golden_zwtv dump_zwtv_output_hashes -- --ignored --nocapture`
Expected: 4 行輸出與 Task 2 Step 2 記錄的雜湊**逐字相同**(12/12 個值)。**任何一個雜湊不同即為 bug——回退 Step 1 找槽位錯位或幀索引錯誤,不得放寬為「差異很小」。**

- [ ] **Step 4: Commit**

```bash
git add iso532/src/zwtv/mod.rs
git commit -m "perf: fuse zwtv calc_slopes loops, drop duplicate work on spec frames"
```

---

### Task 4: 效能驗證與 lint 收尾

**Files:**
- 無新增修改(僅驗證;若 clippy/fmt 有意見則就地修)

- [ ] **Step 1: 重構後 bench(準則 2)**

Run(單執行緒): `RAYON_NUM_THREADS=1 cargo bench -p iso532 --bench loudness -- zwtv_10s`
Run(多執行緒): `cargo bench -p iso532 --bench loudness -- zwtv_10s`
Expected: avx2 行——單執行緒自基線(~285.9 ms)降至 ~250 ms(容許 ±10% 機器噪音);多執行緒不劣化(criterion 顯示 `No change` 或 `improved`)。若單執行緒改善不足 5%,記錄實測數字回報(不阻擋合入——收益推估本就標註需實測回填),但**多執行緒劣化 >2% 則需回查工作項粒度**。

- [ ] **Step 2: lint 與格式(準則 3)**

Run: `cargo clippy --all-targets -- -D warnings`
Expected: 無輸出(乾淨)。
Run: `cargo fmt --check`
Expected: 無輸出(乾淨)。

- [ ] **Step 3: 收尾 commit(僅在 Step 2 有就地修時)**

```bash
git add -u
git commit -m "chore: clippy/fmt cleanup for calc_slopes dedup"
```

- [ ] **Step 4: 回填實測數字**

把 Task 2 Step 3(前)與 Task 4 Step 1(後)的 bench 數字,回填到 `docs/superpowers/plans/2026-07-05-roadmap-master-plan.md` R1 節驗收準則 2 之後,格式:

```markdown
> **實測回填(YYYY-MM-DD,Ryzen 5 3600):** 單執行緒 <前> → <後> ms;多執行緒 <前> → <後> ms。
```

```bash
git add docs/superpowers/plans/2026-07-05-roadmap-master-plan.md
git commit -m "docs: record R1 measured perf numbers in master plan"
```

---

## Self-Review 紀錄

- **範圍覆蓋:** 主計畫 R1 兩個 Modify 項——`zwtv/mod.rs` 分流合併(Task 3)、`calc_slopes.rs` 確認回傳 N(已確認現況即回傳,`calc_slopes.rs:15`,故無程式碼改動,僅 Task 1 補測試)。三條驗收準則分別落在 Task 3 Step 3、Task 4 Step 1、Task 4 Step 2。兩項風險緩解分別落在 Task 1 與 Task 3 設計要點。
- **無佔位符:** 所有程式碼區塊為完整可貼上內容;所有指令附預期輸出。
- **型別一致:** `calc_slopes_into(&frame, spec) -> f64`、`calc_slopes_n_only(&frame) -> f64` 與 `calc_slopes.rs:9,18` 現行簽名一致;`loudness_chunk: &mut [f64]`、`spec: &mut [f64]` 由 rayon `par_chunks_mut` 推導。

---

## 完成與審查紀錄(2026-07-09)

**狀態:已完成並合入 main**——commits `6fba02f`(Task 1 看守測試)、`99698fc`(Task 2 雜湊快照工具)、`9d8c496`(Task 3 迴圈融合)。

**驗收結果(三準則全數達成,同機無負載 A/B,HEAD worktree 對照):**

| 配置 | 重構前 | 重構後 | 變化 |
|---|---|---|---|
| 單執行緒 AVX2 | 279.1 ms | **244.7 ms** | **−12.3%**(正中 ~250 ms 目標) |
| 多執行緒 AVX2 | 76.5 ms | **69.3 ms** | **−9.4%**(優於推估) |
| 單執行緒 scalar | 577.1 ms | 535.5 ms | −7.2% |
| 多執行緒 scalar | 362.9 ms | 363.0 ms | 無劣化 |

- **準則 1(逐位不變):** 4 訊號 × 3 輸出共 12 個 FNV-1a 雜湊,重構前後逐字相同(`sine_1k_60: n=0b10971021634b4e spec=62496b610f7c223d`、`pulse_1k_70: n=b92a2b970de3067f spec=bdab430b961720f0`、`step_60_80: n=40ac75b0dcaed5a8 spec=2fdc839b4f702621`、`annexb_sig10: n=83da1e1c06d5296c spec=3c2b914686402b54`;`time=f076bcb342595537` 三者共同)。`cargo test` 全綠。
- **準則 3(lint):** clippy `-D warnings` 與 `fmt --check` 乾淨。
- **量測陷阱:** bench 時機器須閒置——背景負載曾造成多執行緒 scalar +3% 的假性劣化,重跑即消失。

**8 角度審查(逐行/移除行為/跨檔/reuse/簡化/效率/altitude/conventions + 逐項對抗驗證):無 correctness bug。** 已套用的審查修正:`zip` → `zip_eq`(槽位對齊不變式由靜默截斷改為 panic 看守,零成本、逐位不變)。

**遺留改善項(不阻擋,供後續 phase 取用):**
1. `nl_loudness` 每次 `process()` 配置 ~3.4 MB Vec,違反 scratch 重用設計——**R5 串流 API 零配置驗收的前置**(`temporal_weighting` 同款)。
2. nl 輸出改 time-major 可同時消除 AVX2 端 strided scatter 與下游 gather(逐位不變;但 scalar 路徑與 golden 測試的 band-major 比對需配套)——可併入 R4 頻帶平行化評估。
3. 4:1 降採樣比在 `zwtv/mod.rs` 四處硬編碼,建議仿 `third_octave_levels.rs` 的 `DEC_FACTOR` 抽常數。
4. 融合迴圈可加 `.with_min_len(16..64)` 降低 rayon 微任務開銷(未經 bench 證實,量級推估 5–20%)。
5. 看守測試值域上限 12,選不到 RNS/USL 表第 0–2 列(需 nm ≥ 15.1,約 100 dB+ 輸入可達);延伸值域過 21.5 是便宜補強。
6. `.gitignore` 的 `AGENTS.md` 條目檔尾無換行。
