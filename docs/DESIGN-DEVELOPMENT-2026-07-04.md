# ISO 532-1 Rust + AVX2 設計發展文件

**日期：** 2026-07-04
**基準版本：** commit `ad83515` + 工作副本架構優化（ZwtvProcessor / rayon / calc_slopes 拆分，尚未 commit）
**量測環境：** AMD Ryzen 5 3600（6 核 12 緒，AVX2+FMA，無 AVX-512）、Windows 10、rustc release profile。Python 對照組：mosqito 1.2.1 + numpy，同一台機器。
**原則：** 本文件所有數字皆為本機實測值，無估計值；分析推論處會明確標示「推估」。

---

## 1. 目的與範圍

本文件審查 `iso532` crate 在第二輪架構優化（`ZwtvProcessor` scratch 重用、`calc_slopes` N-only/into 拆分、spec 降採樣為每 4 幀、rayon 幀平行、tol 轉置）落地後的：

1. 量化誤差（對 mosqito golden、AVX vs scalar）
2. 對 Python 的效能提升量
3. Rust+AVX2+FMA 加速倍率
4. 進一步優化的最大潛力上限
5. 長時間運作穩定性設計現況
6. 隱性穩定性缺陷清單與對策
7. 未來對接其他響度／心理聲學標準的架構準備

驗證狀態：31 項測試 + 2 doctests 全綠（含 golden 端對端、simd_parity、annexb），`cargo clippy --all-targets -- -D warnings` 與 `cargo fmt --check` 乾淨。

---

## 2. 現況架構摘要

```
signal (48 kHz f64)
  └─ third_octave_levels        28 頻帶 IIR 濾波器組，AVX2: 7×f64x4，逐樣本推進，DEC_FACTOR=24 → 2 kHz 幀網格   [序列]
  └─ 轉置 tol → frame-major     28 筆連續讀取取代 28 次跨步 gather                                              [序列]
  └─ main_loudness_frames_into  每幀 28→21 帶核心響度，rayon par_chunks_exact(28)                              [幀平行]
  └─ nl_loudness                21 帶 × 24 虛擬子步非線性衰減遞迴，AVX2: 5×f64x4 + 1 帶 scalar                  [序列·時間遞迴]
  └─ calc_slopes_n_only         每幀總響度 N（不物化 240 點 spec），rayon par_iter_mut                          [幀平行]
  └─ calc_slopes_into           僅 t%4==0 幀物化 240 點 specific loudness，rayon par_chunks_mut                 [幀平行]
  └─ temporal_weighting         0.47·LP(3.5ms) + 0.53·LP(70ms) 時間遞迴                                        [序列·時間遞迴]
  └─ 每 4 幀降採樣 → 2 ms 輸出網格（N、N_specific、time_axis）
```

`ZwtvProcessor` 持有 4 條 scratch buffer（tol 轉置、core、loudness、spec_time_major），重複呼叫零重配置（有容量守恆測試）。`loudness_zwtv()` 免費函式為一次性包裝。輸出維持扁平 row-major `Vec<f64>`（為 C-ABI 鋪路）。

---

## 3. 量化誤差（2026-07-04 實測，9 組 golden 資料集）

架構優化後全數重測（`calc_slopes` 經過重構，不沿用舊數據）。結果與優化前完全一致——重構未改變任何數值語意。

### 3.1 對 mosqito golden（AVX2 路徑，端對端）

| 項目 | 最大絕對誤差 | 最大相對誤差 | 備註 |
|---|---|---|---|
| zwst 總響度 N | **0（精確相等）** | 0 | 9/9 資料集；mosqito 對 N 做小數 3 位捨入，兩邊捨入後逐位一致 |
| zwst N_specific（240 點） | 8.2e-14 | 2.9e-12 | 最差：sine_250_80 |
| zwtv N(t) | 1.6e-14 | 3.8e-15 | 最差：annexb_sig5 |
| zwtv N_specific(t) | 1.3e-9 | 3.0e-9 | 最差：step_60_80（位準階躍，落在 calc_slopes r8 捨入邊界） |

### 3.2 AVX2 vs scalar（同輸入端對端）

| 項目 | 最大絕對誤差 | 最大相對誤差 |
|---|---|---|
| zwtv N(t) | **0（9/9 位元一致）** | 0 |
| zwtv N_specific(t) | 1.4e-9 | 3.2e-9 |

N(t) 位元一致的原因：總響度在 calc_slopes 末端經 1/1000 sone 量化（≤16 sone 時），吸收了 FMA 合併造成的 ULP 級差異。N_specific 無此量化，1e-9 級差異源自 step 訊號在 `r8()`（1e-8 捨入）邊界上的分支選擇不同，屬預期且有 golden 測試看守上界。

### 3.3 結論

全部誤差都在感知無意義的量級（sone 顯示解析度為 1e-3）。設計上的正確性雙保險——(1) golden 端對端測試鎖對 mosqito 的偏差、(2) simd_parity 測試鎖 AVX 對 scalar 的偏差——在本輪重構後依然全數成立。

---

## 4. 效能：對 Python 提升量與加速倍率（實測）

### 4.1 criterion 基準（10 秒三正弦訊號，480k 樣本）

| 基準 | scalar | AVX2 | AVX2 加速 |
|---|---|---|---|
| filter_bank_10s（單執行緒，無 rayon 參與） | 241.4 ms | 20.1 ms | **12.0×** |
| zwtv_10s 全管線（rayon 預設 12 緒） | 397.9 ms | **79.1 ms** | **5.03×** |
| zwtv_10s 全管線（RAYON_NUM_THREADS=1） | 598.8 ms | 285.9 ms | 2.09× |

（Codex 於 README/`docs/bench-results.txt` 記錄的 77.6 ms / 388.6 ms 為同日另一輪執行，差異在執行間噪音範圍內。）

### 4.2 歷次優化軌跡（zwtv AVX2，10 秒訊號）

| 里程碑 | 時間 | 相對前一輪 |
|---|---|---|
| Phase 5 初版 | 387.6 ms | — |
| + nl target_feature／尾帶修正（`ad83515`） | 258.8 ms | -33% |
| + 本輪架構優化（多執行緒） | **79.1 ms** | -69% |
| 累計 | | **4.9×** |

### 4.3 對 Python（mosqito 1.2.1，同機實測 22.365 s / 10 s 訊號）

| 模式 | Rust 時間 | 對 Python 加速 | 即時倍率 |
|---|---|---|---|
| 多執行緒（12 緒） | 79.1 ms | **283×** | 126× |
| 單執行緒 | 285.9 ms | 78× | 35× |

Python 端連即時的一半都跑不到（0.45× 即時）；Rust 端單執行緒即有 35× 即時餘裕。

### 4.4 即時預算與多軌擴展（以單執行緒數字計，每軌佔一核）

- 每 2 ms 輸出幀攤提成本：285.9 ms ÷ 5000 幀 = **57.2 µs/幀** → 200 µs 預算內，餘裕 **3.5×**
- 單核可承載 2000 ÷ 57.2 ≈ **35 軌**；6 實體核理論 ~210 軌、保留 30% 餘裕實務 **~147 軌**
- 64 軌 VST 目標僅佔本機約 **30%** 算力

注意：單執行緒 285.9 ms 比上一輪的 258.8 ms 略退步（+10%），原因見 §5.2 第 1 點，屬已知且可修復的取捨。

---

## 5. 階段剖析與最大潛力上限

### 5.1 各階段實測（10 秒訊號，AVX2 路徑，3 次取中位）

| 階段 | 單執行緒 | 12 緒 | 平行放大 | 屬性 |
|---|---|---|---|---|
| filter_bank | 19.6 ms | 19.6 ms | 1×（未平行） | 序列掃描；頻帶獨立 |
| tol 轉置 | 1.0 ms | 1.0 ms | — | 記憶體搬移 |
| main_loudness | 48.5 ms | 8.8 ms | 5.5× | 幀獨立 |
| nl_loudness | 17.4 ms | 17.5 ms | 1×（未平行） | 時間遞迴；**頻帶獨立** |
| calc_slopes N-only（全幀） | 148.5 ms | 16.0 ms | 9.3× | 幀獨立 |
| calc_slopes spec（每 4 幀） | 38.6 ms | 4.9 ms | 7.9× | 幀獨立 |
| temporal_weighting | 1.8 ms | 1.9 ms | — | 時間遞迴 |
| **合計** | **275.4 ms** | **69.7 ms** | 4.0× | criterion 含配置/組裝為 285.9/79.1 |

多執行緒下瓶頸已完全換位：**幀平行階段全部被壓扁，剩下兩個未平行的序列階段 filter_bank（25%）與 nl_loudness（22%）合佔近半**，構成目前的 Amdahl 地板（約 40 ms）。

### 5.2 剩餘優化空間（按預期收益排序；標示為推估，落地後需實測）

1. **消除 calc_slopes 重複計算（單執行緒 -37 ms，推估）**：目前 `calc_slopes_n_only` 跑全部幀、`calc_slopes_into` 又對 t%4==0 幀重算一次——每 4 幀有 1 幀算兩遍。`calc_slopes_into` 本身回傳 N，讓 t%4==0 幀只走 into、其餘走 n_only 即可。單執行緒可望回到 ~250 ms 以下，多執行緒省 ~4 ms。零數值風險。
2. **filter_bank 頻帶平行（多執行緒 19.6→~4 ms，推估）**：7 個 f64x4 向量群組互相獨立，各自完整掃一次訊號，rayon 分 7 工即可。每群組讀 3.84 MB 訊號，L3（32 MB）內可共享。時間遞迴只存在於「同頻帶內」，跨頻帶無依賴，語意零風險。
3. **nl_loudness 頻帶群組平行（多執行緒 17.4→~4 ms，推估）**：同理，5 個 4 帶群組 + 1 個 scalar 尾帶互相獨立，rayon 分 6 工。時間遞迴在帶內，跨帶無依賴。
4. 落地 1–3 後多執行緒地板推估 ~**25–30 ms**（10 秒訊號）≈ **330–400× 即時**；此後的上限由記憶體頻寬與 2 kHz 網格上不可省略的逐子步遞迴（24 子步 × 20k 幀）決定，繼續壓榨需換演算法或換平台向量寬度（AVX-512 f64x8 於 Zen 4+ 可再翻倍 filter bank 與 nl；Apple M 系列 NEON f64x2 見 ROADMAP §5）。
5. **串流模式的單幀成本**與批次攤提不同：串流時 rayon 不參與（單幀無平行空間），有效成本即單執行緒 57.2 µs/幀，落地第 1 點後推估 ~50 µs。真正的 64 軌 VST 吞吐靠「軌間平行」（每軌一核）而非幀內平行——這也是為什麼本文件的多軌數學全部採單執行緒數字。

---

## 6. 長時間運作穩定性設計現況

針對「連續運作數小時～數天」（VST 場景）審查現有設計，先列已經站得住的部分：

1. **所有遞迴皆為收縮映射**：濾波器組 biquad 極點在單位圓內、三級平滑與 temporal weighting 的 `a1 = exp(-1/(fs·τ)) < 1`、nl 網路係數 `b[4], b[5] = exp(-Δt/τ) < 1`。狀態有界且對初值指數遺忘，不存在無界累積或漂移路徑。
2. **無累積型計時變數**：`time_axis` 由幀索引推導（`i·24/48000`），不是累加浮點時間戳，長時間運作無精度衰減問題。
3. **零重配置的持久物件**：`ZwtvProcessor` scratch 容量守恆有測試看守；重複呼叫不增長記憶體（nl 與 temporal_weighting 內部仍有每呼叫配置，見 §7-P1）。
4. **rayon 平行是決定性的**：三處 par 迴圈皆為「每工作項寫入互斥槽位」或「保序 collect」，無歸約順序依賴——同輸入永遠同輸出（本次實測 Processor 重複呼叫與免費函式逐位相等、AVX 執行間 N(t) 位元一致，皆佐證）。
5. **全域可變狀態僅一處**：`FORCE_SCALAR`（AtomicBool，測試/基準專用），不影響正確性、僅影響路徑選擇。

---

## 7. 隱性穩定性缺陷清單與對策

依「進入即時/串流場景前必須處理」分級。**現行批次離線用途下這些都不是錯誤**（全部測試綠、誤差達標），它們是切換到長時間即時運作時會浮現的隱患。

### P0 — 串流 API 落地前必須解決

| # | 缺陷 | 機制 | 對策 |
|---|---|---|---|
| 1 | **Denormal 失速** | 靜音段輸入下，平滑濾波器與 nl 狀態指數衰減進入 f64 denormal 區；x86 上 denormal 運算需微碼輔助，單次可慢數十倍。`TINY=1e-12` 只加在 log10 輸出端，濾波器狀態本身未受保護。離線=變慢；即時=**錯過 deadline**。 | kernel 作用域設定 MXCSR FTZ/DAZ（AVX 路徑），或狀態沖洗（`|state| < 1e-30 → 0`）。scalar 路徑用狀態沖洗。加「長靜音段吞吐不退化」的迴歸測試。 |
| 2 | **NaN/Inf 無輸入防護** | 單一 NaN 樣本經 IIR 遞迴永久毒化狀態。批次呼叫汙染一次結果即結束；串流下狀態**永不恢復**。 | 串流入口逐 chunk 檢查（`is_finite` 掃描成本遠低於濾波本體），遇非有限值：清零該樣本並計數回報，或重置狀態。批次 API 維持現狀（文件註明 GIGO）。 |
| 3 | **非因果初始化與前視** | (a) nl 初始狀態讀「最後一幀的最終虛擬子步」（wraparound，復刻 mosqito）；(b) nl 與 temporal_weighting 的子步內插讀 `loudness[t+1]`——前視一幀。串流時看不到未來也看不到結尾。 | 設計決策需明文化：前視改為固定 **1 幀（0.5 ms）演算法延遲**；wraparound 初始化改為零初始（僅影響開頭暖機段，與 golden 的差異限定在前幾幀，需定義驗收準則並補串流專屬 golden）。 |
| 4 | **mid-stream 錯誤中止語意** | `main_loudness` 遇任一幀低頻帶 >120 dB 即回傳 Err，`collect::<Result>` 使**整段批次失敗**。即時場景一個爆音幀不能讓量測器死掉。 | 串流 API 改為逐幀策略：夾限至 120 dB 並在結果標記 flag，不中止。批次 API 維持 ISO 合規的硬錯誤。 |

### P1 — 影響即時素質，串流重構時一併處理

| # | 缺陷 | 機制 | 對策 |
|---|---|---|---|
| 5 | **熱路徑殘餘配置** | `nl_loudness` 每呼叫配置輸出 Vec；scalar 帶 helper 每帶配置 3 條 `24·n_time` 向量（10 秒訊號約 11.5 MB 暫態）；`temporal_weighting` 配置 2 條 Vec。音訊執行緒禁止配置。 | 移入 `ZwtvProcessor` scratch；串流版按 chunk 尺寸預配。 |
| 6 | **rayon 全域執行緒池** | 程式庫隱式起 thread pool；VST host 中音訊執行緒不可觸發執行緒建立，且多實例共享池造成吞吐耦合。 | 串流路徑天然不走 par 迴圈（單幀無平行空間），需以 API 設計保證；離線路徑可選 `ThreadPool` 注入。 |
| 7 | **panic 作為內部契約** | 形狀 assert 在 Rust 內安全，但 panic 穿越 C-ABI 是 UB；rayon 工作項 panic 會傳播中止整次呼叫。 | FFI 層全面 `catch_unwind` 映射錯誤碼（ROADMAP §4 已預留 `Iso532Error`→錯誤碼）。 |

### P2 — 已知且接受，記錄在案

| # | 事項 | 說明 |
|---|---|---|
| 8 | `r8()` 1e-8 捨入 + RNS 線性掃描 | 忠實復刻 mosqito 分支語意（parity 的代價）；step 類訊號在捨入邊界產生 1e-9 級 N_specific 偏差，有 golden 上界看守。RNS 掃描每幀每帶 O(18)，效能上非熱點。 |
| 9 | `FORCE_SCALAR` 為行程級全域 | 同行程兩個使用者互相干擾。定位為測試/基準工具，文件註明不供產品邏輯使用。 |
| 10 | 批次 API 記憶體與訊號長度成正比 | 10 秒訊號峰值工作集約 100 MB 級（含 core/nl/spec）。長錄音應分段或等串流 API。 |

---

## 8. 未來標準對接審查

現行分層（`dsp/` 通用 DSP、`core/` ISO 532-1 專屬、`zwst`/`zwtv` 編排、`tables*` 生成物）對擴充是乾淨的，逐項評估：

| 標準 | 可複用 | 需新增 | 架構阻力 |
|---|---|---|---|
| **sharpness（DIN 45692）** | 直接消費 `n_specific`（240 點已完整輸出） | 加權積分函式 + `sone2phone` | 無——最低垂的果實 |
| **ISO 532-2（Moore-Glasberg）** | golden 驗證方法、誤差框架、輸出結構 | FFT 前端 + ERB 尺度（與 Bark 完全不同的濾波路徑） | 低；`dsp/` 加 FFT 模組（rustfft） |
| **ECMA-418-2（Sottek）** | 同上 + 部分 IIR 基建 | hearing model 濾波器組、調變分析 | 低-中 |
| **roughness / fluctuation strength** | specific loudness 時間序列 | 調變深度分析 | 一個介面注意點：現行 zwtv 只在每 4 幀（500 Hz 網格）物化 spec；調變分析若需 2 kHz 全速率 spec，`calc_slopes_into` 保留了全速率能力，屆時以參數開啟即可，**不要移除全速率路徑** |

結構性建議（時機：第二個標準動工時，非現在）：

1. **workspace 化**：`dsp-core` / `iso532-1` / `<新標準>`，ROADMAP §1 已預留；現行模組邊界已按此切，屆時是搬移不是重構。
2. **串流 trait 統一**：`LoudnessStream`（`push(&mut self, chunk) -> Option<Frame>`）設計成標準無關的 trait，zwtv 是第一個實作者，後續時變指標（roughness 等）沿用同一介面——VST 端只認 trait。
3. **輸出結構維持扁平 row-major `Vec<f64>`**：C-ABI/numpy 零拷貝的前提，任何新標準的輸出都遵循此約定。

---

## 9. 發展路線建議（優先序）

1. ~~**calc_slopes 重複計算修正**（§5.2-1）~~——**已完成（2026-07-09，R1）**：單執行緒 AVX2 279.1 → 244.7 ms（−12.3%）、多執行緒 76.5 → 69.3 ms（−9.4%），輸出逐位不變（12/12 雜湊相同）。審查與實測紀錄見 `docs/superpowers/plans/phases/phase-r1-calc-slopes-dedup.md`。
2. **串流 API 重構**（P0 全部 + P1-5/6）——VST 前置條件，含 denormal 防護、NaN 防護、1 幀延遲語意定案、逐幀錯誤策略、零配置。此項落地前不要動 VST。
3. **filter_bank / nl 頻帶平行**（§5.2-2/3）——離線吞吐再 2.3–2.8×（推估），與串流工作正交可並行。
4. **C-ABI + Python binding**——驗證便利性高，`Iso532Error` 與扁平輸出已就緒（ROADMAP §4）。
5. **zwst ISO 參考濾波器組模式**（§10.2）——重用 zwtv 前端，把穩態對 ISO 基準偏差從 ±0.8% 壓到量化底線；獨立小項，可隨時插入。
6. sharpness → 其他標準（§8 順序）。

---

## 10. ISO 532-1 基準值逼近分析（2026-07-04 實測）

前述 §3 的誤差都是「對 mosqito」的相容性誤差；本節回答另一個問題：**mosqito（=本 crate）對 ISO 532-1 官方基準值的殘餘偏差在哪裡、為何存在、能否修正**。基準資料：`data/annexb/` 的 Annex B 官方測試訊號、參考 CSV（240 點 N′ 曲線）與時變 xlsx（N(t) 參考曲線 + ±5% 容差帶）。

### 10.1 偏差實測（工具 `iso_gap_report`，scratchpad 保存）

| 測試訊號 | 涵蓋階段 | 我方 N | ISO 定值 | 偏差 |
|---|---|---|---|---|
| Signal 1（直接給定 28 頻帶位準） | 僅 main_loudness + calc_slopes | 83.300 | 83.296 | **+0.005%**（= 輸出量化步階） |
| Signal 3（1 kHz 60 dB wav，44.1k→48k） | zwst 全管線 | 4.052 | 4.019 | **+0.82%** |
| Signal 5（粉紅噪 60 dB wav） | zwst 全管線 | 10.418 | 10.498 | **−0.76%** |
| Signal 10（1 kHz 音脈衝 10 ms 70 dB） | zwtv 全管線 | N(t) max abs 2e-4 sone | 官方曲線 | **0/500 點超出 ±5% 帶**；N′(8.5 Bark) max abs 1e-4 |

三項結論：

1. **響度轉換級（main_loudness + calc_slopes）對 ISO 基準幾乎精確**：Signal 1 偏差 0.005%，且 83.300 vs 83.296 的差恰為 >16 sone 時 1/100 sone 的輸出量化步階；N′ 曲線 max abs 3e-4（0/240 違反容差）。數學式本身沒有逼近缺陷。
2. **zwtv 時變管線對官方參考曲線幾乎精確**：max abs 2e-4 sone、平均帶符號誤差 −0.00000。因為 zwtv 前端的 28 頻帶濾波器組是照 ISO 參考程式（BASIC/C 附錄 A）的係數移植的。
3. **殘餘偏差全部集中在 zwst 的頻譜前端**：Signal 3/5 的 ±0.8% 完全來自 mosqito 用 scipy Butterworth（IEC 61260 風格）濾波器組 + decimate + 全段 RMS 計算三分之一倍頻程位準，而 ISO 基準值是用標準自帶的參考濾波器組產生的。約 0.1 dB 的頻帶位準差即對應此量級的響度差；這在 IEC 61260 class 1 容差遮罩內，屬「合規但不同」的實作自由度，不是 bug。Signal 3 另外疊加 44.1→48 kHz 重採樣漣波。

### 10.2 修正可行性（已實驗驗證）

把 zwst 前端換成**已移植的 ISO 參考濾波器組**（`zwtv::third_octave_levels`，跳過前 0.5 s 暫態後對頻帶強度取時間平均，再走同一轉換級）：

| 訊號 | mosqito 路徑 | ISO 濾波器組路徑 |
|---|---|---|
| Signal 3 | 4.052（+0.82%） | 4.020（**+0.025%**，剩 1 個 0.001 sone 量化步階 + 重採樣殘留） |
| Signal 5 | 10.418（−0.76%） | 10.498（**+0.000%，精確命中**） |

即：**修正可能，且不需要新演算法**——重用現有 zwtv 前端即可把穩態偏差從 ±0.8% 壓到量化底線。實作建議：

1. 新增 `loudness_zwst_iso`（或 `ZwstMode::IsoReference` 參數）走 ISO 濾波器組路徑；**保留現行 mosqito 路徑為預設**以維持 golden 相容性（§3 的位元級一致驗證體系不能破壞）。
2. 暫態處理需定案：本實驗跳過前 0.5 s；正式實作應以濾波器組穩定時間（最長時間常數約 ~0.1 s 量級）定義丟棄窗並寫入文件。
3. 44.1 kHz 輸入的殘留 +0.025% 來自重採樣品質，屬次要；若要求更緊可換高階 sinc 重採樣器再量測。
4. 天花板認知：ISO 532-1 合規定義是 ±5%/0.1 sone 容差而非位元一致，官方基準值本身由參考程式（單精度 BASIC 年代）產生；量化步階（≤16 sone 為 0.001、>16 sone 為 0.01）是任何實作的逼近下限。目前修正路徑已達此下限。

---

## 11. 附錄：量測方法

- **誤差**：`err_report`（scratchpad 保存）對 `data/golden/` 9 組資料集端對端比對，max-abs / max-rel（分母 >1e-9 才計 rel）。
- **效能**：criterion `benches/loudness.rs`（sample_size 10），10 秒三正弦訊號；單執行緒以 `RAYON_NUM_THREADS=1` 固定。
- **階段剖析**：`stage_profile`（scratchpad 保存）複製 `ZwtvProcessor::process` 逐階段插 `Instant`，3 次取中位。
- **Python**：mosqito 1.2.1 `loudness_zwtv`，同訊號 3 次取中位（2026-07-02 實測 22.365 s）。
- **ISO 基準逼近**：`iso_gap_report`（scratchpad 保存）對 `data/annexb/` 官方參考值比對；Signal 1 輸入位準取自 ISO 532-1 Annex B.2（經自我驗證：算出 N 命中 ISO 定值 83.296 至量化步階、N′ 曲線 0/240 違反容差）。
