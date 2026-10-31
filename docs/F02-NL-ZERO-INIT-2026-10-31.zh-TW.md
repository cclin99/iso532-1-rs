# F-02：批次非線性時間衰減自零狀態起算

> 對照／Pair: [English](F02-NL-ZERO-INIT-2026-10-31.md) · 來源：en · 同步 2026-11-01

- 日期：2026-10-31
- 範圍：`iso532::zwtv` 批次路徑（`loudness_zwtv`、`ZwtvProcessor`），兩種後端
  （scalar、AVX2+FMA），兩種場型。串流路徑原本就自零狀態起算，不變。
- 狀態：已修正；每個時變結果的起始段數值行為改變
- 定位：下方的 MoSQITo 比較是驗證過程中的發現，加上本專案的目前判斷；並非對
  MoSQITo 的裁定

## 發現

ISO 532-1 Annex A 以每個臨界頻帶一組雙電容網路來模擬非線性時間衰減。參考 C 程式在
第一幀之前將兩個電容電壓（`UoLast`、`U2Last`）初始化為零。

MoSQITo 1.2.1（`_nonlinear_decay.py`）以 `uo_mat[:, col-1]` 將遞迴在整段訊號上
向量化；在 `col = 0` 時 NumPy 讀到的是最後一欄，其內容是最後一幀的第 24 個插值步，
`core[:, -1] + (0 - core[:, -1]) / 24 * 23 = core[:, -1] / 24`。因此每個頻帶都以其
最終主響度的二十四分之一作為種子。Rust 批次路徑刻意重現了這個種子
（`mosqito_seed`，在 README 中記載為相容性選擇），以便階段層級與端到端的 golden
比較保持精確。

獨立審核（`docs/修正報告.md` §4、`docs/修正後獨立驗證報告.md` §2）重現了其後果：
對兩段前 0.5 s 皆為相同靜音的 1 s 訊號，在第二段的後半加入 1 kHz / 80 dB 純音，
會使批次結果的前 0.25 s 改變 0.113550559256 sone，第一幀由 0 變為
0.001623810180 sone，而 C 程式與 Rust 串流對兩者都給出 0。目前判斷：遵循
Annex A。訊號前綴的結果不得取決於其後的樣本。

## 重現（修正前／修正後，AVX2 預設 dispatch，本機）

| 案例 | 修正前（尾端種子） | 修正後（零狀態） | C 程式／串流 |
|---|---:|---:|---:|
| 靜音 0.5 s + 1 kHz 80 dB：第 0 幀的 N | 0.001623810180 sone | 0 | 0 |
| 同上，前 0.25 s 對全靜音訊號的 max \|dN\| | 0.113550559256 sone | 0 | 0 |
| 同上，240 個 Bark 在前 0.25 s 的 max \|dN'\| | 0.1677 sone/Bark | 0 | 0 |
| 合成閘門訊號 x3：批次與串流首次相符到 1e-9 的幀 | 544（`N_WARMUP_FRAMES` = 580） | 0（位元逐一） | - |

在 golden fixture 上量得的種子效應大小（預設 dispatch，批次修正前對修正後；
「最後不同幀」指 21 個非線性衰減輸出中任一個仍位元不同的最後一個三分之一倍頻程幀，
以 2000 幀/s 計）：

| fixture | 種子最大值（sone） | nl 階段：不同的幀數／最後不同幀 | 端到端 max \|dN\|（sone） |
|---|---:|---:|---:|
| sine_1k_60 | 0.0511 | 88 / 100 | 0.0118 |
| sine_250_80 | 0.1909 | 151 / 161 | 0.0650 |
| sine_4k_60 | 0.0722 | 42 / 45 | 0.0046 |
| white_60 | 0.0332 | 65 / 250 | 0.0352 |
| step_60_80 | 0.1685 | 1001 / 1000 | 0.0558 |
| annexb_sig3 (10 s) | 0.0512 | 88 / 100 | 0.0118 |
| annexb_sig5 (10 s) | 0.0269 | 102 / 239 | 0.0378 |
| pulse_1k_70、annexb_sig10（靜音尾端） | 0 | 0 / - | 0（位元逐一相同） |

端到端差異比非線性階段持續更久，因為帶種子的慢電容（`U2`，時間常數 75 ms）與
時間加權濾波器會把它帶下去；在 10 s 的 fixture 上，兩條路徑自輸出幀 482（訊號 3）
／532（訊號 5）起在 golden 容差內，自第 1002 / 980 幀起位元逐一相同。

## 修正

`NlInit { Zero, MosqitoTail }` 選擇初始狀態。`loudness_zwtv` 與
`ZwtvProcessor::process` 使用 `Zero`；`ZwtvProcessor::process_with` 與較低階的
`nl_loudness_with` / `nl_loudness_scalar_with` / `nl_loudness_avx2` 明確接受此選擇。
Python binding 以 `loudness_zwtv(..., nl_init="zero" | "mosqito_tail")` 暴露它。
24 步插值、對下一幀的前視、遞迴順序、輸出格線與串流延遲都未更動。C ABI v1 沒有
此開關，沿用預設值。

保留 `MosqitoTail` 是為了讓九個 MoSQITo golden fixture 與 MoSQITo 直接 parity 套件
仍可位元逐一比較；它被記載為 parity 工具，而非量測模式。

## 新增的驗證

- `tests/nl_zero_init.rs`（自足，在 CI 中）：對四種內容與長度不同的尾端的前綴
  不變性，在由 0.5 s 前綴決定的 250 個輸出幀上，`N` 與全部 240 個 Bark 列位元逐一
  相同；靜音前綴上的響度恰為零；批次自第 0 幀起與因果串流位元逐一相等（合成訊號
  與審核的反例）；processor 重複使用；審核得到的修正前數值釘在 `MosqitoTail` 下；
  訊號結尾為靜音時兩種初始化相同。先失敗紀錄：以修正前的程式碼，四個僅經 API 的
  測試中有三個失敗（`N frame 0 = 0.0016238101803973733`、
  `batch=0.0029794411839959064 stream=0`）。
- `nonlinear_decay.rs` 中的單元測試：種子公式、1 幀與 2 幀輸入、靜音尾端相等、
  安靜的起始會暴露種子而響亮的起始會覆寫它、兩種初始化下 AVX2 對 scalar。
- `tests/golden_zwtv.rs`：階段層級與端到端的 MoSQITo 比較在 `MosqitoTail` 下執行，
  容差不變；零狀態預設在靜音尾端 fixture 上對照 golden 資料檢查（與相容路徑位元
  逐一相同），在 10 s fixture 上自第 600 幀起檢查，自第 1100 幀起與相容路徑位元
  逐一相同。
- `tests/stream.rs`、`tests/low_freq_correction.rs`：批次對串流現在自第 0 幀起斷言
  位元逐一相等，而非 warm-up 後 <= 1e-9 / 1e-6。
- Python：`test_zwtv_parity` 以 `nl_init="mosqito_tail"` 執行 binding（精確的
  MoSQITo 比較，容差不變）；新的
  `test_zwtv_default_matches_mosqito_given_a_silent_tail` 將預設值與在訊號後補
  0.5 s 靜音執行的 MoSQITo 比較，這會讓 MoSQITo 自己的種子恰為零（0.5 s 足夠：
  在這些 fixture 上，最多 0.177 s 的靜音就能把每個頻帶的主響度推到恰為 0）。

## 凍結 hash：歸因

每個重新記錄的常數都與先前的值成對，先前的值仍在 `MosqitoTail` 下斷言。兩次執行
之間唯一的差異是初始狀態，而靜音尾端 fixture（`pulse_1k_70`、`annexb_sig10`）在
兩張表中的 hash 相同。

| 關卡 | 路徑 | 修正前（現為 `MosqitoTail`） | 修正後（預設 `Zero`） |
|---|---|---|---|
| `hash_gate` windows scalar | n / n_specific | `f3215787aaa48fbe` / `ff98c57f3018ef94` | `a7c2a418292a1a46` / `16937b45e6e4155d` |
| `hash_gate` windows AVX2 | n / n_specific | `f3215787aaa48fbe` / `3f241da3fe334097` | `a7c2a418292a1a46` / `3d4b4b2df9073e48` |
| `hash_gate` linux scalar | n / n_specific | `f3215787aaa48fbe` / `6e181dac593b5fef` | `a7c2a418292a1a46` / `05dc55b516e20132` |
| `hash_gate` linux AVX2 | n / n_specific | `f3215787aaa48fbe` / `8213780cd5384fb0` | `a7c2a418292a1a46` / `197c1084aab28c59` |
| `golden_zwtv` sine_1k_60 | n / n_specific | `0b10971021634b4e` / `62496b610f7c223d` | `89eacdd9fbaa911f` / `f41af57bbf84a2a1` |
| `golden_zwtv` step_60_80 | n / n_specific | `40ac75b0dcaed5a8` / `2fdc839b4f702621` | `d8da35c757b04b89` / `ad4d8b343c25af1f` |
| `golden_zwtv` pulse_1k_70、annexb_sig10 | n / n_specific | 不變 | 不變 |
| Python 契約（`test_smoke.py`） | n | `44e6822074554786` | `9c0b638bfb7758d6` |
| 所有關卡 | time_axis | `f076bcb342595537` | 不變 |

`n` 在 Windows 與 Linux 上位元逐一相同（與先前一樣）；只有 `n_specific` 帶有 libm
的 ULP 雜訊。Linux 的值是在 `ubuntu:24.04` 容器（glibc 2.39、rustc 1.99.1）中記錄的，
與 GitHub runner 使用相同的映像。

## 影響

- MoSQITo 1.2.1 parity 再次被限定範圍：對於最後一幀非靜音的每個訊號，預設輸出在
  起始段與 MoSQITo 不同（最多約 0.1-0.2 sone，持續前 0.05-0.5 s，依訊號而定）。
  `NlInit::MosqitoTail` 可還原 MoSQITo 的數值。
- 批次與串流現在自第一幀起位元逐一一致。`N_WARMUP_FRAMES = 580` 與 `WARMUP` 旗標
  作為凍結的 v1 契約，維持其值與語義；該旗標不再標示批次／串流差異
  （doc comment 已更新）。
- panel 以 git tag 釘住引擎，在其相依版本升級之前不受影響。
- 修正前的 golden/hash 常數仍以 `MosqitoTail` 標籤保留在原始碼樹中，因此沒有失去
  任何對先前已驗證數值的比較。
