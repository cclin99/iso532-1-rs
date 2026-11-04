# 0.4.0 發布前獨立驗收

結論：**PARTIAL**。未發現數值或 API 回歸的發布阻擋項。公開串流 API 原本不提供比響度，該項要求仍無法驗證；紀錄一致性因 commit 表漏列一筆而未通過。兩者不構成產品回歸證據，但不能宣稱九項無條件全部完成。本輪未 tag、push、commit、stage 或執行 GitHub CI。

Astra (`gpt-6-astra`), 2026-11-04 Asia/Taipei. `fca4ccda18a8fbada77031425e5e683f1acd5a8d` (`fca4ccd`).

| §2 | Status | Evidence |
|---|---|---|
| 1 | PASSED | [source-integrity.json](source-integrity.json) |
| 2 | PASSED | [golden-results.json](golden-results.json) |
| 3 | PASSED | [gates/gates-results.json](gates/gates-results.json) |
| 4 | PASSED | [numeric-results.json](numeric-results.json) |
| 5 | PASSED | [diagnostic-controls.json](diagnostic-controls.json) |
| 6 | PARTIAL | [contracts/contracts-results.json](contracts/contracts-results.json) |
| 7 | PASSED | [gates/gates-results.json](gates/gates-results.json) |
| 8 | PASSED | [gates/mosqito-measurements.json](gates/mosqito-measurements.json) |
| 9 | FAILED | [release-numeric-comparison.json](release-numeric-comparison.json) |

## 1. Freeze / 凍結

從 git archive 建置，未追蹤 main。candidate／Round 1／baseline 共 560／560／394 個追蹤檔，執行後均與 archive 位元相同。主樹 HEAD 為 `7900035c7ac318d789310fe817552a413c154b41`；原追蹤樹乾淨，只有本交付資料夾新增未追蹤。來源 hash 見 [source-integrity.json](source-integrity.json)。Rust/Cargo 1.99.1、Python 3.11.9、NumPy 2.4.6、maturin 1.14.1、MSVC 19.44.35228 x64 `/O2 /fp:precise`；完整 Python 套件與 Linux 工具鏈見 gates logs。

## 2. C golden

123 個二進位資料檔全部重現凍結 manifest。官方來源與只改一格的版本 hash 符合簡報，正規化 diff 符合提交版本。錯來源負控制退出 1。發現：metadata 除生成時間，兩 DLL hash 與替換 diff hash（archive CRLF 對原生成器產生的 LF）亦不同，不能寫「只有日期不同」。原 metadata hash 符合凍結 manifest；資料檔位元不受影響。見 [golden-meta-differences.json](golden-meta-differences.json)。

## 3. Gates

Workspace：146 passed、0 failed、3 ignored。全新 wheel／venv，`ISO532_REQUIRE_PARITY=1`：87 passed、0 xfailed。fmt、兩項 clippy、指定測試、文件配對、docs 去識別檢查與 benchmark 編譯通過。Linux lib 30、hash 1、contract dump 1、CI 子集 29 通過。初始環境失敗（離線 pip、缺 matplotlib 依賴、Docker pipe 權限）已修復重跑，與最終產品結果分開保留。

## 4. F-04 / F-05 / F-06 / F-07

獨立 C wrapper 呼叫官方入口，外部 Rust CLI 呼叫凍結 crate。SIG18 cell 36 等於 nm[4] = 0.8138793716641407，cell 35 = 0.8201342464748338；總量 bits `401fc356fc47a15a` 與 Round 1 相同。SIG23 總量 4.7508434035893385。只有 band 20 非零時總量為 0.3999999999999986（`24.0-23.6`，數學 0.4 的 binary64 計算結果），第一 band 各格全 0。13 序列最大總量差 2.71180278250682250e-05、比響度差 2.09972652732481890e-04；四尾點最大差 8.98730629847466211e-11／3.25986050435033438e-23。九組頻帶位準穩態最大差 1.52994289734920130e-05／1.50002845644259253e-04。所有驗收門檻通過。

| Signal | N max | Specific max | Round 1 specific max |
|---|---:|---:|---:|
| annexb_c01_sig18 | 6.613789616e-06 | 9.396542937e-05 | 4.377285282e-02 |
| annexb_c01_sig23 | 3.248153462e-07 | 8.248619202e-05 | 3.508193084e-02 |
| annexb_c01_sig24 | 1.753251574e-06 | 6.217173584e-05 | 3.485164721e-02 |
| annexb_c01_sig25 | 7.781257789e-07 | 8.249086827e-05 | 2.639265176e-02 |
| annexb_sig10 | 9.794874511e-08 | 1.097084125e-04 | 3.842240067e-03 |
| annexb_sig3 | 1.471770910e-07 | 6.183566522e-05 | 3.526614607e-03 |
| annexb_sig5 | 2.711802783e-05 | 6.235161843e-05 | 3.147031276e-02 |
| pulse_1k_70 | 1.464543375e-07 | 1.097089178e-04 | 1.286871240e-02 |
| sine_1k_60 | 1.471443349e-07 | 6.183565230e-05 | 3.582281567e-03 |
| sine_250_80 | 2.022091941e-05 | 2.099726527e-04 | 2.495591954e-03 |
| sine_4k_60 | 4.987334279e-08 | 8.213898854e-05 | 2.867147115e-03 |
| step_60_80 | 1.645393574e-06 | 1.297287710e-04 | 2.208874236e-02 |
| white_60 | 1.915379471e-06 | 6.235281873e-05 | 3.111792681e-02 |

Round 1 對 candidate：24 個 Annex B WAV（訊號 15 為 diffuse）加 3 秒 contract，共 70219 幀；N／time 位元差均為 0。比響度 16902 格改變，全部在 after-segment 分支，分支外為 0。排序後首差：訊號 2、Bark cell 72／frame 5。完整座標與 f64 hex 見 numeric-results.json。來源衍生追蹤只作變更定位輔證，不當作獨立 C 真值。

## 5. Diagnostic / 診斷

給定相同 Rust NL 向量，epsilon=0／slope 表 binary64 的 C 總量最大差 1.42108547152020037e-14，重現先前 slope 階段宣稱（並非完整 pipeline 宣稱）。發現：比響度最大差 4.25633562081179928e+00；拿掉 epsilon 後格點歸屬改變，因 9 次 float32 0.1 累加為 0.9000000134110451 > 0.9。純診斷控制只改格線為整數索引／10，比響度最大差降至 1.26565424807267846e-14，總量不變。整份 C 常數全改 binary64，端到端總量最大差 5.91793281046193442e-11，不證明端到端 1.5e-14。交付 diff、座標與 hash；各診斷版均不取代授權的 0.24f 參考。

## 6. Contracts / 契約

兩版官方參考點均 73,116／73,116 通過，最小餘裕 0.059702781183555126（訊號 2、比響度 1.0 Bark、工作表 G17）。四訊號自訂 chunk、每版 4,136 幀，N 與推導時間位元差為 0。七組格線與九個 DLL exports 相同，header 位元相同。補充 FFI panic 測試 17／17 與 C smoke 通過；cbindgen 0.29.4 再生僅行尾不同，LF 正規化後相同。發現／缺口：兩版公開 StreamFrame 均無比響度及浮點 time_axis；時間由 frame index 推導。無法驗公開 stream-specific 相等。此為既有能力缺口，不是回歸或獨立發布阻擋。工作簿衍生 Nmax／N5 摘要未納入參考點數。

## 7. Hashes / 雜湊

Windows 與 Linux 各四組 scalar／AVX2 × zero／mosqito_tail 的 N／specific／time 均與平台凍結值完全相同。Windows wheel 的 Python N／time hash 亦相同。四組 Windows Round 1 specific 舊 hash 已於獨立 target 重跑且符合舊表；初次共享 target 的快取結果被排除為無效證據，無須動用 CPU／UCRT 差異容許。期望與實測 hex 見 gates-results.json。

## 8. MoSQITo

僅為相容性對照，不作正確性權威。九組 fixture：時變總量最大差 3.94196712451133635e-03、穩態總量 4.88005984661032954e-04，均低於 5e-3。比響度最大差 3.14702989925296772e-02（時變 annexb_sig5）與 7.95965803937281891e-03（穩態 annexb_sig5）重現紀錄；比響度不設驗收門檻。

## 9. Record consistency / 紀錄一致性

版本、CITATION 已揭露例外、CHANGELOG 標記與 CI py hash 設定符合。C 表共 54 個數字（含 Round 1、穩態）均符合打印捨入；gate 計數與凍結 hash 重現。發現：release commit 表 12 筆只表示 11 筆，漏列 `5bbbb93228b9972c0277415bebd565364de974fc`，故本項 FAILED。另應修正 metadata 只有日期變動的描述，避免宣稱不可取得的公開 stream-specific 證據。歷史 RED 執行與過往 Linux 執行不冒稱重建歷史事件；本輪提供 candidate／隔離 Round 1／Linux 當前證據。此為文件發現，不是數值缺陷證據。

## 交付與界線

見 [replay.md](replay.md)、[delivery-check.md](delivery-check.md)、[delivery-integrity.json](delivery-integrity.json)。完整性清單 hash 對應去識別化交付位元並排除自身；來源／輸入／binary hash 保留原義。F-03 權威、穩態前端驗證、效能實測、發行封裝與遠端 CI 在範圍外。據此更新 release 獨立驗證節前應校正紀錄措辭，並保留串流缺口。
