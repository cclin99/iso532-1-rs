# R3 審查修復 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 收掉 `docs/R3-REVIEW-2026-07-11.md` 的發現 #1–#9(#10 明確遞延 R5),在 R5 凍結 ABI v1 前補齊契約守衛。

**Architecture:** 四個獨立 phase,每個 phase 結束時全套測試綠、可單獨進版:F1 把 ABI 契約(框架數、錯誤碼、場型)的單一事實來源收進 core 並用 CI 機器強制 header 同步;F2 修 Python binding 的 GIL 資料競爭與 parity 套件 collection 錯誤;F3 讓 golden 凍結契約從「有文件」變「有腳本守衛」;F4 把跨語言 bitwise 契約工具收斂到單一來源。

**Tech Stack:** Rust(iso532 core / iso532-ffi / iso532-py)、pyo3 0.23 + numpy 0.23、cbindgen 0.29.4(本機已裝,CI 需 pin 同版)、pytest、GitHub Actions。

**審查依據:** `docs/R3-REVIEW-2026-07-11.md` §2(發現編號 #1–#10 沿用該表)。

**環境前提(本機,Windows):** repo 根 `D:\ISO532`;golden 資料在 `data/`(local-only);Python 工具鏈 venv 在 `.venv/`(含 maturin 1.14.1)。Rust 測試命令均在對應 crate 目錄下執行。

---

## Phase F1 — ABI 契約強化(發現 #2、#3、#4、#9 的 core 部分)

### Task 1: core 匯出 `zwtv_out_frames`,消滅 binding 手抄公式

**Files:**
- Modify: `iso532/src/zwtv/mod.rs`(常數化 + 新函式 + 既有字面值替換)
- Modify: `iso532/src/lib.rs:51`(re-export)
- Test: `iso532/src/zwtv/mod.rs` 內的 `#[cfg(test)] mod tests`

- [ ] **Step 1: 寫失敗測試**

在 `iso532/src/zwtv/mod.rs` 的 `mod tests` 內新增(緊鄰既有測試):

```rust
#[test]
fn zwtv_out_frames_matches_pipeline_output() {
    // 覆蓋 len mod 96 的關鍵邊界 + 一個大值:公式對 24/4 兩層 ceil 逐段常數
    let signal: Vec<f64> = (0..48_000)
        .map(|i| (i % 480) as f64 / 480.0 * 0.02 - 0.01)
        .collect();
    for len in [4800usize, 4801, 4823, 4824, 4895, 4896, 4897, 48_000] {
        let n = loudness_zwtv(&signal[..len], 48_000.0, FieldType::Free)
            .unwrap()
            .n
            .len();
        assert_eq!(super::zwtv_out_frames(len), n, "len={len}");
    }
}
```

- [ ] **Step 2: 跑測試確認編譯失敗**

Run: `cd iso532 && cargo test zwtv_out_frames_matches -- --nocapture`
Expected: 編譯錯誤 `cannot find function zwtv_out_frames in module super`

- [ ] **Step 3: 實作**

`iso532/src/zwtv/mod.rs`——在 `ParMode` 定義前加入:

```rust
/// 輸出格線相對 third-octave 框架的再抽取因子(2 ms 格線)。
pub(crate) const OUT_DECIM: usize = 4;

/// `loudness_zwtv` 對 `signal_len` 樣本輸入的輸出框架數:
/// ceil(ceil(signal_len / DEC_FACTOR) / OUT_DECIM)。純函數、不驗證輸入;
/// C ABI 的 `iso532_zwtv_out_frames` 必須直接轉發本函式(勿手抄公式)。
pub fn zwtv_out_frames(signal_len: usize) -> usize {
    signal_len
        .div_ceil(third_octave_levels::DEC_FACTOR)
        .div_ceil(OUT_DECIM)
}
```

同檔案把 `process()` 內的三處字面值 `4` 換成 `OUT_DECIM`(語義同一才換;`240` 不動):

```rust
        let n_out = n_time.div_ceil(OUT_DECIM);           // 原 line 66
```
```rust
        self.loudness
            .par_chunks_mut(OUT_DECIM)                    // 原 line 70
```
```rust
                let t0 = out_idx * OUT_DECIM;             // 原 line 74
```
```rust
        for t in (0..n_time).step_by(OUT_DECIM) {         // 原 line 88
```

`iso532/src/lib.rs:51` 改為:

```rust
pub use zwtv::{loudness_zwtv, zwtv_out_frames, ZwtvProcessor};
```

- [ ] **Step 4: 跑測試確認通過 + 純重構驗證(hash gate 不得動)**

Run: `cd iso532 && cargo test`
Expected: 全綠;特別確認 `hash_gate` 測試通過(本 task 是純重構,任何 hash 變化 = 改壞了,停下調查)。

- [ ] **Step 5: Commit**

```bash
git add iso532/src/zwtv/mod.rs iso532/src/lib.rs
git commit -m "feat(core): export zwtv_out_frames, single source for output framing (review #2)"
```

### Task 2: core 提供 `Iso532Error::code()` 與 `FieldType` 標準轉換

**Files:**
- Modify: `iso532/src/error.rs`
- Modify: `iso532/src/lib.rs:52-56`(FieldType 定義後加 impl)
- Test: 兩檔各自的 `#[cfg(test)]`(error.rs 目前無測試模組,新建)

- [ ] **Step 1: 寫失敗測試**

`iso532/src/error.rs` 檔尾新增:

```rust
#[cfg(test)]
mod tests {
    use super::Iso532Error;

    /// 凍結表:C ABI 的 ISO532_ERR_* 正值鏡像這裡,不得重編號。
    #[test]
    fn error_codes_are_frozen() {
        assert_eq!(Iso532Error::LevelExceeds120dB.code(), 1);
        assert_eq!(Iso532Error::SignalTooShort { got: 0, need: 4800 }.code(), 2);
        assert_eq!(Iso532Error::UnsupportedSampleRate(44_100.0).code(), 3);
    }
}
```

`iso532/src/lib.rs` 既有測試區(或檔尾新建 `#[cfg(test)] mod field_type_tests`)新增:

```rust
#[cfg(test)]
mod field_type_tests {
    use crate::FieldType;

    #[test]
    fn try_from_i32_matches_abi_table() {
        assert_eq!(FieldType::try_from(0), Ok(FieldType::Free));
        assert_eq!(FieldType::try_from(1), Ok(FieldType::Diffuse));
        assert_eq!(FieldType::try_from(2), Err(2));
        assert_eq!(FieldType::try_from(-1), Err(-1));
    }

    #[test]
    fn from_str_matches_py_vocabulary() {
        assert_eq!("free".parse(), Ok(FieldType::Free));
        assert_eq!("diffuse".parse(), Ok(FieldType::Diffuse));
        assert!("FREE".parse::<FieldType>().is_err()); // 大小寫敏感,py 契約如此
    }
}
```

- [ ] **Step 2: 跑測試確認編譯失敗**

Run: `cd iso532 && cargo test error_codes_are_frozen try_from_i32 from_str_matches`
Expected: 編譯錯誤(`code` 方法與兩個 trait impl 不存在)

- [ ] **Step 3: 實作**

`iso532/src/error.rs` 的 enum 定義後:

```rust
impl Iso532Error {
    /// 穩定數值代碼;C ABI 的 ISO532_ERR_*(正值)鏡像本表。凍結:
    /// 新變體只能追加新代碼,既有編號不得改動。
    pub fn code(&self) -> i32 {
        match self {
            Iso532Error::LevelExceeds120dB => 1,
            Iso532Error::SignalTooShort { .. } => 2,
            Iso532Error::UnsupportedSampleRate(_) => 3,
        }
    }
}
```

`iso532/src/lib.rs` 的 `FieldType` 定義後:

```rust
impl TryFrom<i32> for FieldType {
    type Error = i32;
    /// C ABI 契約:0 = Free、1 = Diffuse(ISO532_FIELD_* 鏡像本表)。
    fn try_from(v: i32) -> Result<Self, i32> {
        match v {
            0 => Ok(FieldType::Free),
            1 => Ok(FieldType::Diffuse),
            other => Err(other),
        }
    }
}

impl std::str::FromStr for FieldType {
    type Err = ();
    /// Python binding 契約:"free" / "diffuse",大小寫敏感。
    fn from_str(s: &str) -> Result<Self, ()> {
        match s {
            "free" => Ok(FieldType::Free),
            "diffuse" => Ok(FieldType::Diffuse),
            _ => Err(()),
        }
    }
}
```

- [ ] **Step 4: 跑測試確認通過**

Run: `cd iso532 && cargo test`
Expected: 全綠(含新三測試)。

- [ ] **Step 5: Commit**

```bash
git add iso532/src/error.rs iso532/src/lib.rs
git commit -m "feat(core): stable error codes + FieldType conversions for bindings (review #9)"
```

### Task 3: ffi 消費 core 單一來源;release 硬檢查;ISO532_FIELD_* 常數

**Files:**
- Modify: `iso532-ffi/src/lib.rs`
- Test: `iso532-ffi/tests/ffi.rs`

- [ ] **Step 1: 寫失敗測試**

`iso532-ffi/tests/ffi.rs` 新增(放在 `error_mapping_matches_spec_table` 後):

```rust
/// header 契約:場型常數必須存在且值凍結(cbindgen 會輸出成 #define)。
#[test]
fn field_constants_are_frozen() {
    assert_eq!(ISO532_FIELD_FREE, 0);
    assert_eq!(ISO532_FIELD_DIFFUSE, 1);
    assert_eq!(ISO532_ERR_INTERNAL, -4);
}
```

- [ ] **Step 2: 跑測試確認編譯失敗**

Run: `cd iso532-ffi && cargo test field_constants_are_frozen`
Expected: 編譯錯誤 `cannot find value ISO532_FIELD_FREE`

- [ ] **Step 3: 實作**

`iso532-ffi/src/lib.rs` 逐處修改:

(a) 常數區(line 7-13)追加:

```rust
/// 程式庫內部不變量被打破(如框架數查詢與實際輸出不一致)。
/// 收到此碼代表 iso532 的 bug,請回報;輸出緩衝未被寫入。
pub const ISO532_ERR_INTERNAL: i32 = -4;
/// field_type 合法值:自由場。
pub const ISO532_FIELD_FREE: i32 = 0;
/// field_type 合法值:擴散場。
pub const ISO532_FIELD_DIFFUSE: i32 = 1;
```

(b) `error_code`(line 18-24)改為轉發 core 凍結表:

```rust
fn error_code(e: &Iso532Error) -> i32 {
    e.code()
}
```

(c) 刪除 `field_from`(line 26-32);兩個 extern fn 內的

```rust
        let Some(field) = field_from(field_type) else {
            return ISO532_ERR_INVALID_FIELD_TYPE;
        };
```

改為:

```rust
        let Ok(field) = FieldType::try_from(field_type) else {
            return ISO532_ERR_INVALID_FIELD_TYPE;
        };
```

(d) `iso532_zwtv_out_frames`(line 42-45)改為轉發 core(doc 註解同步改寫,會流入 header):

```rust
/// Number of output frames `iso532_loudness_zwtv` will write for a signal of
/// `signal_len` samples, on the ISO 2 ms output grid. Pure; does not validate
/// (validation happens in the main call). Forwards `iso532::zwtv_out_frames`.
#[no_mangle]
pub extern "C" fn iso532_zwtv_out_frames(signal_len: usize) -> usize {
    iso532::zwtv_out_frames(signal_len)
}
```

(e) `iso532_loudness_zwtv` 的 `Ok(r)` 分支:把 `debug_assert_eq!`(line 85)換成 release 也生效的硬檢查,**在任何 copy 之前**:

```rust
            Ok(r) => {
                let frames = r.n.len();
                if frames != iso532::zwtv_out_frames(signal_len)
                    || r.n_specific.len() != 240 * frames
                {
                    return ISO532_ERR_INTERNAL;
                }
                // SAFETY: 呼叫端契約——各緩衝大小如上;來源為剛建構的 Vec。
                unsafe {
```

(f) 兩個 extern fn 的 `# Safety` doc 註解補上對齊與場型(會流入 header;zwtv/zwst 都改):

```rust
/// # Safety
/// `signal` must be non-null, 8-byte aligned (a valid `double*`), and valid
/// for `signal_len` reads; each out pointer must be valid (and 8-byte
/// aligned) for the writes documented above. `field_type` must be
/// ISO532_FIELD_FREE (0) or ISO532_FIELD_DIFFUSE (1); other values return
/// ISO532_ERR_INVALID_FIELD_TYPE.
```

(g) `use iso532::{loudness_zwst, loudness_zwtv, FieldType, Iso532Error};` 維持不變(FieldType 已在)。

- [ ] **Step 4: 跑測試確認通過(bitwise 對照不得動)**

Run: `cd iso532-ffi && cargo test --features test-panic`
Expected: 全綠,含既有 `zwtv_happy_path_matches_rust_api_bitwise`、`error_mapping_matches_spec_table`(錯誤碼值未變,只換來源)與新 `field_constants_are_frozen`。

- [ ] **Step 5: Commit**

```bash
git add iso532-ffi/src/lib.rs iso532-ffi/tests/ffi.rs
git commit -m "fix(ffi): release-hard frame check, core-owned mappings, field constants (review #2/#4/#9)"
```

### Task 4: 重生 header、修正 smoke.c 的錯誤宣稱

**Files:**
- Modify: `iso532-ffi/include/iso532.h`(cbindgen 再生,不手改)
- Modify: `iso532-ffi/tests/smoke.c:1-3, 35, 53`

- [ ] **Step 1: 再生 header**

Run: `cd iso532-ffi && cbindgen --config cbindgen.toml --crate iso532-ffi --output include/iso532.h`
Expected: 無錯誤。`git diff include/iso532.h` 應恰好顯示:新增 `ISO532_ERR_INTERNAL`/`ISO532_FIELD_FREE`/`ISO532_FIELD_DIFFUSE` 三個 #define(含 doc)、`iso532_zwtv_out_frames` 與兩個 loudness 函式的 doc 註解更新。**若出現其他簽名變動,停下調查。**

(本機 cbindgen 為 0.29.4;Task 5 的 CI 會 pin 同版,版本不一致會造成格式 diff。)

- [ ] **Step 2: 修 smoke.c**

檔頭註解(line 1-3)改為(移除「簽名漂移會編譯失敗」的錯誤宣稱——C 連結只比對符號名):

```c
/* C smoke test for the committed include/iso532.h (spec §9).
 * Compiled by CI with gcc (ubuntu) and MSVC cl (windows) against the cdylib.
 * 注意:C 連結不檢查簽名——header 與 Rust 的同步由 CI 的 cbindgen 再生
 * 比對步驟把關;本檔案負責呼叫慣例與行為煙霧測試。 */
```

兩處呼叫的 field 參數字面值 `0` 改用新 #define(同時編譯期驗證 define 存在):

```c
    code = iso532_loudness_zwtv(signal, LEN, 48000.0, ISO532_FIELD_FREE, out_n,
                                out_spec, out_bark, out_time);
```

```c
    code = iso532_loudness_zwst(signal, LEN, 48000.0, ISO532_FIELD_FREE, out_n,
                                out_spec, out_bark);
```

(line 64-70 的「字面值 3、不依賴 #define」錯誤碼檢查刻意保留原樣。)

- [ ] **Step 3: 本機驗證 C smoke(MSVC)**

Run(PowerShell,x64 Native Tools 環境或 `vcvars64` 後;在 `iso532-ffi/` 下):

```
cargo build --release
cl /nologo /W3 /Iinclude tests\smoke.c /link /LIBPATH:target\release iso532_ffi.dll.lib
copy target\release\iso532_ffi.dll . && smoke.exe
```

Expected: `smoke ok: frames=500 zwtv_n0=...`(若本機無 MSVC 環境,此步標記交由 CI 驗證,不得默默跳過)

- [ ] **Step 4: Commit**

```bash
git add iso532-ffi/include/iso532.h iso532-ffi/tests/smoke.c
git commit -m "feat(ffi): regen header with field/internal constants; fix smoke.c claim (review #3/#4)"
```

### Task 5: CI 加 cbindgen 再生比對閘

**Files:**
- Modify: `.github/workflows/ci.yml`(ffi job,`cargo clippy` 步驟之後)

- [ ] **Step 1: 加步驟**

在 ffi job 的 `- run: cargo clippy --all-targets --all-features -- -D warnings` 之後插入:

```yaml
      - name: header up-to-date (cbindgen regen + diff)
        if: matrix.os == 'ubuntu-latest'
        run: |
          cargo install cbindgen --version 0.29.4 --locked
          cbindgen --config cbindgen.toml --crate iso532-ffi --output include/iso532.h
          git diff --exit-code include/iso532.h
```

- [ ] **Step 2: Commit + push 觀察 CI**

```bash
git add .github/workflows/ci.yml
git commit -m "ci: enforce committed iso532.h matches cbindgen output (review #3)"
git push
```

Expected: ffi job(ubuntu)綠,新步驟 `git diff --exit-code` 無輸出。**Phase F1 出場門檻:三個 job 全綠。**

---

## Phase F2 — Python binding 安全(發現 #1、#5、#9 的 py 部分)

### Task 6: 修 GIL 資料競爭——輸入複製為 owned 再釋放 GIL

**背景(為何要複製):** `py.allow_threads` 釋放 GIL 期間,其他 Python 執行緒可對同一 ndarray 做原地寫入(`sig[:] = 0`);rust-numpy 的借用追蹤只防 Rust 側借用,防不了 Python 側寫入 → 對 `&[f64]` 的資料競爭是 UB。修法:進 `allow_threads` 前把輸入複製成 owned `Vec`(10 s 訊號 ~3.8 MB,相對 ~50 ms 計算可忽略);輸出維持零複製。

**Files:**
- Modify: `iso532-py/src/lib.rs:1-3(模組 doc)、44-47、71-74`

- [ ] **Step 1: 實作**

(資料競爭無法用確定性測試捕捉——本 task 無新測試,以既有 smoke 套件的 bitwise 契約守恆為行為驗證。)

模組 doc(line 1-3)改為:

```rust
//! Python bindings for the `iso532` crate. Batch API only (R3); the
//! streaming API arrives with R5. The input is copied to an owned buffer
//! before the GIL is released (soundness: other Python threads may mutate
//! the ndarray mid-computation); outputs are moved into numpy arrays
//! without an extra copy.
```

`loudness_zwtv`(line 44-47)改為:

```rust
    let field = parse_field(field_type)?;
    let owned = contiguous(&signal)?.to_vec();
    let r = py
        .allow_threads(move || iso532_core::loudness_zwtv(&owned, fs, field))
        .map_err(|e| PyValueError::new_err(e.to_string()))?;
```

`loudness_zwst`(line 71-74)同型改法:

```rust
    let field = parse_field(field_type)?;
    let owned = contiguous(&signal)?.to_vec();
    let r = py
        .allow_threads(move || iso532_core::loudness_zwst(&owned, fs, field))
        .map_err(|e| PyValueError::new_err(e.to_string()))?;
```

- [ ] **Step 2: 建置 + 跑 smoke 套件(bitwise 契約必須不變)**

Run:
```bash
cd iso532-py
../.venv/Scripts/python.exe -m maturin develop --release
../.venv/Scripts/python.exe -m pytest tests/test_smoke.py -v
```
Expected: 全綠——特別是 `test_bitwise_contract_n_and_time_axis`(輸入複製不得改變任何位元)。

- [ ] **Step 3: Commit**

```bash
git add iso532-py/src/lib.rs
git commit -m "fix(py): copy input before releasing GIL, close data-race UB (review #1)"
```

### Task 7: `parse_field` 改用 core `FromStr`

**Files:**
- Modify: `iso532-py/src/lib.rs:17-25`

- [ ] **Step 1: 實作**

```rust
fn parse_field(s: &str) -> PyResult<iso532_core::FieldType> {
    s.parse().map_err(|_| {
        PyValueError::new_err(format!(
            "field_type must be \"free\" or \"diffuse\", got {s:?}"
        ))
    })
}
```

- [ ] **Step 2: 跑測試(既有 `test_error_mapping` 已覆蓋 "FREE" 拒收)**

Run: `cd iso532-py && ../.venv/Scripts/python.exe -m maturin develop --release && ../.venv/Scripts/python.exe -m pytest tests/test_smoke.py -v`
Expected: 全綠。

- [ ] **Step 3: Commit**

```bash
git add iso532-py/src/lib.rs
git commit -m "refactor(py): field vocabulary from core FromStr (review #9)"
```

### Task 8: parity 套件的 `import iso532` 改 importorskip

**Files:**
- Modify: `iso532-py/tests/test_parity_mosqito.py:18`

- [ ] **Step 1: 實作**

line 18 的 `import iso532  # noqa: E402` 改為:

```python
iso532 = pytest.importorskip("iso532")
```

(docstring「skips cleanly elsewhere」的承諾自此成立:`setup_env.sh` 建的 .venv 有 mosqito、無 iso532 wheel,collection 將 skip 而非報錯。)

- [ ] **Step 2: 驗證 collection 與(可選)完整 parity**

Run: `cd iso532-py && ../.venv/Scripts/python.exe -m pytest tests/ --collect-only -q`
Expected: 正常列出所有測試、零 error(dev venv 兩個模組都在,不觸發 skip 路徑)。

如時間允許跑完整 parity 傘(~5–10 分鐘)確認回歸零:
Run: `../.venv/Scripts/python.exe -m pytest tests/test_parity_mosqito.py -v`
Expected: 18 passed。

- [ ] **Step 3: Commit**

```bash
git add iso532-py/tests/test_parity_mosqito.py
git commit -m "fix(py-test): importorskip iso532 so parity suite skips, not errors (review #5)"
```

**Phase F2 出場門檻:** smoke 全綠 + bitwise 契約 hash 不變 + collect-only 乾淨。

---

## Phase F3 — Golden 鏈守衛(發現 #6、#7)

### Task 9: `golden_manifest.py` 加 Python 版本守衛

**Files:**
- Modify: `tools/golden_manifest.py:14-18`(import 區之後)

- [ ] **Step 1: 實作**

import 區(line 14-18)之後、`ROOT = ...` 之前插入:

```python
if sys.version_info < (3, 11):
    sys.exit(
        "golden_manifest.py needs Python >= 3.11 (hashlib.file_digest); "
        "run it with the tools venv per docs/GOLDEN-REGEN-SOP.md"
    )
```

- [ ] **Step 2: 驗證既有行為不變**

Run: `.venv/Scripts/python.exe tools/golden_manifest.py --verify`
Expected: `verify OK: 178 files match`(本機 golden 鏈健在的前提下;若本機 data/ 不全,以 `--generate --data-root/--manifest` 打到暫存目錄煙霧測試亦可)。

- [ ] **Step 3: Commit**

```bash
git add tools/golden_manifest.py
git commit -m "fix(tools): actionable error on Python < 3.11 in golden_manifest (review #7)"
```

### Task 10: `setup_env.sh` 執行凍結契約(版本、tarball SHA256、完整 sanity import)

**Files:**
- Modify: `tools/setup_env.sh`
- Modify: `docs/GOLDEN-REGEN-SOP.md`(§C 表格加一行)

- [ ] **Step 1: 實作 setup_env.sh**

(a) venv Python 解析完成後(line 26 `fi` 之後、`pip install --upgrade pip` 之前)插入版本守衛:

```bash
$PY - <<'EOF'
import sys
if sys.version_info[:2] != (3, 11):
    sys.exit(
        f"golden chain requires Python 3.11 (got {sys.version.split()[0]}); "
        "see tools/requirements.lock header"
    )
EOF
```

(b) 安裝 mosqito 前(原 line 29 之前)插入 tarball SHA256 守衛(值來自 `tools/requirements.lock` 標頭,兩處必須一致):

```bash
$PY - <<'EOF'
import hashlib
want = "50c0ebdc5102c67cfe4362178ce07d7e6b3211d7cb3e6051082e503ff019f16f"
with open("mosqito-1.2.1.tar.gz", "rb") as f:
    got = hashlib.sha256(f.read()).hexdigest()
if got != want:
    raise SystemExit(f"mosqito tarball sha256 mismatch:\n  got  {got}\n  want {want}")
print("mosqito tarball sha256 OK")
EOF
```

(c) sanity import(原 line 30)擴充涵蓋 gen_golden 的 lazy import(openpyxl)與 mosqito load 路徑(pyuff):

```bash
$PY -c "import mosqito, scipy, numpy, openpyxl, pyuff; print('golden env OK, scipy', scipy.__version__, 'numpy', numpy.__version__)"
```

- [ ] **Step 2: 完整跑一次腳本驗證(冪等,重裝 lock 套件約 1–3 分鐘)**

Run: `bash tools/setup_env.sh`
Expected: 依序印出 `mosqito tarball sha256 OK`、`golden env OK, scipy 1.17.1 numpy 2.4.6`、`ls data/annexb` 列表;exit 0。

- [ ] **Step 3: 更新 SOP 維護清單**

`docs/GOLDEN-REGEN-SOP.md` §C 表格追加一列:

```markdown
| 契約執行 | `setup_env.sh` 腳本守衛:Python == 3.11、tarball SHA256、sanity import 含 openpyxl/pyuff |
```

- [ ] **Step 4: Commit**

```bash
git add tools/setup_env.sh docs/GOLDEN-REGEN-SOP.md
git commit -m "fix(tools): setup_env enforces the freeze contract it documents (review #6)"
```

**Phase F3 出場門檻:** `bash tools/setup_env.sh` 全程綠 + `golden_manifest.py --verify` OK。

---

## Phase F4 — Bitwise 契約單一來源(發現 #8)

### Task 11: 建 `tools/iso532_testkit.py`(Python 側單一來源 + known-answer 自檢)

**Files:**
- Create: `tools/iso532_testkit.py`

- [ ] **Step 1: 建檔**

```python
"""Shared helpers for the cross-language bitwise contract (single source).

Python 側唯一的契約訊號與 FNV-1a 實作;Rust 對應物在
iso532/tests/common/mod.rs (fnv1a_f64) 與 iso532/tests/py_contract_dump.rs
(contract_signal)。KNOWN_ANSWER 由兩側各自斷言——任一側移植漂移,
其測試套件會在查任何凍結契約 hash 之前先紅。
"""
import numpy as np

# fnv1a_f64([0.0, 1.0, 2.0, 3.0]);Rust 側同值斷言在 py_contract_dump.rs
KNOWN_ANSWER = 0xB90557CFD5E83390


def contract_signal(n=48000):
    """純整數演算訊號(無 libm,Python/Rust 逐位相同)。"""
    i = np.arange(n, dtype=np.uint64)
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


# import 時自檢:任何消費者(smoke 測試、bench)先過這關才拿得到工具
assert fnv1a_f64(np.array([0.0, 1.0, 2.0, 3.0])) == KNOWN_ANSWER, (
    "fnv1a_f64 port drifted from the Rust reference"
)
```

- [ ] **Step 2: 驗證自檢**

Run: `.venv/Scripts/python.exe -c "import sys; sys.path.insert(0, 'tools'); import iso532_testkit; print('testkit OK')"`
Expected: `testkit OK`

- [ ] **Step 3: Commit**

```bash
git add tools/iso532_testkit.py
git commit -m "feat(tools): shared testkit for cross-language bitwise contract (review #8)"
```

### Task 12: dump 工具遷入 core tests(重用 `common::fnv1a_f64`)+ Rust 側 known-answer

**Files:**
- Create: `iso532/tests/py_contract_dump.rs`
- Modify: `iso532-ffi/tests/ffi.rs:215-247`(整段刪除)
- Modify: `.github/workflows/ci.yml`(rust job 的 `--test` 清單)

- [ ] **Step 1: 建 core 測試檔**

`iso532/tests/py_contract_dump.rs`:

```rust
//! R3-P3 跨語言 bitwise 契約的凍結工具(手動執行)。
//! 重凍:cargo test --test py_contract_dump -- --ignored --nocapture
//! Python 對應物:tools/iso532_testkit.py(contract_signal / fnv1a_f64)。

// 本 binary 只用 common 的 fnv1a_f64;golden_dir/read_bin 等 helper 在此
// 未用,壓掉 dead_code 以免 clippy -D warnings 紅(其他測試 binary 同模式)。
#[allow(dead_code)]
mod common;

use common::fnv1a_f64;
use iso532::FieldType;

/// 與 tools/iso532_testkit.py 的 contract_signal 逐位相同:純整數演算、
/// 無 libm(sin 合成會因 libm ULP 差異炸 hash)。
fn contract_signal() -> Vec<f64> {
    (0..48_000_u64)
        .map(|i| ((i * 2_654_435_761) % 96_001) as f64 / 96_000.0 * 0.02 - 0.01)
        .collect()
}

/// 與 tools/iso532_testkit.py 的 KNOWN_ANSWER 同一常數:
/// 任一側 FNV-1a 移植漂移,先於契約 hash 在此紅掉。
#[test]
fn fnv1a_known_answer_matches_python_testkit() {
    assert_eq!(fnv1a_f64(&[0.0, 1.0, 2.0, 3.0]), 0xb905_57cf_d5e8_3390);
}

#[test]
#[ignore = "manual: freeze constants for iso532-py/tests/test_smoke.py (R3-P3)"]
fn dump_py_bitwise_contract_hashes() {
    let r = iso532::loudness_zwtv(&contract_signal(), 48_000.0, FieldType::Free).unwrap();
    eprintln!(
        "py-contract: n={:#018x} time={:#018x} frames={}",
        fnv1a_f64(&r.n),
        fnv1a_f64(&r.time_axis),
        r.n.len()
    );
}
```

- [ ] **Step 2: 跑 dump 驗證常數不變(遷移不得改變契約值)**

Run: `cd iso532 && cargo test --test py_contract_dump -- --ignored --nocapture`
Expected 輸出必須逐字為:

```
py-contract: n=0x44e6822074554786 time=0xf076bcb342595537 frames=500
```

(與 `iso532-py/tests/test_smoke.py` 現行 N_HASH/TIME_HASH 一致。不一致 = 遷移打錯,停下調查。)

- [ ] **Step 3: 刪 ffi 側複本**

刪除 `iso532-ffi/tests/ffi.rs` 檔尾整段(line 215-247:`// ---- R3-P3 跨語言 bitwise 契約的凍結工具` 註解起,含 `py_contract_signal`、`fnv1a_f64`、`dump_py_bitwise_contract_hashes`)。

Run: `cd iso532-ffi && cargo test --features test-panic`
Expected: 全綠(其餘測試不依賴被刪函式)。

- [ ] **Step 4: CI rust job 收錄新測試檔**

`.github/workflows/ci.yml` rust job 的 cargo test `--test` 清單(`--test hash_gate` 之後)追加:

```yaml
          --test py_contract_dump
```

(known-answer 測試無 data/ 依賴,CI 可跑;dump 測試掛 `#[ignore]` 不會誤觸。)

- [ ] **Step 5: Commit**

```bash
git add iso532/tests/py_contract_dump.rs iso532-ffi/tests/ffi.rs .github/workflows/ci.yml
git commit -m "refactor(test): move contract dump to core tests, dedupe fnv1a (review #8)"
```

### Task 13: `test_smoke.py` 與 `bench_binding.py` 改用 testkit

**Files:**
- Modify: `iso532-py/tests/test_smoke.py:1-32`
- Modify: `tools/bench_binding.py:6-19`

- [ ] **Step 1: test_smoke.py 換頭**

line 1-32(docstring 至 `fnv1a_f64` 定義結束)整段換成:

```python
"""Smoke + cross-language bitwise contract tests (no mosqito; runs in CI)."""
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
from iso532_testkit import contract_signal, fnv1a_f64  # noqa: E402

import iso532  # noqa: E402

FS = 48000.0

# Frozen from Rust:
#   cd iso532 && cargo test --test py_contract_dump -- --ignored --nocapture
# n/time_axis are bitwise-stable across platforms and backends (see
# docs/CI-HASH-GATE-DEBUG-2026-07-10.md). Values MUST come from an actual
# dump run — never invented, never copied from another signal.
N_HASH = 0x44E6822074554786
TIME_HASH = 0xF076BCB342595537
```

檔內其餘所有 `py_contract_signal()` 呼叫(6 處:`test_zwtv_shapes_and_axes`、`test_zwtv_diffuse_accepted`、`test_zwst_shapes`、`test_bitwise_contract_n_and_time_axis`、`test_error_mapping`、`test_strict_input_contract`)改為 `contract_signal()`。

- [ ] **Step 2: bench_binding.py 換訊號來源**

line 6-19(import 區與訊號建構)改為:

```python
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from iso532_testkit import contract_signal

import iso532

FS = 48000
sig = contract_signal(10 * FS)
```

- [ ] **Step 3: 跑 smoke(契約 hash 必須仍過)+ bench 煙霧**

Run:
```bash
cd iso532-py && ../.venv/Scripts/python.exe -m pytest tests/test_smoke.py -v
cd .. && .venv/Scripts/python.exe tools/bench_binding.py
```
Expected: smoke 全綠(`test_bitwise_contract_n_and_time_axis` 過 = 訊號單一來源與舊實作逐位相同);bench 印出 `binding zwtv 10s best-of-20: ... ms`。

- [ ] **Step 4: Commit**

```bash
git add iso532-py/tests/test_smoke.py tools/bench_binding.py
git commit -m "refactor(py-test): consume shared testkit signal + fnv (review #8)"
```

**Phase F4 出場門檻:** 三個 crate 測試全綠 + smoke bitwise 契約 hash 逐位不變 + push 後 CI 三 job 全綠。

---

## 明確遞延(不在本計畫,已記錄理由)

| 項目 | 去向 | 理由 |
|---|---|---|
| 發現 #10:`loudness_zwtv_into` 消除 FFI 雙重配置 | R5 | 需要重排 `ZwtvProcessor::process()` 尾段輸出組裝;R5 串流 API 本來就要重構同一段,現在做是拋棄式工程。 |
| 發現 #9 殘餘:py 錯誤訊息子字串被測試釘住 | 已知取捨 | 訊息文字視為 core `Display` 的凍結契約;改文案需同步 `test_smoke.py::test_error_mapping`。若 R6 需要 typed exceptions 再收斂。 |
| CI 效率清理(lint ×6、workspace 合併、`cargo test --release`、pip cache、composite action) | 獨立 chore PR | 非缺陷;見 `docs/R3-REVIEW-2026-07-11.md` §4 清單。 |

## 總驗收(全部 phase 完成後)

1. `cd iso532 && cargo test` 全綠(hash gate 12/12 逐位不變)
2. `cd iso532-ffi && cargo test --features test-panic` 全綠
3. `cd iso532-py && ../.venv/Scripts/python.exe -m pytest tests/ -v` smoke 全綠、parity 18/18(或 collect-only 乾淨 + 週期性跑 parity)
4. `bash tools/setup_env.sh && .venv/Scripts/python.exe tools/golden_manifest.py --verify` 綠
5. push 後 GitHub Actions 三 job(rust/ffi/py)× 兩 OS 全綠,含新 cbindgen diff 閘
6. `docs/R3-REVIEW-2026-07-11.md` §2 表格逐項對照:#1–#9 每項能指出對應 commit
