# Release 紀錄：v0.4.0（2026-11-04）

> 對照／Pair: [English](RELEASE-0.4.0-2026-11-04.md) · 來源：zh · 同步 2026-11-05

**狀態：** Astra 對候選 `fca4ccd` 的獨立驗收已交付，結論 PARTIAL，無數值或 API 的發布阻擋項（見「獨立驗證」節）。tag `v0.4.0` 打在記錄本節的 commit，推送後的 CI 結果記在 tag 訊息。2026-11-05 推送 `main`，CI run 41929707757 六個 job 全綠，`v0.4.0` 打在 `118322f`；產出物與發布後確認見下方兩節。實作者：Claude Opus 5.5，依 [`superpowers/plans/phases/phase-0.4.0-slope-annexa.md`](superpowers/plans/phases/phase-0.4.0-slope-annexa.md) 與決策備忘 [`C01-F03-SLOPE-ALIGNMENT-DECISION-2026-11-03.zh-TW.md`](C01-F03-SLOPE-ALIGNMENT-DECISION-2026-11-03.zh-TW.md)（D1–D5，§7 修訂）。Round 1 起點 `5cb036a`（v0.3.1 之後的文件 commit）；Round 2 起點 `9301c0d`（第一輪驗證後的決策修訂）。

本次範圍：slope 階段（`calc_slopes_impl`）對齊 ISO 532-1:2017 Annex A，正確性參考由 MoSQITo 1.2.1 改為官方 Annex A C 程式。屬數值變更，依版號規則升 minor。API、輸出格線、串流契約、SIMD 分派、C ABI、Python shape 都不變；`USL[12][4]` 維持 0.24（F-03 暫定）。

## 自 v0.3.1 以來的 commit（本階段）

| commit | 內容 |
|---|---|
| `93ba5e4` | Round 1 Task 1：F-04／F-05／F-06 三個 RED 單元測試 |
| `d011921` | Round 1 Task 2：`calc_slopes_impl` 修正（刪除每幀捨入、Annex A band 補完、band 0 不讀 band 20） |
| `9d8ae5a` | Round 1 Task 3：契約與串流測試不變；`annexb.rs` 內 sig10 對 MoSQITo 的那一行改為相容性容差 |
| `777d8e8` | Round 1 Task 4：`tools/gen_golden_c.py`、`tools/golden-c-usl12-4.diff`、`tools/golden-c.sha256`、`tests/golden_c.rs` |
| `8beeb90` | Round 1 Task 5：MoSQITo golden 降為相容性對照、重凍 n hash、版號 0.4.0、CHANGELOG、README、F-03 狀態 |
| `2fc1708` | Round 1 Task 6：本紀錄初稿（兩語言） |
| `5bbbb93` | 英文決策備忘的配對行修正（只動文件） |
| `fe3d0b2`、`9301c0d` | 第一輪驗證後的決策修訂（F-07、C golden 分層門檻）與 Round 2 計畫 |
| `a1a261d` | Round 2 Task 7：F-07 的 RED 單元測試 |
| `0bb2272` | Round 2 Task 8：F-07 修正、`n_specific` hash 重凍、C golden 全序列門檻、MoSQITo specific 改為記錄、CI py job 的 `HASH_GATE_DUMP_ONLY` |
| `fca4ccd` | Round 2 Task 9：CHANGELOG、README、本紀錄（兩語言）；受驗的候選快照 |
| `7900035`、`b119d20`、後續 | 驗收簡報、獨立驗證輪交付（含只對該交付資料夾生效的 `.gitattributes`）、本節；只動文件與驗證證據。tag 處的 crate 原始碼與受驗的 `fca4ccd` 完全相同。 |

## 使用者看到的變化

- 每個總響度值都可能改變：不再每幀捨入到 0.001／0.01 sone（F-04）；約 1% 的時變幀因 band 補完（F-05）改變 1e-3 ～ 2.6e-2 sone（加權輸出後對 MoSQITo golden ≤ 3.9e-3 sone）。
- 比響度在「斜率段於格點取樣位置之前結束」的那一格改取包含取樣位置的那一段的值（F-07），例如訊號 18 第 1564 幀 3.7 Bark 由 0.77011 改為核心響度 0.81388。總響度不受影響（逐位元相同）。被補完 band 的下一 band 改從 `ZUP` 起算（F-05），其時變比響度也會改變。兩者合計，比響度對 Annex A C golden 全序列最大差由 4.4e-2 降到 2.1e-4 sone/Bark；對 MoSQITo 則依設計不同，時變最大 3.15e-2 sone/Bark（annexb_sig5）、穩態 7.96e-3（annexb_sig5）。
- 直接呼叫 `core::calc_slopes*` 且 `nm[20] > nm[0]` 時，不再出現負的 band-0 比響度（F-06）；經 pipeline 的輸入不受影響。
- `N(t)` 不再跨 OS／後端逐位元相同：scalar 與 AVX2 差最多 2.6e-10 sone。依賴 n 或 n_specific hash 的下游需逐平台重凍。

## 驗證（本機，`0bb2272` 狀態，Windows x64，rustc 1.99.1）

- `cargo fmt --all -- --check`、`cargo clippy --workspace --all-targets -- -D warnings`、`iso532-ffi` 的 `cargo clippy --all-targets --all-features -- -D warnings`：clean。
- `cargo test --workspace`：146 passed、0 failed、3 ignored（三個都是既有的手動 helper 或效能測試：`dump_zwtv_output_hashes`、`dump_py_bitwise_contract_hashes`、`silence_throughput_within_20pct_of_sine`）。`cargo bench --workspace --no-run`：通過。
- F-07：`f07_sample_after_segment_end_is_core_or_next_segment` 修正前 FAILED（`spec[36]` 0.770106544821296590 vs `nm[4]` 0.813879371664140705），修正後通過；該幀總響度修正前後逐位元相同（`0x401fc356fc47a15a`）。`f07_specific_matches_the_annex_a_reference_port`：官方 `f_calc_slopes` 的 binary64 移植（不含 band 邊界 epsilon）在 507 個幀上總響度與 240 格比響度都在 1e-9 內。
- `hash_gate.rs`：`n` 與 `time_axis` 各平台值都不變，只重凍 `n_specific`（舊新值見下表）。`golden_zwtv.rs` 的 AVX2 snapshot 同樣只改 `n_specific` 欄。
- Annex B：`annexb` 3、`annexb_validator` 24 全過；判定規則 `max(0.1, 0.05·|ref|)` 未改。
- Linux（`ubuntu:24.04` 容器，glibc 2.39，rustc 1.99.1，`0bb2272` 的 `git archive`）：`cargo test --lib` 30 passed；`hash_gate` 以新常數斷言通過；CI 測試子集加 `nl_zero_init` 全過；`py_contract_dump` 的 N hash 與 `test_smoke.py` 凍結值相同。
- Python（以 `0bb2272` 建置的 0.4.0 wheel，`ISO532_REQUIRE_PARITY=1`）：87 passed、0 xfailed。

| `hash_gate.rs` 的 `n_specific` | Round 1 | Round 2（F-07） |
|---|---|---|
| windows scalar | `0x16937b45e6e4155d` | `0x80e89aeeafaf2164` |
| windows avx2 | `0x3d4b4b2df9073e48` | `0x38b0cdbd447978d7` |
| windows scalar mosqito_tail | `0xff98c57f3018ef94` | `0xb2247c2f9f943399` |
| windows avx2 mosqito_tail | `0x3f241da3fe334097` | `0xced0f74f725403e1` |
| linux scalar | `0x05dc55b516e20132` | `0x3065b74438e81ca6` |
| linux avx2 | `0x197c1084aab28c59` | `0xe510c9ec5b5244c3` |
| linux scalar mosqito_tail | `0x6e181dac593b5fef` | `0x062926a7788343e3` |
| linux avx2 mosqito_tail | `0x8213780cd5384fb0` | `0x10130ca6b26aa5af` |

## 獨立驗證（Astra，`fca4ccd`）

2026-11-04 交付，受驗 commit `fca4ccd`，結論 **PARTIAL**：九項中七項 PASSED，沒有數值或 API 的發布阻擋項。報告：[`verification/2026-11-04-release-0.4.0-fca4ccd/report.md`](verification/2026-11-04-release-0.4.0-fca4ccd/report.md)（簡報：`verification/briefs/2026-11-04-release-0.4.0-acceptance.zh-TW.md`）。

- 凍結：以 git archive 建置 candidate／Round 1／baseline，共 560／560／394 個追蹤檔，執行後與 archive 位元相同。
- C golden：123 個資料檔全部重現 `tools/golden-c.sha256`；官方來源與單格替換版 hash 符合；給錯來源時工具退出 1。
- Gate：workspace 146 passed／0 failed／3 ignored；全新 venv 的 wheel 在 `ISO532_REQUIRE_PARITY=1` 下 87 passed、0 xfailed；fmt、兩種 clippy、文件配對、docs 去識別化、benchmark 編譯通過；Linux lib 30、hash 1、contract dump 1、CI 子集 29 通過。
- F-04～F-07 以獨立 C wrapper 與外部 Rust 程式驗證：訊號 18 第 1564 幀 cell 36 = `nm[4]` = 0.8138793716641407，總量 bits `401fc356fc47a15a` 與 Round 1 相同；訊號 23 第 3893 幀總量 4.7508434035893385；只有 band 20 非零時總量 0.3999999999999986（數學值 0.4 的 binary64 結果），band 0 全 0。13 個序列對 0.24f C golden 最大差：總響度 2.712e-5、比響度 2.100e-4；四個尾點 8.99e-11／3.26e-23；全部與上表一致。
- F-07 不動總響度：Round 1（`2fc1708`）對 `fca4ccd`，24 個 Annex B WAV 加 3 秒 contract 共 70,219 幀，`n` 與 `time_axis` 位元差 0；比響度 16,902 格改變，全部在 after-segment 分支。
- hash：Windows 與 Linux 各四組 scalar／AVX2 × zero／mosqito_tail 的 `n`、`n_specific`、`time_axis` 都與凍結值相同，不需動用 CPU／UCRT 差異容許；Windows wheel 的 Python N／time hash 也相同。
- MoSQITo：時變總響度最大差 3.94e-3、穩態 4.88e-4，均低於 5e-3；比響度記錄值 3.147e-2／7.960e-3 可重現。
- 契約（PARTIAL）：兩版的 Annex B 官方參考點都是 73,116／73,116 通過，最小餘裕 0.0597（訊號 2，1.0 Bark）；四個訊號的自訂 chunk 串流 `n` 與推導時間跟批次位元相同；七組格線、九個 DLL exports、header 與 v0.3.1 相同。缺口：公開 `StreamFrame` 沒有比響度，簡報要求的串流比響度相等無法驗證。這是既有能力缺口，不是回歸。
- 紀錄一致性（FAILED）：commit 表原本漏列 `5bbbb93`，已在本次補上。其餘版號、CITATION 例外、CHANGELOG、CI 設定，以及 C 表的 54 個數字都相符。

診斷發現（不是驗收門檻）：給定相同 NL 向量，C 端拿掉 `_ZUP` epsilon、slope 表改 binary64 後，總響度差 1.4e-14；但比響度差變成 4.26，因為 float32 的 `ZK += 0.1f` 累加 9 次是 0.9000000134110451 > 0.9，格點歸屬隨之改變。只把格線改成整數索引／10，比響度差就降到 1.3e-14。整份 C 常數改 binary64 的端到端總響度差是 5.9e-11，不能宣稱端到端 1.5e-14。另外，C golden 的 `meta.json` 跟凍結版本不只日期不同，兩個 DLL hash 和替換 diff 的行尾（CRLF 對 LF）也不同；資料檔位元不受影響。

範圍外：F-03 權威、穩態前端、效能實測、發行封裝、遠端 CI。

## 產出物（自 `v0.4.0` 建置，Windows x64，rustc 1.99.1，2026-11-05）

| 檔案 | SHA-256 |
|---|---|
| `iso532-0.4.0-cp39-abi3-win_amd64.whl` | `724b272c86ee35b27a51852674538adeeb1979143364de89c59b5476ad244cc0` |
| `iso532_ffi.dll` | `11a126257863df923e8ae41108fddb570f3f30a2bee0ed3be8c73b688d4ceb28` |
| `iso532_ffi.dll.lib` | `e5b7a8f812cd9e6d8be7a22f15dd0493ef3ebda7920757f3858d1e63026c05a9` |
| `iso532.h` | `0f548fd348cb0e3999ce8892bec05d4a5afd53740eb695428ad0eca9a45b709b` |

`iso532.h` 與 import library 跟 0.3.1 發布的檔案位元相同（header 取 tag 的 Git blob 原樣；匯出符號未變）。wheel 在全新 venv 以 `ISO532_REQUIRE_PARITY=1` 跑 `iso532-py/tests`：87 passed。PE 二進位內嵌建置資訊，在另一台機器重建不期望逐位元重現 DLL 與 wheel 的 hash。防毒掃描待手動；產出物未上傳。

## 發布後確認（2026-11-05，`v0.4.0`）

報告：[`verification/2026-11-05-perf-compliance-118322f/report.md`](verification/2026-11-05-perf-compliance-118322f/report.md)（主代理執行，非 Astra）。

- 效能：與 `v0.3.1` 同一 session 交錯 A/B，`calc_slopes` 階段本身慢 6%～12%（含比響度）／0%～4%（只算總響度）；端對端只有單核 batch 一致慢約 2%，其餘在約 ±4% 的輪間雜訊內；Python binding 3 秒處理時間兩版相同。README 效能表已改用本次量測。
- 標準對照：Annex B 25 個訊號、73,116 個工作簿參考點，0.4.0 與 0.3.1 都 0 個超出逐點判準，最小餘裕 0.0597 sone/Bark；20 個時變訊號的 Nmax 與 N5 在 max(0.1, 5%) 內（診斷，工作簿未訂容差），一致偏高約 0.15%，兩版差 ≤ 7e-4 sone。偏差已追查到聲壓換算：工作簿與固定的「滿刻度 1.0 = 2√2 Pa」吻合，而 Annex C 校準檔低 0.0226 dB；改用 2√2 後降到 ≤ 0.007%（[`verification/2026-11-05-annexb-bias-118322f/`](verification/2026-11-05-annexb-bias-118322f/report.md)）。N5 定義、恰好 1% 規則仍 UNRESOLVED，F-03 仍 PENDING。
- `CITATION.cff` 於 tag 之後補登為 0.4.0、`date-released: "2026-11-05"`（tag 本身仍是 0.3.1）；`message` 仍寫引用 MoSQITo 參考實作，是否改措辭待決。

## Annex A C golden（D4 修訂／D-D、D-G）

- 參考程式：官方 `ISO_532-1.c`（SHA-256 `a74b45ed297cd09ac60701a923120341137d227e536f3109ae4ece810d834491`），只把 `USL[12][4]` 由 `0.22f` 改為 `0.24f`（替換版 SHA-256 `739af24dee118027cb419fcdb051d8b56b274211d986140d66d7ff4b9d52a7e9`）；MSVC 19.44.35228 x64，`/O2 /fp:precise`；wrapper 只呼叫 `f_loudness_from_signal` 與 `f_loudness_from_levels`。Round 2 未改 C 端，`data/golden-c/` 沿用 Round 1 產出。
- 門檻分三層：C-01 尾點總響度與比響度 1e-10；全序列總響度 1e-4 sone；全序列比響度 3e-4 sone/Bark（F-07 後實測最大 2.100e-4 向上取到 1 位有效數字）。全序列殘差來自 C 程式的 `_ZUP += .0001f`、float32 格線累加 `ZK += 0.1f` 與其他 float32 常數（歸因見「獨立驗證」節的診斷）。
- C-01 尾點（Annex B 訊號 18／23／24／25 的最後一個輸出點），F-07 前後相同：

| 訊號 | Rust 0.4.0 − C golden（0.24f） | specific 最大差 | Rust 0.4.0 − 未修改 C（0.22f） |
|---|---|---|---|
| 18 | −6.61e-11 | 9.1e-24 | −1.43e-8 |
| 23 | −5.16e-11 | 3.3e-23 | −1.28e-7 |
| 24 | −8.99e-11 | 2.2e-23 | −9.33e-9 |
| 25 | −7.41e-11 | 4.7e-24 | −7.41e-11 |

- 全序列（時變，Rust 對 C golden 0.24f，AVX2 預設分派）：

| 訊號 | 總響度最大差（sone） | 比響度最大差（F-07 後） | 比響度最大差（F-07 前） |
|---|---:|---:|---:|
| sine_1k_60 | 1.471e-7 | 6.184e-5 | 3.582e-3 |
| sine_250_80 | 2.022e-5 | 2.100e-4 | 2.496e-3 |
| sine_4k_60 | 4.987e-8 | 8.214e-5 | 2.867e-3 |
| white_60 | 1.915e-6 | 6.235e-5 | 3.112e-2 |
| pulse_1k_70 | 1.465e-7 | 1.097e-4 | 1.287e-2 |
| step_60_80 | 1.645e-6 | 1.297e-4 | 2.209e-2 |
| annexb_sig3 | 1.472e-7 | 6.184e-5 | 3.527e-3 |
| annexb_sig5 | 2.712e-5 | 6.235e-5 | 3.147e-2 |
| annexb_sig10 | 9.795e-8 | 1.097e-4 | 3.842e-3 |
| annexb_c01_sig18 | 6.614e-6 | 9.397e-5 | 4.377e-2 |
| annexb_c01_sig23 | 3.248e-7 | 8.249e-5 | 3.508e-2 |
| annexb_c01_sig24 | 1.753e-6 | 6.217e-5 | 3.485e-2 |
| annexb_c01_sig25 | 7.781e-7 | 8.249e-5 | 2.639e-2 |

穩態（以 C golden 的頻帶位準跑 main loudness ＋ slopes，九個訊號）：總響度最大 1.530e-5 sone（annexb_sig5），比響度最大 1.500e-4 sone/Bark（sine_250_80；F-07 前 7.960e-3）。總響度數字 F-07 前後相同。

## 對 MoSQITo 的比響度（D-H：只記錄、不設門檻）

| 來源 | 最大差（sone/Bark） |
|---|---|
| Rust `golden_zwtv`（`NlInit::MosqitoTail`） | sine_1k_60 3.582e-3、pulse_1k_70 1.287e-2、step_60_80 2.209e-2、annexb_sig10 3.842e-3 |
| Rust `golden_zwst`（端對端） | sine_1k_60 6.3e-14、sine_250_80 3.922e-5、sine_4k_60 1.3e-14、white_60 1.8e-15、annexb_sig3 1.0e-14、annexb_sig5 7.960e-3 |
| Rust `golden_core`／`golden_zwst`（只跑 slopes） | sine_250_80 3.922e-5，其餘三組 0 |
| Python parity，時變（mosqito_tail 與預設＋靜音尾段兩組相同） | sine_1k_60 3.582e-3、sine_250_80 2.496e-3、sine_4k_60 2.867e-3、white_60 3.112e-2、pulse_1k_70 1.287e-2、step_60_80 2.209e-2、annexb_sig3 3.527e-3、annexb_sig5 3.147e-2、annexb_sig10 3.842e-3 |
| Python parity，穩態 | sine_250_80 3.922e-5、step_60_80 1.033e-3、annexb_sig5 7.960e-3，其餘六組 ≤ 6.3e-14 |
| `tools/compare_mosqito.py`，3 秒 | `nl_init="mosqito_tail"` 1.86e-3（0.3.1 為 3.46e-15）；預設 3.25e-2（F-02 起始段，數字不變） |

總響度對 MoSQITo 仍以 5e-3 sone 看守，數字 F-07 前後相同。

## 第一輪 finding 的處理

1. **全序列 1e-10 不可行。** 依決策備忘 §7 改為三層門檻（見上）。比響度的 4.4e-2 是 F-07，Round 2 已修正；剩下 ≤ 2.1e-4 來自 C 程式的 band 邊界 epsilon 與 float32 格線累加（獨立驗證的診斷：兩者需一起換掉，比響度才降到 1e-14 量級）。
2. **MoSQITo specific 相容性超出 D-E。** 依 D-H，對 MoSQITo 的比響度改為只記錄，Python parity 的兩個 strict `xfail` 已移除。
3. **Python 的 n hash 只在本機 Windows 成立。** CI 的 py job 已比照 Rust job 在 windows-latest 設 `HASH_GATE_DUMP_ONLY=1`。

## 未做／待辦

- 產出物已建置並記 hash，尚未做防毒掃描，也未上傳 GitHub Release。
- 公開 `StreamFrame` 不含比響度（v0.3.1 即如此），串流與批次的比響度相等無法從公開 API 驗證；串流契約的位元相等涵蓋 `n` 與由 frame index 推導的時間。
- `CITATION.cff` 的版本與日期已在 tag 之後補登；`message` 的 MoSQITo 措辭待決。
- Round 2 的 RED commit `a1a261d` 本身過不了 `clippy -D warnings`（17 位有效數字的測試常數觸發 `excessive_precision`）；`0bb2272` 加上 `#[allow]` 後恢復 clean。
- F-03（Table A.9）仍 PENDING；穩態前端仍待決。
