# Release 紀錄草稿：v0.4.0（2026-11-04，待獨立驗收）

> 對照／Pair: [English](RELEASE-0.4.0-2026-11-04.md) · 來源：zh · 同步 2026-11-04

**狀態：草稿。** 尚未打 tag、未推送、未跑 CI、未建置發行產出物；tag 在 Astra 獨立驗收之後。實作者：Claude Opus 5.5，依 [`superpowers/plans/phases/phase-0.4.0-slope-annexa.md`](superpowers/plans/phases/phase-0.4.0-slope-annexa.md) 與決策備忘 [`C01-F03-SLOPE-ALIGNMENT-DECISION-2026-11-03.zh-TW.md`](C01-F03-SLOPE-ALIGNMENT-DECISION-2026-11-03.zh-TW.md)（D1–D5）。起點 `5cb036a`（v0.3.1 之後的文件 commit）。

本次範圍：slope 階段（`calc_slopes_impl`）對齊 ISO 532-1:2017 Annex A，正確性參考由 MoSQITo 1.2.1 改為官方 Annex A C 程式。屬數值變更，依版號規則升 minor。API、輸出格線、串流契約、SIMD 分派、C ABI、Python shape 都不變；`USL[12][4]` 維持 0.24（F-03 暫定）。

## 自 v0.3.1 以來的 commit（本階段）

| commit | 內容 |
|---|---|
| `93ba5e4` | Task 1：F-04／F-05／F-06 三個 RED 單元測試 |
| `d011921` | Task 2：`calc_slopes_impl` 修正（刪除每幀捨入、Annex A band 補完、band 0 不讀 band 20） |
| `9d8ae5a` | Task 3：契約與串流測試不變；`annexb.rs` 內 sig10 對 MoSQITo 的那一行改為相容性容差 |
| `777d8e8` | Task 4：`tools/gen_golden_c.py`、`tools/golden-c-usl12-4.diff`、`tools/golden-c.sha256`、`tests/golden_c.rs` |
| `8beeb90` | Task 5：MoSQITo golden 降為相容性對照、重凍 n hash、版號 0.4.0、CHANGELOG、README、F-03 狀態 |
| 本草稿所在 commit | Task 6：本紀錄（兩語言） |

## 使用者看到的變化

- 每個總響度值都可能改變：不再每幀捨入到 0.001／0.01 sone（F-04）；約 1% 的時變幀因 band 補完（F-05）改變 1e-3 ～ 2.6e-2 sone（加權輸出後對 MoSQITo golden ≤ 3.9e-3 sone）。
- 寬頻輸入的時變比響度在「被補完 band 的下一 band」也會改變（下一 band 改從 `ZUP` 起算）：對 MoSQITo 最大 1.13e-2 sone/Bark（white_60）、9.0e-3（annexb_sig5），對 Annex A C golden 則更接近。
- 直接呼叫 `core::calc_slopes*` 且 `nm[20] > nm[0]` 時，不再出現負的 band-0 比響度（F-06）；經 pipeline 的輸入不受影響。
- `N(t)` 不再跨 OS／後端逐位元相同：scalar 與 AVX2 差最多 2.6e-10 sone。依賴 n hash 的下游需逐平台重凍。

## 驗證（本機，`8beeb90` 狀態，Windows x64，rustc 1.99.1）

- `cargo fmt --all -- --check`、`cargo clippy --workspace --all-targets -- -D warnings`：clean。
- `cargo test --workspace`：140 passed、0 failed、5 ignored（其中 2 個是 `golden_c` 全序列 1e-10 的已知 finding，見下）。`cargo bench --workspace --no-run`：通過。
- 契約與串流：`output_grid` 7、`stream` 11（1 ignored 為既有）、`stream_scalar` 1、`stream_no_rayon` 1、`simd_parity` 2、`determinism` 1，全過，測試未改。
- Annex B：`annexb` 3、`annexb_validator` 24 全過；訊號 10 的 500 個 ISO 參考點 0 例外（max |N − ref| 1.25e-4）。判定規則 `max(0.1, 0.05·|ref|)` 未改。
- Linux（`ubuntu:24.04` 容器，glibc 2.39，rustc 1.99.1；Task 5 工作樹，Rust 程式與這些測試和 `8beeb90` 相同）：CI 的測試子集加 `nl_zero_init` 全過，`hash_gate` 以新的 Linux 常數斷言通過；容器量到的 `n_specific` hash 與既有凍結值相同。
- Python（0.4.0 wheel，`ISO532_REQUIRE_PARITY=1`）：83 passed、4 xfailed（strict），見「已知 finding」。

## Annex A C golden（D4／D-D）

- 參考程式：官方 `ISO_532-1.c`（SHA-256 `a74b45ed297cd09ac60701a923120341137d227e536f3109ae4ece810d834491`），只把 `USL[12][4]` 由 `0.22f` 改為 `0.24f`（替換版 SHA-256 `739af24dee118027cb419fcdb051d8b56b274211d986140d66d7ff4b9d52a7e9`）；MSVC 19.44.35228 x64，`/O2 /fp:precise`；wrapper 只呼叫 `f_loudness_from_signal` 與 `f_loudness_from_levels`。資料檔重跑逐位元可重現（只有 `meta.json` 的日期不同）。
- C-01 尾點（Annex B 訊號 18／23／24／25 的最後一個輸出點）：

| 訊號 | Rust 0.4.0 − C golden（0.24f） | specific 最大差 | Rust 0.4.0 − 未修改 C（0.22f） |
|---|---|---|---|
| 18 | −6.61e-11 | 9.1e-24 | −1.43e-8 |
| 23 | −5.16e-11 | 3.3e-23 | −1.28e-7 |
| 24 | −8.99e-11 | 2.2e-23 | −9.33e-9 |
| 25 | −7.41e-11 | 4.7e-24 | −7.41e-11 |

`meta.json` 的 `unmodified_c_delta`（C golden − 未修改 C）為 −1.42e-8／−1.28e-7／−9.24e-9／0，與決策備忘 §2 的量級一致（≤ 1.3e-7）。

## 已知 finding（交決策者）

1. **全序列 1e-10 不可行。** 九個訊號與四個 C-01 訊號的全序列，Rust 0.4.0 對 C golden：總響度最大 2.7e-5 sone（annexb_sig5），比響度最大 4.4e-2 sone/Bark（訊號 18）。總響度差來自官方 C 自身的 `_ZUP += .0001f` 與 float32 常數（同一 NL 輸入下，官方算術的 slope 對 Rust 逐幀已達 9.7e-6）；比響度差來自斜率與核心響度相交的那一格：MoSQITo 規則把斜率外插到核心值以下，C 寫核心值（例：訊號 18 第 391 點 bark 36，Rust 0.7701、C 0.8139）。後者是另一個繼承自 MoSQITo 的 specific 圖形差異，本階段依計畫不改。1e-10 因此只強制在 C-01 尾點；全序列比較保留為 `#[ignore]` 的嚴格測試。
2. **MoSQITo specific 相容性超出 D-E。** F-05 讓下一 band 的時變比響度改變，white_60／annexb_sig5 對 MoSQITo 達 1.13e-2／9.0e-3 sone/Bark，大於 5e-3。Python parity 這兩項列為 strict `xfail`；Rust `golden_zwtv` 的端對端比較本來就不含這兩個訊號。是否放寬相容性容差由決策者決定。
3. **Python 的 n hash 只在本機 Windows 成立。** `test_smoke.py` 的 n hash 改為逐平台；Linux 值與 GitHub runner 同一 glibc，Windows 值只對凍結的機器成立。CI 的 py job 目前沒有設 `HASH_GATE_DUMP_ONLY`，windows-latest 上很可能失敗；需在 CI 加這個環境變數（比照 Rust job）或改用 CI 實測值，本階段未改 CI。

## 未做／待辦

- 未打 tag、未推送、未跑 GitHub CI、未建置發行產出物。
- `CITATION.cff` 仍為 0.3.1：過去在 release commit 才更新版本與 `date-released`，發版日未定。
- `tools/doc_pairs.py --check` 有一個既有錯誤：`C01-F03-SLOPE-ALIGNMENT-DECISION-2026-11-03.md` 的 pair line 寫成「Pair／對照」，在起點 `5cb036a` 就存在，本階段未改決策備忘。
- F-03（Table A.9）仍 PENDING；穩態前端仍待決。
