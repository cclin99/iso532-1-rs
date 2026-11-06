# F03 多因素矩陣預登記（2026-11-06 Asia/Taipei）

產品固定快照`118322f8300dc752f1d38a79db230a2db5ff2870`；實際HEAD `62e8559e8fe01350b9e07148784a6635d4522691`。獨立數值診斷，不改產品/DSP/正式測試/golden，不commit/push，不改舊輪證據。使用者已授權GNU Octave。

## A：穩態主矩陣256個新運算格子

訊號2–5 × 前端{官方Annex IIR、原生MoSQITo noct時域濾波} × 校準{2sqrt(2)、.02/原始校準PCM的RMS，預期2.835797716391444} × **全段濾波後RMS skip**{0,.2秒} × USL{.22,.24} × 下游模式{官方C、SQAT、Mo原始rounding、Mo取消rounding診斷}。共有32個共同28帶聲級向量，每個經8個下游組合，共256格。Mo取消rounding是診斷模式，不是第四套實作。

Mo前端實際為decimate→Butterworth bandpass SOS→RMS，**不是FFT**。機械抽取原`_n_oct_time_filter`，只將最後RMS起點改為ceil(skip×降採樣後取樣率)；skip0必須逐band與原生noct_spectrum精確相同。官方C用原post-filter skip API。主矩陣兩者均先濾完整訊號再取RMS，輸入統一binary64 Pa，不偷偷重置濾波器。

共同levels分別送原生C `f_loudness_from_levels`、原樣SQAT method0、Mo `_main_loudness`→`_calc_slopes`。前後端互換明標hybrid，engine名稱包含多種選擇，不能當單一純因子。Mo no-round只刪兩個N rounding敘述，保留negative clamp與N-prime。運算前凍結改動與hash。

另加8個crop/reset負控制：4訊號×2前端，sqrt校準、輸入先裁前.2秒再重置濾波、post-filter skip0、共同C022下游；與主矩陣「全段濾波後skip.2」比較，不能混作同一window操作。

## B：時變代表矩陣64格

固定訊號{6,15,16,25}：6為既測N單格最敏感；15為既測Mo最大誤差抵消及N-prime單格最敏感；16為非單格殘差較大；25為不敏感負控制。因子：校準{sqrt,cal}×USL{.22,.24}×四種上述模式。時變**沒有**穩態skip因子。第15號diffuse，其餘free。

64格包含24份已驗hash的舊原生sqrt結果（3實作×2USL×4訊號），以及40個新運算格（24個cal原生＋16個兩校準Mo no-round）。與穩態264新格分開列帳，不覆寫舊輸出。

## C：舊全20個時變訊號重分析，不冒稱新運算

6–25號×3原生實作×2USL，共120份不可變舊輸出，與B引用的24份重疊，不能加總當新執行數。逐固定time/Bark計算e022、d=N024−N022、e024=e022+d及|e024|−|e022|，區分抵消(e022×d<0)、增強與overshoot。不得拿不同位置的兩個max相減當因果效果。固定審查signal15 frame4803=9.606秒，從raw arrays/reference重新計算所有值。

## 指標、配對效果、門檻與對齊

- 分開參考：官方四位小數工作簿，以及固定sqrt校準、穩態post-filter skip.2的C022全精度輸出。參考不隨因子改變；TV全精度C022引用前必查hash。
- 每格記設計、來源/輸入/輸出hash、signed N、N/N-prime最大絕對/RMS偏差與座標。相對誤差只對|reference|≥1e−4且記排除數。穩態全240 Bark；工作簿TV N-prime僅6–13部分Bark軌跡，signal15沒有完整N-prime工作簿參考，完整矩陣只與原生C比較。
- 各訊號及模式內，主效應為其他設定相同的high−low之平均；兩因子交互作用為配對f11−f10−f01+f00平均。Mo rounding另作二元因子。確定性有限設計不產虛構p值或隨機母體推論；最佳/最差限同訊號同參考同指標。跨訊號只是描述。
- 依實際sample index固定2ms/0.1Bark格線，Mo原回傳標籤保留並列漂移，沿用已觀察linspace差異的明記解讀；不擬合位移/插值/任意padding/輸出校準，額外尾端及共同點數列帳。
- 控制：舊manifest不變、原樣source hash、單格與no-round精確diff、Mo skip0原API精確相等、每模式至少一個穩態格重複一致、匹配Mo no-round的N-prime不變、signal25不敏感、誤差分解殘差及contrast算術≤1e−12。均為診斷門檻，不是ISO合格門檻。
- 交付雙語報告/預登記、可機讀矩陣/結果/效果、標單位/域/參考的SVG或PNG、重播、環境與完整性證據。第三方完整source/WAV/XLSX/大型陣列留新tmp。SVG另查去識別工具未涵蓋部分，最後刷新去識別後hash；不混淆原始hash。Table A.9權威仍未定，不推導產品改值。
