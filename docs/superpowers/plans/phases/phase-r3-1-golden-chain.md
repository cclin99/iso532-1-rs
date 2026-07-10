# R3-P1:R-14 Golden 再生鏈收口 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 golden 再生鏈(mosqito venv → gen_golden.py → data/golden)鎖版本、加 SHA256 manifest、寫 SOP,並實地驗證一輪乾淨重建。

**Architecture:** 三個獨立元件——`tools/requirements.lock`(pip 環境凍結)、`tools/golden_manifest.py`(SHA256 生成/驗證工具,per-環境契約)、`docs/GOLDEN-REGEN-SOP.md`(換機器再生程序)。最後用一個乾淨 venv 全程重跑作為 Exit Gate。

**Tech Stack:** Python 3.11(stdlib only:hashlib/argparse/platform)、pip freeze、既有 tools/gen_golden.py 與 tools/setup_env.sh。

**Spec:** `docs/superpowers/specs/2026-07-10-r3-c-abi-python-binding-design.md` §7

**Exit Gate:** 乾淨重建 venv → 重生 golden → `golden_manifest.py --verify` 全符 → `cargo test` golden 套件全綠。

---

## 背景(給零脈絡的工程師)

- `data/`(177 MB)是 **gitignored**:`data/golden/`(155 MB,mosqito 逐階段中間值,little-endian f64 `.bin` + `meta.json`)+ `data/annexb/`(ISO Annex B wav/csv/xlsx,clone 自 MoSQITo GitHub repo)。
- 生成鏈:`tools/setup_env.sh` 建 `.venv` 裝 mosqito → `tools/gen_golden.py` 寫入 `data/golden/`。
- Rust 測試 `iso532/tests/golden_*.rs`、`annexb.rs` 開檔即讀,檔案缺失即 panic。
- 目前 `.venv` 實測:Python 3.11.9、numpy 2.4.6、scipy 1.17.1、mosqito 裝自本地 `mosqito-1.2.1.tar.gz`(sha256=50c0ebdc5102c67cfe4362178ce07d7e6b3211d7cb3e6051082e503ff019f16f)。**沒有任何 lockfile。**
- **per-環境契約**(重要,見 `docs/CI-HASH-GATE-DEBUG-2026-07-10.md`):golden 位元組取決於生成機器的 libm(scipy/numpy 底層),SHA256 manifest 只回答「**本機**重生是否與測試驗證過的資料一致」,不是跨平台契約。
- 所有指令在 repo 根(`D:\ISO532`)、Git Bash 下執行。

### Task 0 開始前

確認前置(不符即停,回報使用者):

```bash
ls mosqito-1.2.1.tar.gz && ls data/golden/sine_1k_60/meta.json && .venv/Scripts/python.exe --version
```

Expected: 三者都存在,Python 3.11.9。

---

### Task 1: requirements.lock + setup_env.sh 改從 lock 安裝

**Files:**
- Create: `tools/requirements.lock`
- Modify: `tools/setup_env.sh:28`(install 行)
- Modify: `.gitignore`(加 `.venv*/`)

- [ ] **Step 1: 生成 lockfile**

```bash
.venv/Scripts/python.exe -m pip freeze --exclude mosqito > tools/requirements.lock
```

- [ ] **Step 2: 在 lockfile 開頭加註記標頭**

用編輯器在 `tools/requirements.lock` 最前面插入(pip 的 requirements 格式支援 `#` 註解):

```
# Frozen environment for the golden regeneration chain (R-14).
# Python 3.11.9 (rebuild the venv with this exact minor version).
# mosqito is installed separately from the local tarball (see setup_env.sh):
#   mosqito-1.2.1.tar.gz  sha256=50c0ebdc5102c67cfe4362178ce07d7e6b3211d7cb3e6051082e503ff019f16f
# Regenerate this file: .venv/Scripts/python.exe -m pip freeze --exclude mosqito
```

- [ ] **Step 3: 驗證 lockfile 內容**

```bash
grep -E "^(numpy|scipy)==" tools/requirements.lock
```

Expected: `numpy==2.4.6` 與 `scipy==1.17.1` 各一行(版本以實際 freeze 輸出為準,不得手改)。

- [ ] **Step 4: 改 setup_env.sh 從 lock 安裝**

`tools/setup_env.sh` 第 28 行,把:

```bash
$PY -m pip install --quiet ./mosqito-1.2.1.tar.gz openpyxl matplotlib
```

改為:

```bash
$PY -m pip install --quiet -r tools/requirements.lock
$PY -m pip install --quiet --no-deps ./mosqito-1.2.1.tar.gz
```

(`--no-deps`:mosqito 的相依已全在 lock 裡,不讓 pip 解析器另拉版本。)

- [ ] **Step 5: `.gitignore` 加一行**

在 `.gitignore` 的 `.venv/` 行後面加:

```
.venv*/
```

(Task 4 會建 `.venv-check/`。)**注意:`.gitignore` 工作區可能已有使用者未提交的修改——commit 時只 add 本任務的三個檔案,且 `.gitignore` 用 `git add -p .gitignore` 只揀入這一行。**

- [ ] **Step 6: Commit**

```bash
git add tools/requirements.lock tools/setup_env.sh
git add -p .gitignore   # 只揀 .venv*/ 那個 hunk
git commit -m "chore: freeze golden-chain python env into requirements.lock (R-14)"
```

---

### Task 2: tools/golden_manifest.py(SHA256 生成/驗證)

**Files:**
- Create: `tools/golden_manifest.py`
- Create: `tools/golden.sha256`(由工具生成後 commit)

- [ ] **Step 1: 寫工具(完整程式碼)**

`tools/golden_manifest.py`:

```python
"""Generate/verify a SHA256 manifest for data/golden and data/annexb.

PER-ENVIRONMENT contract: golden bytes depend on the libm of the machine
that generated them (see docs/CI-HASH-GATE-DEBUG-2026-07-10.md). The
manifest answers exactly one question: "does regeneration on THIS machine
reproduce the data the Rust test suite was validated against?" On a new
machine a mismatch is EXPECTED: regenerate the manifest per the SOP
(docs/GOLDEN-REGEN-SOP.md) and re-run the golden tests.

Usage:
  python tools/golden_manifest.py --generate
  python tools/golden_manifest.py --verify
"""
import argparse
import hashlib
import platform
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PATTERNS = ("golden/**/*.bin", "golden/**/meta.json", "annexb/*")


def collect(data_root: Path) -> dict[str, str]:
    files = set()
    for pattern in PATTERNS:
        files.update(p for p in data_root.glob(pattern) if p.is_file())
    entries = {}
    for p in sorted(files):
        with p.open("rb") as f:
            digest = hashlib.file_digest(f, "sha256").hexdigest()
        entries[p.relative_to(data_root).as_posix()] = digest
    return entries


def env_header() -> list[str]:
    try:
        import numpy
        import scipy

        vers = f"numpy {numpy.__version__}, scipy {scipy.__version__}"
    except ImportError:
        vers = "numpy/scipy not importable"
    return [
        "# PER-ENVIRONMENT manifest: only valid on the machine/env that generated it.",
        "# On a new machine, follow docs/GOLDEN-REGEN-SOP.md instead of trusting --verify.",
        f"# env: {platform.platform()} / {platform.machine()} / "
        f"python {platform.python_version()} / {vers}",
    ]


def generate(data_root: Path, manifest: Path) -> int:
    entries = collect(data_root)
    if not entries:
        print(f"error: no files matched under {data_root}", file=sys.stderr)
        return 1
    lines = env_header() + [f"{h}  {rel}" for rel, h in sorted(entries.items())]
    manifest.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {manifest} ({len(entries)} files)")
    return 0


def verify(data_root: Path, manifest: Path) -> int:
    if not manifest.exists():
        print(f"error: manifest {manifest} missing", file=sys.stderr)
        return 1
    want = {}
    for line in manifest.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#"):
            continue
        digest, rel = line.split(None, 1)
        want[rel] = digest
    got = collect(data_root)
    missing = sorted(set(want) - set(got))
    extra = sorted(set(got) - set(want))
    mismatch = sorted(rel for rel in set(want) & set(got) if want[rel] != got[rel])
    for rel in missing:
        print(f"MISSING   {rel}")
    for rel in extra:
        print(f"EXTRA     {rel}")
    for rel in mismatch:
        print(f"MISMATCH  {rel}")
    if missing or extra or mismatch:
        print(
            f"verify FAILED: {len(missing)} missing, {len(extra)} extra, "
            f"{len(mismatch)} mismatch (of {len(want)} manifest entries)"
        )
        return 1
    print(f"verify OK: {len(want)} files match")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--generate", action="store_true")
    mode.add_argument("--verify", action="store_true")
    ap.add_argument("--data-root", type=Path, default=ROOT / "data",
                    help="override for self-tests")
    ap.add_argument("--manifest", type=Path, default=ROOT / "tools" / "golden.sha256",
                    help="override for self-tests")
    args = ap.parse_args()
    if args.generate:
        return generate(args.data_root, args.manifest)
    return verify(args.data_root, args.manifest)


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: 自我測試——tamper 必須被抓到**

用暫存 fixture 驗證工具本身(不碰真實 data/):

```bash
T=$(mktemp -d)
mkdir -p "$T/data/golden/x" "$T/data/annexb"
printf 'aaa' > "$T/data/golden/x/a.bin"
printf '{}'  > "$T/data/golden/x/meta.json"
printf 'wav' > "$T/data/annexb/b.wav"
P=.venv/Scripts/python.exe
$P tools/golden_manifest.py --generate --data-root "$T/data" --manifest "$T/m.sha256"
$P tools/golden_manifest.py --verify   --data-root "$T/data" --manifest "$T/m.sha256"
printf 'BAD' > "$T/data/golden/x/a.bin"
$P tools/golden_manifest.py --verify --data-root "$T/data" --manifest "$T/m.sha256"; echo "exit=$?"
rm "$T/data/annexb/b.wav"
$P tools/golden_manifest.py --verify --data-root "$T/data" --manifest "$T/m.sha256"; echo "exit=$?"
rm -rf "$T"
```

Expected 依序:`wrote ... (3 files)`、`verify OK: 3 files match`、`MISMATCH golden/x/a.bin ... exit=1`、`MISSING annexb/b.wav ... exit=1`。

- [ ] **Step 3: 生成真實 manifest**

```bash
.venv/Scripts/python.exe tools/golden_manifest.py --generate
.venv/Scripts/python.exe tools/golden_manifest.py --verify
```

Expected: `wrote tools/golden.sha256 (N files)` 後 `verify OK: N files match`(N 約 100–140,依實際檔數)。

- [ ] **Step 4: 抽查 manifest 內容**

```bash
head -5 tools/golden.sha256 && grep -c "annexb/" tools/golden.sha256
```

Expected: 前 3 行是 `#` 環境標頭;annexb 條目數 ≥ 4(3 個 wav + csv/xlsx)。

- [ ] **Step 5: Commit**

```bash
git add tools/golden_manifest.py tools/golden.sha256
git commit -m "feat: add per-environment SHA256 manifest for golden data (R-14)"
```

---

### Task 3: docs/GOLDEN-REGEN-SOP.md

**Files:**
- Create: `docs/GOLDEN-REGEN-SOP.md`

- [ ] **Step 1: 寫 SOP(完整內容)**

```markdown
# Golden 資料再生 SOP(R-14)

`data/` 是 gitignored;本文是換機器、venv 損毀、或需要重生 golden 時的唯一程序。
**核心觀念:`tools/golden.sha256` 是 per-環境契約**——golden 位元組取決於生成
機器的 libm(scipy/numpy 底層),跨機器 SHA256 不同是預期行為,不是錯誤
(佐證:`docs/CI-HASH-GATE-DEBUG-2026-07-10.md`)。

## A. 同機器重生(venv 損毀 / data 誤刪)

前置:repo 根有 `mosqito-1.2.1.tar.gz`(sha256 見 `tools/requirements.lock` 標頭)。

    bash tools/setup_env.sh                                   # 建 .venv(從 requirements.lock 安裝)+ 抓 Annex B
    .venv/Scripts/python.exe tools/gen_golden.py              # 重生 data/golden(約 5–15 分鐘)
    .venv/Scripts/python.exe tools/golden_manifest.py --verify
    cd iso532 && cargo test --test golden_core --test golden_dsp --test golden_zwst --test golden_zwtv --test annexb

四步全過 = 鏈健在。`--verify` 失敗 ⇒ 環境已漂移(檢查 Python 小版本、
requirements.lock 是否被動過、mosqito tarball sha256)。

## B. 換新機器(SHA256 預期 mismatch)

1. 跑 A 的前兩步。
2. `--verify` **預期失敗**(libm 不同)。此時改跑 golden 測試:
   `cargo test --test golden_core --test golden_dsp --test golden_zwst --test golden_zwtv --test annexb`
3. 測試全綠 ⇒ 新環境的 golden 有效。重新凍結契約:
   `.venv/Scripts/python.exe tools/golden_manifest.py --generate`
   commit `tools/golden.sha256`,commit 訊息記錄新環境(OS/CPU)。
4. 測試有紅 ⇒ 不是環境噪音,是真回歸或上游版本漂移——停下來調查,
   不得直接重新凍結。

## C. 什麼會讓鏈斷掉(維護清單)

| 依賴 | 固化方式 |
|---|---|
| numpy/scipy 版本 | `tools/requirements.lock`(pip freeze 全鎖) |
| mosqito 1.2.1 | 本地 tarball + sha256(lock 標頭) |
| Annex B wav/xlsx | SHA256 在 `tools/golden.sha256`;來源是 MoSQITo GitHub repo tag v1.2.1(setup_env.sh) |
| Python 小版本 | 3.11(lock 標頭註記) |
| golden 位元組 | `tools/golden.sha256`(per-環境) |
```

- [ ] **Step 2: Commit**

```bash
git add docs/GOLDEN-REGEN-SOP.md
git commit -m "docs: golden regeneration SOP (R-14)"
```

---

### Task 4: Exit Gate——乾淨 venv 全程重建驗證

**Files:** 無新檔(驗證任務;產生的 `.venv-check/`、`data/golden.bak` 最後刪除)

- [ ] **Step 1: 備份現有 golden**

```bash
cp -r data/golden data/golden.bak
```

- [ ] **Step 2: 建乾淨 venv 並從 lock 安裝**

```bash
python -m venv .venv-check
.venv-check/Scripts/python.exe -m pip install --quiet -r tools/requirements.lock
.venv-check/Scripts/python.exe -m pip install --quiet --no-deps ./mosqito-1.2.1.tar.gz
.venv-check/Scripts/python.exe -c "import mosqito, numpy, scipy; print(numpy.__version__, scipy.__version__)"
```

Expected: `2.4.6 1.17.1`(與 lock 一致)。

- [ ] **Step 3: 用乾淨 venv 重生 golden(約 5–15 分鐘)**

```bash
.venv-check/Scripts/python.exe tools/gen_golden.py
```

Expected: 每組訊號印 `done <name>`,共 9 組,無 traceback。

- [ ] **Step 4: manifest 驗證(R-14 的核心命題)**

```bash
.venv-check/Scripts/python.exe tools/golden_manifest.py --verify
```

Expected: `verify OK`。**若 FAILED:先 `rm -rf data/golden && mv data/golden.bak data/golden` 還原,然後停下回報**——這代表同機器同 lock 重生不可重現,是 R-14 的真異常,不得矇混。

- [ ] **Step 5: golden 測試全綠**

```bash
cd iso532 && cargo test --test golden_core --test golden_dsp --test golden_zwst --test golden_zwtv --test annexb && cd ..
```

Expected: 全 PASS(0 failed)。

- [ ] **Step 6: 清理**

```bash
rm -rf data/golden.bak .venv-check
```

- [ ] **Step 7: 在 phase 計畫檔尾附上收尾註記並 commit**

在本檔(`docs/superpowers/plans/phases/phase-r3-1-golden-chain.md`)最末追加:

```markdown
---
## 收尾註記(執行完成後填)
- Exit Gate 實測:乾淨 venv 重生 → `verify OK: <N> files match`;golden 測試 <M> passed。
- manifest 檔數:<N>;環境:<manifest 標頭第 3 行原文>。
- 偏差(若有):<無/列點>
```

(`<N>`/`<M>` 填實測值,不得杜撰。)

```bash
git add docs/superpowers/plans/phases/phase-r3-1-golden-chain.md
git commit -m "docs: R3-P1 closeout — golden chain rebuild verified (R-14)"
```

---
## 收尾註記(執行完成後填)
- Exit Gate 實測:乾淨 venv 重生 → `verify OK: 175 files match`;golden 測試 20 passed(另 1 ignored 的手動 hash dump helper)。
- manifest 檔數:175;環境:`# env: Windows-10-10.0.19045-SP0 / AMD64 / python 3.11.9 / numpy 2.4.6, scipy 1.17.1`。
- 偏差(若有):sandbox 內第一次 lock 安裝無法連線套件來源;取得網路核准後以同一份 lock 成功安裝,版本與預期一致。`gen_golden.py` 實測 9 組全數完成,耗時 67.2 秒。
