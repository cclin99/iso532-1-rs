# R3-P3:iso532-py(Python binding + parity 迴歸傘)Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** pyo3 Python binding(abi3-py39 wheel)+ pytest parity 傘(9 組訊號 vs mosqito)+ 跨語言 bitwise 契約測試 + CI 雙平台 wheel build。

**Architecture:** `iso532-py` 獨立 crate,**直接 path 依賴 `iso532`(不經 C-ABI)**;pyo3 `allow_threads` 釋放 GIL,`into_pyarray` 零拷貝輸出。pytest 分兩層:`test_smoke.py`(無 mosqito,CI 可跑,含 bitwise 契約)與 `test_parity_mosqito.py`(本機 `.venv`,之後所有階段的迴歸傘)。

**Tech Stack:** pyo3 0.23(abi3-py39)+ rust-numpy 0.23 + maturin ≥1.7、pytest、numpy。(若 0.23 已不可用,改用當下最新的 pyo3/numpy **同號配對**,並在收尾註記記錄。)

**Spec:** `docs/superpowers/specs/2026-07-10-r3-c-abi-python-binding-design.md` §6、§9
**前置:** R3-P1(`.venv` 已鎖版本)、R3-P2(`iso532-ffi` 的 `dump_py_bitwise_contract_hashes` 已存在)

**Exit Gate:** pytest parity 9 組全過(rtol 1e-6 / atol 1e-9);CI 雙平台 wheel artifact + smoke 測試綠;bitwise 測試過。

---

## 背景(給零脈絡的工程師)

- **命名地雷**:Python 模組要叫 `iso532`,但依賴的 Rust crate 也叫 `iso532`——lib target 與依賴同名會撞。解法:renamed dependency `iso532_core = { package = "iso532", path = "../iso532" }`,程式碼裡用 `iso532_core::`。
- **bitwise 訊號地雷**:跨語言 bitwise 測試的訊號**不得用 sin 合成**(numpy 與 Rust 是不同 libm,訊號本身就差 ULP)。用純整數演算訊號(只有 IEEE 確定性運算):`s[i] = ((i*2654435761) mod 96001)/96000.0*0.02 - 0.01`,i∈0..48000。R3-P2 已放好 Rust 端凍結工具。
- `n`/`time_axis` 已實證跨平台跨 backend 逐位穩定(`docs/CI-HASH-GATE-DEBUG-2026-07-10.md`),bitwise 測試只驗這兩項。
- Rust API:`iso532_core::loudness_zwtv(&[f64], fs, FieldType) -> Result<LoudnessTimeVarying, Iso532Error>`;`n_specific` 是 240×frames bark-major row-major 扁平 Vec。zwst 回 `LoudnessStationary { n: f64, n_specific, bark_axis }`。
- mosqito Python API(parity 對照組):`from mosqito.sq_metrics import loudness_zwtv, loudness_zwst`;zwtv 回 `(N, N_spec(240,frames), bark_axis, time_axis)`,zwst 回 `(N, N_specific, bark_axis)`。
- `.venv`(P1 已鎖)是 parity 的執行環境;Git Bash 下啟用:`source .venv/Scripts/activate`。

### Task 0 開始前

```bash
cd /d/ISO532 && ls tools/requirements.lock iso532-ffi/tests/ffi.rs && .venv/Scripts/python.exe -c "import mosqito; print('ok')"
```

---

### Task 1: pytest 測試先行(red)

**Files:**
- Create: `iso532-py/tests/test_smoke.py`
- Modify: `.gitignore`(加 `iso532-py/dist/`、`.pytest_cache/`、`__pycache__/`)

- [ ] **Step 1: test_smoke.py(完整程式碼;無 mosqito 依賴,CI 可跑)**

```python
"""Smoke + cross-language bitwise contract tests (no mosqito; runs in CI)."""
import numpy as np
import pytest

import iso532

FS = 48000.0

# Frozen from Rust (R3-P2 tooling):
#   cd iso532-ffi && cargo test --test ffi dump_py_bitwise_contract_hashes -- --ignored --nocapture
# n/time_axis are bitwise-stable across platforms and backends (see
# docs/CI-HASH-GATE-DEBUG-2026-07-10.md). Values MUST come from an actual
# dump run — never invented, never copied from another signal.
N_HASH = 0x0     # 凍結步驟(Task 3)以實測值取代
TIME_HASH = 0x0  # 凍結步驟(Task 3)以實測值取代


def py_contract_signal():
    """純整數演算訊號:與 iso532-ffi/tests/ffi.rs 的 py_contract_signal 逐位相同。"""
    i = np.arange(48000, dtype=np.uint64)
    return ((i * np.uint64(2654435761)) % np.uint64(96001)).astype(
        np.float64
    ) / 96000.0 * 0.02 - 0.01


def fnv1a_f64(arr):
    """與 iso532/tests/common/mod.rs 的 fnv1a_f64 同一演算法。"""
    h = 0xCBF29CE484222325
    for b in np.ascontiguousarray(arr, dtype="<f8").tobytes():
        h ^= b
        h = (h * 0x100000001B3) & 0xFFFFFFFFFFFFFFFF
    return h


def test_zwtv_shapes_and_axes():
    n, spec, bark, time = iso532.loudness_zwtv(py_contract_signal(), FS)
    assert n.shape == (500,)  # ceil(ceil(48000/24)/4)
    assert time.shape == (500,)
    assert spec.shape == (240, 500)
    assert bark.shape == (240,)
    assert bark[0] == pytest.approx(0.1)
    assert bark[-1] == pytest.approx(24.0)
    assert np.all(np.isfinite(n)) and np.all(n >= 0)


def test_zwtv_diffuse_accepted():
    n, _spec, _bark, _time = iso532.loudness_zwtv(py_contract_signal(), FS, "diffuse")
    assert n.shape == (500,)


def test_zwst_shapes():
    n, spec, bark = iso532.loudness_zwst(py_contract_signal(), FS)
    assert isinstance(n, float) and n > 0
    assert spec.shape == (240,)
    assert bark.shape == (240,)


def test_bitwise_contract_n_and_time_axis():
    n, _spec, _bark, time = iso532.loudness_zwtv(py_contract_signal(), FS)
    assert hex(fnv1a_f64(n)) == hex(N_HASH)
    assert hex(fnv1a_f64(time)) == hex(TIME_HASH)


def test_error_mapping():
    sig = py_contract_signal()
    with pytest.raises(ValueError, match="48000"):
        iso532.loudness_zwtv(sig, 44100.0)
    with pytest.raises(ValueError, match="too short"):
        iso532.loudness_zwtv(sig[:100].copy(), FS)
    with pytest.raises(ValueError, match="field_type"):
        iso532.loudness_zwtv(sig, FS, "FREE")


def test_strict_input_contract():
    sig = py_contract_signal()
    with pytest.raises(TypeError):
        iso532.loudness_zwtv(sig.astype(np.float32), FS)  # dtype 不符
    with pytest.raises(TypeError):
        iso532.loudness_zwtv(sig[::2], FS)  # 非連續 view
```

- [ ] **Step 2: `.gitignore` 追加(同 P1 注意:只揀本任務的 hunk)**

```
iso532-py/dist/
.pytest_cache/
__pycache__/
```

- [ ] **Step 3: 確認 red**

```bash
source .venv/Scripts/activate
python -m pip install --quiet pytest
pytest iso532-py/tests/test_smoke.py -x 2>&1 | tail -3
```

Expected: FAIL/ERROR,`ModuleNotFoundError: No module named 'iso532'`。

- [ ] **Step 4: Commit**

```bash
git add iso532-py/tests/test_smoke.py
git add -p .gitignore
git commit -m "test: add failing pytest smoke suite for iso532-py (R3-P3)"
```

---

### Task 2: binding 實作(green,bitwise 除外)

**Files:**
- Create: `iso532-py/Cargo.toml`
- Create: `iso532-py/pyproject.toml`
- Create: `iso532-py/src/lib.rs`

- [ ] **Step 1: Cargo.toml**

```toml
[package]
name = "iso532-py"
version = "0.1.0"
edition = "2021"
description = "Python bindings for the iso532 crate (ISO 532-1:2017 Zwicker loudness)"
license = "Apache-2.0"

[lib]
# Python 模組名;與依賴 crate 同名會撞,故依賴用 renamed dep iso532_core
name = "iso532"
crate-type = ["cdylib"]

[dependencies]
iso532_core = { package = "iso532", path = "../iso532" }
pyo3 = { version = "0.23", features = ["abi3-py39", "extension-module"] }
numpy = "0.23"
```

- [ ] **Step 2: pyproject.toml**

```toml
[build-system]
requires = ["maturin>=1.7,<2"]
build-backend = "maturin"

[project]
name = "iso532"
description = "ISO 532-1:2017 Zwicker loudness (Rust iso532 crate bindings)"
requires-python = ">=3.9"
dependencies = ["numpy>=1.24"]
dynamic = ["version"]

[tool.maturin]
module-name = "iso532"
```

- [ ] **Step 3: src/lib.rs(完整程式碼)**

```rust
//! Python bindings for the `iso532` crate. Batch API only (R3); the
//! streaming API arrives with R5. GIL is released during computation;
//! outputs are moved into numpy arrays without an extra copy.

use numpy::ndarray::Array2;
use numpy::{IntoPyArray, PyArray1, PyArray2, PyReadonlyArray1};
use pyo3::exceptions::{PyTypeError, PyValueError};
use pyo3::prelude::*;

fn parse_field(s: &str) -> PyResult<iso532_core::FieldType> {
    match s {
        "free" => Ok(iso532_core::FieldType::Free),
        "diffuse" => Ok(iso532_core::FieldType::Diffuse),
        other => Err(PyValueError::new_err(format!(
            "field_type must be \"free\" or \"diffuse\", got {other:?}"
        ))),
    }
}

fn contiguous<'py, 'a>(signal: &'a PyReadonlyArray1<'py, f64>) -> PyResult<&'a [f64]> {
    signal
        .as_slice()
        .map_err(|_| PyTypeError::new_err("signal must be a C-contiguous 1-D float64 ndarray"))
}

/// Time-varying loudness (ISO 532-1 zwtv).
/// Returns (n[frames], n_specific[240, frames], bark_axis[240], time_axis[frames]).
#[pyfunction]
#[pyo3(signature = (signal, fs, field_type = "free"))]
fn loudness_zwtv<'py>(
    py: Python<'py>,
    signal: PyReadonlyArray1<'py, f64>,
    fs: f64,
    field_type: &str,
) -> PyResult<(
    Bound<'py, PyArray1<f64>>,
    Bound<'py, PyArray2<f64>>,
    Bound<'py, PyArray1<f64>>,
    Bound<'py, PyArray1<f64>>,
)> {
    let field = parse_field(field_type)?;
    let slice = contiguous(&signal)?;
    let r = py
        .allow_threads(|| iso532_core::loudness_zwtv(slice, fs, field))
        .map_err(|e| PyValueError::new_err(e.to_string()))?;
    let frames = r.n.len();
    // 240×frames row-major(bark-major)扁平 Vec → (240, frames) C-order,零拷貝
    let spec = Array2::from_shape_vec((240, frames), r.n_specific)
        .expect("n_specific is 240*frames by construction")
        .into_pyarray(py);
    Ok((
        r.n.into_pyarray(py),
        spec,
        r.bark_axis.into_pyarray(py),
        r.time_axis.into_pyarray(py),
    ))
}

/// Stationary loudness (ISO 532-1 zwst).
/// Returns (n, n_specific[240], bark_axis[240]).
#[pyfunction]
#[pyo3(signature = (signal, fs, field_type = "free"))]
fn loudness_zwst<'py>(
    py: Python<'py>,
    signal: PyReadonlyArray1<'py, f64>,
    fs: f64,
    field_type: &str,
) -> PyResult<(f64, Bound<'py, PyArray1<f64>>, Bound<'py, PyArray1<f64>>)> {
    let field = parse_field(field_type)?;
    let slice = contiguous(&signal)?;
    let r = py
        .allow_threads(|| iso532_core::loudness_zwst(slice, fs, field))
        .map_err(|e| PyValueError::new_err(e.to_string()))?;
    Ok((r.n, r.n_specific.into_pyarray(py), r.bark_axis.into_pyarray(py)))
}

#[pymodule]
fn iso532(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(loudness_zwtv, m)?)?;
    m.add_function(wrap_pyfunction!(loudness_zwst, m)?)?;
    m.add("__version__", env!("CARGO_PKG_VERSION"))?;
    Ok(())
}
```

- [ ] **Step 4: 裝進 .venv 並跑測試**

```bash
source .venv/Scripts/activate
python -m pip install --quiet maturin
cd iso532-py && maturin develop --release && cd ..
pytest iso532-py/tests/test_smoke.py -v
```

Expected: **只有 `test_bitwise_contract_n_and_time_axis` FAIL**(常數還是 0x0),其餘全 PASS。若編譯錯誤來自 pyo3/numpy API 差異(版本演進),依編譯器訊息修正,保持行為不變。

- [ ] **Step 5: fmt/clippy**

```bash
cd iso532-py && cargo fmt && cargo clippy --all-targets -- -D warnings && cd ..
```

- [ ] **Step 6: Commit**

```bash
git add iso532-py/Cargo.toml iso532-py/pyproject.toml iso532-py/src/lib.rs
git commit -m "feat: iso532-py pyo3 binding (zwtv+zwst, abi3-py39, GIL released)"
```

---

### Task 3: 凍結 bitwise 契約常數

**Files:**
- Modify: `iso532-py/tests/test_smoke.py`(兩個常數)

- [ ] **Step 1: 從 Rust 端取實測值(R3-P2 已放好工具)**

```bash
cd iso532-ffi && cargo test --test ffi dump_py_bitwise_contract_hashes -- --ignored --nocapture 2>&1 | grep py-contract && cd ..
```

Expected: `py-contract: n=0x................ time=0x................ frames=500`。

- [ ] **Step 2: 把印出的值填入 test_smoke.py 的 `N_HASH`/`TIME_HASH`**

**反作假條款:必須是上一步實際印出的值。**填入後刪除兩行「凍結步驟(Task 3)…」註解。

- [ ] **Step 3: 驗證 green(跨語言逐位契約成立的時刻)**

```bash
source .venv/Scripts/activate && pytest iso532-py/tests/test_smoke.py -v
```

Expected: 全 PASS。若 bitwise FAIL:先檢查訊號生成是否逐位一致(兩邊各 dump 前 5 個樣本的 `to_le_bytes`/`tobytes().hex()` 比對),**不得放寬為容差比對**——契約依據是 `n`/`time_axis` 的實證跨平台穩定性。

- [ ] **Step 4: Commit**

```bash
git add iso532-py/tests/test_smoke.py
git commit -m "test: freeze cross-language bitwise contract for n/time_axis (R3-P3)"
```

---

### Task 4: pytest parity 迴歸傘(9 組訊號 vs mosqito)

**Files:**
- Create: `iso532-py/tests/test_parity_mosqito.py`

- [ ] **Step 1: 寫 parity 測試(完整程式碼)**

```python
"""Parity umbrella: Rust binding vs mosqito 1.2.1 direct run (spec §9).

Runs ONLY in the local .venv (mosqito + data/annexb present); skips
cleanly elsewhere. This suite is the regression umbrella for every
phase after R3 — do not weaken tolerances to make a change pass.
Expected runtime: ~5-10 min (mosqito zwtv is ~0.45x realtime).
"""
import sys
from pathlib import Path

import numpy as np
import pytest

pytest.importorskip("mosqito")
from mosqito.sq_metrics import loudness_zwst, loudness_zwtv  # noqa: E402

import iso532  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
if not (ROOT / "data" / "annexb").is_dir():
    pytest.skip("data/annexb missing — run tools/setup_env.sh", allow_module_level=True)

sys.path.insert(0, str(ROOT / "tools"))
from gen_golden import FS, make_signals  # noqa: E402

NAMES = [
    "sine_1k_60",
    "sine_250_80",
    "sine_4k_60",
    "white_60",
    "pulse_1k_70",
    "step_60_80",
    "annexb_sig3",
    "annexb_sig5",
    "annexb_sig10",
]

# 與 iso532/tests golden 端對端容差一致(spec §9;實測可達再單向收緊)
RTOL, ATOL = 1e-6, 1e-9


@pytest.fixture(scope="session")
def signals():
    return make_signals()


@pytest.mark.parametrize("name", NAMES)
def test_zwtv_parity(signals, name):
    sig = np.ascontiguousarray(signals[name], dtype=np.float64)
    want = loudness_zwtv(sig, float(FS))
    got = iso532.loudness_zwtv(sig, float(FS))
    for label, g, w in zip(("N", "N_specific", "bark", "time"), got, want):
        np.testing.assert_allclose(
            g,
            np.asarray(w, dtype=np.float64),
            rtol=RTOL,
            atol=ATOL,
            err_msg=f"{name}/{label}",
        )


@pytest.mark.parametrize("name", NAMES)
def test_zwst_parity(signals, name):
    sig = np.ascontiguousarray(signals[name], dtype=np.float64)
    want_n, want_spec, want_bark = loudness_zwst(sig, float(FS))
    got_n, got_spec, got_bark = iso532.loudness_zwst(sig, float(FS))
    np.testing.assert_allclose(got_n, float(want_n), rtol=RTOL, atol=ATOL, err_msg=f"{name}/N")
    np.testing.assert_allclose(
        got_spec,
        np.asarray(want_spec, dtype=np.float64).ravel(),
        rtol=RTOL,
        atol=ATOL,
        err_msg=f"{name}/N_specific",
    )
    np.testing.assert_allclose(got_bark, want_bark, rtol=RTOL, atol=ATOL, err_msg=f"{name}/bark")
```

- [ ] **Step 2: 跑 parity(約 5–10 分鐘)**

```bash
source .venv/Scripts/activate && pytest iso532-py/tests/test_parity_mosqito.py -v
```

Expected: 18 passed(zwtv 9 + zwst 9),0 skipped。若個別訊號超容差:記錄實際 max diff,對照 `iso532/tests/golden_zwtv.rs` 同訊號是否也超(golden 用同容差)——golden 綠而 parity 紅才是 binding 的 bug;兩者都紅則停下回報。

- [ ] **Step 3: Commit**

```bash
git add iso532-py/tests/test_parity_mosqito.py
git commit -m "test: mosqito parity umbrella, 9 signals x zwtv+zwst (R3-P3)"
```

---

### Task 5: lock 更新 + binding 開銷量測 + CI py job

**Files:**
- Modify: `tools/requirements.lock`(納入 maturin/pytest)
- Create: `tools/bench_binding.py`
- Modify: `.github/workflows/ci.yml`(追加 py job)

- [ ] **Step 1: 更新 requirements.lock(venv 多了 maturin/pytest)**

```bash
.venv/Scripts/python.exe -m pip freeze --exclude mosqito --exclude iso532 > tools/requirements.lock
```

然後把 P1 的 5 行標頭註解(`# Frozen environment ...` 至 `# Regenerate ...`)原樣插回檔案開頭,並把 Regenerate 行改為:
`# Regenerate: .venv/Scripts/python.exe -m pip freeze --exclude mosqito --exclude iso532`

- [ ] **Step 2: tools/bench_binding.py(spec §13 指標:binding 開銷 ≤ +2%)**

```python
"""Binding-overhead check (spec §13). Compare against a SAME-DAY
`cargo bench` zwtv number on this machine (X2 iron law: no cross-day
comparison of historical numbers)."""
import time

import numpy as np

import iso532

FS = 48000
i = np.arange(10 * FS, dtype=np.uint64)
sig = ((i * np.uint64(2654435761)) % np.uint64(96001)).astype(np.float64) / 96000.0 * 0.02 - 0.01

iso532.loudness_zwtv(sig, float(FS))  # warm-up
best = float("inf")
for _ in range(20):
    t0 = time.perf_counter()
    iso532.loudness_zwtv(sig, float(FS))
    best = min(best, time.perf_counter() - t0)
print(f"binding zwtv 10s best-of-20: {best * 1e3:.1f} ms")
```

- [ ] **Step 3: 量測並記錄(收尾註記用)**

```bash
source .venv/Scripts/activate && python tools/bench_binding.py
cd iso532 && cargo bench --bench loudness -- zwtv 2>&1 | tail -20 && cd ..
```

記下兩個數字;binding best-of-20 對 criterion 同日數字的差 ≤ +2% 即達標(略超不阻塞——記錄實測值,差 >5% 才需調查)。

- [ ] **Step 4: ci.yml 追加 py job(`jobs:` 層級)**

```yaml
  py:
    strategy:
      fail-fast: false
      matrix:
        os: [windows-latest, ubuntu-latest]
    runs-on: ${{ matrix.os }}
    defaults:
      run:
        working-directory: iso532-py
        shell: bash
    steps:
      - uses: actions/checkout@v4
      - uses: dtolnay/rust-toolchain@stable
        with:
          components: rustfmt, clippy
      - uses: Swatinem/rust-cache@v2
        with:
          workspaces: iso532-py
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: cargo fmt --check
      - run: cargo clippy --all-targets -- -D warnings
      - run: pip install maturin && maturin build --release --out dist
      - name: install wheel into clean venv, run smoke suite
        run: |
          python -m venv sv
          if [ -x sv/bin/python ]; then VP=sv/bin/python; else VP=sv/Scripts/python.exe; fi
          "$VP" -m pip install --quiet dist/*.whl pytest
          "$VP" -m pytest tests/test_smoke.py -v
      - uses: actions/upload-artifact@v4
        with:
          name: wheel-${{ matrix.os }}
          path: iso532-py/dist/*.whl
          if-no-files-found: error
```

(smoke suite 含 bitwise 測試——`n`/`time_axis` hash 跨平台穩定,兩個 runner 都必須綠;mosqito parity 不上 CI,那是本機 `.venv` 的事。)

- [ ] **Step 5: Commit + push**

```bash
git add tools/requirements.lock tools/bench_binding.py .github/workflows/ci.yml
git commit -m "ci: add py job — dual-platform wheel build + smoke suite (R3-P3)"
git push
```

- [ ] **Step 6: 請使用者確認 GitHub Actions**

無 gh CLI/token——請使用者開 Actions 頁確認 `test`/`ffi`/`py` 三個 job 全綠。紅燈時抄回失敗 log 迭代。

---

### Task 6: Exit Gate 檢查 + 收尾

- [ ] **Step 1: 總驗收清單(spec §12)逐條核對**

```bash
cd /d/ISO532
git diff --stat e96dffa..HEAD -- iso532/src/        # 應為空(準則 6)
grep -c "v0" iso532-ffi/include/iso532.h            # ≥1(準則 5)
source .venv/Scripts/activate && pytest iso532-py/tests -v   # 全綠(準則 2、3 的 py 面)
```

- [ ] **Step 2: 在本檔尾追加收尾註記並 commit**

```markdown
---
## 收尾註記(執行完成後填)
- CI:test/ffi/py 三 job 雙平台全綠(<commit>)。
- parity 實測:18 passed,耗時 <分:秒>;最大偏差 <值>(容差 rtol 1e-6/atol 1e-9)。
- bitwise 契約:N_HASH=<hex> TIME_HASH=<hex>(凍結自 dump_py_bitwise_contract_hashes)。
- binding 開銷:python <ms> vs cargo bench <ms>(同日同機),差 <百分比>。
- wheel:wheel-windows-latest / wheel-ubuntu-latest artifacts 存在。
- 偏差(若有):<無/列點>
```

(全部填實測值,不得杜撰。)

```bash
git add docs/superpowers/plans/phases/phase-r3-3-python.md
git commit -m "docs: R3-P3 closeout — R3 exit gates met" && git push
```
