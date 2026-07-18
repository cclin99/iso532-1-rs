# R5 第三輪審查修正清單（2026-07-18）

> 交接對象：Codex。審查範圍：工作樹中針對 `docs/R5-REVIEW-2-FIXES-2026-07-17.md` 的修復（未 commit，基於 3254bde）。
> 方法：8 角度 finder → 23 個去重候選 → 每項獨立驗證 → **14 CONFIRMED / 3 PLAUSIBLE / 6 REFUTED**。
> 總評：**修復品質良好**。P1 效能目標經驗證確實達成（chunk 層級 `#[target_feature]` 內聯路徑打通、緩衝清零移入 emit 分支、reset 零配置、DenormalGuard 已刪、guarded_or 只包冷路徑）；第二輪 21 項均有處理。以下是修復本身引入或遺留的問題。
> 全域約束不變：workspace 測試全綠 + hash gate 12/12 逐位不變 + C ABI 僅加法。

---

## P0 — commit 前必修

### 1. py `sone2phon` 的 NaN 仍然靜默通過（第二輪項④修復不完整）

`iso532-py/src/lib.rs:85` 的防護 `if n < 0.0` 在 IEEE-754 下對 NaN 為 false，`iso532.sone2phon(float('nan'))` 仍靜默回傳 NaN（`+inf` 也通過並回傳 `inf`）——這正是項④要消除的行為模式。

**修法**：防護改為 `if !(n >= 0.0)`（同時涵蓋負值與 NaN；`inf` 視需求另議，建議一併 `if !n.is_finite() || n < 0.0`）。`iso532-py/tests/test_smoke.py` 現只測 `-0.001`，補 `float('nan')`（及 `inf` 若擋）預期 `ValueError` 的案例。Rust 核心不動（已驗證公式未被改動，維持 spec parity）。

### 2. 非 x86_64 建置的 unused-variable 警告（R7 前置雷）

`iso532/src/zwtv/stream.rs:107-130`：`new_tol_stage(avx2: bool)` 與 `new_nl_stage(.., avx2: bool)` 只在 `#[cfg(target_arch = "x86_64")]` 分支消耗參數；模組本身無架構閘（`lib.rs` 無條件 `pub mod zwtv`，且已有 aarch64 fallback 與 `TODO(R7)` 註記），aarch64 配 `-Dwarnings` 直接建置失敗。

**修法**：兩個建構子各補一行 `#[cfg(not(target_arch = "x86_64"))] let _ = avx2;`（或參數改 `_avx2` 並在 x86_64 分支 alias）。一行修，零風險。

### 3. MXCSR 測試重排序：覆蓋縮窄 + 無註解的隱形順序約束

`iso532/tests/stream.rs:228`：`push_and_flush_restore_mxcsr` 把 `ZwtvStream::new` 移到 `_mm_getcsr` 基準快照之前。**實測驗證**：new() 的係數 sqrt/exp 計算會置位 sticky inexact bit（0x1f80→0x1fa0），恢復自然的基準先行順序測試即失敗。後果：(a) new() 不再有「不改動呼叫端 MXCSR」的看守——未來若 new() 回歸殘留 FTZ/DAZ 控制位（DenormalGuard 防的正是這類 bug），測試依然全綠；(b) 未來有人把測試整理回自然順序會遇到無法理解的失敗。

**修法**（擇一，建議 a）：
- (a) 快照回到 new() 之前，比較時遮罩掉 sticky status bits、只比對 FTZ/DAZ 與控制位：`assert_eq!(before & !0x3f, after & !0x3f)`（低 6 位為 sticky status flags）。這同時恢復 new() 覆蓋並允許自然順序。
- (b) 保持現順序，但必須加註解說明 new() 合法弄髒 sticky status bits、刻意排除在 guard 契約外。

### 4. reset() 缺欄位窮舉保護，flush→reset→push 復原路徑零測試覆蓋

`iso532/src/zwtv/stream.rs:283-310`：reset() 用具名欄位逐一清零、無 `let Self {..}` 窮舉解構。唯一測試 `reset_matches_a_new_stream` 的前置狀態恰好全在預設值（4800%24==0 → sample_phase 已是 0；乾淨訊號 → pending 空；未 flush → flushed false），已驗證刪掉 `self.flushed = false` 或 `self.sample_phase = 0` 全套測試照樣綠。而 header 文件承諾的 flush 後 reset 復原路徑完全沒被測過。

**修法**：
- reset() 改為窮舉解構 `let Self { field: _, tol, nl, tw, sample_phase, ... , flushed } = self;`（**不用 `..`**），新增欄位即編譯錯誤。順帶：push() 的解構尾端有 `..`，一併補齊。
- 新增測試：push 非 24 倍數長度且含 NaN 的訊號 → flush → reset → 再 push，與全新 stream 逐位比對（殺掉上述三個 mutant）。

### 5. `iso532_stream_residual_flags` 文件不實：「毒化 handle 回 0」是假的

`iso532-ffi/src/lib.rs:107`（與重生的 `include/iso532.h:86`）宣稱 "A null or panicking handle also returns zero"。實作讀 `pending` 不可能 panic，`guarded_or(0)` 的預設值不可達；handle 也沒有 poison 位（毒化僅靠 push 的 `assert!(!self.flushed)` 重新觸發）。毒化後呼叫會拿到 panic 當下的殘留 bits 而非 0，且與 push 文件「毒化後僅 `iso532_stream_free` 合法」矛盾。

**修法**（文件修正，錯誤碼與簽名不動）：改為「null handle 回傳 0；handle 毒化（前次 push/flush 回 -2）後本函式回傳值未定義，僅 `iso532_stream_free` 合法」。同次修正併入第 6 項一起重生 header。另補一個 FFI 測試：`iso532_stream_residual_flags(NULL) == 0`（此文件承諾目前無測試看守）。

### 6. `residual_flags` 中途輪詢語意未定義 → 事件雙重計數

`iso532/src/zwtv/stream.rs:389` 與 FFI/header 文件寫 pending flags「不會附掛於任何幀」——只有 flush 後為真。中途呼叫回傳的 flags 之後仍會附掛到下一個 on-grid 輸出幀：每次 push 後輪詢的監測端會把同一 NONFINITE_INPUT 事件計數兩次（一次 residual、一次 frame flag），或因後續輪詢回 0 而誤清警報。

**修法**（文件補充，與第 5 項同次 header 重生）：rustdoc 與 header 各補一句「flush 前回傳值為暫定（provisional），將附掛於下一個輸出幀；僅 flush 後的值代表尾端未交付事件」。

---

## P1 — 建議同批補上

### 7. NaN 復原測試的 skip=794 是零餘裕的硬編常數

`iso532/tests/stream.rs:187`：實測 794 恰是首個通過幀（frame 793 差 1.017e-9 > 容差、794 差 9.88e-10，距 1e-9 僅 1.2%）。backend 機制已排除（forced-scalar 與 AVX2 軌跡 17 位數字全同），但跨 OS libm 差異或未來合法的數值變動只要推移 >1.2% 就假失敗。衰減 ~3%/幀，**skip 改 800+ 即有 ~20% 餘裕**；註解補「measured 794, margin via 800」。（96k 訊號長度經驗證是合理的收斂餘裕設計，不要縮短。）

### 8. TOL chunk 驅動迴圈骨架雙份（scalar/AVX2 逐字重複 ~20 行）

`iso532/src/zwtv/stream.rs:178-246`：nonfinite 消毒、phase/emit 分支、on_frame 呼叫、flag 重置、餘量回傳的協定完整重複兩份，僅內層 band 前進不同。未來協定修正只改到一份 → 後端靜默分歧。

**修法**：抽 `#[inline(always)]` 泛型骨架，收 advance/emit 兩個閉包；scalar fn 與 `#[target_feature(enable="avx2,fma")]` wrapper 內各自實例化（閉包在 target_feature fn 內定義會繼承其 features，Rust 1.86 起穩定，無 UB 疑慮）。**硬性關卡：改後 hash gate 12/12 逐位不變 + chunk 不變性測試全綠才算完成**；若逐位有變，放棄此項改記入不修清單。

### 9. `zwtv_reference_zerostate` 未鏡射「use_avx2 讀一次」

`iso532/src/zwtv/stream.rs:455-465`：oracle 路徑仍讀兩次（`third_octave_levels_with_mode` 內一次、`new_nl_stage(b, use_avx2())` 一次）。現行測試因 one-test-per-binary 慣例不會觸發混合後端，屬一致性缺口。比照 new()：函式開頭 `let avx2 = crate::simd::use_avx2();` 一次讀取後傳遞。

### 10. `NlGroupState::reset()` 重刻 `zero()`

`iso532/src/zwtv/nonlinear_decay.rs:239`：與 zero() 同為清 prev_uo/prev_u2，同 struct 兩份手動同步的零狀態定義。呼叫點已在 unsafe 區塊，刪 reset() 改 `*state = NlGroupState::zero()` 即可。（TolGroupState/TolBandState 因保留係數欄位，其獨立 reset 合理，不動。）

---

## P2 — 選配清理（不擋收）

11. **`NlStage::Avx2` 的 `b: [f64;6]` 與 `NlConsts` 同源雙份**（stream.rs:98-104）：項⑭已從三份減到兩份；可讓 NlConsts 保留/曝露 scalar 陣列供尾 band 使用。低急迫（兩者在 new_nl_stage 同一運算式初始化，drift 需刻意為之）。
12. **`stream_no_rayon.rs` 未遷移 `common::run_chunked`**（stream_no_rayon.rs:6-9）：無隔離約束阻擋（common 不碰 rayon），`mod common;` + `run_chunked(&signal, std::iter::empty())` 即可。（stream_alloc.rs 的手刻迴圈是刻意的——run_chunked 在計數區內配置記憶體——不要遷移。）
13. **emit 管線參數穿線**（stream.rs:393）：on_internal_frame 9 參數（clippy allow）、emit_loudness 7 參數。可把 field/nl/tw/held_core/has_held/emitted_internal/pending 收成 `EmitState` 子結構，helpers 變 2-3 參數方法；借用不相交已驗證可行。另 emit_loudness 的 `held`/`next` 是相鄰同型 `&[f64;21]`，對調可編譯——重構時留意。
14. **FFI 佈局 runtime 斷言與 const 區塊雙份**（ffi/tests/ffi.rs:330-356）：size/5 個 offset 與 lib.rs:57-84 的 const 斷言完全重複，可刪。**但保留 flags==1/2/4 三個字面值斷言**（const 區塊只斷言與 `FrameFlags::bits()` 對等，字面值才凍結 C ABI 數值）——或改把字面值搬進 const 區塊再刪測試版。null 路徑測試（:357-373）保留。
15. **FFI residual 測試瘦身**（ffi/tests/ffi.rs:296）：48_048/NaN@48_030 魔術常數與核心測試重複且無推導註解；FFI 層只需驗 bits() 轉發——短 chunk 含一個 NaN 即可。配合第 5 項補 `residual_flags(NULL)==0` 斷言。

---

## 記錄不修（驗證已排除，勿重做）

- **reset() 釘定建構時後端**：刻意且正確——項⑪要求就地清零保留係數/Box（RT 零配置），重新 dispatch 反而重引入項⑦消除的混合後端風險；無任何呼叫端受影響。
- **throughput 測試手刻迴圈**：計時保真的正確設計（排除 flush 與 Vec 增長，ratio 斷言不被常數開銷稀釋），不遷移 run_chunked。
- **per-sample 相位模數**：整數運算與 FP 關鍵路徑平行，收益 <1%，屬過早微優化。
- **advance_nl_stage 內聯**：項⑨原文要求（AVX2 臂整包 annotated helper）已如實達成；殘餘每 2 kHz 一次的 enum dispatch 可忽略。可選擇性加 `#[inline]` 作零風險 polish。
- **on_frame 的 [f64;28] 傳值**：複製次數未比修復前增加（HEAD 是 Option 傳值，反而多一層），且 ~0.9 MB/s 為雜訊。
- **96k 測試長度**：debug profile 全測 1.26 秒，換 ~1.2 秒無再分歧斷言的實質餘裕，保留。
- **FP 收縮風險（PLAUSIBLE，記錄性質）**：泛型閉包確實把凍結的 scalar 數學帶進 target_feature 區域，但 rustc 保證無隱式 fp-contract（只有顯式 `mul_add` 才融合），現況不會變位；若未來工具鏈破壞此保證，zerostate 逐位比對測試與 Linux hash gate 會立即抓到。已知小缺口：**Windows hash gate 為 dump-only**——維持 Linux CI 斷言即可。
- **stream_alloc 換訊號**：配置行為已驗證全數據無關，換 fixture 無實質影響。

---

## 完成後驗證 gate（全綠才 commit）

```bash
cd iso532 && cargo test && cargo clippy --all-targets -- -D warnings && cargo fmt --check
cd iso532 && cargo test --test golden_zwtv dump_zwtv_output_hashes -- --ignored --nocapture   # 12/12 逐位不變（項 8 骨架重構的硬關卡）
cd iso532-ffi && cargo test --features test-panic && cargo clippy --all-targets --features test-panic -- -D warnings
# header 重生（項 5/6 文件修正後）：
cbindgen --config cbindgen.toml --crate iso532-ffi --output include/iso532.h   # diff 僅註解變動
# py（項 1）：maturin 重 build 後
cd iso532-py && ../.venv/Scripts/python.exe -m pytest tests/test_smoke.py -v
# 新回歸測試（項 4 flush→reset→push、項 1 NaN ValueError）須在修復前的碼上失敗
# 項 2 驗證（如有 aarch64 toolchain）：cargo check --target aarch64-unknown-linux-gnu 無警告；否則至少 cargo check 本機無新警告
```
