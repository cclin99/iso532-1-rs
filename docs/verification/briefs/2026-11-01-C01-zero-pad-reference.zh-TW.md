# 驗證交辦簡報：C-01，為尾端輸出點建立官方 C library 參考值

> 對照／Pair: [English](2026-11-01-C01-zero-pad-reference.md) · 來源：zh · 同步 2026-11-01

對象：Astra（`gpt-6-astra`）。2026-11-01（Asia/Taipei）由主代理依使用者決定「使用 ceil 方式」（保留 ceil，即 `docs/C01-OUTPUT-LENGTH-DECISION-2026-10-31.zh-TW.md` §4 上策）發出。數值驗收輪；不改程式。

## 1. 問題

Rust 的 batch 與 stream 回傳 `ceil(ceil(L/24)/4)` 個點。Annex B 訊號 18、23、24、25（`floor(L/24)` 是 4 的倍數且 `L mod 24 > 0`）的最後一個 Rust 點是內部幀 `K = floor(L/24)`，官方 Annex A C library 永遠不會輸出這一幀，因為它的幀數是整數除法 `NumSamples / DecFactor`。所以這四個點目前沒有官方預期值（備忘 §2.1）。本庫已證明（備忘 §2.2，現為 `iso532/tests/output_grid.rs`）第 `j` 點的值只取決於 index `≤ 96j` 的樣本，因此只要把輸入補零到至少 `24(K+1)` 個樣本，官方 C library 就會算出完全相同的第 `K` 幀。

請以補零輸入的官方 C library 為這四個點各建立一個獨立預期值，並說明 Rust 值是否在捨入層級一致。

## 2. 範圍

1. 以 2026-10-31 各輪相同的工具鏈與旗標編譯封存的官方 C 程式（`ISO_532-1.c`，SHA-256 `a74b45ed297cd09ac60701a923120341137d227e536f3109ae4ece810d834491`）；記錄編譯器、版本、旗標與二進位 hash。
2. 對訊號 18、23、24、25 各自：讀入 Annex B WAV，補零到「下一個 96 的倍數再加 96」個樣本（讓 C library 輸出第 `K` 幀以後的幀），以時變模式執行 C 程式（自由場，與 Annex B 相同），從 specific 與 total 輸出讀出第 `K` 幀（specific 檔第 `K/4` 列；total 檔經 CLI 的 `floor` 再抽取後若存在則一併記錄）。
3. 與 Rust 在同一點的值比較：對**未補零**訊號執行 `loudness_zwtv`（目前 `main`，記錄 commit）取 `n[frames-1]` 與 `n_specific[.., frames-1]`。回報每點的絕對差與 240 個 Bark 步的最大差；驗收目標是捨入層級，即與已驗證的第 14–17 點同級（`≤ 1e-14` sone，備忘 §2.1）；Annex B 容差 `max(0.1, 0.05·|ref|)` 只作為退一步的陳述。
4. 負對照：證明補零也不會改變 C 輸出較早的點（補零與未補零兩次 C 執行的第 `0..K-1` 幀完全相同），以確認補零執行是合法參考而不是另一個訊號。
5. 契約測試的長度邊界對照：取一個基底訊號，對長度 `L ∈ {4800, 4801, 4823, 4824, 4825, 4895, 4896, 4897}` 記錄 C library 幀數（`floor(L/24)`）、CLI total 與 specific 點數、Rust 點數，確認備忘 §2 的表格。

範圍外：更改任何輸出格線、golden 或測試；穩態模式；F-03。

## 3. 證據規則

- 每個數字都由交付資料夾內的腳本產生，且可由記錄的 commit、C 二進位 hash 與 Annex B WAV hash 重現。
- Rust 的點同時以 bits（`f64::to_bits` 十六進位）與十進位回報，使比較不依賴列印精度。
- 本輪不以 MoSQITo 為參考；若有差異一律寫「發現／目前判斷」，不寫 bug。
- 若 C library 無法輸出第 `K` 幀（例如有隱藏的長度檢查），如實說明並停止；不得以其他實作的值替代。

## 4. 交付

- 資料夾：`docs/verification/2026-11-01-C01-zero-pad-<受驗 commit>/`，`<受驗 commit>` 為該輪當時的 `git rev-parse --short HEAD`；不得覆蓋舊資料夾。
- 檔案：`report.md`（繁體中文）與 `report.en.md`（英文），結構與數字相同；`results.json`（每訊號：L、K、frames、C 值、Rust 值與 bits、|diff|、specific 最大 |diff|）；執行腳本；`delivery-check.md`。
- 交付前：`python tools/redact_paths.py <資料夾>` 再 `python tools/redact_paths.py --check <資料夾>`；把輸出（含 skipped 與警告）記在 `delivery-check.md`。資料夾內只放 UTF-8 文字檔；C 二進位與 WAV 不進庫（只記 hash）。
- 每點的結論用語：AGREES（捨入層級）、WITHIN TOLERANCE（僅 Annex B 規則）、DIFFERS、NOT OBTAINABLE。

## 5. 背景文件

- `docs/C01-OUTPUT-LENGTH-DECISION-2026-10-31.zh-TW.md`（與 `.md`）：三套規則、各情況、§2.2 量測、決策。
- `iso532/tests/output_grid.rs`：釘住點數、時間軸與前綴決定性的契約測試。
- `docs/修正報告2.md` §11.4 與 §12.2 C-01 列：原始稽核發現與驗收項。
- `docs/verification/README.md`：交付慣例與先前各輪。
