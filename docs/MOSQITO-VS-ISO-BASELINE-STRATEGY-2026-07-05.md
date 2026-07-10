# 基準值選擇策略:mosqito golden vs ISO 532-1 理論值

**日期:** 2026-07-05
**性質:** 參考文件(策略決策依據)
**前置文件:** `DESIGN-DEVELOPMENT-2026-07-04.md` §10(偏差實測)、`ROADMAP.md` §1(後續標準候選)
**適用範圍:** ISO 532-1 現有實作的維護,以及 sharpness(DIN 45692)、ECMA-418-2、ISO 532-2、roughness 等後續標準的驗證基準選擇。

---

## 1. 問題定義

已量測到 mosqito 的 zwst 穩態路徑對 ISO 532-1 Annex B 官方基準值有 ±0.8% 偏差(Signal 3 +0.82%、Signal 5 −0.76%),而 zwtv 時變路徑幾乎精確(0/500 點超容差)。後續標準實作前需要回答三個問題:

1. 這個偏差在 mosqito 端是**刻意設計**的嗎?成因是 Python 實作的限制嗎?
2. 後續標準的驗證目標應該選 **ISO 理論值** 還是 **mosqito golden**?
3. 兩者衝突時的決策準則是什麼?

---

## 2. 偏差的實作成因解剖(mosqito 原始碼證據)

### 2.1 mosqito zwst 前端實際在做什麼

`loudness_zwst.py` 的頻譜前端呼叫的是 mosqito 的**通用聲級計工具** `sound_level_meter/noct_spectrum`,不是 ISO 參考濾波器組。逐步拆解(`_n_oct_time_filter.py`):

| 步驟 | 實作 | 依據 |
|---|---|---|
| 濾波器設計 | scipy `butter(3, (w1, w2), 'bandpass', output='sos')`——3 階 Butterworth 帶通(雙線性變換,6 階 IIR) | 註解明載 **ANSI S1.1-1986**(即 IEC 61260 同族),不是 ISO 532-1 Annex A |
| 低頻帶前置降採樣 | `fc < fs/200`(48 kHz 下即 fc < 240 Hz,約 25–200 Hz 的 10 個頻帶)先 `scipy.signal.decimate(sig, q)`——Chebyshev-I 8 階 + **filtfilt 零相位** | 數值必要性:fc=25 Hz 在 48 kHz 下正規化頻寬 ~1e-3,直接設計病態(原始碼註解自承 "filter design issue [ref needed]") |
| 濾波 | `sosfilt`(因果、單向) | — |
| 位準計算 | **全段 RMS**(`sqrt(mean(sig_filt²))`,含濾波器啟動暫態,無丟棄窗) | — |
| 44.1 kHz 輸入 | `scipy.signal.resample`(FFT 法)重採樣到 48 kHz | — |

而 ISO 532-1 Annex B 的穩態基準值是用**標準自帶參考程式的濾波器鏈**(遞迴濾波器組,逐樣本推進)產生的。兩條路徑的頻帶邊緣形狀差 ~0.1 dB,經響度轉換級放大即為 ±0.8% 的 N 偏差。

### 2.2 對照:zwtv 為什麼幾乎精確

mosqito 的 zwtv 前端(`_third_octave_levels`)**逐係數移植了 ISO 參考程式(Annex A BASIC/C)的 28 頻帶濾波器組**——因為時變方法的前端是標準規定性的(prescriptive),沒有替換自由。這正是我們實測 zwtv 對官方曲線 0/500 點超容差、而 zwst 有 ±0.8% 的原因:**偏差不在響度數學,全部在 zwst 可自由選擇的頻譜前端**(§10.1 Signal 1 直接餵頻帶位準時偏差僅 +0.005%,即輸出量化步階,已證明轉換級精確)。

### 2.3 本 crate 的復刻範圍

Rust 端 `zwst/mod.rs` + `dsp/filtfilt.rs` 對 mosqito 路徑做了**逐位級復刻**,包括 scipy `decimate` 的 Chebyshev-I 8 階係數與 `sosfiltfilt` 的 odd padding 語意——這是 golden parity 達 8.2e-14 的前提。也就是說:我們**繼承了 mosqito 的 ±0.8% 偏差,而且是刻意繼承的**(相容性優先)。

---

## 3. 分析:這是刻意設計嗎?是 Python 的關係嗎?

結論:**是刻意的工程選擇,但不是「刻意製造偏差」——偏差是被標準允許、被作者接受的副作用。Python 的效能現實是主要動機之一,但不是唯一動機。** 分四層論證:

### 3.1 標準本身賦予這個自由度(首要原因)

ISO 532-1 的穩態方法(Method 1)參考程式的**輸入是 28 個三分之一倍頻程頻帶位準**,不是時域訊號。從訊號取得頻帶位準的方式,標準只要求符合 IEC 61260-1 class 1 三分之一倍頻程分析,**沒有規定必須用 Annex A 的濾波器組**(那是時變方法的規定件)。所以 mosqito 對 zwst 選 Butterworth 前端:

- **不違反標準**——±0.8% 遠在 ±5% 合規容差內;
- Annex B 穩態基準值恰好是用標準自家濾波器鏈生成的,任何「合規但不同」的濾波器實作都會顯出這個量級的偏移。這是「合規自由度的顯影」,不是誤差意義上的 bug。

### 3.2 Python 效能現實(使用者猜測的部分——對,但要精確化)

ISO 參考濾波器組必須**逐樣本推進遞迴狀態**,這種迴圈在純 Python/numpy 是災難性的慢。證據就在 mosqito 自己身上:

- zwtv **被迫**移植 ISO 濾波器組(標準規定性),結果 mosqito zwtv 在本機跑 10 秒訊號要 22.4 秒(**0.45× 即時**,連即時一半都不到);
- zwst **可以避開**這個代價——scipy 的 `butter`/`sosfilt`/`decimate` 全是向量化 C 程式碼,整段訊號一次過。

所以精確的說法是:**Python 下「能用 scipy 向量化原語就不要手寫逐樣本迴圈」是生存法則,zwst 恰好有標準賦予的自由度可以這麼做,mosqito 就做了**。若標準對穩態前端也是規定性的,mosqito 只能像 zwtv 一樣硬吃效能代價——可見這是「自由度 + 效能動機」的交集,單靠 Python 因素不成立(zwtv 就是反例)。

### 3.3 工具重用的架構動機

`noct_spectrum` 是 mosqito 的**跨指標共用件**(sound level meter 模組,同時服務頻譜分析等其他功能),維護一套通用 IEC 61260 風格濾波器組、讓各指標共用,比為 zwst 單獨維護一份 ISO 專屬濾波器組更符合程式庫經濟學。ANSI S1.1/Butterworth 也是業界慣用寫法(MATLAB `poctave` 同族)。

### 3.4 各偏差成分不是同一性質,分開記錄

| 成分 | 性質 | 量級貢獻 |
|---|---|---|
| Butterworth vs ISO 參考濾波器形狀 | 合規自由度(刻意選擇) | 主要(~0.1 dB 帶位準 → ±0.8% N) |
| 全段 RMS 含啟動暫態、無丟棄窗 | 簡化(對數秒級穩態訊號影響小) | 次要 |
| 低頻帶 decimate(Cheby-8 filtfilt)通帶漣波 | 數值必要性(非刻意偏差) | 次要 |
| 44.1→48 kHz FFT resample 漣波 | 便利性選擇 | Signal 3 殘留 +0.025% 的來源 |

---

## 4. 後續標準的基準選擇建議

### 4.1 主軸:mosqito golden parity(維持現行策略)

四個理由,按重要性排序:

1. **驗證密度**:golden 可對**任意訊號**生成(9 組資料集、任何邊界案例都能加),parity 可測到 1e-12 量級;官方基準值只有少數幾個訊號、容差 ±5%/0.1 sone——粗了 10 個數量級。回歸偵測能力完全不是同一級。
2. **可除錯性**:與 mosqito 分歧時可以**逐階段二分定位**(餵中間值進 Python 對照),這是本專案 5 個 phase 一路走來的核心方法論;對 ISO 紙面數值除錯只能猜。
3. **合規性可遞移**:mosqito 已在 ISO 容差內(本專案 §10 實測亦独立確認:全部訊號都在 ±5% 帶內),位元級 parity 自動繼承合規。**但每個新指標動工前要重新確認一次遞移前提**(見 4.3)。
4. **使用者遷移一致性**:從 mosqito 遷來的使用者拿到逐位一致的數字,信任成本最低。

### 4.2 副軸:IsoReference 模式只在「量得到有意義 gap」時才建

zwst 的 `ZwstMode::IsoReference`(§10.2,重用 zwtv 前端)是這個策略的範本:**mosqito 路徑為預設(golden 體系不可破壞),ISO 參考路徑為選配**。對後續標準,先跑 gap report 再決定:

- gap ≪ 容差且 ≪ 感知意義(sone 顯示解析度 1e-3)→ **不建第二模式**,文件記錄了事;
- gap 達容差的可觀比例、或使用者場景需要對官方基準報告(認證、法規)→ 建選配模式。

### 4.3 每個新標準動工前的固定前置作業(寫入計畫模板)

1. **gap report 先行**:複製 §10 的 `iso_gap_report` 方法,先量 mosqito 參考實作對該標準官方驗證資料的偏差,**動工前就知道要繼承多少偏差、偏差集中在哪一級**。
2. **parity debt 登記**:mosqito 的純實作痕跡(如 zwst/zwtv 的 `r8()` 1e-8 捨入、nl wraparound 初始化)復刻時逐項登記為「相容性債」——復刻但標記,未來若 mosqito 修正或我們提供 ISO 模式時有清單可循。
3. **自由度地圖**:標明該標準哪些環節是規定性的(必須位元級照抄參考程式)、哪些是自由度(mosqito 的選擇只是選項之一)——zwst/zwtv 的教訓就是這條線決定了偏差出現的位置。

### 4.4 決策準則速查

| 情境 | 選擇 |
|---|---|
| 日常開發、回歸測試、SIMD parity | mosqito golden(唯一基準) |
| 標準合規性宣告 | 官方驗證資料 + 標準容差(golden 遞移 + 獨立確認) |
| 認證/法規場景要求貼官方基準值 | IsoReference 類選配模式(僅在 gap 有意義時建) |
| mosqito 與官方值衝突且超出容差 | 視為 mosqito bug,上報 upstream,我方文件記錄並以官方值為準 |

第 4 列至今未發生(所有已測偏差均在容差內),但規則需先立:**parity 的忠誠上限是「合規的 mosqito」,不是「任何 mosqito」**。

---

## 5. 結論

1. mosqito zwst 的 ±0.8% 偏差是**刻意的工程選擇**:標準賦予穩態前端實作自由度,mosqito 用 scipy 向量化原語(Butterworth + decimate + 全段 RMS)換取 Python 下可接受的效能與跨指標工具重用;偏差是被接受的副作用,在 ±5% 容差內合規。「Python 實作的關係」是主要動機之一,但前提是標準允許——zwtv 沒有這個自由度,mosqito 就老實付出了 0.45× 即時的代價逐係數移植。
2. 後續標準**維持 mosqito golden 為主軸**(驗證密度、可除錯性、遞移合規、遷移一致性),官方基準值作為每標準動工前的 gap report 與最終合規確認,IsoReference 選配模式僅在 gap 有意義時建。
3. 本文件 §4.3 的三項前置作業(gap report / parity debt 登記 / 自由度地圖)應納入後續每個標準的 phase 計畫模板。
