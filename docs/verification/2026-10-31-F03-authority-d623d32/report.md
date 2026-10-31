# F-03：Table A.9 權威來源獨立追查

- 驗證方：Astra（gpt-6-astra）；日期：2026-10-31（Asia/Taipei）。
- 受驗程式快照：`d623d32931d07c11e327b3226398cd45440ef121`，以 `git rev-parse HEAD` 核實。本輪是文件來源稽核，沒有執行數值驗收。
- 範圍：`USL[12][4]` 差異與 ISO 532-1:2017 corrected version 2017-11 的關係；未改程式、表格、官方資料或 golden。

## 判定

後續針對論文的補查見 [literature-followup.md](literature-followup.md)：已核實 1991 原刊 BASIC 表的該位置為 0.22，以及 MetaSona 固定版本直接記錄 0.22／0.24 差異；兩者未解決 2017 更正的方向與原因。

**PARTIAL：已直接核實「2017-11 修正版確實更正 Table A.9」；尚未取得可驗證授權的 Table A.9 全文，不能確認該次更正是否就是 0.24 → 0.22，也不能宣判 Rust 的缺陷歸屬。F-03 權威值 gate 維持 PENDING／UNRESOLVED。**

| 待答問題 | 本輪結果 | 證據界線 |
|---|---|---|
| 標準版次 | 已確認 Edition 1，2017-06；corrected version 2017-11 | ISO 官方書目與國家標準機構公開預覽 |
| 修正涉及何處 | 已確認 Table A.9 | ISO Foreword，印刷頁 iv；EVS 預覽 PDF 第 4 頁（zero-based 3）；ANSI ISO 預覽同頁序 |
| 修正文日期 | BSI 國家前言記載 ISO corrected text 日期為 2017-11-17 | ANSI 所提供 BSI 預覽 PDF 第 2 頁；此為 BSI 對 ISO 更正日期的一手記錄 |
| BSI 採用日期 | 2018-09-30 | 與 ISO 更正日期不同，不得混用 |
| 對應格正式正值 | PENDING | 沒有將非授權鏡像或搜尋摘要升格為正式全文 |
| Table A.9 正式印刷頁碼／PDF 頁序 | PENDING | 印刷 p.27 僅為未核實線索；沒有權威全文確認，不能填成已驗證頁碼，更不能推算 PDF 頁序 |
| 哪格由何值改為何值、為何更正 | PENDING | 前言沒有列 old/new 值、受影響格、原因或附件同步情形 |

## 直接原文證據與沿革

[EVS 的 ISO 公開預覽](https://www.evs.ee/en/StandardDownload/DownloadPreview?language=EnglishLanguage&productId=88577)封面標示 2017-11 修正版，前言印刷 iv 的必要摘錄為：**“Table A.9 has been corrected.”** 此句證明更正的表號，沒有提供具體數字或修正原因。[ANSI 的 ISO 預覽](https://webstore.ansi.org/preview-pages/ISO/preview_ISO%2B532-1-2017.pdf)可交叉核對相同前言。EVS 預覽共 7 個 PDF 頁面；ANSI ISO 預覽共 5 頁，均未涵蓋 Table A.9。

[ANSI 的 BSI 預覽](https://webstore.ansi.org/preview-pages/BSI/preview_30381841.pdf)國家前言（PDF 第 2 頁）在 30 September 2018 的修訂紀錄列：**“Implementation of ISO corrected text 17 November 2017: See ISO foreword for details”**。同檔 PDF 第 6 頁是 ISO Foreword 印刷 iv，同樣指出 A.9 更正。這支持將 ISO 更正文日期與 BSI 納入日期分開記錄；仍不支持猜測更正原因。BSI 預覽目錄的 Annex B 起於印刷 44，ISO 預覽則為 45，故不同出版排版不可互套 PDF 頁碼。

[ISO 官方書目](https://www.iso.org/standard/63077.html) life cycle 記錄正式發布 2017-06-15，並列 2017-11 corrected version；2022 年確認與後續修訂專案是另外的事件，不能用來解釋 2017 年哪一格係數的修正。[NEN 修正版書目](https://www.nen.nl/en/nen-iso-532-1-2017-cor-2017-11-en-241373)列當地出版日 2017-12-01，取代原 NEN-ISO 532-1:2017；這也是採用／出版沿革，不是更正原因。

## 與程式差異的對應

本輪直接讀取 `iso532/src/tables.rs:86`，Rust 第 13 列／第 5 欄（zero-based `[12][4]`）為 `0.24`。`RNS[11]=0.42`、`RNS[12]=0.30`，與既有報告 §15 記錄一致。保存的官方 C `0.22f` 及其來源 hash 本輪引用 `docs/修正報告2.md` §15 的既有核驗紀錄，沒有重新下載附件或宣稱重新驗證 C hash。C float 字面值與 Rust f64 的表示精度不可混為 bitwise 同值。

搜尋引擎浮出的非標準機構 PDF 鏡像提供線索：印刷 p.27、Table A.9 的 Index 6、比響度區段 `0.300 ≤ N′ < 0.420`、Critical band 5，顯示 `0.22`。**這只用於尋找正式來源，並非本輪權威結論。** 本輪未下載、交付該鏡像全文，也未以之關閉 gate。正式核驗仍須將這一列／欄與程式逆序的 RNS/USL 排列逐項對照，不能把程式第 13 列直接叫標準 Index 13。

存在「表 A.9 被更正」這件事，使版本修正成為值得追查的可能解釋；但是「確有更正」與「恰好此格由 0.24 改成 0.22」是不同命題。要證明後者，至少需要更正前後授權版本的同格，或 ISO／國家標準機構對特定格與原因的正式釐清。目前不能排除其他表格欄位、排版或數值才是修正對象，也不能斷言 MoSQITo 傳抄原因。

## 尚需取得與合法路徑

使用者確認目前沒有授權全文／訂閱。已另整理[正式取得方式、待核對頁面與英文購前詢問](acquisition-checklist.md)；本輪維持文件追查交付，不購買或代寄詢問。

1. 從 [ISO 官方書目](https://www.iso.org/standard/63077.html)、[EVS](https://www.evs.ee/en/iso-532-1-2017) 或 [NEN 修正版頁](https://www.nen.nl/en/nen-iso-532-1-2017-cor-2017-11-en-241373)取得授權全文；本輪未購買、未代送訊息、未繞過存取限制。已有機構授權時依其範圍閱覽。
2. 保存文件識別、取得來源、版次、原始檔 hash，記錄 Table A.9 印刷頁碼與該檔 PDF 頁序，摘錄必要單格、行列標題與相鄰區段，不將整份付費標準進庫。
3. 要解決修訂原因，取得 2017-11-17 correction 的正式明細、2017-06 原版同格，以及 C 附件是否同步更新的紀錄；或用合法取得的更正前後版本核對差異。僅有 corrected 全文值也不自動證明傳抄或修正起因。

供後續詢問標準機構的草稿（未寄送）：請協助確認 ISO 532-1:2017 corrected text 2017-11-17 的 Table A.9 更正涉及哪些儲存格及 old/new 值；是否包含比響度 0.300 ≤ N′ < 0.420、Critical band 5，並請提供更正原因、適用印刷頁碼，以及電子 C 附件是否隨之更新及其版本識別。我們觀察到某實作為 0.24，而保存的 ISO C 附件為 0.22f，希望依授權標準與正式釐清處理。

## 方法限制與交付

本輪網路閱讀成功取得官方書目、授權預覽的文字及 PDF 頁序。web screenshot 對 EVS／ANSI ISO 回報 cache miss，故上述兩份預覽與 BSI 日期紀錄仍限網路 PDF 文字解析證據。主代理另下載並渲染 [iTeh 公開 sample](https://cdn.standards.iteh.ai/samples/63077/58c7f464f167413abde1367b3e0906db/ISO-532-1-2017.pdf)，本驗證方獨立 `view_image` 檢視其第 4 頁，確認印刷 iv 的 A.9 更正陳述，且以 `Get-FileHash -Algorithm SHA256` 重算 PDF hash 為 `d0a5128da2b094ac1fa198e93e2871155d63f276dee542827b1783ca29316176`。這是原始公開預覽檔的 hash，不是交付 Markdown hash；該預覽未涵蓋 Table A.9，PDF 與整頁影像不列入本交付資料夾。主代理目前本機下載的 EVS 檔只有封面／版權 2 頁，與 web 工具解析的 7 頁版本不同，不能聲稱兩者 byte-identical。ISO OBP 文字接口僅回覆需 JavaScript，未取得 Table A.9；ASN 公開預覽抓取失敗。未取得全文是本輪結果的限制，不能寫成標準本身不存在相關規定。

交付僅包含 UTF-8 Markdown 報告與精簡來源清單；去識別化執行結果另記於 `delivery-check.md`。來源文件 hash 如後續補入，與去識別化後交付文字的 hash 分別標明意義。
