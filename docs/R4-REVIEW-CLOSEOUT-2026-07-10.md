# R4 頻帶平行化:審查與收尾報告(2026-07-10)

**階段:** R4 filter_bank / nl_loudness 頻帶平行化(離線吞吐)
**計畫:** `docs/superpowers/plans/phases/phase-r4-band-parallel.md`(含完整審查紀錄)
**實作:** Codex(依 phase 計畫);**審查與收尾:** Claude
**結論:TL;DR — 四項驗收全數通過、無正確性缺陷;三項流程/契約缺口已全採上策修復並收尾進版。**

---

## 1. 審查結論

8 角度審查(逐行、移除行為稽核、跨檔追蹤、重用、簡化、效率、altitude、慣例)+ 全套實證驗證,**未發現任何正確性缺陷**。移除行為稽核逐一比對舊/新 kernel 的每個係數載入、FP 指令序列與遞減條件,回報零候選;雜湊實證與其結論一致。

### 驗收準則:4/4 通過

| 準則 | 結果 |
|---|---|
| 1. golden 逐位不變 | ✅ `dump_zwtv_output_hashes` 12/12 雜湊與 R1 記錄逐字相同 |
| 2. simd_parity 不變 | ✅ 全綠(改走 `ParMode::Sequential` 臂) |
| 3. 效能(MT 45–55 ms;ST ≤2%) | ✅ 見下表,同日 A/B 實測 |
| 4. 決定性 20 次跑逐位相同 | ✅ 通過(auto + forced-scalar 雙路徑) |

### 效能實測(Ryzen 5 3600;同日 A/B:`git worktree` 檢出 R1 9d8c496 當場重量基線)

| 項目 | R1 基線 | R4 | 變化 | 判定 |
|---|---|---|---|---|
| zwtv_10s MT AVX2 | 74.2 ms | **52.2 ms** | **−30%** | ✅ 落在 45–55 ms 目標區間 |
| zwtv_10s ST AVX2 | 249.0 ms | 252.8 ms | +1.5% | ✅ ≤2% |
| zwtv_10s ST scalar | 553.9 ms | 558.0 ms | +0.7% | ✅ ≤2% |
| filter_bank_10s ST AVX2 | 21.6 ms | 24.3 ms | +2.7 ms | 歸因:tol 迴圈互換(1 趟→7 趟掃訊號)實測成本,攤到管線 +1.1%,預算內 |
| zwtv_10s MT scalar | (無同日基線) | 139.5 ms | 歷史參考 ~136.5 ms | 無硬性目標 |

**量測方法學教訓(已寫入主計畫 X2 慣例):** 對 R1 歷史數字直比會得到 ST +3~5% 假警報——連本次未改動的 scalar ST 路徑都「劣化」4%,證明跨日機器條件不可比。**緊預算驗收(如 ST ≤2%)必須同日同機 A/B**:worktree 檢出基準 commit 當場重量。

### 風險核對:9 項中 6 項確實避開,3 項部分(現已全數關閉)

| # | 風險 | 審查時狀態 | 收尾後 |
|---|---|---|---|
| 1 | L3 頻寬競爭 → 收益縮水 | ✅ 已實測(MT −30%;tol +2.7 ms 被吸收,「回報不重工」適用) | — |
| 2 | false sharing | ✅ `par_chunks_mut` 連續互斥切片 | — |
| 3 | rayon 巢狀 / R5 須 Sequential | ⚠️ ParMode 就位但註解遺漏 R5 契約文字 | ✅ 註解已補 |
| 4 | 群組狀態誤共享 | ✅ 狀態全為 kernel 區域變數 | — |
| 5 | `chunks_mut(0)` panic | ✅ 四路徑守衛齊全 | — |
| 6 | `#[target_feature]` × rayon closure | ✅ 屬性僅存於含 intrinsics 的 kernel | — |
| 7 | scalar 平行暫態記憶體 | ⚠️ 行為如計畫接受,但離線限定註記未寫入 | ✅ 註記已補 |
| 8 | FORCE_SCALAR race | ✅ 單一 `#[test]` 獨立 binary | — |
| 9 | Sequential 臂 bit-rot | ⚠️ 等價斷言被 `use_rayon` 計畫外條件在 1 緒環境架空 | ✅ 已回歸純 match |

---

## 2. 三項議題的決策與執行(全採上策)

### 議題 1:`use_rayon()` 計畫外條件 → 回歸純 `match mode`

Codex 在 `use_rayon()` 加了計畫外的 `rayon::current_num_threads() > 1`,使 `ParMode::Rayon` 在 1 緒 pool 靜默走 Sequential 臂——determinism 的雙臂等價斷言(R5 前置契約)在 `RAYON_NUM_THREADS=1` 環境空洞化,且平行程式碼路徑無法強制。

**執行:** 移除該條件(`use_rayon` = `mode == ParMode::Rayon`,並由 `pub(super)` 收斂為私有);ParMode 註解補上計畫指定的 R5 契約文字與暫態記憶體警告。**驗證:** 全測試綠、12/12 雜湊不變、clippy/fmt 乾淨;ST AVX2 253.6 ms 對修改前 252.8 ms 統計上無變化(p = 0.46)——證實原檢查的「效能保護」實際價值為零(1 緒 pool 上 6–7 個 chunk 的 rayon 派工開銷是 µs 級)。

### 議題 2:commit 結構 → 分段進版,逐 commit 驗證

實作原堆在未提交工作區,計畫的 5 commit / 4 雜湊檢查點未建。**執行:** 按階段拆 4 個 commit,每個 commit 的樹獨立以 worktree 檢出跑全測試 + 雜湊比對:

| Commit | 內容 | 對應計畫 |
|---|---|---|
| `a16b41f` perf: band-parallel third_octave_levels behind ParMode | tol 迴圈互換 + ParMode + 平行化;simd_parity tol 行 | Task 2+3(合併) |
| `0aff1bf` perf: band-parallel nl_loudness behind ParMode | nl 群組切片改寫 + 平行化;simd_parity nl 行 | Task 4+5(合併) |
| `9158f98` test: add 20-run bitwise determinism guard | determinism.rs + fnv1a_f64 搬遷 | Task 1 |
| (本 commit)docs | 主計畫回填 + phase 計畫(含審查紀錄)+ 本文件 | Task 6 Step 3 |

**已知偏差(事後補提交的固有限制,commit 訊息內註明):** tol 的「互換」與「翻平行」已是同函式終態,無法拆回計畫原設計的兩步,4 個檢查點恢復為 2 個;測試 commit 後進(計畫要求先行的意義在實作期看守,事後補提交僅影響歷史敘事)。

### 議題 3:Task 6 文件回填 → 完成並制度化方法學

主計畫 R4 節已回填上表實測數字;X2 慣例(單機基準噪音)擴充納入「同日 A/B(worktree)」硬性要求;phase 計畫文件尾附完整審查紀錄。

---

## 3. 遺留清理項(低優先,建議 R5 前順手處理)

1. **`nl_group_avx2` 尾帶以切片長度推斷**(`nonlinear_decay.rs`):「短 chunk = 恰 1 帶」僅因 21 % 4 == 1 成立;改傳明示帶數參數更穩。
2. **排程樣板 4 處重複**(tol/nl × scalar/avx2):可收斂為 `zwtv/mod.rs` 內單一 `chunks_dispatch` helper;附帶統一 `n_time==0` 守衛的 3 種寫法。R5 若平行化第 5 個階段前先做此項。
3. **測試配方重複**:`synth_core`(determinism ↔ simd_parity)與 `synth_signal`(determinism ↔ bench)可下沉 `tests/common`。

## 4. R5 交接備註

- `ParMode` 即 R5 串流的排程契約:**音訊路徑必須 `Sequential`,不得觸發 thread pool**;determinism 測試的 Rayon/Sequential 逐位等價斷言就是這條契約的看守。
- scalar 後備路徑在 Rayon 模式的暫態配置隨執行緒數放大(10 s @12 緒:tol ~46 MB、nl ~138 MB),僅限離線;R5 scratch 化根治。
- `ZwtvProcessor::process` 的 calc_slopes 融合迴圈目前無 ParMode 臂(R4 範圍外);R5 串流化時一併決定 `process_with_mode` 的形狀。
