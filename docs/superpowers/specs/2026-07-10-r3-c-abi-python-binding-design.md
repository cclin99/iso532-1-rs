# R3:C-ABI + Python binding 設計規格

日期:2026-07-10
狀態:已核可(brainstorming 三策分析後採上策)
上游文件:`docs/superpowers/plans/2026-07-05-roadmap-master-plan.md` §R3、
`docs/ARCHITECTURE-PERFORMANCE-RISK-REPORT-2026-07-10.md`(R-14/R-17)、
`docs/CI-HASH-GATE-DEBUG-2026-07-10.md`(bitwise 契約實證)

---

## 1. 目標與範圍

為 `iso532` crate 建立批次 API 的 C-ABI(`iso532-ffi`)與 Python binding
(`iso532-py`),並把 R-14(golden 再生鏈失效)以「本機收口」深度一併關閉。

**R3 的定位是驗證槓桿**:pytest parity 傘(Rust binding vs mosqito 直跑)
是之後 R5 串流重構與所有後續階段的迴歸傘;傘的完整性優先於一切。

**範圍內**:zwtv + zwst 兩個批次入口的 C-ABI 與 Python 介面、R-14 本機收口
(lockfile + SHA256 manifest + 再生 SOP)、CI 加 C smoke test 與雙平台
wheel build。

**明確不做**(YAGNI / 留給後續階段):
- CI 重生 golden、golden 測試上 CI —— R7(三平台 CI)範圍;現在做會把
  hash-gate 的跨平台 libm 戰役在 155 MB 資料上重打一次。
- opaque handle / 串流 C-ABI —— R5 收尾時以 `iso532_stream_*` 擴充。
- PyPI 發佈 —— wheel 是內部驗證工具,CI artifact 即交付。
- `FORCE_SCALAR` / `ParMode` 匯出 —— 不進任何 binding 介面。
- 輸出指標 NULL = 略過該輸出 —— v0 全指標必填,選擇性輸出是 v1 之後的事。

## 2. 已鎖定的上游決策(不重議)

來自 roadmap 主計畫 §R3:

1. **記憶體模型:caller-allocated 兩段式**——查尺寸 → 呼叫端配置 → 填入。
   不回傳 Rust 配置的指標,無跨 allocator 釋放問題。
2. **錯誤碼**:`0=OK`,`Iso532Error` 三變體映射 1/2/3,負值保留給 FFI 層。
   一經發布不得重排。
3. **panic 邊界**:每個 `extern "C"` 函式體整體包 `catch_unwind`,panic → -2。
4. **執行緒**:rayon 照常參與批次路徑;文件註明程式庫使用行程級 thread pool。
5. **v0 標記**(R-17):`.h` 標註 `/* v0, pre-1.0: may change */`,R5 收尾
   一併升 v1 凍結。

## 3. 架構

```
D:\ISO532\
├── iso532/          ← 完全不動(驗收:src/ 零 diff)
├── iso532-ffi/      ← 新 crate,crate-type = ["cdylib","staticlib"]
│   ├── src/lib.rs       extern "C" 薄殼,path 依賴 iso532
│   ├── tests/           錯誤映射、panic 注入、尺寸 property 測試
│   └── include/iso532.h cbindgen 生成後入 git,標 /* v0 */
├── iso532-py/       ← 新 crate,pyo3(abi3-py39)+ maturin + rust-numpy
│   ├── src/lib.rs       直接 path 依賴 iso532(不經 C-ABI)
│   └── tests/           pytest parity 傘 + bitwise 測試
└── tools/
    ├── requirements.lock    新增(pip freeze 全鎖)
    └── golden_manifest.py   新增(SHA256 生成/驗證)
```

**不建 Cargo workspace**:三個獨立 crate 用 path 依賴。理由——R8 規則
(workspace 化在第二個標準動工時做,不提前);workspace 會把 `target/`
移到 repo 根,弄髒 bench baseline 路徑與 CI cache 設定。

**`iso532-py` 直接依賴 Rust API,不繞經 C-ABI**:pyo3 原生呼叫才能
零拷貝並保留具名錯誤;C-ABI 與 Python binding 是兄弟層,不是父子層。

## 4. C 介面(v0)

輸出幀數閉式解(實作事實,自 `DEC_FACTOR=24` 與 calc_slopes `step_by(4)`):
`frames = ceil(ceil(signal_len / 24) / 4)`。

```c
/* v0, pre-1.0: may change until R5 freezes v1 (risk R-17) */

/* 純函數,= ceil(ceil(signal_len/24)/4);不做輸入驗證(驗證在主呼叫) */
size_t  iso532_zwtv_out_frames(size_t signal_len);

int32_t iso532_loudness_zwtv(const double *signal, size_t signal_len,
                             double fs, int32_t field_type,      /* 0=Free, 1=Diffuse */
                             double *out_n,          /* frames        */
                             double *out_n_specific, /* 240 × frames, bark-major row-major */
                             double *out_bark,       /* 240           */
                             double *out_time);      /* frames        */

int32_t iso532_loudness_zwst(const double *signal, size_t signal_len,
                             double fs, int32_t field_type,
                             double *out_n,           /* 1   */
                             double *out_n_specific,  /* 240 */
                             double *out_bark);       /* 240 */
```

- 所有指標必填;任一 NULL → -1。
- 每個 `extern "C"` 函式體以 `ffi_guard!` 巨集統一包 `catch_unwind`。
- header 由 cbindgen 生成後 **commit 入 git**;CI 的 C smoke test 對著已
  commit 的 header 編譯——簽名漂移即編譯失敗,免額外 drift 檢查工具。
- ABI 承諾:Windows 只承諾 MSVC ABI(與 VST host 生態一致)。

## 5. 錯誤碼佈局(發布後不得重排)

| 碼 | 意義 | 來源 |
|---|---|---|
| 0 | OK | |
| 1 | `LevelExceeds120dB` | `Iso532Error` |
| 2 | `SignalTooShort` | `Iso532Error` |
| 3 | `UnsupportedSampleRate` | `Iso532Error` |
| -1 | NULL 指標 | FFI 層 |
| -2 | panic 被 catch_unwind 攔截 | FFI 層 |
| -3 | field_type 不是 0/1 | FFI 層 |

## 6. Python 介面

```python
iso532.loudness_zwtv(signal, fs, field_type="free")
# -> (n: ndarray[frames], n_specific: ndarray[240, frames],
#     bark_axis: ndarray[240], time_axis: ndarray[frames])

iso532.loudness_zwst(signal, fs, field_type="free")
# -> (n: float, n_specific: ndarray[240], bark_axis: ndarray[240])
```

- `field_type` 收 `"free"` / `"diffuse"`(不分大小寫不做——精確匹配),
  其他值 → `ValueError`。
- 輸入嚴格要求 C-contiguous float64 1D ndarray,否則 `TypeError`
  (不做隱式轉換或拷貝——parity 測試要求位元級可控)。
- 計算段 `py.allow_threads` 釋放 GIL;回傳 `PyArray::from_vec` 零額外拷貝,
  `n_specific` reshape 成 `(240, frames)`。
- `Iso532Error` → `ValueError`(帶 Rust Display 訊息);panic 由 pyo3
  自帶 catch_unwind 轉 `PanicException`。
- wheel:`abi3-py39` 單 wheel per OS;不發佈 PyPI,CI artifact 即交付。

## 7. R-14 收口元件(本機收口深度)

背景:golden 再生鏈 = `mosqito-1.2.1.tar.gz + numpy + scipy + Python 3.11`
→ `tools/gen_golden.py` → `data/golden/*.bin`(155 MB,gitignored)。
現況三斷點:版本未鎖(venv 實測 numpy 2.4.6 / scipy 1.17.1,無 lockfile)、
無完整性檢查、Annex B wav 依賴上游 GitHub repo。

1. **`tools/requirements.lock`**:pip freeze 全鎖(numpy、scipy、mosqito
   tarball 含 sha256),標頭註記 Python 3.11.9;`tools/setup_env.sh` 改為
   從 lock 安裝。
2. **`tools/golden_manifest.py`**:`--generate` / `--verify` 兩模式,
   SHA256 涵蓋 `data/golden/**`(.bin + meta.json)與 `data/annexb/*.wav`
   (順便固化上游 wav 來源)。清單 `tools/golden.sha256` 入 repo。
   **標頭明載生成環境(OS/CPU/套件版本)——這是 per-環境契約,不是跨平台
   契約**(hash-gate 教訓:libm ULP 噪音使跨環境 SHA256 必然不同)。
3. **`docs/GOLDEN-REGEN-SOP.md`**:換機器/重建 venv 的完整再生與驗證步驟
   (重建 venv → gen_golden → manifest --verify → cargo test golden 全綠)。

## 8. 資料流

- **C 端**:`iso532_zwtv_out_frames(len)` 查尺寸 → caller 配置四塊緩衝 →
  呼叫 → 檢查錯誤碼。
- **Python 端**:ndarray → `as_slice()` 借用(零拷貝入)→ 釋放 GIL 計算 →
  `from_vec` 移交(零拷貝出)。
- **pytest parity**:合成/載入 9 組訊號(6 組合成 + 3 組 Annex B wav,
  與 `gen_golden.py` 同一生成程式碼)→ mosqito 直跑 + binding 各算一次 →
  容差/位元比對。

## 9. 測試策略

| 層 | 測試 | 跑在哪 |
|---|---|---|
| ffi 單元 | 錯誤映射 1/2/3、NULL→-1、field_type→-3 | 本機 + CI |
| ffi panic | `test-panic` feature 的隱藏匯出 → -2;**rayon 工作項內 panic → -2**(寫測試證實 join 點 resume 被外層接住,不假設) | 本機 + CI |
| ffi property | 200 組隨機長度(取樣範圍 4800..=48_000,涵蓋 `SignalTooShort` 下限與各降採樣餘數):`iso532_zwtv_out_frames()` == 實際輸出長度(對照直接呼叫 Rust API 的 `n.len()`);另對 0..4800 抽驗查詢函式本身不 panic | 本機 + CI |
| C smoke | 小 .c 程式對已 commit 的 header 編譯連結(ubuntu gcc + windows MSVC),餵 4800 樣本正弦,驗回傳 0 且輸出為有限值 | CI |
| pytest parity(迴歸傘) | 9 組訊號 zwtv + zwst vs mosqito 直跑:容差沿用 golden 端對端實證值 **rtol 1e-6 / atol 1e-9**(roadmap 原訂 atol 1e-12,P3 實測若可達則單向收緊,不放寬) | 本機(venv 有 mosqito) |
| pytest bitwise | 純整數演算訊號(`s[i]=((i·2654435761) mod 96001)/96000·0.02−0.01`,無 libm,Python/Rust 可生成逐位相同輸入;hash-gate 的 sin 合成訊號**不可用**——numpy 與 Rust libm 的 sin 差 ULP)的 `n`/`time_axis` FNV-1a hash == 凍結常數(由 Rust 端 dump 測試實測凍結;`n`/`time_axis` 已實證跨平台跨 backend 穩定) | 本機 + CI(wheel 測試內) |
| wheel 安裝 | maturin build → 乾淨 venv 安裝 → import + 小訊號呼叫 | CI(雙平台) |
| golden manifest | `--verify` 全符 | 本機 |

CI **不裝 mosqito、不重生 golden**(R7 範圍);parity 傘的執行前提寫進
SOP。現有 37 測試與 `iso532/src/` 完全不動。

## 10. CI 變更

現有 `test` job 不動,新增:

- **ffi job**(windows-latest + ubuntu-latest):`cargo fmt/clippy/test`
  (iso532-ffi)+ C smoke test(gcc / MSVC 對已 commit 的 header)。
- **py job**(windows-latest + ubuntu-latest):`maturin build --release`
  → 乾淨 venv 安裝 wheel → import + 小訊號呼叫 + bitwise 測試 → wheel
  上傳為 artifact。

## 11. Phase 切分(交 Codex)

| Phase | 內容 | Exit Gate |
|---|---|---|
| **R3-P1:R-14 收口** | requirements.lock、golden_manifest.py、SOP、實地驗證一輪再生 | 乾淨重建 venv → 重生 golden → SHA256 全符 → cargo test golden 全綠 |
| **R3-P2:iso532-ffi** | crate + header + `ffi_guard!` + ffi 全部測試 + CI ffi job | CI 雙平台全綠(含 C smoke);panic 注入與 property 測試過 |
| **R3-P3:iso532-py** | pyo3 crate + pytest parity 傘 + CI py job | 9 組 parity 全過;雙平台 wheel artifact;bitwise 測試過 |

P1 先行:parity 傘依賴可信的 mosqito 環境。

## 12. 整體驗收準則

1. CI 全綠:現有 test job + ffi job(含 C smoke)+ py job(含雙平台
   wheel build 與安裝測試)。
2. pytest parity 9 組全過(rtol 1e-6 / atol 1e-9)——此測試集自此成為
   後續所有階段的迴歸傘。
3. panic 注入測試全過:100% 匯出函式 panic → -2,行程不死。
4. 乾淨機器照 SOP 重建 → golden SHA256 全符。
5. `iso532.h` 帶 v0 註記(R-17)。
6. `iso532/src/` 零 diff(FFI 與 binding 是純外掛層)。

## 13. 關鍵指標

| 指標 | 目標 |
|---|---|
| binding 開銷 | Python 呼叫 vs 原生 Rust ≤ +2%(10 s 訊號) |
| parity 精度 | rtol 1e-6 / atol 1e-9(實測可達再收緊至 atol 1e-12) |
| bitwise 契約 | Python 端 `n`/`time_axis` hash == 凍結常數 |
| panic 安全 | 注入測試 100% 函式回 -2 |
| 環境可重建 | 乾淨機器照 SOP → SHA256 全符 |

## 14. 風險與陷阱

| # | 風險 | 機率/影響 | 緩解 |
|---|---|---|---|
| 1 | panic 穿越 FFI = UB(漏包一個函式) | 中/高 | `ffi_guard!` 統一包裝;注入測試逐函式跑 |
| 2 | rayon 工作項 panic 繞過 catch_unwind 傳播路徑差異 | 低/高 | rayon panic 在 join 點 resume——寫測試證實被外層接住,不假設 |
| 3 | 尺寸查詢與實際輸出 off-by-one(降採樣邊界) | 中/中 | 200 組有效長度 property test(覆蓋 24×4 各餘數類) |
| 4 | SHA256 manifest 被誤解為跨平台契約 | 高/中 | manifest 標頭明載 per-環境;SOP 文件明載 |
| 5 | pyo3/numpy 版本矩陣(abi3 vs 非 abi3) | 中/低 | abi3-py39 單 wheel;CI 裝最舊支援版驗 |
| 6 | Windows MSVC/GNU toolchain ABI 不合 | 低/中 | 只承諾 MSVC ABI;CI 的 MSVC smoke 驗證 |
| 7 | zwst 與 zwtv 錯誤碼/命名慣例不一致 | 低/低 | 兩者同一 phase 同一巨集實作;v0 期仍可修 |
| 8 | parity 容差設過緊(roadmap 的 atol 1e-12)導致假紅燈 | 中/中 | 以 golden 實證值起步,單向收緊 |

## 15. 與後續階段的接縫

- **R5(串流)**:C-ABI 擴充 `iso532_stream_*` 四函式(opaque handle 僅
  該處引入),錯誤碼沿用本表;R5 收尾升 v1 凍結 header。
- **R7(三平台 CI)**:CI golden 重生(actions/cache)、macOS wheel、
  NEON parity——本 spec 刻意不做的部分在該階段收口。
- pytest parity 傘自 R3 起是所有階段的迴歸驗收工具。
