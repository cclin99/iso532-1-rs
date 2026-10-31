# Table A.9：論文與工程文件補充追查

查閱與獨立核對：Astra（gpt-6-astra），2026-10-31（Asia/Taipei）。此為同輪來源補充，沒有變更受驗程式、表格或 golden。

## 結論

**有正式論文支持這個 USL 位置早在 1991 年已採 0.22，也有開源專案原始文件直接記錄 0.22／0.24 差異。** 這次不再僅有二手論文轉寫線索。然而，本輪仍未找到直接說明「2017-11 Table A.9 哪格由何值改為何值，以及原因」的正式更正明細或論文。這是本輪檢索結果，不是宣稱這類文件不存在。

| 來源 | 已直接核實 | 能支持的結論 | 不能支持的結論 |
|---|---|---|---|
| ISO 修正版 Foreword | 印刷 iv 指明 A.9 曾更正，詳見本輪主報告 | 正式更正涉及 Table A.9 | 沒有特定格 old/new 值或原因 |
| Zwicker 等人 1991 年原始期刊論文 | 印刷 p.40／PDF 第 2 頁 BASIC 行 3270，第 13 個 USL DATA 列之第 5 值為 0.22 | 0.22 在 1991 原始發表程式中已存在，早於 2017 修正 | 不能證明 2017 年改的恰為該格，也不能決定現行正式表值 |
| MetaSona 固定 commit 原始文件及程式 | 明記 `[12][4]` 的 0.22／MoSQITo 0.24 差異及來源說明 | 另有工程專案明確記錄同一位置差異，非僅本專案觀察 | 非標準機構裁定、非同儕審查論文，沒有證明更正原因 |
| LISQM | 有上述 MetaSona 差異摘要 | 提供可追溯線索 | 是二手索引，沒有親自執行驗證，不能替代原始證據 |

## 1991 年原始論文：一手歷史係數證據

E. Zwicker, H. Fastl, U. Widmann, K. Kurakata, S. Kuwano, S. Namba, *Program for calculating loudness according to DIN 45631 (ISO 532B)*, Journal of the Acoustical Society of Japan (E), 12(1), 39–42 (1991)。[J-STAGE 原刊頁](https://www.jstage.jst.go.jp/article/ast1980/12/1/12_1_39/_article)，DOI [10.1250/ast.12.39](https://doi.org/10.1250/ast.12.39)，[原刊 PDF](https://www.jstage.jst.go.jp/article/ast1980/12/1/12_1_39/_pdf/-char/ja)。

主代理自 J-STAGE 下載原始 PDF 並渲染，Astra 獨立查看第 2、3 頁影像與重算檔案 hash。PDF 共 4 頁；原始檔 SHA-256：`9ada5cbaf31122d72e734ceb7929edd9f3517de84ea7c7d4bf93e4305ee6559d`。這是來源 PDF hash，不是去識別化交付文件 hash。

印刷 p.40／PDF 第 2 頁，BASIC 行 3270 的必要單列摘錄：

```text
3270 DATA 0.40,0.33,0.26,0.24,0.22,0.22,0.22,0.22
```

同頁 USL 資料從 BASIC 行 3150 起，每行 8 值，行 3270 為第 13 列。印刷 p.41／PDF 第 3 頁，BASIC 行 3760–3800 以外層 18、內層 8 的迴圈讀入 USL；前頁 `OPTION BASE 1` 使此位置為 BASIC `USL(13,5)`，轉成 zero-based 即 `[12][4]`。其第 5 值為 `0.22`。RNS 在同頁以遞減次序列出，與本案程式第 13 列的位置相符；不能將其直接當作 2017 標準 Table A.9 的 Index 13。

因此「0.22 是 2017 年才首次引入的數值」不符合這份歷史證據。但若 2017 初版某格印錯、修正版恢復舊值，仍與此證據相容；是否如此必須核對 2017 前後正式版本，不能由 1991 論文反推。

## MetaSona：固定版本的一手工程文件

GitHub connector 解析 `main` 至 commit `11afbef856721a0de4f7ff2b6addeee3ff907165`，再直接讀取該固定快照：

- [THIRD_PARTY.md，第 36–38 行](https://github.com/huaaudio/metasona/blob/11afbef856721a0de4f7ff2b6addeee3ff907165/THIRD_PARTY.md#L36-L38)：作者記錄刻意保留 `MS_UPPER_SLOPES[12][4]=0.22`，並指出所比對 MoSQITo revision 使用 `0.24`；作者將來源歸為提供給該專案的 `psychohelperc/ISO_532-1.c` 表，而非為符合 fixture 調整。
- [src/ms_loudness.c，第 59–74 行](https://github.com/huaaudio/metasona/blob/11afbef856721a0de4f7ff2b6addeee3ff907165/src/ms_loudness.c#L59-L74)：註解直接說明同一差異，第 74 行的第 5 值確為 `0.22`。
- 文件固定 MoSQITo revision 為 `d990c33f94f1b2050b2d811dea492219ebe97b30`；本補充直接核實的是 MetaSona 的文件與程式，不冒稱又獨立完成該 MoSQITo revision 的全表比對。

此 commit 只是本輪查閱快照，不是「首次修正該係數」的 commit；未追定該行首次加入的歷史。MetaSona 文件沒有提供 supplied C 檔與 ISO 官方附件之同一性 hash，也沒有引述 A.9 的印刷頁碼、更正前後值或原因，所以作者的來源說明仍須與規範權威證據區分。

[LISQM 的 Zwicker loudness 頁](https://zhenxianli.github.io/LISQM/metrics/loudness-zwicker.html)與 [MetaSona 專案頁](https://zhenxianli.github.io/LISQM/projects/metasona.html)確有此差異摘要；本輪已沿連結追到上列原始 repo，故結論以原始文件為依據。LISQM 本身是開源實作目錄，不是標準或學術論文。

## 更新後的證據判斷

可以向使用者明確說明「有：1991 原論文的 BASIC 表，以及 MetaSona 原作者工程紀錄都支持 0.22 這條歷史／實作線索」。仍不能說「已確認 ISO 在 2017-11 將此格從 0.24 改為 0.22」。官方 A.9 現行單格值、更正方向與原因保留 PENDING；程式處置界線不變。

未把論文全文、整頁影像或第三方完整原始碼加入交付；本檔只提供必要單列摘錄、固定來源定位及判斷。
