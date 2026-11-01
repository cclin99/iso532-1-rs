# 驗證交辦簡報：C-01，為尾端輸出點建立官方 C library 參考值

> 對照／Pair: [English](2026-11-01-C01-zero-pad-reference.md) · 來源：zh · 同步 2026-11-01

對象：Astra（`gpt-6-astra`）。2026-11-01（Asia/Taipei）由主代理依使用者決定「使用 ceil 方式」（保留 ceil，即 `docs/C01-OUTPUT-LENGTH-DECISION-2026-10-31.zh-TW.md` §4 上策）發出。數值驗收輪；不改程式。

## 1. 問題

Rust 的 batch 與 stream 回傳 `ceil(ceil(L/24)/4)` 個點。Annex B 訊號 18、23、24、25（`floor(L/24)` 是 4 的倍數且 `L mod 24 > 0`）的最後一個 Rust 點是內部幀 `K = floor(L/24)`，官方 Annex A C library 永遠不會輸出這一幀，因為它的幀數是整數除法 `NumSamples / DecFactor`。所以這四個點目前沒有官方預期值（備忘 §2.1）。本庫已證明（備忘 §2.2，現為 `iso532/tests/output_grid.rs`）第 `j` 點的值只取決於 index `≤ 96j` 的樣本，因此只要把輸入補零到至少 `24(K+1)` 個樣本，官方 C library 就會算出完全相同的第 `K` 幀。

請以補零輸入的官方 C library 為這四個點各建立一個獨立預期值，並說明 Rust 值是否在捨入層級一致。

## 2. 範圍

1. 以 2026-10-31 各輪相同的工具鏈與旗標編譯封存的官方 C 程式（`ISO_532-1.c`，SHA-256 `a74b45ed297cd09ac60701a923120341137d227e536f3109ae4ece810d834491`）；記錄編譯器、版本、旗標與二進位 hash。
2. 對訊號 18、23、24、25 各自：讀入 Annex B WAV，補零到 `L_pad = 96 * (ceil(L/96) + 1)` 個樣本，以時變模式、48 kHz、自由場執行官方 C library。直接擷取未抽取的 total 與 240 個 specific 值之第 `K` 幀；CLI 輸出另作格線與序列化對照。索引與精度要求見 §2.1。
3. 與 Rust 在同一點的值比較：對**未補零**訊號執行固定受驗快照的 `loudness_zwtv`，取 `n[frames-1]` 與 `n_specific[b * frames + frames-1]`（`b = 0..239`）。回報 total 絕對差與 240 個 Bark 步各自的差及最大差；驗收目標為 total `≤ 1e-14` sone、specific 最大絕對差 `≤ 1e-14` sone/Bark。這是本輪沿用備忘 §2.1 的捨入層級門檻，不是宣稱 IEEE 位元一致。Annex B 容差 `max(0.1, 0.05·|ref|)` 只作為退一步的陳述。
4. 負對照／不變性對照：比較補零與未補零兩次 C library 執行的**全部**內部幀 `0 ≤ k < K`，分別記錄 total 與 specific 的比較數、位元不一致數、最大差與首個差異座標；不能用每 4 幀抽取的 CLI 檔代替全部幀。預期完全相同；失敗時不得宣稱補零參考已驗收。
5. 契約測試的長度邊界對照：取一個基底訊號，對長度 `L ∈ {4800, 4801, 4823, 4824, 4825, 4895, 4896, 4897}` 記錄 C library 幀數（`floor(L/24)`）、CLI total 與 specific 點數、Rust 點數，確認備忘 §2 的表格。

範圍外：更改任何輸出格線、golden 或測試；穩態模式；F-03。

### 2.1 索引、輸入與精度

- 全部索引從 0 起算。`K = floor(L/24)` 永遠由**原始**長度決定；確認 `K mod 4 = 0`、`L mod 24 > 0`。目標輸出點 `j = K/4 = frames-1`，時間 `t = 24K/48000 = 96j/48000` 秒。CLI total 與 specific 對應的都是資料列 `j`（排除標頭），不是 total 的第 `K` 列。
- 上述補零長度確保 CLI total 也包含 `j`；若實測缺列，記錄異常，不能靜默略過。C library 第 `K` 幀才是數值參考；CLI 的文字捨入不能用來判定 `1e-14` 層級一致。
- 使用獨立 harness 讀取 C library 計算完成、CLI 序列化之前的陣列。可新增只負責呼叫／輸出的 wrapper；不得改官方演算法、常數、迴圈邊界或原檔。交付 wrapper、建置命令及 hash；如必須調整 export 或入口，交付完整轉換腳本與 diff，並證明計算本體未變。
- 記錄 WAV 格式、聲道、原始樣本數、PCM 解碼與聲壓校準方式。C 與 Rust 必須收到相同的原始聲壓樣本；補零只附加於尾端，不重採樣、不重新正規化。保存原始 WAV、解碼樣本與補零樣本的 hash 及其編碼定義。
- C 與 Rust 的 total 及全部 240 個 specific 值均保留可往返的十進位（至少 17 位有效數字）與 IEEE-754 binary64 bits。先驗有限值與陣列形狀，再算誤差；NaN／Infinity 不得通過比較。
- 比較器負對照：對參考值副本的一個有限值注入大於門檻的偏移，要求同一比較器判為非 AGREES 並指出座標；原始證據不得改寫。這與上一項的補零不變性對照分開記錄。

### 2.2 長度邊界的預期值

以下是公式預期值，**不是已執行結果**。固定同一個至少 4897 樣本的基底訊號及 hash，各列取其前 `L` 樣本。另列 C library 與 CLI 的實測值，以及 Rust `n`、`n_specific`、`time_axis` 的實測長度；specific 元素數應為 `240 * frames`。

| L | C library 幀數 | CLI total 點數 | CLI specific 點數 | Rust 點數 |
|---:|---:|---:|---:|---:|
| 4800 | 200 | 50 | 50 | 50 |
| 4801 | 200 | 50 | 50 | 51 |
| 4823 | 200 | 50 | 50 | 51 |
| 4824 | 201 | 50 | 51 | 51 |
| 4825 | 201 | 50 | 51 | 51 |
| 4895 | 203 | 50 | 51 | 51 |
| 4896 | 204 | 51 | 51 | 51 |
| 4897 | 204 | 51 | 51 | 52 |

## 3. 證據規則

- 每個數字都由交付資料夾內的腳本產生，且可由記錄的 commit、C 二進位 hash 與 Annex B WAV hash 重現。
- 開始前固定完整 commit、短 commit、工作樹狀態與受驗來源 hash；不得追蹤移動中的 `main`。本簡報修訂時的 HEAD 為 `d0bd38bba540f6b3f2414737c08c3c33c6a8c558`，僅供定位，不是本輪已驗證證據。若工作樹含未提交變更，從固定 commit 建立隔離快照；新增 harness 與受驗來源分開記錄。
- Rust 的點同時以 bits（`f64::to_bits` 十六進位）與十進位回報，使比較不依賴列印精度。
- 本輪不以 MoSQITo 為參考；若有差異一律寫「發現／目前判斷」，不寫 bug。
- 若 C library 無法輸出第 `K` 幀（例如有隱藏的長度檢查），如實說明並停止；不得以其他實作的值替代。

## 4. 交付

- 資料夾：`docs/verification/2026-11-01-C01-zero-pad-<受驗 commit>/`，`<受驗 commit>` 為該輪當時的 `git rev-parse --short HEAD`；不得覆蓋舊資料夾。
- 檔案：`report.md`（繁體中文）與 `report.en.md`（英文），結構與數字相同；`results.json`（每訊號：L、K、frames、C 值、Rust 值與 bits、|diff|、specific 最大 |diff|）；執行腳本；`delivery-check.md`。
- `results.json` 另含 `L_pad`、`j`、時間、全部 specific 值與 bits、兩種負對照、八列長度實測、有限值／形狀檢查、各 gate 狀態。交付命令、版本、建置與執行日誌、退出碼、來源／輸入 hash 清單，以及去識別化後的 `delivery-integrity.json`。
- 交付前：`python tools/redact_paths.py <資料夾>` 再 `python tools/redact_paths.py --check <資料夾>`；把輸出（含 skipped 與警告）記在 `delivery-check.md`。資料夾內只放 UTF-8 文字檔；C 二進位與 WAV 不進庫（只記 hash）。
- 逐檔盤點工具未涵蓋的副檔名與非 UTF-8 檔，另行檢查；無警告或退出碼 0 不能代表全部格式已檢查。檢視交付 diff，涵蓋報告、腳本、命令、日誌、清單。日誌寫入完成後重跑去識別化與 `--check`，再產生完整性清單；清單記錄最終檔案 hash 並明確排除自身。若再修改檔案，須重做檢查與 hash。原始輸入／binary／受驗來源 hash 保留原義，不冒稱去識別化副本與原檔位元相同。
- 每點的結論用語：AGREES（捨入層級）、WITHIN TOLERANCE（僅 Annex B 規則）、DIFFERS、NOT OBTAINABLE。
- 四個訊號的 total 與 specific 均達 AGREES、兩種負對照與八列邊界全部通過，才可建議 C-01 本輪數值驗收結案。另列 passed／failed／blocked／skipped／partial；缺資料、建置失敗或無法取得完整精度值時保留缺口，不以歷史結果補成 passed。報告交付不自動修改稽核結案列，也不包含 commit／push。

## 5. 背景文件

- `docs/C01-OUTPUT-LENGTH-DECISION-2026-10-31.zh-TW.md`（與 `.md`）：三套規則、各情況、§2.2 量測、決策。
- `iso532/tests/output_grid.rs`：釘住點數、時間軸與前綴決定性的契約測試。
- `docs/修正報告2.md` §11.4 與 §12.2 C-01 列：原始稽核發現與驗收項。
- `docs/verification/README.md`：交付慣例與先前各輪。
