# 正式取得方式與待核對頁面

使用者目前沒有授權 PDF 或標準訂閱。本清單僅整理正式取得路徑與購前確認事項；未購買、未寄送詢問。即使取得現行修正版全文，也不保證能解決舊值、更正方向及原因。

## 正式路徑

| 路徑 | 應指定的文件 | 購前確認事項 |
|---|---|---|
| [ISO 官方](https://www.iso.org/standard/63077.html) | ISO 532-1:2017，Edition 1，English PDF，corrected version 2017-11 | 確認交付版本；另問是否可取得未更正的 2017-06 原版及更正明細 |
| [EVS](https://www.evs.ee/en/iso-532-1-2017) | ISO 532-1:2017 英文版 | 商品名稱未直接帶 corrected 日期，購前請供應商確認實際交付為 corrected 2017-11；同時確認授權與閱覽方式 |
| [NEN 明示修正版](https://www.nen.nl/en/nen-iso-532-1-2017-cor-2017-11-en-241373) | NEN-ISO 532-1:2017(Cor. 2017-11) en | 頁面說 NEN Connect 可閱現版及舊版；本輪未驗證其中是否實際保留本標準「未更正 2017-06」版本，須先詢問再決定是否購買／訂閱 |

上述連結提供正式訂購或授權管道，不代表本次已取得全文，也不保證所有歷史版本都可下載。不要將不同國家採用版的出版日視為 ISO 更正文日期。

## 文件取得後逐項核對

| 項目 | 待閱位置 | 必須記錄的證據 |
|---|---|---|
| 文件識別 | 封面／版權頁 | 完整標準號、語言、Edition 1、2017-06、corrected 2017-11；取得來源與授權版次；原始 PDF SHA-256 |
| 更正陳述 | ISO Foreword 印刷 iv | Table A.9 更正句及該份檔案的 PDF 頁序；不能套用其他出版版的頁序 |
| 表本體 | Table A.9；權威印刷頁碼尚未確認，p.27 僅為搜尋線索 | 表號、完整表頭、列標、欄標、相關單格與相鄰區段；記錄實際印刷頁碼及 PDF 頁序 |
| 目標格 | 待核實線索：Index 6，`0.300 ≤ N′ < 0.420`，Critical band 5 | 直接核對值為何，並確認與 Rust `USL[12][4]` 的對應；RNS/USL 以高到低排列，不得把程式第 13 列當作標準 Index 13 |
| 修正前值 | 授權的未更正 2017-06 原版，同一 Table A.9 格 | 確認原版未被後來 corrected PDF 取代；獨立記錄版次、原始 hash、頁碼、old 值及行列標題 |
| 更正方向與原因 | 2017-11-17 更正明細／供應商或標準機構正式回覆 | 哪些格被改、old/new 值、原因與適用範圍；前言本身沒有提供這些細節 |
| 電子附件 | ISO 電子 C 程式包及正式版本紀錄 | C 附件是否隨更正同步更新、更新日期與識別方式；保留原始包與 C 檔 hash，不只依檔名或內部舊日期推定 |

取得後只交付核驗所需的短摘錄、定位與判斷，不把付費標準全文進庫。原始文件 hash 與去識別化後報告 hash 分開記錄。若全文仍未說明更正原因，將「表值已核實」與「修訂原因未解」分別報告。

## 可複製的英文購前詢問（未寄送）

> I am considering obtaining ISO 532-1:2017 for a document and software consistency review. Please confirm whether the English document supplied is Edition 1, corrected version 2017-11. Can you also provide licensed access to the original, uncorrected June 2017 text, rather than a historical catalogue entry that downloads the corrected text? If using a subscription, please confirm that this specific uncorrected version is actually available before purchase.
>
> The corrected foreword states that Table A.9 was corrected. Is an official correction notice or change record available identifying the affected cells, old and new values, and the reason for the correction dated 17 November 2017? In particular, we need to verify the row for 0.300 ≤ N′ < 0.420 and Critical band 5, its correspondence to the supplied C implementation, and whether the electronic C package was updated at the same time. Please advise on the appropriate document, version identifiers, and licensed access route. We understand that purchasing the current corrected text alone may not establish the correction history or its cause.
