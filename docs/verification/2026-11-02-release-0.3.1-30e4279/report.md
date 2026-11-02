# 0.3.1 發布前獨立驗收

**ACCEPT** — 本簡報範圍內沒有阻擋打 tag 的事項。

2026-11-02 (Asia/Taipei). 實際執行日較簡報預定 2026-11-01 晚一天；交付使用實際日期，未覆蓋舊輪次。

## 逐項結果

| §2 | 項目 | 結果 | 證據摘要 |
|---|---|---|---|
| 1 | 凍結 | PASSED | 固定封存 30e427963da88db8b23e82cf612f047f36cd164b；基準實際 commit 62e46ca7d6ac65df7c4a4db8df8380e30234e267。逐檔記錄 275 個追蹤來源 hash。 |
| 2 | 庫內 gate | PASSED | Rust 138 通過／0 失敗／3 ignored；manifest 175 檔；正式 pytest 69 通過。fmt、兩種 clippy、文件配對與 docs 去識別化皆通過。 |
| 3 | C-02 | PASSED | C01/C02 合計獨立案例：Rust 66、C 52、Python 48，全通過；確認第一個違規 index、優先順序、C 哨兵、有限邊界與串流下一幀／殘留旗標。 |
| 4 | C-01 | PASSED | 16 種長度；正式訊號 [3, 5, 10]、前綴 [4801, 24013, 47927]；n／time／全部 240 Bark 列位元相同。自訂串流 chunk 包含 1 與 >96 樣本。 |
| 5 | V-01 | PASSED | 21 直接＋19 損壞副本控制通過；5 曲線／982 點；最小餘裕 0.08513610649320266 sone/Bark，訊號 3 比響度第 66 列（零起算）。 |
| 6 | 有限輸入穩定性 | PASSED | 8 inputs、40 arrays、4,720,928 個 binary64 值相同；首差異 null。全部 12 個凍結 Windows hash 符合。 |
| 7 | 產出物 | PASSED | 全部 4 個產物 hash 符合紀錄與 SHA256SUMS；header 與已提交 blob 位元相同；9 個匯出符合基準，import library 位元相同。乾淨 wheel 版號 0.3.1，兩個 NaN 呼叫均丟 ValueError。 |
| 8 | 紀錄一致性 | PASSED | 版號／日期／CHANGELOG／commit 表一致；CI 41278186406 對應固定 SHA，6 jobs 成功；驗證數量符合 release 紀錄。 |

## 發現與目前判斷

- 初次 Windows tar.exe 解壓造成 Unicode 文件路徑錯碼，文件配對失敗；以 Python tarfile 從同一 archive 重解，逐一對照 git tree，文件配對重跑通過，仍有 10 則既有未配對 backlog 警告。Rust／C／Python 原始碼位元未變。
- 環境 core.autocrlf=true 使 archive header 為 CRLF；產物 header 與 archive 副本不相同，但與固定 commit 的 Git blob 逐位元相同。此差異僅換行，未用正規化取代已提交 blob 比較。
- 初次 maturin 因獨立 venv 缺 console script 失敗；複製同版本執行檔後成功 release build。正式 pytest 在成功 build 後重跑；初次 pytest 不作正式證據。依賴使用原 golden venv 的 .pth，受驗 extension 位於獨立 venv；另以全新且無 .pth 的 wheel venv 驗安裝。
- 次正規數、±0 成功；1e300 實際為 LevelExceeds120dB（C code 1），沒有被有限性檢查拒絕。C ABI 不公開 index，由 Rust／Python 驗證 index。
- 完整 Rust 首輪帶 Windows dump-only 設定；另以 HASH_GATE_DUMP_ONLY=0 重跑嚴格 hash gate 通過，獨立腳本亦核對 12 個常數。重現 runner 已改為嚴格設定。
- C 編譯初始化的 vswhere 缺失訊息不阻擋後續 MSVC 編譯及執行。

## 範圍與交付

可用 WAV 為 7 檔：正式訊號 3／5／10 加 4 個輔助訊號；另測 3 秒 contract。不是全部 25 訊號的重新認證。Signal 3 的 44.1→48 kHz 前處理及 hash 已記錄。V-01 餘裕涵蓋現有正式參考 5 條曲線，不外推至未提供曲線。這些界線不阻擋本簡報的 tag 驗收。

完整命令、harness、逐例 hex／首差異、原始輸入／binary／來源 hash 見 results.json、contracts/、numerics/。工具版本見 freeze.json 與各子結果：Rust/cargo 1.99.1、Python 3.11.9、MSVC 19.44.35228；gate NumPy 2.4.6，numerics NumPy 2.4.4。主工作樹 HEAD 4e615bfb3b5be39db8074f34e7c6208feaa35aab，初始 clean；交付後只有本輪未追蹤資料夾。v0.3.0 的 annotated tag object 與 peeled commit 分欄記錄。

F-03、穩態前端、補零官方 C、MoSQITo 時間、人工防毒、全 25 訊號與新的 Linux 實測均不在範圍。既有 pytest parity 按簡報執行，但獨立數值驗收不以 MoSQITo 為 oracle。歷史報告沒有補入 passed。未更動受驗程式／測試／golden，未 stage、commit、push 或 tag。

正式 gate 來源為 formal-gates.json 的實際 process exit；pytest 計數自終端摘要解析，5 個缺檔／失敗／skipped 等負面控制均未產生 ACCEPT（summary-negative-controls.json）。交付文字統一為 LF。去識別化與文字格式盤點見 delivery-check.md；delivery-integrity.json 僅對處理後交付文字檔計算並排除自身，原始 binary／WAV／來源 hash 保持原義。下一步由主代理覆核；打 tag 前另依此英文報告更新 release 紀錄獨立驗證節。
