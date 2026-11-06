# F03 — SQAT、MoSQITo、官方 C 在 USL[12][4] 的實際誤差

**數值執行完成：**三套原生實作、兩種單格係數、全部24個 Annex WAV（2–25）加上第1號聲級輸入案例。開始於2026-11-05；完成於 2026-11-06T00:13:28.305430+08:00。產品固定快照 `118322f8300dc752f1d38a79db230a2db5ff2870`；repository HEAD `493fd595ef62aaded72ed57af1a75327ba14a5b0`。未改產品、正式測試或golden，未commit/push。

這一格係數差 **0.02**，相對0.22為 **9.090909%**；這是斜率係數差，**不能當成響度誤差百分比**。對同一個真實21帶輸入向量，各實作自身將係數由0.22改為0.24後，未經時間加權的N變化：SQAT與官方C各約 **−0.016866 sone**，MoSQITo保留原生rounding後為 **−0.017 sone**。這些是各自的單格前後差；對官方C baseline的誤差另列於共同輸入表。完整端到端的單格最大影響另列第二表。

本報告分開三件事：①原樣baseline對官方四位小數工作簿的偏差；②原樣baseline對本輪重新計算之全精度官方C的偏差；③每套實作只改USL[12][4]一格後的原生前後差。Baseline：SQAT=.24、MoSQITo=.24、官方C=.22；counterfactual為反向單格版本。完整baseline偏差也含前端、常數精度、取樣尾端與rounding等差異，不能全部歸因於USL。

## 原樣 baseline 對官方工作簿

| 實作 | max \|ΔN\|, sone | RMS ΔN, sone | max \|ΔN′\|, sone/Bark | max \|ΔN\| location |
|---|---|---|---|---|
| SQAT v2.0 / Octave 8.4.0 | 0.0168838908734 | 0.00202358898472 | 5.35405607121e-05 | sig6 @ 6.8200 s |
| MoSQITo 1.2.1 / Python | 0.0808 | 0.00211862016789 | 0.0395908676514 | sig5 @ 0.0000 s |
| 官方 C / MSVC | 8.05072623393e-05 | 3.01327304954e-05 | 5.36754530822e-05 | sig16 @ 1.1000 s |

## 各原生實作的單格影響：0.24 減 0.22

| 實作 | max \|N(.24)−N(.22)\|, sone | RMS ΔN, sone | max \|ΔN′\|, sone/Bark | max \|ΔN\| location |
|---|---|---|---|---|
| SQAT v2.0 / Octave 8.4.0 | 0.0168514726032 | 0.00202478380181 | 0.00999557966297 | sig6 @ 6.8400 s |
| MoSQITo 1.2.1 / Python | 0.0168983166682 | 0.00202442000558 | 0.0154062754797 | sig6 @ 6.7220 s |
| 官方 C / MSVC | 0.0168514660219 | 0.00202486611005 | 0.00999557577141 | sig6 @ 6.8400 s |

## 分組比較：N 偏差（sone）

| 實作 | 輸入組別 | baseline max \|ΔN\| vs workbook | baseline RMS ΔN | cell max \|ΔN\| |
|---|---|---|---|---|
| SQAT v2.0 / Octave 8.4.0 | 1: levels | 3.88410476404e-05 | 3.88410476404e-05 | 0 |
| SQAT v2.0 / Octave 8.4.0 | 2–5: stationary | 5.39941774438e-05 | 3.50452428047e-05 | 0 |
| SQAT v2.0 / Octave 8.4.0 | 6–25: time varying | 0.0168838908734 | 0.00202369280636 | 0.0168514726032 |
| MoSQITo 1.2.1 / Python | 1: levels | 0.0043 | 0.0043 | 0 |
| MoSQITo 1.2.1 / Python | 2–5: stationary | 0.0808 | 0.047006090031 | 0 |
| MoSQITo 1.2.1 / Python | 6–25: time varying | 0.0228893512431 | 0.00207537686982 | 0.0168983166682 |
| 官方 C / MSVC | 1: levels | 3.9575637814e-05 | 3.9575637814e-05 | 0 |
| 官方 C / MSVC | 2–5: stationary | 5.43889610789e-05 | 3.5301821958e-05 | 0 |
| 官方 C / MSVC | 6–25: time varying | 8.05072623393e-05 | 3.0132045379e-05 | 0.0168514660219 |

## 相同真實21帶 core 向量

| 實作 | N(.22) | N(.24) | 原樣 baseline N − 官方C(.22) | 自身單格 signed ΔN | cell max \|ΔN′\| @ 5.4 Bark |
|---|---|---|---|---|---|
| SQAT v2.0 / Octave 8.4.0 | 4.39262221003 | 4.37575618046 | -0.0168660414643 | -0.0168660295669 | 0.00999041974926 |
| MoSQITo 1.2.1 / Python | 4.393 | 4.376 | -0.0166222219257 | -0.017 | 0.00998541974926 |
| 官方 C / MSVC | 4.39262222193 | 4.37575619911 | 0 | -0.0168660228128 | 0.00999040666562 |

## 相同人工輸入的 slope 案例

| 實作 | N(.22) | N(.24) | signed whole-pattern ΔN | \|ΔN′\| @ 4.6 Bark |
|---|---|---|---|---|
| SQAT v2.0 / Octave 8.4.0 | 0.810818850267 | 0.804663547237 | -0.0061553030303 | 0.003998 |
| MoSQITo 1.2.1 / Python | 0.811 | 0.805 | -0.006 | 0.004 |
| 官方 C / MSVC | 0.810818895245 | 0.804663594682 | -0.00615530056249 | 0.00399799862956 |

## 對未改官方 C 的全精度比較

| 實作 | baseline max \|ΔN\| vs C(.22) | baseline max \|ΔN′\| vs C(.22) | counterfactual max \|ΔN\| vs C(.22) | counterfactual max \|ΔN′\| vs C(.22) |
|---|---|---|---|---|
| SQAT v2.0 / Octave 8.4.0 | 0.0168516486327 | 0.00999558701527 | 2.02912656277e-06 | 1.23580166012e-06 |
| MoSQITo 1.2.1 / Python | 0.0808543889611 | 0.0717794727493 | 0.0808543889611 | 0.0717794727493 |
| 官方 C / MSVC | 0 | 0 | 0.0168514660219 | 0.00999557577141 |

## 相對 N 指標與受影響格點

| 實作 | workbook max N error %, \|ref\|≥1e−4 | workbook max N error %, \|ref\|≥1 | cell max N change %, \|N(.22)\|≥1 | cell changed N points (>1e−12) |
|---|---|---|---|---|
| SQAT v2.0 / Octave 8.4.0 | 49.9015902272 | 0.478807222633 | 0.47746302351 | 25767/48724 |
| MoSQITo 1.2.1 / Python | 49.9075676435 | 0.816082802548 | 0.480303295409 | 24622/48724 |
| 官方 C / MSVC | 49.9015909659 | 0.00494218618924 | 0.477462802498 | 25763/48720 |

## 比響度細節

| 實作 | workbook N′ RMS | cell N′ RMS | cell max N′ location | cell changed N′ points (>1e−12) |
|---|---|---|---|---|
| SQAT v2.0 / Octave 8.4.0 | 2.74065371887e-05 | 0.000312210625001 | sig14 @ 9.7920 s, 5.0 Bark | 85310/11693760 |
| MoSQITo 1.2.1 / Python | 0.000936246333573 | 0.000314565778408 | sig15 @ 9.5940 s, 5.8 Bark | 85877/11693760 |
| 官方 C / MSVC | 2.74090993151e-05 | 0.000312223314431 | sig14 @ 9.7920 s, 5.0 Bark | 85310/11692800 |

## 長度與時間標籤列帳

| 實作 | 超出工作簿的frame總數 | 回傳時間標籤最大漂移（秒） | baseline案例數 / 係數版本數 |
|---|---|---|---|
| SQAT v2.0 / Octave 8.4.0 | 8 | 0 | 25 / 2 |
| MoSQITo 1.2.1 / Python | 8 | 0.000499956661178 | 25 / 2 |
| 官方 C / MSVC | 4 | 0 | 25 / 2 |


## 解讀與證據邊界

- SQAT為固定版本、原樣`.m`檔在 **GNU Octave 8.4.0直接執行**，不是C/Python移植或C模擬品。MATLAB R2021a因授權過期Error −10而 **BLOCKED**，故本輪證據屬SQAT原生程式在Octave的數值實跑，不等於MATLAB runtime驗收。
- MoSQITo第2–25號使用原本公開stationary/time-varying API。第1號已是28帶聲級，走其原生private `_main_loudness` → `_calc_slopes`，不冒稱存在公開聲級輸入API。其slope stage原本就將N≤16取到.001 sone、N>16取到.01 sone，再進時間加權；本輪完整保留此行為。
- MoSQITo對工作簿的最大N偏差為穩態第5號 **.0808 sone**，而單格改動在此訊號的影響為 **0**。SQAT與官方C的穩態計算先濾波後跳過前.2秒，MoSQITo原樣公開穩態API則使用自身前端及全段平均、沒有skip參數。本輪未將該差異全部歸因於某一個前端或skip因素，也不能當成USL單格誤差。
- MoSQITo時變6–25號baseline最大工作簿N偏差為 0.0228893512431 sone；改成.22後最大值為 0.0232840920114 sone。由於其他差異與抵消仍存在，單格改動不保證每一種彙總最大誤差都下降。
- 真實共同core案例是第6號內部frame **13677、6.8385秒**，依預登記規則在該訊號全部官方C core frames選最大未加權N單格差。三套收到`common-core.json`中完全相同的21個binary64值，故此表排除前端與時間加權影響。SQAT stage wrapper直接機械抽取原本stage body，原碼行界與hash見`sqat-freeze.json`。
- 人工向量只有第5帶=.35 sone/Bark。解析上，局部.2 Bark區段的N′差是 **.004 sone/Bark**，該段面積差為 **.0004 sone**；這不是整體響度N的差。官方C/SQAT有ZUP+.0001 Bark，所以實際4.6 Bark點距起點.1999 Bark，差約.003998；MoSQITo則為.004。整個specific pattern積分的N差另外列於表中。
- 相同core的零向量與第2號穩態負控制，三套單格差都精確為0。完整原生訊號 **1–5及25** 的N和N′單格差也全部為0。是否真正走到該係數，取決於輸入與斜率區段，並非所有訊號都會受影響。
- 原始WAV一律`int16 / 32768 * 2*sqrt(2)`轉成double Pa、48kHz單聲道，沒有依輸出擬合校準。第15號diffuse，其餘free field。官方工作簿是四位小數參考值；比較的是數值偏差，不將小數顯示值視為無誤差物理真值。
- 工作簿N′涵蓋1–5號完整240 Bark profile、6–13號各一條指定Bark時間軌跡，**不是6–25號完整240×time參考矩陣**。對C及單格影響的全格點N′比較則使用本輪原生完整輸出。所有N′單位皆為sone/Bark。
- MoSQITo回傳時間標籤使用含終點的linspace，與實際`[::24][::4]`資料取樣格線有漂移。首次精確標籤assert已拒絕，後依`alignment-deviation.md`明記偏離原protocol，按原碼固定sample index映射2ms物理格線，**沒有插值、最佳配準位移或更動響度值**。原始回傳時間保留於raw arrays；漂移、額外尾端frame均列帳。工作簿未列的尾端只在工作簿比較排除，對C與同實作前後差各保留其共同或完整格線。
- 相對誤差只對|reference|≥1e−4計算，較小值的排除數與相對最大值座標均見詳細JSON；另補充預登記的|N reference|≥1 sone百分比。RMS按各表定義的格點池加權。JSON欄位`above_1e12`、`above_1e4`分別代表絕對誤差>1e−12、>1e−4。1e−4是工作簿精度診斷，**不是標準合格門檻**；最大絕對與最大相對誤差通常出現在不同座標。
- Table A.9權威原文判定仍 **PENDING**。這次不宣告標準全文所有要求通過、不處理規範表格與參考程式的權威衝突，也不授權修改產品係數。官方C對自身為0只是參考定義，不是額外獨立證明。

## 來源、重播與交付

[SQAT v2.0](https://github.com/ggrecow/SQAT/releases/tag/v2.0)，commit `94f489c053d1366da05d5e62838c3f54ac7715c3`、主檔SHA-256 `1113ab411f8a6792bd0f7c972bc45124187324222ee8f7d43d9e0765fd57bd5b`；[MoSQITo 1.2.1](https://pypi.org/project/mosqito/)，原始安裝source hash見`frozen-inputs.json`；官方C原碼SHA-256 `a74b45ed297cd09ac60701a923120341137d227e536f3109ae4ece810d834491`。官方C本輪以MSVC `/O2 /fp:precise`全新編譯，未沿用舊數值輸出；原創wrapper include原樣C並匯出其原生slope/core stages。

重播與細節見`replay.md`、`preregistration.md`、`preregistration-supplement.md`、`alignment-deviation.md`、`per-signal-metrics.json`、`stratified-summary.json`、`common-core.json`、`sqat-freeze.json`、`builds.json`、`raw-output-hashes.json`、`execution-audit.json`、`delivery-check.md`。刻意排程重啟與已修復的harness準備錯誤均留log，不當成數值失敗或隱藏。完整第三方原碼、WAV、工作簿、大型陣列只保留本機tmp與hash，不隨報告進庫。交付檔hash於去識別後計算，與原始來源/輸入/binary hash分開。
