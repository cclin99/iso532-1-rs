# F-03 單格係數敏感度：測試能否反對 0.24？

日期：2026-10-31（Asia/Taipei）。獨立驗證方：Astra（gpt-6-astra）。受驗快照 `d623d32931d07c11e327b3226398cd45440ef121`。遵循 AGENTS 與 iso532-rust-verification skill；本輪為隔離數值實驗，沒有改正式程式、USL 表、官方資料或 golden，未 commit／push。

## 結論

**目前測試沒有排除 0.24，但這不等於測試證實 0.24 是正式標準值。** 在本輪會受該格影響的定向案例與 Annex B signal 14 中，0.22 較接近官方 C 的部分輸出；然而 0.24 和 0.22 都在既有 `max(0.1, 5% × |reference|)` 數值容差內。沒有出現「只有 0.22 通過、0.24 失敗」的情形。

「MoSQITo 作者曾看過正式標準」是來源歷史假說，輸出測試不能證明或否定作者看過什麼；即便看過，也不能邏輯推出每個係數必然抄對、所看版次正確或採用理由為何。「0.24 是規範正值」則須直接標準證據；有限而有容差的測試通過，不能反推該單格唯一值。

## 方法與證據獨立性

1. 以 HEAD 的 `calc_slopes.rs` 與 `tables.rs` 建立隔離副本。0.24 版保持算法與表；0.22 版只改目標一格，另將 import 指向對應副本。原始 pipeline 僅用於取得相同的 21-band 中間量與時間加權。
2. 定向輸入含 band 3／4／5 的單一 spike，值為 0.299999、0.30、0.300001、0.35、0.419999、0.42、0.420001、0.5、1.0，加平坦 0.35 與 silence，共 29 個。band 編號為 zero-based。這些是人工 stage fixtures，不是標準 Annex B 測試信號。
3. 另讀既有 F-02 保存的 Annex B signals 1、10、14 已校準 input.bin，以當前 scalar pipeline 重算中間量。對兩版傳入完全相同 nm；時變資料均為 zero initialization，在 2 kHz slope stage 比較，總響度另外用同一時間加權並取每四點。
4. 將既有官方 C 檔原封複製到新 tmp 目錄，以 MSVC `/O2 /fp:precise /LD` 重新編譯，只 export `f_calc_slopes`。C 原始檔 SHA-256 是 `a74b45ed297cd09ac60701a923120341137d227e536f3109ae4ece810d834491`，與既有保存附件一致。每個 C nm／N／N′ buffer 都加 guard，全部完好，輸出均 finite。
5. 另與前輪保存的官方 C 完整 pipeline 輸出 `c-reference.npz` 在共同輸出格點比對，檔案 hash 載於 summary.json。本輪沒有重新下載官方檔案，也沒有重新產生該完整 C reference。這與用 MoSQITo 衍生 golden 自我比較不同；但仍是官方 C 實作比較，不能取代正式 Table A.9。

使用 `max(0.1,5%×|reference|)` 作辨識能力診斷；不使用加法容差，不允許 temporal shift 或例外比例來掩蓋差異。定向 nm 是人工中間量，沒有宣稱來自可實現的完整物理音訊；此診斷不宣稱它是標準接受條款的正式適用集合。C 的 float 字面常數、格點偏移與 Rust 的 rounding 仍可能有差異，不能把全部 C 殘差歸因於單一係數。**官方 C 本身使用0.22，因此「0.22更近C」是數值一致性佐證，不能當作獨立證明正式 Table A.9 正值。**

## 實際數值

| 同源輸入集合 | slope frames | N′ 有改變的 frames | 兩版 max ΔN（時間加權前，sone） | 兩版 max ΔN′（sone/Bark） | 加權輸出 max ΔN（sone） |
|---|---:|---:|---:|---:|---:|
| 定向／控制 | 29 | 7 | 0.016 | 0.01000000000000012 | 不適用 |
| Annex B 1 | 1 | 0 | 0 | 0 | 不適用 |
| Annex B 10 | 2,000 | 0 | 0 | 0 | 0 |
| Annex B 14 | 26,310 | 8,614 | 0.021 | 0.015942575797156577 | 0.007095731984794185 |

最容易解讀的定向案例：僅 `nm[4]=0.35`，其餘為零：

| 指標 | 0.24 版 | 0.22 版 | 官方 C（同 nm） |
|---|---:|---:|---:|
| N，sone | 0.805 | 0.811 | 0.810818895244731 |
| 對 C max N′ 絕對差 | 0.004022006138603207 | 0.00002200634721954975 | — |

這表示定向案例可觀察到 0.22 更接近 C；但 0.24 的最大 N′ 差僅約 0.004，遠低於 0.1 floor，故兩者仍同時通過這項容差診斷。鄰頻 band3=0.35 與平坦0.35控制的兩版差為零。

選定真實信號的共同輸出格點，對保存完整 C reference 的結果：

| 信號 | 0.24 max N 差 | 0.22 max N 差 | 0.24／0.22 max N′ 差 | 超出 max 容差點數 |
|---|---:|---:|---:|---:|
| 1 | 0.0043395756 | 0.0043395756 | 0.0002799992／同值 | 兩版均 0 |
| 10 | 0.0001606797 | 0.0001606797 | 0.0039162645／同值 | 兩版均 0 |
| 14 | 0.0150847089 | 0.0128375944 | 0.0508231749／同值 | 兩版均 0 |

Signal 14 的最大 N′ C 殘差位置不受此格主導，所以改格後全域最大 N′ 殘差相同，不代表該信號沒有受影響。其 0.24／0.22 兩版各有 6,578 輸出 frames，保存 C 為 6,577；上表僅比較共同的 6,577，額外尾點未作完整一致性接受。

本次 0.24 baseline 對前輪 Rust 輸出：三案 N 完全相同；N′ max 差分別為 0、1.38e-14、1.46e-12（本輪 scalar 對前輪 avx2）。這將敏感度與原有結果連接起來，但不冒稱比響度逐 bit 相同。

## 既有測試應如何解讀

主代理本輪重讀 F-02 `AnnexB深入分析.json`，確認已有 25 案與 84 workbook judgments，strict/hard exceptions 均為零；`5450d39` 至本 HEAD 的 `iso532/src` 無差異。這是**重讀前輪證據**，不是本輪重跑全 25 案。前輪仍有 8 個輸出 shape 差異及既有 unresolved 項，不能寫成全面 ISO 接受。

本輪僅用 3 個 Annex B 輸入敏感度實驗，不能聲稱其餘 22 案換成0.22仍通過，也不能將觀測最大差當所有可能輸入的最大誤差界限。它已足以展示兩種情況：一些訊號不敏感（1／10），另一些訊號敏感但仍容許兩種值（14）。因此「現有測試全綠」缺乏區分係數的充分能力。

以 MoSQITo 產生的 golden 若期待0.24，改成0.22可能破壞既有 parity；那證明與 MoSQITo 不同，不能單獨證明違反 ISO。反之，接近官方 C 支持與該參考實作一致，也不回答作者看過哪份標準或2017更正原因。正式改表門檻維持不變。

## 交付與重現

`summary.json` 保留完整數值摘要、每個定向 nm、輸入／中間量／保存 C reference hashes。`analyze.py` 與 `probe-main.rs.txt` 是實際執行腳本及 Rust probe；`prepare.py` 可從受驗快照與只讀前輪來源建新隔離目錄。先建立新 destination（不得覆蓋舊run），以 MSVC 開發環境在其 `c` 目錄執行 `cl /nologo /O2 /fp:precise /LD /I. ISO_532-1.c /link /OUT:slopes.dll /EXPORT:f_calc_slopes`；再 `cargo build --release --offline --manifest-path <PROBE>/Cargo.toml`，執行 `python <PROBE>/analyze.py --prior-work <PRIOR_WORK> --probe-root <PROBE> --out <NEW_RUN>`。

實際首次 release 編譯成功；MSVC 初始化有 `vswhere.exe` 不在 PATH 的提醒，隨後 x64 環境與編譯成功、退出0，DLL成功載入使用。初輪 run1 完成；增加對既有完整輸出比對後重跑 run2，作為本交付 summary。未跑全套 cargo test／benchmark，因正式程式沒有變更，這是定向證據實驗而非產品驗收。完整binary輸出保留在本機 tmp，不進交付；去識別化結果見 delivery-check.md。
