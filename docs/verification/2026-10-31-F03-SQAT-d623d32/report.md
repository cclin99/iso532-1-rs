# F-03：SQAT 來源核對

日期：2026-10-31（Asia/Taipei）；獨立查核：Astra（gpt-6-astra）。本機受驗基準 `d623d32931d07c11e327b3226398cd45440ef121`。本輪只讀公開 GitHub 來源，沒有修改正式係數／golden、執行數值測試、commit／push 或對外留言。

## 結論

**查 SQAT 有參考價值，而且直接結果是 0.24。** 目前 main、v1.3、v1.0 三個固定快照，USL 第13列第5欄皆為0.24，與本案 Rust／MoSQITo 所用數字相同。這使「0.24 只出現在 MoSQITo」不成立；但它仍不能證明 corrected ISO Table A.9 的正式值，亦沒有解決2017更正原因。

SQAT 程式註記的來源鏈為 ISO Annex A 的2014 C程式 → Ella Manor 的2015 AARAE MATLAB實作 → SQAT 的2023改編。它不是直接宣告此格逐字核對2017-11修正版。沒有追查到原始AARAE檔與2014 C檔前，不應把SQAT與MoSQITo視為完全獨立的權威投票，也不能斷言兩者共享哪個傳抄錯誤。

## 固定版本與目標格

檔案均為 `psychoacoustic_metrics/Loudness_ISO532_1/Loudness_ISO532_1.m`。

| 查閱版本 | 固定 commit | 目標行 | 結果 |
|---|---|---:|---|
| main（commit日期2026-10-28） | `82ad35bd280961699742ac87cba5aa7442574022` | 519；USL起507 | 0.24 |
| v1.3（commit日期2025-04-04） | `b144394455c9ab671c470573001ce47fe4f65df7` | 501；USL起489 | 0.24 |
| v1.0（commit日期2023-05-14） | `4b8d3d68f82ff6e17d8df71ae58e87c8b737671b` | 633；USL起621 | 0.24 |

上述日期是本輪GitHub所解析tag／main對應commit的日期，不冒稱所有日期都等同release正式發布日。三個快照的必要單列均為：

```text
0.40 0.33 0.26 0.24 0.24 0.22 0.22 0.22
```

MATLAB採one-based索引，對應 `USL(13,5)`，亦即本案zero-based `[12][4]`。這是程式陣列位置，不能直接當成印刷Table A.9的Index 13。

## 來源註記與PR核對

當前檔案第74–80行記錄2014 Annex A C來源、2015 AARAE作者、2023 SQAT改編與ISO 532-1:2017測試信號驗證；第85–87行記錄2026年修改以貼近C參考程式及改善效能，連結PR #48、#49。舊版v1.0第67–70行已保留同一來源鏈。

- [PR #48](https://github.com/ggrecow/SQAT/pull/48) 說明修正時變響度的多項轉寫問題，包含濾波串接、非線性區段、時間加權、slope sector推進與額外偏置。其 slope 修正說明是sector搜尋／推進條件；本輪讀取完整回傳patch後，未見目標USL列修改。PR正文未提出Table A.9的勘誤內容、0.24／0.22此格來源或更正理由。merge commit為 `9906a826055692bd00fe58c69754389442bb8abd`。
- [PR #49](https://github.com/ggrecow/SQAT/pull/49) 為在#48之上的效能工作；本輪讀取正文及patch，未見USL目標格改動或A.9更正說明。merge commit為 `e86a8fb9a1347a0207afe0f637c13983f0841eae`。
- 透過GitHub connector查issue／PR的 `"A.9"`、`"0.24"` 及commit的 `"USL"`，未找到針對本格更正的明確紀錄。`"A.9"` PR搜尋有不相關／近似匹配結果，逐項不能當成Table A.9命中；#48／#49 comments接口回傳空清單。本輪搜尋範圍不代表所有歷史討論必然不存在，也未做所有commit逐行git blame。

PR聲稱對齊C、某些訊號一致或通過容差，不代表每一格係數皆逐項對齊C。此處實際看到的0.24常數才是本輪直接證據；驗證聲稱不應拿來覆蓋這個觀察。本輪沒有重新執行SQAT測試，因此不把PR作者的數值聲稱列為本輪實測。

## 對目前判斷的影響

SQAT提供了有價值的**0.24實作沿革線索**，與先前1991原論文／官方C的0.22線索共同顯示需要追溯版本與轉寫鏈。最有價值的後續來源是AARAE 2015原始檔及其引用的2014 C版本；只有查到它們或正式2017前後Table A.9，才可能判別0.24的起源。現在不足以斷言「MoSQITo自己抄錯」或「0.24必為ISO正值」。正式改表權威門檻仍為PENDING。

## 交付檢查

僅交付本報告與sources.md，均為UTF-8 Markdown。執行 `python tools/redact_paths.py docs/verification/2026-10-31-F03-SQAT-d623d32` 及隨後 `--check`；結果分別為 `0 file(s) changed`、`clean`，退出碼均0，沒有skipped或警告。逐檔確認沒有非UTF-8或未支援格式。未交付付費標準、完整第三方程式或binary；來源用固定commit連結定位。
