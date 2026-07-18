# PRE-R6-P1:root cargo workspace(純機械搬移)Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把三個兄弟 crate(`iso532`、`iso532-ffi`、`iso532-py`)收進一個 root virtual workspace,統一 lockfile 與 `cargo test`/`clippy`/`fmt` 入口。這是 repo 分割(面板 repo)前置三項之一,見 `docs/PLAN-TIMING-ANALYSIS-2026-07-18.md` §2。

**狀態:** ⬜ 未開始。

**鐵律(沿主計畫 R8 風險 #1 原話):搬移 commit 零邏輯變更。** 本 phase 只允許動:root `Cargo.toml`(新增)、三個 member `Cargo.lock`(刪除)、root `Cargo.lock`(新增)、`.github/workflows/ci.yml`(cache 設定)。`iso532*/src/`、`iso532*/tests/`、`iso532*/Cargo.toml`、`include/iso532.h` 一個位元組都不准動。hash gate 12/12 是最終仲裁——lockfile 重解析若導致任何雜湊變化,停下回報,不得自行「修正」。

**Exit Gate:** 全套測試綠 + hash 12/12 與 R1 逐字相同 + strict parity 18/18 + golden manifest 通過 + CI 三 job 全綠(使用者確認 Actions 頁)。

---

## 背景(給零脈絡的工程師)

- 現況:三 crate 各有 tracked `Cargo.lock`(`git ls-files` 可證),各自 `target/`。root 沒有 `Cargo.toml`。
- workspace 化後 member `Cargo.lock` 會被 cargo 忽略——必須 `git rm`,改 commit root `Cargo.lock`(可重現交付策略沿用 R3 決策)。
- 三個 member `Cargo.toml` **都沒有 `[profile.*]` 區段**(已查核),無 profile 上收問題。
- **`iso532-py` 不能進 `default-members`**:它是 cdylib-only + pyo3 `extension-module`(abi3),`cargo test` 會在連結階段因 Python C API 符號未解析而失敗——它的測試路徑是 maturin + pytest,不是 cargo test。這是設計事實,不是要修的 bug。
- CI 三個 job 用 per-crate `working-directory` + `Swatinem/rust-cache` 的 `workspaces: <crate>`;workspace 化後 cargo 的 target/lock 都在 root,cache 設定要跟著改。
- `.gitignore` 已有 `target/`,root target 目錄免處理。

### Task 0 開始前

```bash
cd /d/ISO532 && git status --short   # 應只有 bash.exe.stackdump(未追蹤,勿動)
grep -c "\[profile" iso532/Cargo.toml iso532-ffi/Cargo.toml iso532-py/Cargo.toml  # 應全為 0
```

---

### Task 1: root workspace + lockfile 統一

**Files:**
- Create: `Cargo.toml`(root)
- Delete: `iso532/Cargo.lock`、`iso532-ffi/Cargo.lock`、`iso532-py/Cargo.lock`
- Create: `Cargo.lock`(root)

- [ ] **Step 1: root Cargo.toml(逐字)**

```toml
[workspace]
resolver = "2"
members = ["iso532", "iso532-ffi", "iso532-py"]
# iso532-py is a cdylib-only pyo3 extension module: `cargo test` cannot link
# it (no Python symbols at test-link time); it is tested via maturin + pytest.
default-members = ["iso532", "iso532-ffi"]
```

- [ ] **Step 2: lockfile 交換 + 版本漂移檢查**

```bash
git rm iso532/Cargo.lock iso532-ffi/Cargo.lock iso532-py/Cargo.lock
cargo generate-lockfile
# 漂移檢查:root lock 的關鍵 dep 版本應與舊 member lock 一致
for p in pyo3 numpy rayon thiserror criterion; do grep -A1 "name = \"$p\"" Cargo.lock | head -2; done
git show HEAD:iso532-py/Cargo.lock | grep -A1 'name = "pyo3"' | head -2
```

若版本不一致:用 `cargo update -p <pkg> --precise <舊版>` 釘回舊版本(lockfile 統一不是升級依賴的時機);釘不回才記錄並讓 hash gate 仲裁。

---

### Task 2: 全量驗證(workspace 入口)

- [ ] **Step 1: Rust 面(root 執行)**

```bash
cargo test                                        # default-members = iso532 + iso532-ffi
cargo test -p iso532-ffi --features test-panic
cargo fmt --check
cargo clippy --workspace --all-targets -- -D warnings
cargo clippy -p iso532-ffi --all-targets --all-features -- -D warnings
```

若 `--workspace` clippy 因 iso532-py 的 extension-module 在此環境無法通過(clippy 不連結,預期能過;萬一不行),降級為逐 crate clippy 並在收尾註記記錄原因。

- [ ] **Step 2: 凍結面(iso532/ 執行)**

```bash
cd iso532
cargo test --test golden_zwtv dump_zwtv_output_hashes -- --ignored --nocapture   # 12/12 與 R1 逐字相同
cargo test --test py_contract_dump -- --ignored --nocapture                      # n=0x44e6822074554786 time=0xf076bcb342595537 frames=500
cd ..
```

- [ ] **Step 3: Python 面(iso532-py/ 執行;maturin 在 workspace member 下照常運作)**

```bash
cd iso532-py
../.venv/Scripts/python.exe -m maturin develop --release
../.venv/Scripts/python.exe -m pytest tests/test_smoke.py -v            # 10/10
ISO532_REQUIRE_PARITY=1 ../.venv/Scripts/python.exe -m pytest tests/test_parity_mosqito.py -q   # 18 passed, 0 skipped
cd ..
.venv/Scripts/python.exe tools/golden_manifest.py --verify
```

- [ ] **Step 4: header 未動證明**

```bash
git diff --exit-code iso532-ffi/include/iso532.h iso532*/src iso532*/tests iso532*/Cargo.toml
```

---

### Task 3: CI cache 設定 + commit + push

**Files:**
- Modify: `.github/workflows/ci.yml`

- [ ] **Step 1: 三處 `rust-cache` 的 `workspaces:` 改指 root**

`workspaces: iso532` / `workspaces: iso532-ffi` / `workspaces: iso532-py` 三行全改為 `workspaces: .`。job 的 `working-directory` 不動(member 目錄下執行 cargo 在 workspace 內完全合法)。

- [ ] **Step 2: 單一 commit + push**

```bash
git add Cargo.toml Cargo.lock .github/workflows/ci.yml
git commit -m "build: unify crates under a root cargo workspace"
git push
```

- [ ] **Step 3: 請使用者確認 GitHub Actions**

無 gh CLI/token——請使用者開 Actions 頁確認 `test`/`ffi`/`py` 三 job 全綠。紅燈時抄回失敗 log 迭代(常見:rust-cache 路徑、maturin 找不到 workspace lock)。

---

### Task 4: 收尾註記

- [ ] 在本檔尾追加(全部實測值,不得杜撰):

```markdown
---
## 收尾註記(執行完成後填)
- commit:<hash>;CI 三 job:<綠/紅與處置>。
- hash gate:12/12 逐字相同(<是/否>);py-contract:<相同/漂移>。
- parity:18 passed / 0 skipped;golden manifest:<通過/失敗>。
- lockfile 漂移:<無/列出釘回或接受的套件與版本>。
- 偏差(若有):<無/列點>
```

```bash
git add docs/superpowers/plans/phases/phase-pre-r6-1-workspace.md
git commit -m "docs: PRE-R6-P1 closeout — root workspace landed" && git push
```

---

## 風險與陷阱

| # | 風險 | 機率 | 影響 | 緩解 |
|---|---|---|---|---|
| 1 | root lock 重解析拉到較新依賴 → 數值/行為漂移 | 低 | 高 | Task 1 Step 2 釘回舊版;hash gate 12/12 最終仲裁 |
| 2 | `cargo test --workspace` 誤含 iso532-py → 連結失敗被誤判為壞掉 | 中 | 低 | `default-members` 排除;背景節已載明這是設計事實 |
| 3 | rust-cache 指向舊 member 路徑 → CI 快取失效或紅燈 | 中 | 中 | Task 3 Step 1;紅燈迭代 |
| 4 | 搬移 commit 混入其他變更 | 低 | 高 | 鐵律節白名單;Task 2 Step 4 的 `git diff --exit-code` 看守 |

---
## 收尾註記(2026-07-18)
- commit:單一提交，hash 於交付回報（Git commit 無法在自身內容中自引最終 hash）；CI 三 job:未確認（push 後待 GitHub Actions）。
- hash gate:12/12 逐字相同(是);py-contract:相同（n=0x44e6822074554786,time=0xf076bcb342595537,frames=500）。
- parity:18 passed / 0 skipped;golden manifest:通過（175 files match）；smoke:10 passed。
- lockfile 漂移:無（pyo3 0.23.5,numpy 0.23.0,rayon 1.12.0,thiserror 1.0.69,criterion 0.5.1 均與 member lock 一致）。
- 偏差:root `cargo test` 兩次皆在啟動 `simd_dispatch` 時發生 Windows ACL `os error 5`；先前 suite 已通過，另行執行的 FFI 17 tests、fmt、workspace clippy、FFI clippy 均通過。此為環境阻礙，未修改任何邏輯或雜湊以迴避。