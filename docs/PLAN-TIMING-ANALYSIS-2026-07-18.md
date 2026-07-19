# 計畫時序分析：repo 分割時機與 ZwtvStream pyclass 進入時機（2026-07-18）

> 前提：R5 三輪審查已於 commit `6f12e8c` 封盤，串流 API v1（含 `iso532_stream_*` C ABI）已凍結。
> 架構結論沿用 `docs/ARCH-EVAL-REPO-SPLIT-2026-07-18.md`（分 2 repo）；本文回答「何時分」與「pyclass 何時做」。

## 1. 專案目標與進度盤點

主計畫 `docs/superpowers/plans/2026-07-05-roadmap-master-plan.md` 八階段對照現況：

| 階段 | 內容 | 狀態 |
|---|---|---|
| R1 | calc_slopes 去重 | ✅（2026-07-09 封盤） |
| R2 | zwst IsoReference | ⏸ 使用者決定遞延 |
| R3 | C-ABI + Python（批次） | ✅（`bb37c97`，2026-07-11） |
| R4 | 頻帶平行化（離線） | ✅（2026-07-10 封盤，MT AVX2 52.2 ms） |
| R5 | 串流 API + phon | ✅（`3254bde` + `6f12e8c`，v1 凍結） |
| R6 | VST 插件（64 軌 + 面板） | 未開工——**下一個大階段** |
| R7 | NEON + CI 三平台 | 未開工（R6 出 macOS 版前必須） |
| R8 | workspace 化 + sharpness | 未開工（觸發條件：第二個標準動工） |

三種交付方案的完成度（對照 ARCH-EVAL 表）：

- **方案 1（靜態 + C-ABI + py）**：✅ 完整。
- **方案 2（動態 + C-ABI + py）**：C-ABI ✅；**py 僅有批次 `loudness_zwtv`，`ZwtvStream` 尚未綁 pyclass**——這是唯一缺口。
- **方案 3（動態 + 面板）**：未開工，等於 R6。

關鍵事實：repo 目前**沒有任何 git tag**、根目錄**沒有 workspace `Cargo.toml`**（三 crate 為兄弟目錄）。這兩點直接影響下面的時機判斷。

## 2. repo 分割時機：R6a 開工日，不提前、不延後

**結論：repo B（面板/VST）在 R6a 可行性原型開工的那一刻開，之前不開。**

### 為何不提前

- 提前開只會得到空殼 repo。R6a 的三個致命問題（宿主取樣率、64 軌聚合架構是否同行程、CLAP/VST3 授權）**決定 repo B 的骨架**——聚合架構若被迫走共享記憶體 IPC，repo 佈局完全不同。答案出來前寫的任何腳手架都是猜。
- 引擎側在分割前還有收尾（見 §4 前置清單），先分割會讓 repo B 依賴一個尚未定稿的消費面。

### 為何不延後

- R6a 原型本身就是應用層程式（掛 nih-plug、跑 DAW 實測），寫在引擎 repo 裡違反 ARCH-EVAL 的隔離理由（依賴重量、CI 污染、授權隔離）——**原型第一行程式碼就該落在 repo B**。所以「開 repo B」與「R6a 開工」是同一件事。

### 分割前引擎 repo 的三項前置（順序固定）

1. **root workspace `Cargo.toml`**（ARCH-EVAL 待辦）：純機械變更，統一 `cargo test --workspace`。Gate：全測綠 + hash 12/12 不變 + clippy/fmt 乾淨。注意 `iso532-py` 的 renamed dep `iso532_core` 與 ffi 的 crate-type 不受 workspace 化影響，但 profile 合併要檢查（workspace 只認 root profile——三 crate 現有 `[profile.*]` 設定須上收）。
2. **ZwtvStream pyclass**（見 §3）——引擎 API 面的最後一塊。
3. **打第一個 tag**（建議 `v0.1.0`，標註 ABI v1）：repo B 的消費契約是「repo A 的 tagged release」，沒有 tag 就沒有可依賴的凍結點。tag 內容物 = crate（git tag dep 給 nih-plug 用）+ `iso532.h` + dll/lib + wheel。

> 澄清一個易混淆點：**R8 的「workspace 化」與這裡的 root workspace 是兩件事**。前置 1 只是把三個既有兄弟 crate 收進一個 virtual workspace（半天內）；R8 是把 `dsp-core` 從 `iso532` 拆出來供 sharpness/ECMA 複用（結構性搬移），觸發條件維持主計畫原話「第二個標準動工時做，不提前」，與 repo 分割無關。

## 3. ZwtvStream pyclass 進入時機：現在，repo 分割之前

**結論：作為下一輪 Codex 工作立即排入，在 tag 之前完成。** 理由按權重：

1. **補完方案 2 的交付矩陣**。三方案同時可用是使用者定下的目標；缺口只剩這一格，且是純加法（py API 不在 v1 凍結面）。
2. **tag 的完整性**。第一個 tag 是 repo B 的消費基準，也是三方案的「全量交付點」——pyclass 若排在 tag 後，方案 2 就得等第二個 tag 才完整。工作量 1–2 天，擋不住任何事。
3. **語境新鮮度**。R5 的測試基建（chunk 不變性、ZeroState 參考、純整數跨語言訊號慣例）與三輪審查記憶都還熱，現在做的驗證成本最低；等 R6 期間回頭做要重新暖機。
4. **反向收益**：py 串流接口讓 R6 期間的任何引擎迴歸都能用 pytest 從 Python 端快速複現（多一層驗證槓桿，這正是當初 R3 先於 R5 的同一邏輯）。

VST 本身**不需要** pyclass（nih-plug 直接吃 Rust crate），所以這不是 R6 的依賴——是方案 2 的交付項與 tag 完整性的問題。

### pyclass 設計要點（供 phase 計畫展開，此處先鎖方向）

- **介面**：`class ZwtvStream(field_type: str = "free")`，方法 `push(chunk: np.ndarray) -> (n, n_phon, t_frame_index, flags)`（四個 ndarray，長度 = 該次輸出幀數）、`flush() -> 同形`、`reset()`、屬性 `residual_flags`、`latency_samples`（類屬性/staticmethod）。
- **GIL**：`push` 走 `py.allow_threads`；輸入照批次慣例先拷貝 owned buffer（soundness：其他執行緒可變動 ndarray）。**不承諾 py 層零配置**——每次 push 以 `max_frames_for_chunk` 預配輸出 Vec 再轉 numpy；零配置是 Rust 熱路徑契約，py 層本來就有 ndarray 配置，文件講清楚即可。
- **執行緒安全**：handle 無內部鎖——pyclass 標 `unsendable`（最簡單且誠實），文件註明單執行緒使用。
- **NaN/Inf 語意**：與 Rust 串流一致（置零 + flag，不 raise）——**刻意與批次 py API 的 raise 行為不同**，docstring 明載差異與 `residual_flags` 的 flush 前 provisional 語意（沿用 6f12e8c 定稿的文字）。
- **flush 後語意**：Rust 端 flush 後僅 reset/drop 合法；pyclass 對 flush 後的 push 應轉成 Python 例外而非讓內部 assert 變 panic——binding 層先查狀態旗標。
- **測試**：(a) py 串流 vs py 批次（跳過 N_WARMUP=580 後 atol 1e-9，重述 E3）；(b) py 串流 vs Rust 測試凍結的參考雜湊或純整數訊號逐位（沿 R3 慣例，不用 sin 合成）；(c) chunk 尺寸不變性 py 版（480 vs 全量一次 push，逐位）；(d) NaN 置零 + flags 浮現、flush 後 push raise、reset 後逐位等同新例。
- **凍結面不動**：C ABI、`iso532/src` 核心、hash gate 12/12 皆不得有 diff——這輪只碰 `iso532-py/`。

## 4. 建議排程（整合）

```
現在 ──► ① root workspace Cargo.toml（0.5 天，純機械，單獨 commit）
     ──► ② ZwtvStream pyclass（1–2 天，Codex，phase 計畫另出）
     ──► ③ tag v0.1.0（ABI v1；三方案全量交付點）
     ──► ④ 開 repo B ＝ R6a 可行性原型開工（三個致命問題）
              │
              ├─ R6a 期間背景調研已可開始（主計畫 §10-3 原建議）
              └─ R7（NEON + CI）與 R6a/R6b 無依賴，可插隊；
                 唯一硬約束：VST 出 macOS 版前必須完成
R2  ⏸ 維持遞延（使用者決定）
R8  ⏸ 維持「第二個標準動工才 workspace 化」，與上述皆無關
```

順序 ①→②→③ 不可換：① 讓 ② 的 CI/測試在 workspace 下跑一次驗證搬移無害；③ 必須含 ② 才是完整交付點；④ 依賴 ③ 的 tag 作消費契約。

## 5. 風險備忘

| # | 風險 | 緩解 |
|---|---|---|
| 1 | workspace 化混入行為變更，golden 失效無法歸因 | 沿 R8 鐵律：零邏輯變更、單獨 commit、hash 12/12 綠才繼續 |
| 2 | pyclass 把 Rust 內部 assert（flush 後 push）暴露成 panic→abort | binding 層狀態旗標先擋，轉 Python 例外；panic 注入測試沿 R3 慣例 |
| 3 | py 串流測試誤用 sin 合成訊號 → numpy/Rust libm ULP 差導致逐位測試假紅 | 沿 R3 決策：純整數演算訊號 + Rust dump 凍結常數 |
| 4 | tag 打太早（pyclass 前）→ 方案 2 缺口滾入 R6 期間被遺忘 | 本文 §4 順序固定 ①→②→③ |
| 5 | R6a 原型誤寫進引擎 repo | repo B 於 R6a 開工日即開；原型程式碼一律落 repo B |
