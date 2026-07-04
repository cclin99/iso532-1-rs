# Phase 1 TDD/BDD：基礎建設（骨架、工具鏈、常數表）

**對應計畫：** [plans/phases/phase-1-foundation.md](../plans/phases/phase-1-foundation.md)（主計畫 Task 1–3）　**狀態：** ✅ 已實作
**測試檔：** `iso532/src/tables.rs`（`#[cfg(test)]` sanity）＋工具鏈行為驗收（無 Rust 測試檔，靠腳本輸出）

## 1. 測試策略摘要

Phase 1 幾乎沒有業務邏輯，**驗證重心是「後續 phase 的地基是否可信」**，分三層：

1. **工具鏈行為**：`setup_env.sh`、`gen_golden.py`、`gen_tables.py` 能跑完並產出結構正確的檔案。這些是 shell/Python 腳本，用「執行後檢查產物」驗證，不寫 Rust 測試。
2. **常數表轉錄完整性**：`tables.rs` 手工轉錄自 mosqito，錯字**不會**在本 phase 被數值測試抓到（要到 Phase 2/3 的 golden 才爆）。因此本 phase 只做 shape + 抽樣點 sanity（`table_shapes_and_spot_values`），把「明顯貼錯位置／少一列」擋在最前面。
3. **可編譯性**：`tables_noct.rs`（生成物）掛進 `lib.rs` 後 `cargo test` 能編譯——證明 scipy 生成的 SOS 字面值是合法 Rust。

> ⚠️ 本 phase 綠燈**不代表**常數值正確，只代表「形狀對、能編譯、工具鏈通」。數值正確性由 Phase 2/3 的 mosqito golden 反向保證。

## 2. BDD 行為情境（Gherkin）

### Feature: 環境與 Annex B 測試資料（setup_env.sh）

```gherkin
Scenario: 建立 venv 並安裝 mosqito 1.2.1
  Given repo 根有本地 mosqito-1.2.1.tar.gz
  When 執行 bash tools/setup_env.sh
  Then .venv 建立成功
  And 印出 "mosqito OK" 與 scipy / numpy 版本

Scenario: 抓取 ISO Annex B 官方測試訊號
  Given 有網路可 clone MoSQITo v1.2.1 repo
  When setup_env.sh 執行完畢
  Then data/annexb/ 內含 Test signal 3 (44.1kHz)、5、10 的 wav
  And 對應 test_signal_*.csv 與時變 xlsx 參考檔

Scenario: 無網路時誠實中止
  Given 無法 clone MoSQITo repo
  When setup_env.sh 嘗試抓資料
  Then 腳本停下回報錯誤
  And 不產生任何假造的 wav/csv（絕不造假資料）
```

### Feature: 逐階段 golden 產生器（gen_golden.py）

```gherkin
Scenario: 每個合成與 Annex B 訊號都產出完整逐階段 golden
  Given .venv 已就緒且 data/annexb/ 存在
  When 執行 .venv/Scripts/python tools/gen_golden.py
  Then data/golden/<signal>/ 內每個 pipeline 階段都有 .bin
  And meta.json 記錄 N shape=[1]、N_specific=[240]、third_octave_level=[28, n_time]
  And 每個訊號印出 "done <name>"

Scenario: Test signal 3 檔名勘誤（Phase 1 審查發現）
  Given repo 只有 "Test signal 3 (1 kHz 60 dB)_44100Hz.wav"（無 48kHz 版）
  When gen_golden.py 以正確檔名載入（mosqito load() 自動重採樣到 48kHz）
  Then data/golden/annexb_sig3/ 成功產出（不再被靜默跳過）
  And N.bin ≈ 4.05（實測 4.052；ISO 參考值 4.019）

Scenario: golden 數量級 sanity
  Given sine_1k_60 的 golden 已產出
  When 讀取 data/golden/sine_1k_60/N.bin
  Then N ≈ 4.09 sone（1 kHz 60 dB ≈ 4 sone 量級即合理）
```

### Feature: 常數表（tables.rs 手工轉錄 + tables_noct.rs 生成）

```gherkin
Scenario: ISO 常數表形狀與抽樣點正確
  Given tables.rs 由 mosqito 原始檔逐值轉錄
  When 執行 cargo test table_shapes_and_spot_values
  Then DLL[0][0]==-32.0 且 DLL[7][10]==0.0
  And USL[17][7]==0.02 且 USL[16][7]==0.05
  And ZUP[20]==24.0 且 RNS[16]==0.035
  And TOB_GAIN[27]==3.91006e-3 且 TOB_DELTA[27][1][1]==2.76470e-1

Scenario: scipy 生成的 noct 濾波器係數可編譯且降採樣因子合理
  Given tools/gen_tables.py 用 scipy 生成 tables_noct.rs
  When 掛進 lib.rs 後 cargo test
  Then 編譯成功（repr(float) 產生的字面值皆合法 Rust）
  And NOCT_DECIM_Q 前 10 帶 > 1、其餘為 1
```

## 3. TDD 測試清單（RED→GREEN）

| 測試名 | 檔案 | 輸入 | 預期 | 容差 | 對應 Task |
|---|---|---|---|---|---|
| `table_shapes_and_spot_values` | `src/tables.rs` (`#[cfg(test)]`) | 常數字面值 | 8 個抽樣點等值 | `assert_eq!`（精確）| Task 3 |
| （工具鏈）setup_env 產物檢查 | 手動／CI | `bash tools/setup_env.sh` | `data/annexb/` 齊全 | 檔案存在性 | Task 2 |
| （工具鏈）gen_golden 產物檢查 | 手動／CI | `python tools/gen_golden.py` | 各 signal 逐階段 `.bin` + meta.json | shape 相符 | Task 2 |
| （工具鏈）gen_tables 生成＋編譯 | 手動／CI | `python tools/gen_tables.py` | `tables_noct.rs` 可編譯 | `cargo test` 綠 | Task 3 |

> 本 phase 唯一的 Rust 單元測試是 `table_shapes_and_spot_values`；其餘為腳本產物驗收（無 assert，但為後續所有 golden 測試的前置條件）。

## 4. 已知差異風險 / 排查順序

1. **Test signal 3 檔名**（已修）：repo v1.2.1 只有 `_44100Hz` 版；用 48kHz 檔名會讓 `annexb_sig3/` 被**靜默跳過**。gen_golden.py 檔名須為 `Test signal 3 (1 kHz 60 dB)_44100Hz.wav`。
2. **tables.rs 轉錄錯字**：本 phase 抓不到細部錯字，只擋得住形狀/貼位錯誤；逐值對照 mosqito 原始檔是唯一防線，真正的網由 Phase 2/3 golden 補上。
3. **repr(float) 字面值格式**：scipy → `repr(float(v))` 可能產生 `1e-05` 形式，Rust 接受；生成後掃一眼確認無非法字面。

## 5. 驗收對照

```bash
bash tools/setup_env.sh                      # data/annexb/ 有 wav+csv+xlsx
.venv/Scripts/python tools/gen_golden.py     # data/golden/<signal>/ 齊全
.venv/Scripts/python tools/gen_tables.py     # tables_noct.rs 生成且可編譯
cd iso532 && cargo test                      # 含 table_shapes_and_spot_values 全過
```

抽查：`data/golden/sine_1k_60/N.bin` ≈ 4.09；`NOCT_DECIM_Q` 前 10 帶 > 1。詳見 [plans/phase-1](../plans/phases/phase-1-foundation.md)。
