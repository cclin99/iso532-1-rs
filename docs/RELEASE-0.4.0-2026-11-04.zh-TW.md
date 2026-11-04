# Release 紀錄草稿：v0.4.0（2026-11-04，待獨立驗收）

> 對照／Pair: [English](RELEASE-0.4.0-2026-11-04.md) · 來源：zh · 同步 2026-11-04

**狀態：草稿。** 尚未打 tag、未推送、未跑 CI、未建置發行產出物；tag 在 Astra 獨立驗收之後。實作者：Claude Opus 5.5，依 [`superpowers/plans/phases/phase-0.4.0-slope-annexa.md`](superpowers/plans/phases/phase-0.4.0-slope-annexa.md) 與決策備忘 [`C01-F03-SLOPE-ALIGNMENT-DECISION-2026-11-03.zh-TW.md`](C01-F03-SLOPE-ALIGNMENT-DECISION-2026-11-03.zh-TW.md)（D1–D5，§7 修訂）。Round 1 起點 `5cb036a`（v0.3.1 之後的文件 commit）；Round 2 起點 `9301c0d`（第一輪驗證後的決策修訂）。

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
| `fe3d0b2`、`9301c0d` | 第一輪驗證後的決策修訂（F-07、C golden 分層門檻）與 Round 2 計畫 |
| `a1a261d` | Round 2 Task 7：F-07 的 RED 單元測試 |
| `0bb2272` | Round 2 Task 8：F-07 修正、`n_specific` hash 重凍、C golden 全序列門檻、MoSQITo specific 改為記錄、CI py job 的 `HASH_GATE_DUMP_ONLY` |
| 本紀錄所在 commit | Round 2 Task 9：CHANGELOG、README、本紀錄（兩語言） |

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

## Annex A C golden（D4 修訂／D-D、D-G）

- 參考程式：官方 `ISO_532-1.c`（SHA-256 `a74b45ed297cd09ac60701a923120341137d227e536f3109ae4ece810d834491`），只把 `USL[12][4]` 由 `0.22f` 改為 `0.24f`（替換版 SHA-256 `739af24dee118027cb419fcdb051d8b56b274211d986140d66d7ff4b9d52a7e9`）；MSVC 19.44.35228 x64，`/O2 /fp:precise`；wrapper 只呼叫 `f_loudness_from_signal` 與 `f_loudness_from_levels`。Round 2 未改 C 端，`data/golden-c/` 沿用 Round 1 產出。
- 門檻分三層：C-01 尾點總響度與比響度 1e-10；全序列總響度 1e-4 sone；全序列比響度 3e-4 sone/Bark（F-07 後實測最大 2.100e-4 向上取到 1 位有效數字）。全序列殘差來自 C 程式的 `_ZUP += .0001f` 與 float32 常數。
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

1. **全序列 1e-10 不可行。** 依決策備忘 §7 改為三層門檻（見上）。比響度的 4.4e-2 是 F-07，Round 2 已修正；剩下 ≤ 2.1e-4 來自 C 程式的 band 邊界 epsilon。
2. **MoSQITo specific 相容性超出 D-E。** 依 D-H，對 MoSQITo 的比響度改為只記錄，Python parity 的兩個 strict `xfail` 已移除。
3. **Python 的 n hash 只在本機 Windows 成立。** CI 的 py job 已比照 Rust job 在 windows-latest 設 `HASH_GATE_DUMP_ONLY=1`。

## 未做／待辦

- 未打 tag、未推送、未跑 GitHub CI、未建置發行產出物。
- `CITATION.cff` 仍為 0.3.1：過去在 release commit 才更新版本與 `date-released`，發版日未定。
- Round 2 的 RED commit `a1a261d` 本身過不了 `clippy -D warnings`（17 位有效數字的測試常數觸發 `excessive_precision`）；`0bb2272` 加上 `#[allow]` 後恢復 clean。
- F-03（Table A.9）仍 PENDING；穩態前端仍待決。
