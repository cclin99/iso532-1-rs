# PRE-R6-P2:ZwtvStream pyclass(方案 2 py 串流接口)Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. 完成後以 `.codex/skills/iso532-r3-verification` 的完整流程驗證。

**Goal:** 把 `iso532_core::ZwtvStream` 綁成 Python class,補完方案 2(動態引擎 + Python 接口)的最後一格交付矩陣;完成後打 `v0.1.0` tag 作為三方案全量交付點與面板 repo 的消費基準。時機分析見 `docs/PLAN-TIMING-ANALYSIS-2026-07-18.md` §3(介面方向已在該節鎖定,不重議)。

**狀態:** 🔶 本機實作與三個指定 commit 已完成(2026-07-19);等待 GitHub Actions 三 job 綠燈後才可 push/tag `v0.1.0`。完整 workspace `cargo test` 受主機 LNK1104 exe 建立鎖定阻塞，詳見文末收尾註記。

> **進度註記(2026-07-19,Claude 查案結論):**
> 1. **Access violation root cause:** `iso532_core::ZwtvStream` 是 align(32) 型別(`NlStage::Avx2` 內嵌 `NlConsts`,含 7 個 `__m256d`)。原 pyclass 把它**內嵌**在 struct 裡,而 Python 物件配置(pymalloc)只保證 16-byte 對齊——物件落在 16-mod-32 位址時,AVX2 kernel 的對齊載入(`vmovapd`)直接 AV。這解釋了「看似隨機」的觸發型態(隨配置器狀態而變,與 view/數值無關;FFI 走 `Box` 守對齊所以永遠正常)。**修正已在工作樹:`inner: Box<iso532_core::ZwtvStream>`+ 註解**(附帶效益:pyclass 本體回到 align ≤16,消除 UB)。驗證:原崩潰矩陣(view len 96/479/480/481/504/1920)全過,pytest 三連跑穩定。
> 2. **E3 測試空比較 bug(計畫原稿錯誤):** contract 訊號 1 秒只有 500 幀 < N_WARMUP=580,`n[w:]` 為空,`np.max` 拋 ValueError。修正:訊號 `np.tile(one, 3)` 成 3 秒/1500 幀(Task 1 程式碼已更新)。實測修正版通過,warmup 後 max diff = 3.24e-11 ≤ 1e-9。

**前置:** PRE-R6-P1(root workspace)已落地且 CI 綠。

**Architecture:** 純加法——只動 `iso532-py/src/lib.rs`、`iso532-py/tests/`、`.github/workflows/ci.yml`(pytest 清單一行)。**`iso532/src`、`iso532/tests`、`iso532-ffi/` 零 diff**(py API 不在 v1 凍結面,C ABI 與核心是)。

**Exit Gate:** pytest 全綠(smoke + 新 stream 套件,CI 兩平台)+ strict parity 18/18 不變 + hash gate 12/12 不變 + 核心/FFI 零 diff + CI 三 job 綠 → tag `v0.1.0`。

---

## 背景(給零脈絡的工程師)

核心 API(`iso532/src/zwtv/stream.rs`,已凍結,勿改):

```rust
ZwtvStream::new(field: FieldType) -> Self
push(&mut self, chunk: &[f64], out: &mut [StreamFrame]) -> usize   // assert!(!flushed) — flush 後 push 會 panic
flush(&mut self, out: &mut [StreamFrame]) -> usize                 // 冪等:重複 flush 回 0;out 不得為空
reset(&mut self)                                                   // 任何狀態皆合法,回到全新串流
const latency_samples() -> usize                                   // 24
const max_frames_for_chunk(chunk_len: usize) -> usize
const residual_flags(&self) -> FrameFlags                          // flush 前為 provisional
// StreamFrame { t_frame_index: u64, n: f64, n_phon: f64, flags: FrameFlags },derive Default
// FrameFlags::bits() -> u32;CLAMPED_120DB=1、NONFINITE_INPUT=2、WARMUP=4(凍結)
// iso532::N_WARMUP_FRAMES = 580(pub,凍結)
```

綁定層決策(時機分析 §3 已鎖):

1. **`push` 在 flush 後必須由 binding 先擋**(查 `flushed` 旗標→ `RuntimeError`),不能讓核心 assert 變成 `pyo3_runtime.PanicException` 洩出。`flush` 冪等、`reset` 恆合法,不需擋。
2. **NaN/Inf 語意與批次 py API 刻意不同**:批次 `loudness_zwtv` 遇非法輸入 raise;串流置零 + flag,不 raise。docstring 必須明載,含 `residual_flags` 的 flush 前 provisional 語意。
3. **不承諾 py 層零配置**:每次 push 產生新 ndarray(零配置是 Rust 熱路徑契約,binding 天生有配置)。docstring 一句帶過。
4. **`#[pyclass(unsendable)]`**:核心 handle 無內部鎖,單執行緒使用,unsendable 最誠實。
5. 輸入規約沿批次慣例:C-contiguous 1-D float64,先拷貝 owned buffer 再 `allow_threads`。
6. 測試訊號沿 R3 鐵律:**純整數演算訊號,不得用 sin 合成**(numpy/Rust libm ULP 差)。

### Task 0 開始前

```bash
cd /d/ISO532 && git status --short   # 乾淨(除 bash.exe.stackdump)
ls Cargo.toml                        # root workspace 已存在(P1 前置)
```

---

### Task 1: pytest 測試先行(RED)

**Files:**
- Create: `iso532-py/tests/test_stream.py`

- [ ] **Step 1: test_stream.py(完整程式碼;無 mosqito 依賴,CI 可跑)**

```python
"""Streaming API (ZwtvStream) tests — no mosqito; runs in CI.

NaN semantics deliberately differ from the batch API: streaming zeroes
non-finite samples and raises flags instead of raising exceptions.
"""
import numpy as np
import pytest

import iso532

FS = 48000.0
CHUNK = 480


def py_contract_signal():
    """純整數演算訊號:與 test_smoke.py 同一生成式(R3 鐵律:不用 sin)。"""
    i = np.arange(48000, dtype=np.uint64)
    return ((i * np.uint64(2654435761)) % np.uint64(96001)).astype(
        np.float64
    ) / 96000.0 * 0.02 - 0.01


def run_chunked(sig, chunk):
    s = iso532.ZwtvStream("free")
    parts = [s.push(sig[start : start + chunk]) for start in range(0, len(sig), chunk)]
    parts.append(s.flush())
    return tuple(np.concatenate([p[k] for p in parts]) for k in range(4))


def test_constants_are_frozen():
    assert iso532.ZwtvStream.latency_samples() == 24
    assert iso532.N_WARMUP_FRAMES == 580
    assert iso532.FLAG_CLAMPED_120DB == 1
    assert iso532.FLAG_NONFINITE_INPUT == 2
    assert iso532.FLAG_WARMUP == 4


def test_max_frames_for_chunk_bounds_push_output():
    sig = py_contract_signal()
    for chunk in (1, 24, CHUNK, 4096):
        cap = iso532.ZwtvStream.max_frames_for_chunk(chunk)
        s = iso532.ZwtvStream()
        for start in range(0, len(sig), chunk):
            n, _, _, _ = s.push(sig[start : start + chunk])
            assert len(n) <= cap


def test_chunk_invariance_bitwise():
    sig = py_contract_signal()
    base = run_chunked(sig, len(sig))
    for chunk in (1, 24, CHUNK, 4096):
        got = run_chunked(sig, chunk)
        for label, g, b in zip(("n", "n_phon", "t", "flags"), got, base):
            assert g.tobytes() == b.tobytes(), f"chunk={chunk}/{label}"


def test_stream_matches_batch_after_warmup():
    # 3 s(1500 幀):1 秒只有 500 幀 < N_WARMUP=580,n[w:] 會是空比較。
    sig = np.tile(py_contract_signal(), 3)
    batch_n, _, _, _ = iso532.loudness_zwtv(sig, FS)
    n, n_phon, t_idx, flags = run_chunked(sig, CHUNK)
    assert len(n) == len(batch_n) == 1500
    assert np.array_equal(t_idx, np.arange(len(n), dtype=np.uint64))
    w = iso532.N_WARMUP_FRAMES
    compared = n[w:]
    assert len(compared) > 0
    assert np.max(np.abs(compared - batch_n[w:])) <= 1e-9
    assert np.array_equal((flags & iso532.FLAG_WARMUP) != 0, t_idx < w)
    for v, s in zip(n[w : w + 8], n_phon[w : w + 8]):
        assert s == iso532.sone2phon(float(v))


def test_nan_is_flagged_not_raised():
    sig = py_contract_signal().copy()
    sig[4800:4848] = np.nan
    n, _, _, flags = run_chunked(sig, CHUNK)
    assert np.any((flags & iso532.FLAG_NONFINITE_INPUT) != 0)
    assert np.all(np.isfinite(n))


def test_tail_nan_surfaces_in_residual_flags():
    sig = np.zeros(48_048)
    sig[48_030] = np.nan
    s = iso532.ZwtvStream()
    n, _, _, flags = s.push(sig)
    assert len(n) == 501
    assert not np.any((flags & iso532.FLAG_NONFINITE_INPUT) != 0)
    fn, _, _, _ = s.flush()
    assert len(fn) == 0
    assert s.residual_flags & iso532.FLAG_NONFINITE_INPUT


def test_push_after_flush_raises_and_reset_recovers():
    sig = py_contract_signal()
    s = iso532.ZwtvStream()
    s.push(sig[:CHUNK])
    s.flush()
    fn, _, _, _ = s.flush()  # 冪等:不 raise,回空
    assert len(fn) == 0
    with pytest.raises(RuntimeError, match="reset"):
        s.push(sig[:CHUNK])
    s.reset()
    dirty_then_reset = [s.push(sig[start : start + CHUNK]) for start in range(0, len(sig), CHUNK)]
    dirty_then_reset.append(s.flush())
    got = tuple(np.concatenate([p[k] for p in dirty_then_reset]) for k in range(4))
    base = run_chunked(sig, CHUNK)
    for label, g, b in zip(("n", "n_phon", "t", "flags"), got, base):
        assert g.tobytes() == b.tobytes(), f"reset/{label}"


def test_input_validation():
    sig = py_contract_signal()
    s = iso532.ZwtvStream()
    with pytest.raises(TypeError):
        s.push(sig.astype(np.float32))
    with pytest.raises(TypeError):
        s.push(sig[::2])
    with pytest.raises(ValueError, match="field_type"):
        iso532.ZwtvStream("FREE")
```

- [ ] **Step 2: 確認 RED**

```bash
cd iso532-py && ../.venv/Scripts/python.exe -m pytest tests/test_stream.py -x 2>&1 | tail -3 && cd ..
```

Expected: FAIL/ERROR,`AttributeError: ... 'ZwtvStream'`(現有 wheel 無此 class)。

- [ ] **Step 3: Commit**

```bash
git add iso532-py/tests/test_stream.py
git commit -m "test: add failing ZwtvStream pytest suite (PRE-R6-P2)"
```

---

### Task 2: pyclass 實作(GREEN)

**Files:**
- Modify: `iso532-py/src/lib.rs`

- [ ] **Step 1: 在 lib.rs 追加(完整程式碼;既有函式不動)**

```rust
use numpy::PyArray1; // 既有 use 已含;此處僅示意
use pyo3::exceptions::PyRuntimeError;

type StreamOutput<'py> = (
    Bound<'py, PyArray1<f64>>, // n (sone)
    Bound<'py, PyArray1<f64>>, // n_phon
    Bound<'py, PyArray1<u64>>, // t_frame_index
    Bound<'py, PyArray1<u32>>, // flags
);

fn frames_to_arrays<'py>(
    py: Python<'py>,
    frames: &[iso532_core::StreamFrame],
) -> StreamOutput<'py> {
    let n: Vec<f64> = frames.iter().map(|f| f.n).collect();
    let n_phon: Vec<f64> = frames.iter().map(|f| f.n_phon).collect();
    let t: Vec<u64> = frames.iter().map(|f| f.t_frame_index).collect();
    let flags: Vec<u32> = frames.iter().map(|f| f.flags.bits()).collect();
    (
        n.into_pyarray(py),
        n_phon.into_pyarray(py),
        t.into_pyarray(py),
        flags.into_pyarray(py),
    )
}

/// Streaming time-varying loudness (ISO 532-1 zwtv), 48 kHz, 24-sample latency.
///
/// Single-threaded use only (the handle has no internal lock). Unlike the
/// batch API, non-finite samples do NOT raise: they are zeroed and reported
/// via the NONFINITE_INPUT flag on the frame that consumes them, or via
/// `residual_flags` after `flush()` if no frame follows. Before `flush()`,
/// `residual_flags` is provisional (pending flags travel with the next
/// output frame). `push()` after `flush()` raises RuntimeError; call
/// `reset()` to reuse the stream. Each call allocates fresh output arrays
/// (the zero-allocation guarantee is a Rust-core hot-path contract, not a
/// binding-level one).
#[pyclass(name = "ZwtvStream", unsendable)]
struct PyZwtvStream {
    // Boxed on purpose: the core stream is align(32) (inline AVX2 __m256d
    // constants), but Python object allocation only guarantees 16-byte
    // alignment. Storing it inline in the pyclass is UB and faults on
    // aligned SIMD loads whenever the object lands on a 16-mod-32 address.
    inner: Box<iso532_core::ZwtvStream>,
    scratch: Vec<iso532_core::StreamFrame>,
    flushed: bool,
}

#[pymethods]
impl PyZwtvStream {
    #[new]
    #[pyo3(signature = (field_type = "free"))]
    fn new(field_type: &str) -> PyResult<Self> {
        Ok(Self {
            inner: Box::new(iso532_core::ZwtvStream::new(parse_field(field_type)?)),
            scratch: Vec::new(),
            flushed: false,
        })
    }

    /// Push a chunk; returns (n, n_phon, t_frame_index, flags) for the
    /// frames completed by this chunk (possibly empty).
    fn push<'py>(
        &mut self,
        py: Python<'py>,
        chunk: PyReadonlyArray1<'py, f64>,
    ) -> PyResult<StreamOutput<'py>> {
        if self.flushed {
            return Err(PyRuntimeError::new_err(
                "stream is flushed; call reset() before pushing again",
            ));
        }
        let owned = contiguous(&chunk)?.to_vec();
        let cap = iso532_core::ZwtvStream::max_frames_for_chunk(owned.len());
        self.scratch.resize(cap.max(1), Default::default());
        let (inner, scratch) = (&mut self.inner, &mut self.scratch[..]);
        let written = py.allow_threads(move || inner.push(&owned, scratch));
        Ok(frames_to_arrays(py, &self.scratch[..written]))
    }

    /// Drain the held tail frame. Idempotent: repeated flushes return
    /// empty arrays. After flush, only `reset()` re-enables `push()`.
    fn flush<'py>(&mut self, py: Python<'py>) -> StreamOutput<'py> {
        self.scratch.resize(1, Default::default());
        let (inner, scratch) = (&mut self.inner, &mut self.scratch[..]);
        let written = py.allow_threads(move || inner.flush(scratch));
        self.flushed = true;
        frames_to_arrays(py, &self.scratch[..written])
    }

    /// Reset to a freshly-constructed stream (bitwise-equivalent output).
    fn reset(&mut self) {
        self.inner.reset();
        self.flushed = false;
    }

    /// Undelivered flag bits (provisional before `flush()`).
    #[getter]
    fn residual_flags(&self) -> u32 {
        self.inner.residual_flags().bits()
    }

    #[staticmethod]
    fn latency_samples() -> usize {
        iso532_core::ZwtvStream::latency_samples()
    }

    #[staticmethod]
    fn max_frames_for_chunk(chunk_len: usize) -> usize {
        iso532_core::ZwtvStream::max_frames_for_chunk(chunk_len)
    }
}
```

`#[pymodule]` 內追加:

```rust
    m.add_class::<PyZwtvStream>()?;
    m.add("N_WARMUP_FRAMES", iso532_core::N_WARMUP_FRAMES)?;
    m.add(
        "FLAG_CLAMPED_120DB",
        iso532_core::FrameFlags::CLAMPED_120DB.bits(),
    )?;
    m.add(
        "FLAG_NONFINITE_INPUT",
        iso532_core::FrameFlags::NONFINITE_INPUT.bits(),
    )?;
    m.add("FLAG_WARMUP", iso532_core::FrameFlags::WARMUP.bits())?;
```

實作註記:
- `allow_threads` 的閉包只捕捉 `&mut` 核心 handle 與 scratch slice(皆 `Send`),owned buffer move 進去——若編譯器對 `Ungil` 抱怨,依訊息調整捕捉方式,**行為不變**。
- `parse_field`/`contiguous` 沿用既有 helper,錯誤型別(ValueError/TypeError)自動與批次 API 一致,test_input_validation 依賴此點。
- 若 `FrameFlags`/`N_WARMUP_FRAMES` 的 re-export 路徑與上述不符,以 `iso532/src/lib.rs` 實際 pub 路徑為準,不改核心。

- [ ] **Step 2: build + GREEN**

```bash
cd iso532-py
../.venv/Scripts/python.exe -m maturin develop --release
../.venv/Scripts/python.exe -m pytest tests/test_stream.py -v    # 全 PASS
../.venv/Scripts/python.exe -m pytest tests/test_smoke.py -v     # 10/10 不變
cd ..
```

- [ ] **Step 3: fmt/clippy**

```bash
cargo fmt --check && cargo clippy -p iso532-py --all-targets -- -D warnings
```

- [ ] **Step 4: Commit**

```bash
git add iso532-py/src/lib.rs
git commit -m "feat: ZwtvStream pyclass — streaming loudness for Python (PRE-R6-P2)"
```

---

### Task 3: CI + 全量迴歸

**Files:**
- Modify: `.github/workflows/ci.yml`(py job 的 pytest 行)

- [ ] **Step 1: CI py job 把 stream 套件納入 smoke 層**

`"$VP" -m pytest tests/test_smoke.py -v` 改為 `"$VP" -m pytest tests/test_smoke.py tests/test_stream.py -v`(stream 套件無 mosqito 依賴,兩平台皆可跑)。

- [ ] **Step 2: 完整驗證(`.codex/skills/iso532-r3-verification` 全流程)**

```bash
cargo test && cargo test -p iso532-ffi --features test-panic
cd iso532 && cargo test --test golden_zwtv dump_zwtv_output_hashes -- --ignored --nocapture && cd ..   # 12/12 不變
cd iso532-py && ISO532_REQUIRE_PARITY=1 ../.venv/Scripts/python.exe -m pytest tests/test_parity_mosqito.py -q && cd ..  # 18/18
git diff --exit-code iso532/src iso532/tests iso532-ffi/    # 核心與 FFI 零 diff(本 phase 最高約束)
```

- [ ] **Step 3: Commit + push**

```bash
git add .github/workflows/ci.yml
git commit -m "ci: run ZwtvStream pytest suite in py job (PRE-R6-P2)"
git push
```

- [ ] **Step 4: 請使用者確認 GitHub Actions 三 job 全綠。**

---

### Task 4: tag v0.1.0 + 收尾

- [ ] **Step 1: CI 綠燈確認後打 tag(三方案全量交付點)**

```bash
git tag -a v0.1.0 -m "engine v0.1.0 — C ABI v1 frozen; batch+stream, C header + Python (batch/stream/sone2phon)"
git push origin v0.1.0
```

(push 若因 SSH agent 不在而失敗,請使用者用 SourceTree push tag。)

- [ ] **Step 2: 收尾註記(全部實測值,不得杜撰)**

```markdown
---
## 收尾註記(執行完成後填)
- commits:<test/feat/ci 三個 hash>;tag:v0.1.0 @ <hash>;CI:<三 job 狀態>。
- pytest:test_stream <N> passed;smoke 10/10;parity 18/18 0 skipped。
- hash gate 12/12:<不變/漂移>;核心/FFI 零 diff:<是/否>。
- 偏差(若有):<無/列點——含 pyo3 Ungil 捕捉調整、re-export 路徑差異等>
```

```bash
git add docs/superpowers/plans/phases/phase-pre-r6-2-py-stream.md
git commit -m "docs: PRE-R6-P2 closeout — v0.1.0 tagged" && git push
```

---

## 風險與陷阱

| # | 風險 | 機率 | 影響 | 緩解 |
|---|---|---|---|---|
| 1 | flush 後 push 讓核心 assert 以 PanicException 洩出 | 高(不擋必發) | 中 | binding `flushed` 旗標先擋 → RuntimeError;測試看守 |
| 2 | `allow_threads` 的 `Ungil` 邊界與 `&mut self` 借用衝突 | 中 | 低 | 先拆借用再進閉包(程式碼已示範);編譯器訊息為準,行為不變 |
| 3 | 測試誤用 sin 合成訊號 → libm ULP 假紅 | 低(已寫死) | 中 | 測試沿用 py_contract_signal 純整數生成式 |
| 4 | 誤動核心/FFI(如順手加 re-export) | 低 | 高 | Task 3 Step 2 的 `git diff --exit-code` 是硬 gate |
| 5 | chunk 邊界切片非連續觸發 TypeError 假紅 | 低 | 低 | 1-D 步幅 1 切片必為 C-contiguous;test_input_validation 反向驗證 `[::2]` 被拒 |

---
## 本次收尾實測(2026-07-19,本機；CI/tag 待確認)
- commits:`063a27b`(test),`0052088`(feat),`0f36ba4`(ci);tag:尚未建立;CI:尚未觀測(依指示不 push/tag)。
- pytest:`test_stream` 8 passed;`test_smoke` 10 passed;CI 清單合跑 18 passed;strict parity 18 passed/0 skipped;collect-only 36 tests。
- E3:1500 frames,比較窗 920 frames,warmup 後 max diff=`3.2356339829675562e-11`(<=`1e-9`)。
- hash gate:12/12 不變;py-contract `n=0x44e6822074554786`,`time=0xf076bcb342595537`,500 frames;golden manifest 175 files match。
- FFI:17 passed;cbindgen 0.29.4 產生 header 零 diff;fmt/clippy clean;核心/FFI 零 diff:是。
- 偏差:完整 workspace `cargo test` 三次皆在 `simd_dispatch` 連結階段因主機 `LNK1104` 無法建立 test exe 而受阻(含新 `D:\tmp` target);此 gate 不可宣稱 green。WSL `bash -n` ACL 被拒後，native Git Bash `bash -n tools/setup_env.sh` 通過。