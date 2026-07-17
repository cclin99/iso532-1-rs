# R5 審查修正清單（2026-07-17）

> 交接對象：Codex。前提：R5 實作已在工作樹（未 commit），審查結論為「可收，但以下項目須在 commit / v1 凍結前處理」。
> 審查方法：三路深度審查（kernel 狀態化、FFI/ABI、測試套件）+ 本機全量重跑驗證。
> 已確認無正確性 bug、無 UB、凍結雜湊 12/12 與 R1 紀錄逐字相同、E2/E3/chunk 不變性/零配置/無 rayon 全部由測試真實看守。

---

## P0 — v1 凍結前必修（擋 commit）

### 1. FFI 串流 API 的契約文件全數補齊 + header 重生

計畫 S7.1（phase-r5-stream-api.md:1607-1673）指定的 doc 註解沒有搬進 `iso532-ffi/src/lib.rs`，導致重生的 v1 header 對串流 API 零文件。poison 語意與執行緒限制現在是「不成文契約」——v1 都要凍結了，必須在凍結前寫進去。

補齊以下 rustdoc（cbindgen 會帶進 header）：

- `Iso532Stream`（opaque struct）：`iso532_stream_new` 配置、`iso532_stream_free` 釋放；**同一 handle 不得跨執行緒並行呼叫（無內部鎖）**。
- `iso532_stream_new`：48 kHz 烘焙（不收 fs）；`field_type` 非法回傳 NULL；延遲 24 樣本（1 內部幀）。
- `iso532_stream_push`：`out` 至少 `iso532_stream_max_frames(chunk_len)` 格，不足回 `-4` 且不部分寫入（`*out_written = 0`）；**panic 回 -2 後 handle 視為毒化，之後僅 `iso532_stream_free` 合法**；flush 之後再 push 亦以 -2 浮現（內部 assert）。
- `iso532_stream_flush`：cap ≥ 1；之後僅 free（或 Rust 端 reset）可再用。
- `Iso532StreamFrame`：flag bits 意義（1=CLAMPED_120DB、2=NONFINITE_INPUT、4=WARMUP；WARMUP = t_frame_index < 580）。

完成後 `cbindgen --config cbindgen.toml --crate iso532-ffi --output include/iso532.h`（0.29.4），檢視 diff 僅新增註解、無簽名變動。

### 2. `ISO532_ERR_INTERNAL`(-4) 語意說明修正

`iso532-ffi/src/lib.rs:92-93,129-130` 把 -4 用於「呼叫端 out_cap 不足」，但 header（iso532.h:28-31 對應的錯誤碼文件）仍只說「程式庫內部不變量被打破」。錯誤碼**數值不動**（凍結面），把文件改為雙語意：「內部不變量被打破；串流 push/flush 亦以此碼拒收不足的 out_cap（不部分寫入）」。與第 1 項同一次 header 重生。

### 3. 修正 crate 頂部的不實敘述

`iso532-ffi/src/lib.rs:3`：「Every extern fn body is wrapped in catch_unwind」——`iso532_stream_max_frames`（lib.rs:66-68）與既有 `iso532_zwtv_out_frames` 沒包（兩者皆 panic-free，無實害）。二擇一：改敘述為「每個可能 panic 的 extern fn」，或把兩個查詢函式也包進 `guarded`。建議前者（零風險）。

### 4. 釘住 `N_WARMUP_FRAMES = 580`

測試全部相對於 crate 常數寫（`iso532/tests/stream.rs:3` import），只有下界看守（stream.rs:100 的 first_sustained ≤ 580），沒有上界——把常數調大會靜默弱化 E3 gate 與 WARMUP 窗口而全測仍綠。在 `iso532/tests/stream.rs` 加：

```rust
#[test]
fn warmup_constant_is_frozen() {
    assert_eq!(N_WARMUP_FRAMES, 580);
}
```

### 5. chunk 不變性 / reset 測試改逐位比較

`iso532/tests/stream.rs:54,63,81` 用 `assert_eq!(got, baseline)`（f64 `==`，derive PartialEq）而非計畫要求的 `to_bits()`——±0.0 會混同、NaN 語意錯亂，嚴格弱於逐位。抽一個 helper：

```rust
fn assert_frames_bitwise(got: &[StreamFrame], expected: &[StreamFrame], ctx: &str) {
    assert_eq!(got.len(), expected.len(), "{ctx}: length");
    for (i, (a, b)) in got.iter().zip(expected).enumerate() {
        assert_eq!(a.n.to_bits(), b.n.to_bits(), "{ctx} frame={i}");
        assert_eq!(a.n_phon.to_bits(), b.n_phon.to_bits(), "{ctx} frame={i}");
        assert_eq!(a.t_frame_index, b.t_frame_index, "{ctx} frame={i}");
        assert_eq!(a.flags, b.flags, "{ctx} frame={i}");
    }
}
```

三個呼叫點換用（chunk={size}、random-LCG、reset）。

### 6. 驗收 6 的 Python 側互驗：補做或明文 descope

主計畫驗收 6 要求「py 側以公式重述互驗」，目前只有 Rust 單元測試（sone2phon.rs:18-27，anchors + 1e-12），py binding 未匯出 sone2phon、無對應測試，且實作紀錄未記 descope。**建議補做**（py API 不在 v1 凍結面，成本低）：

- `iso532-py/src/lib.rs` 加 `#[pyfunction] fn sone2phon(n: f64) -> f64`（轉發 `iso532::sone2phon`）並註冊。
- `iso532-py/tests/test_smoke.py` 加一個測試：以 Python 重述公式（`40 + 10*log2(n)` / `40*(n+0.0005)**0.35`）對 `iso532.sone2phon` 掃描互驗（如 0..20 sone 步進 0.02，atol 1e-12）+ anchors 1/2/4 sone。
- 需要 maturin 重 build 後跑 smoke。

若決定不做，改在 phase-r5-stream-api.md 實作紀錄與主計畫 §R5 明文記錄：「py 側互驗 descope，理由：binding 無 sone2phon 出口；Rust 側 1e-12 公式測試為唯一看守」。

---

## P1 — 建議一併補（同批 commit）

### 7. FFI 缺失的兩個負向/契約測試

`iso532-ffi/tests/ffi.rs` 補：

- **out_cap 不足拒收**：`iso532_stream_push(h, ptr, 480, out, 1, &written)` → 回 `ISO532_ERR_INTERNAL`、`written == 0`、handle 仍可用（再以足量 cap push 成功）。
- **`iso532_stream_max_frames` 轉發**：`assert_eq!(iso532_stream_max_frames(480), iso532::ZwtvStream::max_frames_for_chunk(480))`。
- 佈局互鎖（ffi.rs:249-266）補上 `_reserved` 的 `offset_of!` 一組（計畫要求逐欄；現缺最後一欄）。

### 8. smoke.c 補計畫要求的兩點

`iso532-ffi/tests/smoke.c:66-97` 串流段：

- 緩衝大小改用 `iso532_stream_max_frames(CHUNK)` 驗證（靜態陣列 8 可留，加 `if (iso532_stream_max_frames(CHUNK) > 8) { fail }`，讓 C 端真正走過這個 API）。
- 成功路徑印前 3 幀（`t_frame_index, n, n_phon, flags`）——計畫 S7.2 原文「印前 3 幀」。

### 9. 收尾紀錄補兩句

phase-r5-stream-api.md 實作紀錄追記：

- `main_loudness_clamped` 採 `pub(crate)`（計畫寫 `pub`）——刻意收斂可見性，串流路徑夠用、不多曝公開 API。
- 第 6 項的 py 互驗處置結果（補做或 descope 理由）。

---

## P2 — 選配（不擋收）

- `iso532/benches/loudness.rs:109` auto-dispatch 臂在閉包內補 `set_force_scalar(false)`，與 :51/:80 既有 bench 風格一致（現由外層 :108 保證正確，僅風格）。
- `iso532/tests/stream_scalar.rs` 可加一行斷言 scalar 路徑確實生效（如 `assert!(!iso532::simd::use_avx2())`），避免 `set_force_scalar` 壞掉時退化成 AVX2-vs-AVX2（現由 simd_dispatch.rs 背書，屬雙保險）。

---

## 完成後的驗證 gate（全綠才 commit）

```bash
cd iso532 && cargo test && cargo clippy --all-targets -- -D warnings && cargo fmt --check
cd iso532 && cargo test --test golden_zwtv dump_zwtv_output_hashes -- --ignored --nocapture   # 12/12 與 R1 逐字相同
cd iso532-ffi && cargo test --features test-panic && cargo clippy --all-targets --features test-panic -- -D warnings
# 第 6 項若補做：maturin build 後
cd iso532-py && ../.venv/Scripts/python.exe -m pytest tests/test_smoke.py -v
ISO532_REQUIRE_PARITY=1 ../.venv/Scripts/python.exe -m pytest tests/test_parity_mosqito.py -q  # 18/18, 0 skipped
```

Commit 粒度：目前全部變更尚未 commit，修正直接併入計畫原定的 commit 序列（S7 的 FFI/header commit 含 P0-1/2/3/7/8；測試強化併入 S4.3 的測試 commit；py 併入 S0.4 或獨立一個 commit）。header 重生的 diff 須人工檢視：僅註解變動、無簽名/佈局變動。

## 審查已確認乾淨、無須動作的部分（供 Codex 參考，勿重做）

- 四個 kernel 狀態化逐運算式比對：浮點運算圖與舊碼一致；D5 捨入差異（scalar 除法 / AVX2 倒數乘法）正確保留；`mosqito_seed` 精確重現 wraparound；tw 拆半發射位元中立；死碼 `u2[0]` 預寫不搬（AVX2 parity 為證）。
- FFI 無 UB：`chunk_len==0` 走空 slice、`out_written` 先驗後零、無部分寫入、panic 邊界完整、DenormalGuard unwind 還原 MXCSR、frame cast 佈局有 compile-time assert。
- 凍結面：hash_gate 常數未動；`synth_signal` 搬移逐字元相同；FrameFlags bits 與 StreamFrame size=32 有凍結測試；E2 九組 golden `to_bits`、E3 580/1e-9 未放寬。
- 本機重跑：iso532 全套綠（stream 8+1 ignored）、FFI 13/13、clippy/fmt 乾淨、py smoke 6/6、strict parity 18/18。
