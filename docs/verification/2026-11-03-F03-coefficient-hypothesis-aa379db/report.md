# F-03：0.22／0.24 是否補償語言或資料結構誤差？

日期：2026-11-03（Asia/Taipei）。獨立實驗：Astra（gpt-6-astra）。受驗快照：`aa379db8f3dc37f5048ac6c8b7a6d4ba2a6c3b76`。[English](report.en.md)。本輪未改正式表、程式或 golden，未 stage/commit/push/tag。

## 1. 結論與可判定範圍

**受測條件不支持「0.24 是為補償 C/Python 浮點或正確資料排列的誤差」；但這仍不能裁決 ISO 該格應為 0.22 還是 0.24。** 兩個來源在文字常數上已不同。單點算術可以精確算出「給定係數後的結果」，不能從同一個含未知係數的公式反過來唯一推導係數。

| 假說 | 判定 | 本輪證據範圍 |
|---|---|---|
| H_fp：係數差補償浮點精度 | not_supported | 4 個安全內點 × 2 係數 × 6 模式共 48 筆；主點係數效應是最大浮點點值誤差約 289,262 倍。這是有限局部實驗，不是整個算法的全域上界。 |
| H_layout：正確 layout/index 轉換產生差別 | not_supported | 相同邏輯索引在受測排列都取回同值；標記表抓到錯行、錯欄、錯 stride。不能排除其他未測程式的索引 bug。 |
| H_intent：作者刻意補償 | inconclusive | 沒有對應作者解釋或 commit 動機證據；數值實驗不能讀出歷史動機。 |
| H_standard：ISO 該格唯一正值 | inconclusive / PENDING | 未取得授權 Table A.9 目標格或獨立識別約束；不能由本實驗更改正式表。 |

這是研究交付，不是產品發布 ACCEPT，也不是完整 ISO conformant 判定。

## 2. 單點精確計算

來源依據為 [1991 原刊](https://www.jstage.jst.go.jp/article/ast1980/12/1/12_1_39/_pdf) p.42 的上斜率線性段與梯形積分；保存 C 也使用同型公式。本輪沒有取得 2017 標準正文的獨立係數推導式。完整來源與視覺查核範圍見 [sources.md](sources.md)。

令局部起點比響度 `N0=7/20=0.35 sone/Bark`，離起點 `Δz=1/5=0.2 Bark`，上斜率大小 `s`，則：

`N′(z0+Δz) = N0 − s·Δz`

`A = N0·Δz − s·Δz²/2`

`A` 是這一小段的面積（sone），不是完整總響度。起點與兩個候選終點皆落在 `[0.30,0.42)`，對應 zero-based RNS row 12；人工 stage 將它放在 band 4 的高頻側，確實讀取 column 4。

| 給定斜率 s | 精確 N′，sone/Bark | 精確局部 A，sone |
|---|---:|---:|
| 0.22 | 0.306 = 153/500 | 0.0656 = 41/625 |
| 0.24 | 0.302 = 151/500 | 0.0652 = 163/2500 |
| 絕對差 | 0.004 | 0.0004 |

Fraction 精確有理數與 Decimal 80/120 位兩個精度完全相符；這些有限小數恰能表示，所以收斂是精確相等。另三組 `(N0,Δz)` 是 `(0.32,0.05)`、`(0.40,0.3)`、`(0.375,0.125)`，兩係數的全部線段均留在同一安全範圍。

**如果問題是「不預先指定係數，ISO 數學式會推估出唯一多少？」本輪能證明目前資料不足以識別，不能負責任地回答只有 0.22 或只有 0.24。** 已知 N0/Δz，未知 s/N′/A；兩式有三個未知量。兩個候選解各自精確滿足式子，沒有獨立的 N′ 觀測或規範係數可選出其中一個。若將 0.306 自己指定為真值，再反推 0.22，就是循環論證。

## 3. 精度與語言的完整交叉

C 以 MSVC 19.44.35228 x64、`/O2 /fp:strict` 編譯，實測 `FLT_MANT_DIG=24`、`DBL_MANT_DIG=53`。Python 3.11.9、NumPy 2.4.4。兩係數都各跑 C binary32、C binary64、C float 字面值提升成 double、Python float、NumPy float32、NumPy float64。點值與面積都對照同係數的精確 oracle。

| 主點模式 | s=0.22 的 N′ | s=0.24 的 N′ | 兩係數中最大點值絕對誤差 |
|---|---:|---:|---:|
| C double / Python float / NumPy float64 | 0.306 | 0.302 | 9.325873406851316e-18 |
| C float literal → double | 0.30600000023841856 | 0.3020000010728836 | 1.0728836059570312e-9 |
| C float / NumPy float32 | 0.3059999942779541 | 0.3019999861717224 | 1.3828277587890626e-8 |

在所有 4 組輸入、兩係數，C double/Python float/NumPy float64 的點值與面積完全相同；C float/NumPy float32 也完全相同。主點最大面積誤差 `1.0013580322265624e-9`；48 筆最大點值誤差 `1.4543533325195312e-8`。主點的 `0.004 / 1.3828277587890626e-8 = 289262.3448275862`。完整結果亦保留誤差精確分數與 ULP；ULP 以輸出型別計算，float 常數提升至 double 的 ULP 很大不代表絕對誤差很大。

保存 C 寫的是 double 表中的 `0.22f`，其存值為 `0.2199999988079071`；假設換成 `0.24f` 則為 `0.23999999463558197`。這不是 0.02 級別的差，且兩係數都能在精確/高精度運算中成立，沒有「特定語言必須換係數才算對同一公式」的現象。

補充機制量級（設計後加入的精確診斷）：若硬要用 s=0.24 得到 0.22 候選的主點 0.306，固定 N0 時 Δz 必須變為 `11/60`，相較 1/5 改變 `−1/60 Bark`，即 `−1/12`（約 −8.33%）；固定 Δz 時 N0 必須改為 `0.354`，增加 `0.004 sone/Bark`，即 `2/175`（約 1.14%）。這只量化需要的補償，不證明實際作者曾作此補償。

## 4. 資料結構、邊界及 stage trace

來源檢查見 [sources.md](sources.md)：C `[18][8]` 原文目標 0.22f；Rust f64 與本機 MoSQITo 1.2.1 NumPy float64 原文目標 0.24。兩個係數都能經 Python nested、NumPy C/F-order 與對應 flat stride 正確取回；C 二維及複製的 flat row-major 亦相同。`100*row+col` 的目標標記應為 1204，負控錯行=1104、錯欄=1203、F-order 記憶體誤用 C stride=1005，全被抓到。這證明檢查能抓出所注入的錯誤，不代表所有實作都無錯。

另測 0.30/0.42 與 binary64 nextafter 的上下鄰值。簡化重現的索引判斷確實不同，例如 0.30 的 C float 常數＋`>=` 初始查表為 row13，Rust r8＋`<` 初始查表為 row12；Rust 下一段採 `<=` 又是 row13。0.42 前一個 binary64 值在 raw `<` 為 row12，r8 初始判斷為 row11。這包含常數型別、比較符及明確的八位四捨五入政策，不是純語言誤差；也不是完整 stage 的邊界驗收。主點 0.35 遠離這些閾值。

隔離 `git archive` 的 Rust 算子與保存 C，僅插入目標讀取計數，C wrapper 依次設定該格、Rust 兩版只改該格。人工 `nm[4]=0.35`，其餘 0：

| 實作 | s | 目標格查詢次數 | stage 總 N | N′[45]（名義 4.6 Bark） |
|---|---:|---:|---:|---:|
| C | 0.22f | 1 | 0.810818895244731 | 0.30602200613860336 |
| C | 0.24f | 1 | 0.8046635946822402 | 0.30202400750904235 |
| Rust | 0.22 | 2 | 0.811 | 0.30600000000000016 |
| Rust | 0.24 | 2 | 0.805 | 0.30200000000000016 |
| MoSQITo Python | 0.22 | 未插樁計數 | 0.811 | 0.30600000000000016 |
| MoSQITo Python | 0.24 | 未插樁計數 | 0.805 | 0.30200000000000016 |

Rust 計數含準備查詢，不能將兩次解讀為兩個物理斜率段。C 兩版 max ΔN′=`0.003997998629561017`、ΔN=`0.006155300562490806`；Rust 為 `0.0040000000000000036`、`0.006000000000000005`。負控 `nm[3]=0.35` 的 C/Rust 目標讀取皆為 0、換係數後輸出皆完全不變。C buffer guards 完好，兩實作全部 stage 輸出 finite。

C 在 band 上限加 `.0001f`，並以 `0.1f` 推進格點；Rust 有 r8 比較及最後總 N 的 0.001 sone 四捨五入（此量級）。因此同係數 C/Rust 的 stage 殘差不全是浮點，也不能把 stage 總 N 當成局部 A。此次 trace 證明目標格確實可被啟動，與獨立局部 oracle 分工，沒有用 C parity 宣判標準值。

再隔離執行本機 MoSQITo 1.2.1 的實際 `_calc_slopes`，輸入 shape `(21,1)`，其 `_get_rns_index` helper 原文不變，移除 package import 後由隔離 namespace 注入。只有 0.22 分支替換目標 literal；diff 及 helper hash 均保留。兩版本輸出 shape 為 N `(1,)`、N′ `(240,1)`，全部 finite；band4 的 ΔN′ 與 ΔN 分別為 `0.0040000000000000036`、`0.006000000000000005`，band3 負控完全不變。這是實際 Python stage 對照，沒有 Python 查表次數插樁宣稱，也沒有重跑完整音訊 pipeline。C 與 Python 都會隨同一係數改變，無法把來源 literal 不同簡化為 C/Python 語言本身的需要。

## 5. Gate、來源及交付

| Gate | 結果 |
|---|---|
| Fraction 與 Decimal 80/120 精確 oracle | passed |
| 48 筆係數×精度×內點交叉、同係數語言 parity | passed |
| layout 正控與錯誤注入負控 | passed |
| 邊界簡化診斷 | passed（發現比較政策差異；不等於完整邊界驗收） |
| C/Rust 隔離 stage 啟動、負控及 finite/guards | passed |
| 實際 MoSQITo 隔離 stage、shape/finite、係數效應及 band3 負控 | passed |
| 標準目標格及歷史動機 | PENDING / inconclusive |
| 全產品 cargo tests、benchmark、完整音訊/Annex B | not_run，非本輪範圍 |

[ISO 書目](https://www.iso.org/standard/63077.html) 與 [ANSI 公開預覽](https://webstore.ansi.org/preview-pages/ISO/preview_ISO%2B532-1-2017.pdf) 支持 2017-11 有更正 A.9，並說明參考軟體的規範角色；它們沒有提供本輪所需的目標格或獨立推導。保存 C 附件與修正版的對應仍未證明。1991 一手程序的 0.22 是歷史來源佐證，不自動等於 2017 正值。

執行前已有 [design.md](design.md)/[design.en.md](design.en.md)。本輪首跑通過；第二次修正來源行號並加補償量級診斷；第三次新增實際 MoSQITo stage，每次均用新 tmp 目錄，交付第三次結果。MSVC 環境初始化出現 `vswhere.exe` 不在 PATH 的警告，隨後 x64 環境、兩個 C executable 編譯和實際執行均成功；警告未隱藏。`results.json` 包含每筆值、來源/派生/binary hashes、判定；`run-log.json` 是執行命令與 stdout/stderr；diff 檔列隔離插樁/單格替換。完整 source/binary 留 tmp，交付只有 UTF-8 文字。

重現：在 Windows MSVC x64 環境、Python+NumPy、rustc 可用時，從 repo 執行 `python <此資料夾>/run_experiment.py --work <全新tmp目錄> --out <新的results.json> --official-c <保存ISO_532-1.c> --official-header <保存ISO_532-1.h> --mosqito-source <保存_calc_slopes.py> --vcvars <vcvars64.bat>`。腳本驗 C hash、從固定 commit archive Rust，拒絕覆蓋既有 work/results；記錄版本、命令及所有 scoped assertions。這仍需要先前合法保存的 C 與本機 Python 來源，不假裝只靠 git 即可取得外部附件。

覆核後另作唯讀 `cl /Bv` 版本查詢（未提供 source，預期 D8003／退出 2），並同步 runner/results 的 MoSQITo gate 欄位；這不是編譯失敗，也沒有為純 metadata 修改重跑 DSP。查詢結果與用途明列於 environment/log。

去識別化、完整性與未涵蓋後綴的明確處理見 [delivery-check.md](delivery-check.md)。正式改表門檻維持 PENDING。
