# R5 第二輪審查修正清單（2026-07-17）

> 交接對象：Codex。前提：R5 已 commit（`3254bde` streaming API v1 freeze）。
> 審查方法：8 角度平行搜尋（逐行掃描、刪除行為稽核、跨檔追蹤、重用、簡化、效能、深度、慣例）→ 21 個去重候選 → 逐項獨立驗證：**17 CONFIRMED / 4 PLAUSIBLE / 0 REFUTED**。
> 核心結論：**無 loudness 計算錯誤、無 UB、所有 kernel 狀態化重構與 batch 逐位一致**（刪除行為稽核全數通過，hash gates 釘死）。以下為契約缺口、測試漏洞與熱路徑效能問題。
>
> **全域約束**：任何動到 `iso532/src/zwtv/` 的修改，完成後必須 `cargo test --workspace` 全綠，且 hash gate 12/12、chunk 不變性、E2 零狀態等價、零配置、no-rayon 測試不得有任何位元差異。C ABI 僅允許**加法**（新函式），既有簽名/錯誤碼數值/struct 佈局不得動。

---

## P0 — 正確性 / 凍結契約缺口（必修）

### 1. 串流尾端 pending flags 靜默遺失【已實測重現】

`iso532/src/zwtv/stream.rs:304` — `emit_loudness` 在內部幀計數非 `OUT_DECIM`(=4) 倍數時提前 `return 0`，早於 `pending.take()`（line 308）；`flush`（lines 235-246）只呼叫一次 `emit_loudness`，沒有其他排水路徑。最後一個 on-grid 輸出幀之後發生的 `CLAMPED_120DB`/`NONFINITE_INPUT` 事件永遠不會浮現。

實測重現：48 048 樣本、NaN 在樣本 48 030 → 501 幀全部乾淨、flush 寫 0 幀 → 監控輸入損壞的呼叫端看到「乾淨」串流。

**修法（建議，加法式、不動凍結面）**：
- 不可改 flush 的幀輸出行為（會破壞凍結的幀數與 chunk 不變性測試）。
- Rust：新增 `ZwtvStream::residual_flags(&self) -> FrameFlags`（或同名 getter），回傳目前未浮現的 pending flags；flush 後呼叫可取得尾端事件。
- FFI：新增 `uint32_t iso532_stream_residual_flags(const Iso532Stream *stream);`（加法，v1.1）。rustdoc 寫明：「flush 之後呼叫，回傳未附著於任何輸出幀的殘餘旗標；0 表示無」。
- 測試：把實測場景寫成回歸測試（48 048 樣本 + 尾端 NaN → `residual_flags` 含 `NONFINITE_INPUT`）。
- header 重生：`cbindgen --config cbindgen.toml --crate iso532-ffi --output include/iso532.h`，diff 應僅新增一個函式與註解。

### 2. `iso532_stream_flush` 文件與行為矛盾

`iso532-ffi/include/iso532.h:104` — 文件寫「Flush the final lookahead frame. out_cap must be at least one.」暗示必回傳一幀，但只要最後持有的內部幀 index 非 4 的倍數，flush 合法地寫 0 幀 — **4 種長度中 3 種如此**，包含最常見的整秒 48 000 樣本（n_internal=2000，末 index 1999，1999 % 4 ≠ 0 → 0 幀）。

**修法**：行為不能動（凍結），改文件。在 `iso532-ffi/src/lib.rs` 的 flush rustdoc 明寫：「`*out_written` 為 0 或 1；僅當最終內部幀落在輸出格點（1/4 機率）時寫出 1 幀。0 不是錯誤。」與第 1 項同一次 header 重生。

### 3. NaN 恢復測試是空集斷言

`iso532/tests/stream.rs:208` — 48 000 樣本訊號恰好產生 500 輸出幀，`clean.iter().zip(&dirty).skip(550)` 跳過整個序列，恢復比較迴圈執行 0 次。若出現「NONFINITE 樣本永久污染濾波器狀態」的回歸，此測試仍綠。

**修法**：把 550 改為正確的恢復點幀數（NaN 影響衰減後，例如 NaN 位置對應幀 + 100，需 < 500），並在迴圈後加 `assert!(compared > 0)` 防再度空集。

### 4. Python `sone2phon` 對負值靜默回 NaN

`iso532-py/src/lib.rs:84` — 任意 float 直通 Rust 公式，`n < -0.0005` 走 `powf(0.35)` 負底數 → NaN，不拋例外；與 `loudness_zwtv`/`loudness_zwst` 全部驗證輸入並映射 ValueError/TypeError 的慣例不一致。

**修法**：binding 層加 `if n < 0.0 { return Err(PyValueError::new_err("sone must be non-negative")); }`。**不動 Rust core**（凍結 parity 面）。加一個 pytest 案例。

### 5. sone2phon 單調性測試斷言了函式沒有的性質

`iso532/src/sone2phon.rs:5` — 公式在 n=1 有不連續：低分支 n→1⁻ 趨近 40·(1.0005)^0.35 ≈ 40.007，高分支從 40.0 重啟（公式是 mosqito/ISO 532-1 parity，**不能改**）。in-crate 單調性測試只因 0.02 網格恰好踩在 1.0 上才通過；步距改 1e-5 即失敗。

**修法**：改測試——斷言「n=1 接縫兩側各自單調」，並加註解記錄接縫是規格繼承行為；或直接斷言接縫存在（`sone2phon(1.0-1e-9) > sone2phon(1.0)`）把它文件化。

### 6. FFI struct 佈局凍結只有一半是編譯期

`iso532-ffi/src/lib.rs:53` — `const _` 區塊只斷言 size/align；欄位 offset 與 `ISO532_STREAM_FLAG_*` 數值只在 `tests/ffi.rs:302-323` 檢查，而 `iso532_stream_push`（line 118、151）用 `out.cast::<iso532::StreamFrame>()` 直寫 C 端記憶體。任一側單獨重排欄位仍能乾淨編譯 cdylib——build-only 的發佈管線會把 UB 出貨。

**修法**：`std::mem::offset_of!` 與 `FrameFlags::X.bits()` 皆可 const 求值，把 5 個 offset 斷言與 3 個 flag 值斷言全部搬進既有 `const _` 區塊（測試裡的可留可刪）。

### 7. `ZwtvStream::new` 讀兩次 `use_avx2()` 可組出混合後端

`iso532/src/zwtv/stream.rs:105,115` — `new_tol_stage` 與 `new_nl_stage` 各自讀一次 `use_avx2()`（Relaxed AtomicBool，`set_force_scalar` 是公開 API）。併發切換時可組出 AVX2 TOL + scalar NL 的混合串流，輸出不匹配任一凍結快照且無錯誤。（PLAUSIBLE：實務上靠測試慣例緩解，但修法只要一行。）

**修法**：`new()` 開頭讀一次 `let avx2 = crate::simd::use_avx2();`，傳給兩個 stage 建構式。

---

## P1 — 熱路徑效能（修時必須保持逐位不變，hash gates 看守）

### 8. 串流 TOL 熱路徑無法 inline（主要效能問題，估 2-3x）

`iso532/src/zwtv/stream.rs:263` — `TolGroupState::advance` 帶 `#[target_feature(enable = "avx2,fma")]`（third_octave_levels.rs:170-172），但串流呼叫端 `advance_tol` 無標註 → LLVM 禁止 inline：每個輸入樣本 7 次不透明呼叫、`__m256d` 走非 AVX ABI 回傳（48 kHz = 336k 次/秒），broadcast 常數每次重載。batch 路徑 `tol_group_avx2`（line 198）自身有標註所以同一個 `advance` 完整 inline。

**修法**：把 push 的逐樣本迴圈重構為 chunk 層級的 `#[target_feature(enable = "avx2,fma")]` unsafe helper（每次 push 分派一次 enum match，樣本迴圈在 helper 內），讓 `advance` 如 batch 路徑般 inline。**運算序不可變**——只搬呼叫結構、不改任何算式；完成後 hash gate 12/12 與 chunk 不變性必須逐位通過。可順手一併處理第 10 項（同一重構）。

### 9. NL AVX2 臂同樣的跨界問題（成本較小）

`iso532/src/zwtv/stream.rs:129-162` — `advance_nl_stage` 無標註卻執行 `_mm256_loadu_pd`/`_mm256_storeu_pd` 並呼叫帶 `#[target_feature]` 的 `NlGroupState::advance_frame`（nonlinear_decay.rs:251）。內部率 2 kHz × 5 groups ≈ 10k 次/秒跨界。batch 路徑 `nl_loudness_process4`（nonlinear_decay.rs:308-331）已示範正確包法。

**修法**：把整個 AVX2 臂（載入、advance_frame、儲存、tail）包進一個小的 `#[target_feature(enable = "avx2,fma")]` helper。

### 10. `advance_tol` 每樣本零初始化 224-byte 陣列 + enum 重分派（次要）

`iso532/src/zwtv/stream.rs:248-250` — 每樣本 `[0.0; 28]` 零初始化與兩變體 enum match，24 樣本中 23 個不需要（`emit.then_some` 已避免值拷貝，浪費主要是 memset 與分派）。**修法**：併入第 8 項的 chunk 層級重構——match 提到 chunk 迴圈頂、dB 幀只在 emit 分支寫入呼叫端提供的 `&mut [f64; 28]`。

### 11. `reset()` 走 `Self::new` 重新配置堆積（無契約違反，建議修）

`iso532/src/zwtv/stream.rs:203` — `*self = Self::new(self.field)` 重新 Box 配置 + 全 28 頻帶係數重算（exp/log）。目前 RT 承諾只涵蓋 push/flush、C API 無 reset，所以不違約；但即時呼叫端在音訊執行緒 reset 會踩到，且 `stream_alloc.rs` 看不到。

**修法**：就地清零狀態陣列（z/sm/prev、計數器、pending/flushed），保留已算好的係數與既有 Box。在 `stream_alloc.rs` 加 reset 的零配置覆蓋。

### 12. `new()` 裡的 DenormalGuard 無作用

`iso532/src/zwtv/stream.rs:185` — 建構期只算係數（全部 order-1，exp 引數 ~-3e-4 級，不可能產生 denormal），FTZ/DAZ 狀態不影響凍結常數位元；push/flush 各自裝 guard。每次 new/reset 白付兩次序列化 LDMXCSR。

**修法**：刪掉 `new()` 的 `let _guard = DenormalGuard::new();`。

---

## P2 — 死碼 / 重複 / 測試清理

### 13. 死欄位 `t_internal`

`iso532/src/zwtv/stream.rs:177,196,290` — 只有宣告、歸零、遞增，全 repo 無任何讀取（無 Debug/serde/FFI 曝露）；emit 邏輯用的是 `emitted_internal`。**修法**：刪除欄位與遞增行。

### 14. `nl_b` 係數三處存放

`iso532/src/zwtv/stream.rs:171` — `nl_b` 獨立欄位只為了跟 `&mut self.nl` 一起傳進 `advance_nl_stage`，而 `NlStage::Avx2` 的 `NlConsts` 已含同源係數。**修法**：把 `[f64; 6]` 搬進各 `NlStage` 變體（Scalar 放 states 旁；Avx2 放 consts/tail 旁，僅 scalar tail band 需要），兩個呼叫點（stream.rs:300、345）少傳一個參數。已驗證無借用衝突。

### 15. `run_chunked` 複製貼上的排水迴圈

`iso532/tests/stream.rs:31-45` — 主 `for size in chunks` 迴圈後跟著寫死 480 的 `while pos < signal.len()` 排水迴圈，兩塊近乎相同。**修法**：合併為 `for size in chunks.chain(std::iter::repeat(480))`，靠既有 `pos >= signal.len()` break；已驗證對所有現有呼叫端（含無限 iterator）行為等價。

### 16. `stream_scalar.rs` 手刻 drive loop

`iso532/tests/stream_scalar.rs:11-17` — 重寫了 `run_chunked` 的單 chunk 特例。**修法**：把 `run_chunked` 搬到 `iso532/tests/common/mod.rs`（兩個測試 crate 都已 `mod common;`），此處改呼叫 `common::run_chunked(&signal, std::iter::once(signal.len()))`。與第 15 項同一次改。

### 17. `stream_alloc.rs` 內聯 sine fixture

`iso532/tests/stream_alloc.rs:22-24` — 自產 1 kHz sine，而本 commit 才剛把 `synth_signal()` 集中到 `tests/common/mod.rs`。訊號生成在 `ALLOCS` 快照之前，重用無副作用。**修法**：`mod common;` + `common::synth_signal()`。

### 18. `guarded` helper 只支援 i32，new/free 手刻 catch_unwind

`iso532-ffi/src/lib.rs:28,67-72,168-170` — panic 圍堵是本 crate 核心不變量，但非 i32 簽名靠複製貼上維持；下一個新 extern fn 可能漏包而跨 FFI unwind（abort）。**修法**：泛型化 `fn guarded_or<T>(default: T, f: impl FnOnce() -> T) -> T`，`guarded` 改為其 i32 特例，new/free 換用。

---

## 不修（記錄供 v2 參考）

- **`-4` 雙語意**（`iso532-ffi/src/lib.rs:108,146`）：out_cap 不足與內部不變量共用 `ISO532_ERR_INTERNAL`。已凍結，且呼叫端可用 `iso532_stream_max_frames` 自行判別；文件已在第一輪修正寫明雙語意。v2 再考慮 `ISO532_ERR_BUFFER_TOO_SMALL(-5)`。
- **push-after-flush 走 assert panic → -2 毒化**（`iso532/src/zwtv/stream.rs:214` + iso532.h:88-90）：v1 header 已把此路徑寫成契約。可選的無害改善：FFI `iso532_stream_push` 前置 `flushed` 檢查直接回 -2 並設毒化旗標（外顯行為與文件完全相同，省下 unwind 成本與 stderr 噪音）——若做，歸入 P1；不做也不違約。
- **`zwtv_reference_zerostate` 是 `#[doc(hidden)] pub`**（`iso532/src/zwtv/stream.rs:324`）：測試 oracle 進了公開符號面。乾淨解法是 `test-internals` feature gate，但會動 tests/benches 的啟用方式；`#[doc(hidden)]` + 未凍結聲明在 v1 可接受。**若 Codex 認為改動小可順手做**：`#[cfg(feature = "iso532-test-internals")]`，兩個測試檔加 feature 啟用。

---

## 完成後驗證清單

1. `cargo test --workspace` 全綠（含 `stream`、`stream_alloc`、`stream_scalar`、`stream_no_rayon`、`hash_gate`、`determinism`、`ffi`）。
2. hash gate **12/12 逐位不變**（P1 效能重構的硬性關卡）。
3. `cargo bench --bench loudness`（streaming group）：第 8/9 項完成後記錄 before/after，預期 streaming 路徑顯著收斂向 batch。
4. header 重生 diff 檢查：僅新增 `iso532_stream_residual_flags` 與文件註解，無既有簽名變動。
5. `iso532-py`：`pytest` 全綠（含新增的負值 ValueError 案例）。
6. 新增回歸測試存在且會失敗於舊碼：尾端旗標（第 1 項）、`compared > 0`（第 3 項）。
