# C-01 輸出長度契約：ceil／floor 差異、架構比較與上中下策

> 對照／Pair: [English](C01-OUTPUT-LENGTH-DECISION-2026-10-31.md) · 來源：zh · 同步 2026-11-01

2026-10-31 初版，2026-11-01（Asia/Taipei）依使用者要求「架構上如果有差異需要比較後再決定」改版。程式快照 `28f6a49`（v0.3.0 + V-01）。決策備忘，不改程式、不改 golden。改版說明：初版 §1、§2 說多出的尾端點是用「lookahead 為零」的慣例算的、值可能與 C 程式不同；§2.2 的量測顯示輸出值完全不受該 lookahead 影響，該說法撤回。

## 0. 一句話結論

Rust 的輸出點數比官方 CLI 的 total 檔多一點（除非訊號長度是 96 的倍數），但與官方 CLI 的 specific 檔相同（除非 `floor(L/24)` 是 4 的倍數且 L 不是 24 的倍數）。差的是**尾端的一個時間點**；起點、相位、前面所有點都相同，而且多出那點的值完全由真實輸入樣本決定（與後面再接樣本時算出的值逐位元相同）。架構上，ceil 是 stream 路徑唯一能產生的格線；floor 是事後裁切，需要知道總長度。建議維持上策：保留 ceil、把契約寫死、為沒有官方對照的 4 個點補獨立預期值。

## 1. 三套規則分別是什麼

訊號長度 L（樣本，48 kHz），官方內部 2 kHz 點數 `K = floor(L/24)`，餘數 `r = L mod 24`。

| 階段 | Rust（batch 與 stream） | 官方 C library（Annex A `ISO_532-1.c`） | 官方 CLI 輸出檔 |
|---|---|---|---|
| 內部 2 kHz 格線 | `ceil(L/24)` 點，在樣本 `24k` 取濾波器輸出（[third_octave_levels.rs:87-96](../iso532/src/zwtv/third_octave_levels.rs#L87-L96)，`i % 24 == 0`） | `K = L/24`（整數除法＝floor），同樣在樣本 `24k` 取值（`f_calc_third_octave_levels` 的 `pSPL += DecFactor`） | 同 library |
| 輸出 2 ms 格線 | `ceil(ceil(L/24)/4)` 點，取內部 index `0, 4, 8, …`（[zwtv/mod.rs:18-22](../iso532/src/zwtv/mod.rs#L18-L22)） | 不下抽，回傳全部 K 點 | total 檔 `floor(K/4)` 點；specific 檔從 index 0 起每 4 點寫一次，`ceil(K/4)` 點（`docs/修正報告2.md` §11.4） |
| 時間軸 | `t_j = 2j ms`，自 0 起 | 同 | 同；§11.4 已確認共同時點差 0 s |
| 第 t 幀的值 | 只取決於樣本 `≤ 24t`：非線性衰減輸出的是第一個內迴圈的結果，只用到當前幀（[nonlinear_decay.rs:102-130](../iso532/src/zwtv/nonlinear_decay.rs#L102-L130)，`k == 0` 時的 `out0`）；對下一幀的 lookahead 只推進濾波器狀態；時間加權是因果的 | 相同：`f_nl` 寫出的是第一個迭代的 `f_nl_lp(Ui)`，內迴圈只更新狀態 | 同 library |

重點：三者的起點、相位、每幀的值都相同。Rust 的點集合包含 CLI specific 的點集合，CLI specific 又包含 CLI total。差異只在尾端要不要多一個點。

## 2. 什麼時候會差一點

| 情況 | Rust 點數 | CLI total | CLI specific | Rust 多出的點 |
|---|---|---|---|---|
| `L mod 96 = 0` | `K/4` | `K/4` | `K/4` | 無 |
| `K mod 4 ≠ 0`（不論 r） | `ceil(K/4)` | `floor(K/4)` | `ceil(K/4)` | 比 total 多 1，**與 specific 相同**；該點在 C 內部格線上，有 C specific 參考值 |
| `K mod 4 = 0` 且 `r > 0` | `K/4 + 1` | `K/4` | `K/4` | 比兩者都多 1；它是內部 frame K，Rust 用到樣本 `24K` 為止的真實樣本算出，C library 跳過它只因為 `NumSamples/DecFactor` 是整數除法；**沒有任何官方參考值** |

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

### 2.2 量測 2026-11-01：多出的點由前綴決定

探測（目前 build 的 Python binding，臨時腳本，未進庫）：四個 48 kHz 基底訊號（`broadband_570.wav`、Annex B 訊號 5 粉紅噪音、Annex B 訊號 10 音脈衝、合成 1 kHz 70 dB 正弦），各截成九種長度 `L = 96m + d`，`d ∈ {0, 1, 12, 23, 24, 25, 48, 72, 95}`，涵蓋 §2 的三種情況。每個截斷：

| 檢查 | 結果（36/36） |
|---|---|
| Rust 點數等於 `ceil(ceil(L/24)/4)`；CLI 公式如 §2 | 是 |
| stream（每次 push 480 樣本＋flush）點數等於 batch | 是 |
| 截斷訊號的 batch 與同一訊號補零到下一個 96 倍數再加 96 的 batch：前 `n−1` 點逐位元相同 | 是 |
| 最後一點（`K mod 4 = 0, r > 0` 時就是多出的點）：截斷對補零的絕對差 | 36 個全為 0.0 |

所以多出那點的值不取決於訊號之後接什麼：它就是後面再來樣本時 pipeline 算出的同一個數，也就是官方 C library 的迴圈若多跑一幀會對 frame K 算出的同一個數。先前「lookahead 為零」的說法對輸出而言是錯的（lookahead 只影響濾波器狀態，§1）。這也表示訊號 18、23、24、25 的獨立預期值可以要求與補零輸入上的官方 C library 在捨入等級（1e-14 量級）一致，而不只是落在 Annex B 容差內。

## 3. 架構比較

### 3.1 兩種規則在架構上各是什麼

Rust 的 pipeline 是一台逐樣本驅動的因果狀態機：28 個三分之一倍頻程濾波器 → 每第 24 個樣本出一個 2 kHz 幀 → 21 頻帶主響度 → 非線性衰減狀態 → 斜率階段 → 時間加權狀態 → 每第 4 幀出一個輸出點。batch 與 stream 以相同順序跑相同階段；batch 就是把整段訊號一次 push 進去的 stream。ceil 格線在這台機器裡不是任何一處的決定，它只是「從樣本 0 起每第 96 個樣本出一點，最後把持有的幀 flush 出來」自然得到的結果。

floor 格線是另一種性質的規則：「整段訊號都知道以後，若 `L mod 96 ≠ 0` 就丟掉最後一個輸出點」。它是對完成結果的裁切，而且需要 L。機器裡沒有任何階段知道 L；stream 路徑在 `flush` 之前不可能知道，到了 `flush` 時它要丟的那幀也已經算好了。

官方素材本身就同時存在兩種慣例：C library 對內部幀數取 floor，CLI 的 total 寫入器再 floor 一次，但 CLI 的 specific 寫入器對同一組內部幀取 ceil。沒有單一的「官方」尾端規則可以對齊。

### 3.2 各層影響

| 層 | 維持 ceil（現狀） | 改成 floor（CLI total） |
|---|---|---|
| 核心 pipeline（`iso532/src`） | 不變 | 斜率階段之後多一個依長度裁切；`zwtv_out_frames` 改變；前綴因果性質保留（floor 輸出是 ceil 輸出的前綴），但 batch 與 stream 點數不同 |
| 批次 API（`loudness_zwtv`、`ZwtvProcessor`） | 不變 | 凡 `L mod 96 ≠ 0` shape 改變；0.4.0 |
| 串流 API（`ZwtvStream`、panel） | 不變；stream 只能產生 ceil | 要麼 `flush` 多一個總長度參數（API 變更、呼叫端要知道 L、就不再是 stream），要麼 stream 維持 ceil、放棄 F-02 建立的「batch 自第 0 幀起與 stream 逐位元相同」gate |
| C ABI | `iso532_zwtv_out_frames` 不變 | 回傳值改變；手抄公式的呼叫端會多配或越界；header 要加註；v1 語意改變 |
| Python／NumPy | 不變；shape 與 MoSQITo 相同 | shape 與 MoSQITo 不同（MoSQITo 是 ceil 類，我們的 golden 與它一致）；parity 測試要先裁切 |
| golden 與 frozen hash | 不變 | 全部 zwtv hash 重凍；MoSQITo golden 比對前要裁切 |
| 驗證 harness（Annex B、官方 C） | 一條文件化的裁切公式即可到 CLI total；14–17 的額外點保有已驗證的 C specific 對照 | CLI total 形狀自動等價，但 `K mod 4 ≠ 0` 時 CLI specific 反而比 Rust 多一點；已驗證的 14–17 點被丟掉 |
| 未來 Annex A 精確模式（ROADMAP R2 穩態 IsoReference；日後時變對應版） | 若有需要，C 的尾端慣例可一起作為 opt-in 模式加上 | 現在只改格線慣例、其他慣例不動，等於預設路徑混用兩個來源 |
| 文件與版號 | 0.3.x 內；契約寫一次 | 0.4.0；三個 binding 各要遷移說明 |

### 3.3 長期後果

- **可比性。** 維持 ceil，與 CLI total 的比對是 harness 的一行裁切（取前 `floor(floor(L/24)/4)` 點）；與 MoSQITo、SQAT、stream 直接可比。改 floor，與 CLI total 直接可比，其餘每一種比對（MoSQITo golden、stream、CLI specific）都要補零或裁切。
- **不變量。** ceil 保有兩個便宜可測、對即時產品有價值的不變量：前綴因果（`96j < L` 時 `out(x[:L])[j] == out(x)[j]`）與 batch ≡ stream。floor 保留第一個、失去第二個。
- **可擴充性。** 任何想要 C 尾端慣例（floor 格線、穩態 `TimeSkip` 前端）的未來模式，都可以是不動預設路徑之上的一個 opt-in 開關。現在改預設格線，等那個模式出現時還得撤回或重做。
- **判斷錯誤的代價。** 若維持 ceil 而日後認定不對，修法是呼叫端今天就能自己做的裁切。若採 floor 而日後認定不對，修法是第二次破壞性的 shape 變更。

## 4. 上中下策

| | 上策（建議） | 中策 | 下策 |
|---|---|---|---|
| 做法 | 保留 ceil；文件寫死輸出格線契約；新增契約測試；一輪獨立驗證以補零輸入的官方 C library 為 18／23／24／25 的額外點產生預期值 | 保留 ceil；只寫文件與契約測試；額外點永久標為「無官方對照」 | 批次改 floor(floor(L/24)/4)，對齊 CLI total |
| 數值／shape 變更 | 無 | 無 | shape 變更（25 個 Annex B 訊號中 8 個少 1 點；一般訊號凡 `L mod 96 ≠ 0` 皆少 1 點） |
| batch＝stream 逐位元 | 保持 | 保持 | 失去，或 `flush` 需要總長度 |
| 審計 C-01 狀態 | 可關閉：4 個點取得捨入等級的官方 C 預期值（§2.2） | PARTIAL，但有文件 | total 形狀等價，但 specific 與已驗證的 14–17 點變成另一種 PARTIAL |
| 成本 | 文件 0.5 天＋測試 0.5 天（Codex phase）＋一輪 Astra 驗證 | 文件 0.5 天＋測試 0.5 天 | 程式＋三個 binding＋hash 重凍＋golden 裁切＋0.4.0 發版＋重新驗證，約 2–3 天，另有下游遷移 |
| 風險 | 低 | 低 | 中：破壞性變更，而且只對齊 CLI 兩種輸出中的一種 |

### 4.1 獨立預期值怎麼來

額外點（訊號 18、23、24、25）是內部 frame K，取樣點是真實樣本 `24K`。把訊號補零到至少 `24(K+1)` 個樣本再送官方 C library，它會用相同的 28 個頻帶位準算出 frame K；§2.2 顯示該幀的值不受補零影響。因此預期值可以要求在捨入等級一致（14–17 的點一致到 1e-14 以上），Annex B 容差判定（V-01）只是備援陳述。

### 4.2 一個常見的替代案：加 opt-in 的輸出格線選項

例如 `OutputGrid::Full`（預設）與 `OutputGrid::CliTotal`。不列為獨立一策，理由是：裁切對呼叫端是一行程式，stream 無法支援它，而新增 API 面要同時維護 Rust、C ABI、Python 三處。文件給出裁切公式比加選項划算。

## 5. 決定（2026-11-01）

使用者選上策：保留 ceil（「使用 ceil 方式，同意繼續任務」）。

1. 格線依 §1 凍結。同日落地：契約文字寫進兩語言 README、`zwtv_out_frames`／`loudness_zwtv`／`LoudnessTimeVarying` 的文件註解與 C header、CHANGELOG；契約測試 `iso532/tests/output_grid.rs`（16 種長度、精確時間軸、任意 chunk 切分下 stream 點數、補零**與真實延續訊號**兩種情況下前綴逐位元相同，後者比 §2.2 的探測更強）加一個 Python 形狀測試。
2. 已授權 Astra 一輪：簡報 `docs/verification/briefs/2026-11-01-C01-zero-pad-reference.zh-TW.md`；交付到 `docs/verification/2026-11-01-C01-zero-pad-<commit>/`。四個點在捨入層級一致時，稽核 C-01 列即可結案。
3. C 的尾端慣例（floor 幀數、CLI total 再抽取）與 ROADMAP R2 一起留在未來 opt-in Annex A 精確模式的待辦；現在不加 API 選項（§4.2）。

## 6. 不論選哪一策都要做的事

- 把 §1 的契約寫進 README 兩語言與 header 註解：起點 0、2 ms 相位、點數公式、「第 j 點的值只取決於樣本 ≤ 96j」、與 CLI total／specific 的裁切公式。
- 契約測試：長度 4800（最短合法）、`24k±1`、`96k±1`、以及 stream 任意 chunk 切分加 flush 的點數與批次相同；截斷對補零的前綴逐位元相同（把 §2.2 的探測變成測試）；分開驗 `n`、`n_specific`、`time_axis` 三個欄位的長度。
- 審計 §12.2 C-01 列的其他驗收項（空／極短輸入已由 `SignalTooShort` 覆蓋）在同一 phase 完成。
