# 精簡來源清單

查閱日2026-10-31；以下均由GitHub connector直接讀取，並解析固定commit再取檔。

- [main目標列，L519](https://github.com/ggrecow/SQAT/blob/82ad35bd280961699742ac87cba5aa7442574022/psychoacoustic_metrics/Loudness_ISO532_1/Loudness_ISO532_1.m#L519)：USL第13列第5欄0.24。
- [main來源註記，L74–87](https://github.com/ggrecow/SQAT/blob/82ad35bd280961699742ac87cba5aa7442574022/psychoacoustic_metrics/Loudness_ISO532_1/Loudness_ISO532_1.m#L74-L87)：2014 C、2015 AARAE、2023 SQAT與2026修改註記。
- [v1.3目標列，L501](https://github.com/ggrecow/SQAT/blob/b144394455c9ab671c470573001ce47fe4f65df7/psychoacoustic_metrics/Loudness_ISO532_1/Loudness_ISO532_1.m#L501)：0.24。
- [v1.0目標列，L633](https://github.com/ggrecow/SQAT/blob/4b8d3d68f82ff6e17d8df71ae58e87c8b737671b/psychoacoustic_metrics/Loudness_ISO532_1/Loudness_ISO532_1.m#L633)：0.24。
- [v1.0來源註記，L67–70](https://github.com/ggrecow/SQAT/blob/4b8d3d68f82ff6e17d8df71ae58e87c8b737671b/psychoacoustic_metrics/Loudness_ISO532_1/Loudness_ISO532_1.m#L67-L70)：早期版本已有AARAE來源鏈。
- [PR #48](https://github.com/ggrecow/SQAT/pull/48)：已讀正文及patch，未見目標USL列修改／Table A.9勘誤理由；不是本輪數值驗收。
- [PR #49](https://github.com/ggrecow/SQAT/pull/49)：已讀正文及patch，未見目標USL列修改／Table A.9勘誤理由。

檢索紀錄：issue `"A.9"`／`"0.24"` 未命中；PR `"0.24"` 未命中，`"A.9"` 結果需人工排除近似匹配，沒有找到本格勘誤；commit `"USL"` 未命中。本輪沒有把查無結果推成不存在，也未取得AARAE原始檔或2014 C程式作直接核對。
