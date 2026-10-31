# C-01 輸出長度契約：ceil／floor 差異、後續發展影響與上中下策

日期：2026-10-31（Asia/Taipei）。受驗程式快照 `d623d32`（v0.3.0 之後、V-01 之前）。本文是決策備忘，不改程式、不改 golden。英文版在後半部（English version follows the Chinese text）。

---

## 0. 一句話結論

Rust 的輸出點數比官方 CLI 的 total 檔多一點（除非訊號長度是 96 的倍數），但與官方 CLI 的 specific 檔相同（除非 `floor(L/24)` 是 4 的倍數且 L 不是 24 的倍數）。差的是**尾端的一個時間點**，起點、相位、前面所有點都相同。建議採上策：保留現行 ceil 規則、把契約寫死、為沒有官方對照的尾端點補獨立預期值；不建議改成 floor。

## 1. 三套規則分別是什麼

訊號長度 L（樣本，48 kHz），官方內部 2 kHz 點數 `K = floor(L/24)`，餘數 `r = L mod 24`。

| 階段 | Rust（batch 與 stream） | 官方 C library（Annex A `ISO_532-1.c`） | 官方 CLI 輸出檔 |
|---|---|---|---|
| 內部 2 kHz 格線 | `ceil(L/24)` 點，在樣本 `24k` 取濾波器輸出（[third_octave_levels.rs:87-96](../iso532/src/zwtv/third_octave_levels.rs#L87-L96)，`i % 24 == 0`） | `K = L/24`（整數除法＝floor），同樣在樣本 `24k` 取值（`pSPL += DecFactor`，`f_calc_third_octave_levels`） | 同 library |
| 輸出 2 ms 格線 | `ceil(ceil(L/24)/4)` 點，取內部 index `0, 4, 8, …`（[zwtv/mod.rs:18-22](../iso532/src/zwtv/mod.rs#L18-L22)） | library 不下抽，回傳全部 K 點 | total 檔 `floor(K/4)` 點；specific 檔從 index 0 起每 4 點寫一次，`ceil(K/4)` 點（`docs/修正報告2.md` §11.4） |
| 時間軸 | `t_j = 2j ms`，自 0 起 | 同 | 同；§11.4 已確認共同時點差 0 s |
| 最後一個內部 frame 的非線性衰減 | 以 `next = 0` 內插（[nonlinear_decay.rs:143](../iso532/src/zwtv/nonlinear_decay.rs#L143)，MoSQITo 慣例；stream 的 flush 同義） | 最後一點單步更新，不內插（`f_nl` 末行） | 同 library |

重點：三者的起點與相位相同，Rust 的點集合包含 CLI specific 的點集合，CLI specific 又包含 CLI total。差異只在尾端要不要多一個點。

## 2. 什麼時候會差一點

| 情況 | Rust 點數 | CLI total | CLI specific | Rust 多出的點 |
|---|---|---|---|---|
| `L mod 96 = 0` | `K/4` | `K/4` | `K/4` | 無 |
| `K mod 4 ≠ 0`（不論 r） | `ceil(K/4)` | `floor(K/4)` | `ceil(K/4)` | 比 total 多 1，**與 specific 相同**；該點在 C 內部格線上，有 C specific 參考值 |
| `K mod 4 = 0` 且 `r > 0` | `K/4 + 1` | `K/4` | `K/4` | 比兩者都多 1；該點是 Rust 多算的內部 frame K（樣本 `24K`，真實樣本，非補零），**沒有任何官方參考值**，且其非線性衰減是以 `next = 0` 算的 |

### 2.1 Annex B 的 8 個受影響訊號

| 訊號 | Rust | CLI total | CLI specific | 歸類 | 額外點的對照 |
|---|---:|---:|---:|---|---|
| 14 | 6578 | 6577 | 6578 | `K mod 4 ≠ 0` | 與 C specific 相符，最大差 4.92e-19 |
| 15 | 5769 | 5768 | 5769 | 同上 | 8.50e-15 |
| 16 | 2055 | 2054 | 2055 | 同上 | 3.26e-21 |
| 17 | 1455 | 1454 | 1455 | 同上 | 2.31e-21 |
| 18 | 1084 | 1083 | 1083 | `K mod 4 = 0, r > 0` | 無官方參考值 |
| 23 | 1276 | 1275 | 1275 | 同上 | 無 |
| 24 | 1201 | 1200 | 1200 | 同上 | 無 |
| 25 | 1276 | 1275 | 1275 | 同上 | 無 |

其餘 17 個訊號長度是 96 的倍數，三者一致。stream 與 batch 的點數在 F-02 驗證已確認相同（含 4801、4823、4895、4897、24013 等非 96 倍數長度，36/36）。

## 3. 對後續發展的差異

| 利害關係人 | 維持 ceil（現狀） | 改成 floor（對齊 CLI total） |
|---|---|---|
| **panel／stream 路徑** | 不受影響。stream 不知道總長度，只能「每 4 個內部 frame 出 1 點、flush 時把持有的 frame 出完」，這正是 ceil 語意 | batch 與 stream 點數不再相同（stream 多 1 點），或者讓 stream 在 flush 時丟掉已算好的 frame，等於丟真實樣本的資訊；F-02 剛建立的「batch 自第 0 幀起與 stream 逐位元相同」資產失效 |
| **C ABI 消費者** | `iso532_zwtv_out_frames` 不變 | 回傳值改變；用它配置緩衝區的程式自動跟上，手抄公式的程式會多配 1 點或讀越界。C ABI v1 的語意改變，應升 0.4.0 並在 header 註明 |
| **Python／NumPy 使用者** | shape 不變 | `loudness_zwtv` 回傳 shape 改變；與 MoSQITo 的 shape 不再相同，parity 測試要先裁切 |
| **golden／hash gate** | 不變 | 全部 zwtv frozen hash 重凍結；MoSQITo golden 保持 ceil shape，比對需裁切 |
| **ISO 合規主張** | 可以寫「前 `floor(K/4)` 點與 CLI total 格線一一對應；第 `ceil(K/4)` 點與 CLI specific 一一對應；其餘尾端點為本實作的延伸，無官方對照」。審計 C-01 維持 PARTIAL，但範圍縮到 4 個訊號各 1 點 | 可以寫「total 形狀與 CLI 等價」，但 specific 仍比 CLI specific 少 1 點（CLI specific 本身是 ceil），對 14–17 這 4 個已驗證相符的點反而被丟掉 |
| **未來 Annex A 精確模式**（例如穩態 IsoReference 前端或時變的 C 尾端慣例） | 尾端慣例（floor 格線、最後一點單步更新）屬於同一組「C 的尾端習慣」，可以日後一起放進 opt-in 模式 | 現在只改格線不改尾端非線性衰減慣例，等於混用兩套慣例 |
| **版本與文件** | 0.3.x 內可完成（文件＋測試） | 0.4.0；CHANGELOG 要列 shape 變更與遷移說明 |

## 4. 上中下策

| | 上策（建議） | 中策 | 下策 |
|---|---|---|---|
| 做法 | 保留 ceil；文件寫死輸出格線契約；新增契約測試；由獨立驗證為 18／23／24／25 的額外點建立獨立預期值 | 保留 ceil；只寫文件與契約測試；額外點永久標為「無官方對照」 | 批次改 floor(floor(L/24)/4)，對齊 CLI total |
| 數值／shape 變更 | 無 | 無 | shape 變更（8/25 個 Annex B 訊號少 1 點；一般訊號凡 `L mod 96 ≠ 0` 皆少 1 點） |
| batch＝stream 逐位元 | 保持 | 保持 | 失去，或迫使 stream 丟棄尾端 frame |
| 審計 C-01 狀態 | 可從 PARTIAL 收斂到「值的慣例差」；若預期值在容差內甚至可關閉 | PARTIAL，但有明確文件 | total 形狀等價，但 specific 與已驗證點的問題換成另一種 PARTIAL |
| 成本 | 文件 0.5 天＋測試 0.5 天（Codex phase）＋一輪 Astra 驗證 | 文件 0.5 天＋測試 0.5 天 | 程式＋三個 binding＋hash 重凍＋golden 裁切＋0.4.0 發版＋重新驗證，約 2–3 天，另有下游遷移 |
| 風險 | 低 | 低 | 中：破壞性變更，而且只對齊 CLI 兩種輸出中的一種 |

### 4.1 上策的「獨立預期值」怎麼來

額外點（訊號 18、23、24、25）位在內部 frame `K`，取樣點是真實樣本 `24K`。官方 C library 之所以沒有它，只是因為 `NumSamples/DecFactor` 用整數除法。把訊號補零到 `24(K+1)` 以上再送官方 C library，C 會在 frame `K` 算出同一組 28 個頻帶位準（濾波器狀態到樣本 `24K` 為止完全相同）。唯一不同處是最後一個 frame 的非線性衰減慣例（Rust `next = 0` 內插、C 以補零後的下一 frame 內插），所以這組預期值適合用 Annex B 的 `max(0.1, 5 %)` 容差判定，不適合要求 bitwise。這樣可以把「沒有參考值」變成「在容差內、慣例差已量化」，而且不需要 CLI 的 writer。

### 4.2 一個常見的替代案：加 opt-in 的輸出格線選項

例如 `OutputGrid::Full`（預設）與 `OutputGrid::CliTotal`。不列為獨立一策，理由是：裁切對呼叫端是一行程式（取前 `floor(floor(L/24)/4)` 點），stream 無法支援它，而新增 API 面要同時維護 Rust、C ABI、Python 三處。文件給出裁切公式比加選項划算。

## 5. 需要你決定的點

1. 選上、中、下哪一策。我的建議是上策。
2. 若選上策：是否授權 Astra 一輪「補零 C library 參考」驗證（範圍只在 4 個訊號各 1 點，加上契約測試的長度邊界案例）。
3. 尾端非線性衰減慣例（`next = 0` 對 C 的單步更新）要不要列入未來 Annex A 精確模式的待辦，與 ROADMAP R2 的穩態 IsoReference 前端放在一起。

## 6. 不論選哪一策都要做的事

- 把 §1 的契約寫進 README 兩語言與 header 註解：起點 0、2 ms 相位、點數公式、尾端 lookahead 慣例、與 CLI total／specific 的裁切公式。
- 契約測試：長度 4800（最短合法）、`24k±1`、`96k±1`、以及 stream 任意 chunk 切分加 flush 的點數與批次相同；分開驗 `n`、`n_specific`、`time_axis` 三個欄位的長度。
- 審計 §12.2 C-01 列的其他驗收項（空／極短輸入已由 `SignalTooShort` 覆蓋）在同一 phase 完成。

---

# C-01 Output-length contract: ceil vs floor, downstream consequences, and three options

Date: 2026-10-31 (Asia/Taipei). Code snapshot `d623d32` (after v0.3.0, before V-01). This is a decision memo; it changes no code and no golden data.

## 0. One-sentence conclusion

The Rust batch output has one more point than the official CLI's total-loudness file (unless the signal length is a multiple of 96 samples) but the same number of points as the official CLI's specific-loudness file (unless `floor(L/24)` is a multiple of 4 and L is not a multiple of 24). The difference is a single **trailing** time point; start, phase and every earlier point are identical. Recommendation: the "best" option below, i.e. keep the current ceil rule, freeze the contract in writing, and obtain independent expected values for the tail points that have no official reference. Switching to floor is not recommended.

## 1. The three rules

Signal length L (samples at 48 kHz), official internal 2 kHz frame count `K = floor(L/24)`, remainder `r = L mod 24`.

| Stage | Rust (batch and stream) | Official C library (Annex A `ISO_532-1.c`) | Official CLI output files |
|---|---|---|---|
| Internal 2 kHz grid | `ceil(L/24)` frames, filter output sampled at sample `24k` ([third_octave_levels.rs:87-96](../iso532/src/zwtv/third_octave_levels.rs#L87-L96), `i % 24 == 0`) | `K = L/24` (integer division = floor), also sampled at sample `24k` (`pSPL += DecFactor` in `f_calc_third_octave_levels`) | as library |
| Output 2 ms grid | `ceil(ceil(L/24)/4)` points, internal indices `0, 4, 8, …` ([zwtv/mod.rs:18-22](../iso532/src/zwtv/mod.rs#L18-L22)) | no decimation, returns all K frames | total file: `floor(K/4)` points; specific file: every 4th frame from index 0, `ceil(K/4)` points (`docs/修正報告2.md` §11.4) |
| Time axis | `t_j = 2j ms` from 0 | same | same; §11.4 confirmed a 0 s offset on the common points |
| Nonlinear decay of the last internal frame | interpolates towards `next = 0` ([nonlinear_decay.rs:143](../iso532/src/zwtv/nonlinear_decay.rs#L143), MoSQITo convention; stream `flush` has the same meaning) | single update step, no interpolation (last line of `f_nl`) | as library |

Key point: all three share start and phase. The Rust point set contains the CLI specific set, which contains the CLI total set. The only difference is whether one extra trailing point exists.

## 2. When the extra point appears

| Case | Rust points | CLI total | CLI specific | Rust's extra point |
|---|---|---|---|---|
| `L mod 96 = 0` | `K/4` | `K/4` | `K/4` | none |
| `K mod 4 ≠ 0` (any r) | `ceil(K/4)` | `floor(K/4)` | `ceil(K/4)` | one more than total, **same as specific**; the point lies on the C internal grid and has a C specific reference |
| `K mod 4 = 0` and `r > 0` | `K/4 + 1` | `K/4` | `K/4` | one more than both; it is the internal frame K that Rust computes and C does not (sample `24K`, a real sample, not zero padding); **no official reference of any kind**, and its nonlinear decay uses `next = 0` |

### 2.1 The eight affected Annex B signals

| Signal | Rust | CLI total | CLI specific | Case | Reference for the extra point |
|---|---:|---:|---:|---|---|
| 14 | 6578 | 6577 | 6578 | `K mod 4 ≠ 0` | matches C specific, max diff 4.92e-19 |
| 15 | 5769 | 5768 | 5769 | same | 8.50e-15 |
| 16 | 2055 | 2054 | 2055 | same | 3.26e-21 |
| 17 | 1455 | 1454 | 1455 | same | 2.31e-21 |
| 18 | 1084 | 1083 | 1083 | `K mod 4 = 0, r > 0` | none |
| 23 | 1276 | 1275 | 1275 | same | none |
| 24 | 1201 | 1200 | 1200 | same | none |
| 25 | 1276 | 1275 | 1275 | same | none |

The other 17 signals have lengths that are multiples of 96 and agree everywhere. Batch and stream frame counts were confirmed equal in the F-02 verification, including non-multiple-of-96 lengths (4801, 4823, 4895, 4897, 24013; 36/36).

## 3. Consequences for future development

| Stakeholder | Keep ceil (status quo) | Switch to floor (CLI total) |
|---|---|---|
| **panel / stream path** | unaffected; the stream does not know the total length, so it can only emit one point per 4 internal frames and flush the held frame, which is exactly the ceil semantics | batch and stream counts diverge (stream has one more), or the stream must discard an already-computed frame at flush, throwing away real-sample information; the just-verified "batch equals stream bitwise from frame 0" property is lost |
| **C ABI consumers** | `iso532_zwtv_out_frames` unchanged | its return value changes; callers using it adapt automatically, callers with a hand-copied formula over-allocate or read out of bounds; C ABI v1 semantics change, so 0.4.0 with a header note |
| **Python / NumPy users** | shape unchanged | `loudness_zwtv` return shape changes; no longer the MoSQITo shape, parity tests need trimming first |
| **golden / hash gates** | unchanged | all zwtv frozen hashes re-recorded; MoSQITo goldens keep the ceil shape and must be trimmed for comparison |
| **ISO compliance statements** | "the first `floor(K/4)` points map one-to-one to the CLI total grid, the `ceil(K/4)`-th point maps to CLI specific, any further tail point is an extension of this implementation without an official reference"; audit item C-01 stays PARTIAL but shrinks to one point in each of 4 signals | "total shape is equivalent to the CLI", but specific still has one point fewer than CLI specific (which is itself ceil), and the 4 verified points of signals 14–17 are discarded |
| **future exact Annex A mode** (e.g. the stationary IsoReference front end, or the C tail conventions for time-varying) | the tail conventions (floor grid, single-step last frame) belong together and can later go into one opt-in mode | changing only the grid now, but not the last-frame decay convention, mixes two conventions |
| **versioning / docs** | fits in 0.3.x (docs + tests) | 0.4.0; CHANGELOG must list the shape change and migration |

## 4. Three options

| | Best (recommended) | Middle | Worst |
|---|---|---|---|
| Action | keep ceil; freeze the output-grid contract in docs; add contract tests; have an independent round establish expected values for the extra points of 18/23/24/25 | keep ceil; docs and contract tests only; extra points permanently marked "no official reference" | switch batch to floor(floor(L/24)/4) to match CLI total |
| Numeric / shape change | none | none | shape change (one point fewer for 8 of 25 Annex B signals and for every signal with `L mod 96 ≠ 0`) |
| Batch = stream bitwise | kept | kept | lost, or forces the stream to discard its tail frame |
| Audit C-01 status | can converge from PARTIAL to a quantified convention difference, possibly closed if the expected values are within tolerance | PARTIAL, but documented | total shape equivalent, yet specific and the already-verified points become a different PARTIAL |
| Cost | 0.5 day docs + 0.5 day tests (Codex phase) + one Astra round | 0.5 day docs + 0.5 day tests | code + three bindings + hash re-freeze + golden trimming + 0.4.0 release + re-verification, about 2–3 days, plus downstream migration |
| Risk | low | low | medium: a breaking change that aligns with only one of the CLI's two outputs |

### 4.1 Where the "independent expected values" come from

The extra point (signals 18, 23, 24, 25) is internal frame `K`, sampled at real sample `24K`. The official C library lacks it only because `NumSamples/DecFactor` is integer division. Zero-padding the signal to at least `24(K+1)` samples and running the official C library makes it produce frame `K` from the identical 28 band levels (the filter state up to sample `24K` is the same). The single remaining difference is the last-frame nonlinear-decay convention (Rust interpolates towards `next = 0`, C towards the next padded frame), so these expected values are suitable for the Annex B `max(0.1, 5 %)` verdict, not for a bitwise requirement. This turns "no reference" into "within tolerance, convention difference quantified" without needing the CLI writers.

### 4.2 A common alternative: an opt-in output-grid option

For example `OutputGrid::Full` (default) and `OutputGrid::CliTotal`. Not listed as a separate option because trimming is a one-liner for the caller (keep the first `floor(floor(L/24)/4)` points), the stream cannot honour it, and a new API surface has to be maintained in Rust, the C ABI and Python. A documented trimming formula is cheaper.

## 5. Decisions needed

1. Best, middle or worst. My recommendation is best.
2. If best: authorise one Astra round "zero-padded C library reference" (scope: one point in each of 4 signals, plus the length-boundary cases of the contract tests).
3. Whether the last-frame decay convention (`next = 0` versus C's single step) goes on the backlog of a future exact Annex A mode together with the ROADMAP R2 stationary IsoReference front end.

## 6. Work needed under every option

- Write the §1 contract into both READMEs and the header comment: start 0, 2 ms phase, count formula, tail lookahead convention, trimming formulas for CLI total / specific.
- Contract tests: length 4800 (shortest legal), `24k±1`, `96k±1`, and stream with arbitrary chunking plus flush having the same count as batch; check the lengths of `n`, `n_specific` and `time_axis` separately.
- Complete the remaining acceptance items of audit §12.2 row C-01 in the same phase (empty / very short input is already covered by `SignalTooShort`).
