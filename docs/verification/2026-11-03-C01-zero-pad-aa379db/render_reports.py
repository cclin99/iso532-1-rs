"""Render matching bilingual reports from the measured evidence."""
import json
from pathlib import Path
p=Path(__file__).resolve().parent
r=json.loads((p/'results.json').read_text(encoding='utf8'))
d=json.loads((p/'history-diagnostic.json').read_text(encoding='utf8'))
def table(head,rows):
    return '| '+' | '.join(head)+' |\n|'+'|'.join(['---']*len(head))+'|\n'+''.join('| '+' | '.join(map(str,row))+' |\n' for row in rows)+'\n'
grid=table(['Signal','L','K','L_pad','j','Rust frames','t (s)'],[[s['signal'],s['L'],s['K'],s['L_pad'],s['j'],s['frames'],format(s['time_seconds'],'.17g')] for s in r['signals']])
numbers=table(['Signal','C total (sone)','Rust total (sone)','Total abs diff','Max specific abs diff','Verdict'],[[s['signal'],s['total']['C']['decimal17'],s['total']['Rust']['decimal17'],format(s['total']['abs_diff'],'.17g'),format(s['comparison']['max_specific_abs_diff'],'.17g'),s['comparison']['verdict']] for s in r['signals']])
prefix=table(['Signal','C total comparisons','C specific comparisons','Bitwise mismatches (total/spec)','Max abs diff (total/spec)','First mismatch'],[[s['signal'],s['padding_invariance']['total']['compared_count'],s['padding_invariance']['specific']['compared_count'],'0 / 0','0 / 0','none'] for s in r['signals']])
boundary=table(['L','C frames','CLI total','CLI specific','Rust n','Rust spec elements','Rust time','Status'],[[s['L'],s['measured']['C_library_frames'],s['measured']['CLI_total'],s['measured']['CLI_specific'],s['measured']['Rust_n'],s['measured']['Rust_spec_elements'],s['measured']['Rust_time'],'passed' if s['passed'] else 'failed'] for s in r['boundaries']])
history=table(['Signal','Common points','First total diff >1e-14 (j)','Max common total abs diff','Max common specific abs diff','Rust original/padded total/spec mismatches'],[[s['signal'],s['common_output_points'],s['C_vs_Rust_common_total']['first_above_1e_minus14'][0],format(s['C_vs_Rust_common_total']['max_abs_diff'],'.17g'),format(s['C_vs_Rust_common_specific']['max_abs_diff'],'.17g'),'0 / 0'] for s in d['signals']])
gates=table(['Gate','Status'],[[k,'passed' if v else 'failed'] for k,v in r['gates'].items()])
binary=table(['Binary','SHA-256'],r['binary_hashes'].items())
common_files='''- [results.json](results.json): final results, all 241 C/Rust values per signal, bits/decimal17, both controls, input/output hashes, boundaries and gates.
- `signal-*-target.csv`: 964 value pairs with round-trip decimal17 and binary64 bits. `*-Loudness.csv` / `*-SpecLoudness.csv`: original CLI serialization.
- [run-start.json](run-start.json), [run-log.json](run-log.json): preregistration hashes, commands, versions, stdout/stderr, exit codes and library return values.
- [attempt-1-results.json](attempt-1-results.json), [attempt-1-run_experiment.py.txt](attempt-1-run_experiment.py.txt), [control-correction.json](control-correction.json), [control-correction.diff.txt](control-correction.diff.txt): original attempt and explicit comparator-control correction.
- [history-diagnostic.json](history-diagnostic.json), [diagnose_history.py](diagnose_history.py): same-round follow-up, separate from primary acceptance.
- [source-input-hashes.json](source-input-hashes.json), [delivery-check.md](delivery-check.md), [delivery-integrity.json](delivery-integrity.json): material provenance and post-redaction integrity.
'''
en=f'''# C-01 independent verification report

Date: 2026-11-03 (Asia/Taipei). Verifier: Astra. Tested commit: `{r['tested_commit']}` (`aa379db`). Pair: [Traditional Chinese](report.md).

## 1. Decision

**PARTIAL — do not close this round's C-01 numerical gap.** The independent official-C references were obtained. All 960 target specific-loudness comparisons satisfy <=1e-14 sone/Bark, but all 4 total-loudness differences exceed <=1e-14 sone. Each combined point is therefore **WITHIN TOLERANCE**, not AGREES. The largest total difference is 4.1705202592388566e-7 sone. The Annex B fallback `max(0.1,0.05*abs(reference))` passes but does not replace the preregistered gate.

Nine of ten final gates pass; the four-rounding-agreements gate fails. Required inputs/builds/precision were obtainable: **blocked: none**. **Skipped:** full workspace/binding/package/performance acceptance and a separate all-requirements audit closure review. The 7 output-grid tests are supporting evidence, not comprehensive reset/flush/short-input acceptance. No DSP, test, golden, decision memo, brief or audit closure row was changed; no commit/push.

## 2. Frozen material and execution

The bilingual [preregistered design](experiment-design.en.md) was written before execution. `run-start.json` records start `{r['started_utc']}` and both design hashes; the designs remained unchanged. Primary execution finished `{r['finished_utc']}`. The source was extracted from the fixed commit into isolated scratch; archived source hashes before/after match. The pre-existing untracked F-03 delivery was preserved.

Official archive material was recovered from the retained local evidence ZIP and rebuilt this round; prior numbers were not reused. `ISO_532-1.c` is unchanged, SHA-256 `a74b45ed297cd09ac60701a923120341137d227e536f3109ae4ece810d834491`. The original header, CLI main/helper and archive hashes are in the inventory. MSVC 19.44.35228 x64 used `/nologo /O2 /fp:precise`; `_CRT_SECURE_NO_WARNINGS` only suppresses CRT diagnostics. Rust used `{r['environment']['rustc']}`, release profile and default runtime dispatch (AVX2 available). The Rust harness has a separate Cargo manifest/lock and calls the fixed snapshot's public `loudness_zwtv`.

All WAVs are mono 48 kHz signed PCM16 little-endian. Decode integer/32768, calibrate using the official Annex C 60 dB file and the CLI-equivalent sequential accumulation. The pressure multiplier is **2.8357977163914438**, bits `4006afb6b68fc829`. C and Rust use identical little-endian binary64 pressure bytes; the C helper/CLI-equivalent decoder produces identical bytes for every padded and boundary WAV. Padding only appends zeros. Original WAV, decoded PCM, pressure, padded WAV/pressure and calibration hashes are retained. `decoder-wrapper.c.txt` changes no DSP body: it calls the official reader and exports calibrated inputs. `rust-probe.rs.txt` exports full arrays and prints the target bits.

The C/CLI build and all computational subprocesses exited 0. `cl /Bv` without source exited 2 with D8003 as an expected version query; the environment's `vswhere.exe` lookup warning was retained and was nonfatal. Neither is hidden as a numerical pass.

{binary}
## 3. Target points and primary findings

Zero-based indexing: K=floor(L/24), L_pad=96*(ceil(L/96)+1), j=K/4=Rust frames-1. Reference values are undecimated padded C frame K before CLI serialization. All full arrays had the expected shapes and finite values before comparison. Each total and all 240 specific values have decimal17 and binary64 bits in JSON/CSV. The output times are exact Rust grid values; decimal representations below retain binary64 precision.

{grid}{numbers}
The specific column is a maximum over all 240 Bark values, not a selected subset. All 4 totals fail the rounding gate; all 960 specific values pass. CLI total and specific data row j existed, had the expected time and 240 specific columns, and matched four-decimal serialization within 0.000050000001. CLI text did not supply the high-precision references.

## 4. Controls and final gates

All 19,332 original internal total frames and 4,639,680 specific values are bitwise identical between original and padded C runs, including unsampled internal frames. These are measured comparisons, not a CLI-grid inference.

{prefix}
Comparator control: the first attempt compared an injected reference copy against Rust. Because the real total discrepancy was already above threshold, its first reported failure was total, confounding the intended coordinate check. The entire original result and original runner are preserved. The correction compares the original C reference with its +1e-6 copy at `specific[137]` using the **same unchanged comparator**. All 4 baseline self-comparisons return AGREES; all 4 injected comparisons return non-AGREES and exactly that coordinate. Finite/shape rejection controls also pass. No original numerical values or thresholds changed. The corrected reproduction runner is delivered; only this isolated control was rerun, with timestamps and before/after harness hashes in `control-correction.json`.

{gates}
The fixed snapshot's `cargo test -p iso532 --test output_grid --locked --offline` passed **7/7** (0 failed, 0 ignored), including 16 length cases, time grid, zero-padding/real-continuation prefix determinism and stream chunking. Its compiler log and exit code are retained.

## 5. Length-boundary measurements

Base: Annex B 18 first 4897 calibrated samples, hashed in `boundary_base`; each row is an exact prefix. C library counts are actual returns, CLI counts are parsed data rows, Rust counts are loaded output-array lengths. Every row matches the preregistered table.

{boundary}
## 6. Findings and current interpretation

The supplementary read-only diagnostic confirms that C/Rust total differences already exceed 1e-14 at common output **j=54 (0.108 s)** for every signal, well before the added tail point. Rust original versus padded outputs are bitwise equal for **all original total and specific values, including the target**. Combined with the C invariance control, the observed cross-implementation difference is not introduced by this padding operation.

{history}
Source evidence: official C `ISO_532-1.c:1002-1015` computes slope total/specific then applies temporal weighting to total only; `:553-574` carries low-pass state and `:607-614` combines 3.5 ms/70 ms branches. The fixed Rust `iso532/src/zwtv/mod.rs:130-150` and `temporal_weighting.rs:40-55` do the corresponding separation and carry historical state. Thus a nearly vanished final specific spectrum can agree while weighted total still reflects earlier differences. This is a supported interpretation of the state structure; **the upstream numerical root cause is not isolated**, and no F-03 coefficient attribution is made. There are also earlier specific differences, reported separately in the diagnostic.

The decision memo's extension from within-implementation prefix determinism to 1e-14 cross-implementation total agreement was a hypothesis; this run does **not** confirm it. Keeping ceil and obtaining valid padded references are supported here; closing the stricter numerical gate is not. A future separate stage-by-stage investigation would need matched pre-weighting total histories and temporal-weighting outputs before identifying a cause or proposing a change. This report does not amend the existing decision or audit row.

## 7. Evidence, reproduction and limits

{common_files}
Use [commands.md](commands.md) and the delivered scripts to repeat in new scratch/output directories with the inventoried original material. Only UTF-8 text is delivered; WAVs/binaries/full raw arrays remain in scratch and are identified by hashes. Harness hashes recorded before redaction identify the executed originals; final deliverable hashes identify redacted text and do not claim byte identity with those originals. `delivery-integrity.json` explicitly excludes itself.

This is numerical verification on the stated snapshot/toolchain and four signals plus eight shape controls. It is not general ISO certification, an independent F-03 resolution, cross-platform validation or a full C-01 audit closure. The failed strict total gate remains open.
'''
zh=f'''# C-01 獨立驗證報告

日期：2026-11-03（Asia/Taipei）。驗證者：Astra。受驗 commit：`{r['tested_commit']}`（`aa379db`）。對照：[English](report.en.md)。

## 1. 判定

**PARTIAL — 本輪 C-01 數值缺口不得結案。** 已取得獨立官方 C 參考值。960 個目標 specific 比較全部滿足 <=1e-14 sone/Bark，但 4 個 total 絕對差全部超過 <=1e-14 sone。每個合併目標點因此皆為 **WITHIN TOLERANCE**，不是 AGREES。total 最大差為 4.1705202592388566e-7 sone。Annex B 備援 `max(0.1,0.05*abs(reference))` 通過，但不能取代預註冊門檻。

最終十個 gates 中九個通過，four-rounding-agreements 失敗。必要素材／建置／精度均取得：**blocked：無**。**skipped：**全 workspace／binding／package／效能驗收，以及另行完整 audit 條件審查。7 個 output-grid 測試僅是輔證，不是 reset／flush／短輸入的完整驗收。不改 DSP、測試、golden、決策 memo、brief 或 audit closure 列；未 commit／push。

## 2. 固定素材與執行

雙語[預註冊設計](experiment-design.md)在開跑前寫入。run-start.json 記錄開始時間 `{r['started_utc']}` 與兩份設計 hash，設計至今未變；主要執行結束於 `{r['finished_utc']}`。從固定 commit 解出獨立 scratch 快照，受驗來源前後 hash 相符；保留原有未追蹤 F-03 交付資料夾。

從本機保存的歷史證據 ZIP 取回官方 archive 素材，本輪重新建置，未沿用歷史數字。ISO_532-1.c 未變，SHA-256 `a74b45ed297cd09ac60701a923120341137d227e536f3109ae4ece810d834491`；原 header、CLI main/helper、archive hash 均列清單。MSVC 19.44.35228 x64 使用 `/nologo /O2 /fp:precise`；`_CRT_SECURE_NO_WARNINGS` 僅抑制 CRT 診斷。Rust 使用 `{r['environment']['rustc']}`、release profile、預設 runtime dispatch（AVX2 可用）。Rust harness 有獨立 Cargo manifest/lock，呼叫固定快照公開 loudness_zwtv。

所有 WAV 均為單聲道 48 kHz little-endian 有號 PCM16，以整數 / 32768 解碼，使用官方 Annex C 60 dB 校準檔與 CLI 相同逐樣本累加方式。聲壓倍率為 **2.8357977163914438**，bits `4006afb6b68fc829`。C/Rust 取得相同 little-endian binary64 聲壓 bytes；官方 C helper／CLI 等式解碼器對每份補零及邊界 WAV 產生的 bytes 亦相同。補零僅附加零值。原 WAV、解碼 PCM、聲壓、補零 WAV／聲壓與校準檔 hash 均保留。decoder-wrapper.c.txt 不改 DSP 本體，只呼叫官方 reader 並匯出校準輸入；rust-probe.rs.txt 匯出完整陣列並列印目標 bits。

C／CLI 建置及所有計算子程序退出碼均為 0。cl /Bv 未帶來源檔，預期回報 D8003 並退出 2；環境的 vswhere.exe 查找警告保留且非致命。兩者均未被隱藏或冒充數值通過。

{binary}
## 3. 目標點與主要結果

零起算：K=floor(L/24)、L_pad=96*(ceil(L/96)+1)、j=K/4=Rust frames-1。參考值是補零 C 在 CLI 序列化之前、未抽樣的第 K 幀。比較前已驗完整陣列形狀與全部有限值；每個 total 與全部 240 specific 均保留 decimal17 與 binary64 bits 於 JSON／CSV。下表時間保留 Rust 精確格點的 binary64 十進位表示。

{grid}{numbers}
specific 欄是全部 240 Bark 值的最大差，不是抽樣子集。4 個 total 均未達捨入門檻，960 個 specific 全過。CLI total／specific 資料列 j 均存在、時間相符、specific 各 240 欄，四位小數序列化差皆 <=0.000050000001；高精度參考不是取自 CLI 文字。

## 4. 對照與最終 gates

C 原長與補零之間全部 19,332 個原始內部 total 幀與 4,639,680 個 specific 值 bitwise 相同，涵蓋未抽樣到 CLI 的內部幀。這是實測全量比較，不是從 CLI 格點推論。

{prefix}
比較器負對照：首輪把注入後參考副本與 Rust 比較，但既存 total 差已超門檻，first failure 因此為 total，干擾指定座標檢查。已完整保留首輪結果及 runner。修正後以**同一個未變的比較器**，比較原 C 參考與 specific[137] 加 1e-6 的副本。4 組自比皆 AGREES；4 組注入皆非 AGREES 並精確指出該座標。有限值／形狀拒絕路徑亦通過。原始數值與門檻均未改；交付修正版重現 runner，本輪僅重新執行這個隔離對照，時間與前後 harness hash 見 control-correction.json。

{gates}
固定快照 `cargo test -p iso532 --test output_grid --locked --offline` **7/7 passed**（0 failed、0 ignored），涵蓋 16 長度、時間軸、零補／真實延續的前綴決定性與 stream chunking；保留編譯日誌及退出碼。

## 5. 長度邊界實測

基底為 Annex B 18 的前 4897 個校準樣本，hash 見 boundary_base；各列為其精確前綴。C library 幀數來自實際回傳值，CLI 為解析資料列數，Rust 為讀出陣列長度。每列均符合預註冊表。

{boundary}
## 6. 發現與目前判斷

補充唯讀診斷確認：每個訊號 C/Rust total 差早在共同輸出 **j=54（0.108 s）** 已超過 1e-14，早於額外尾點。Rust 原長與補零的**全部原始 total／specific（含目標尾點）均 bitwise 相同**。合併 C 不變性對照，可確認此次補零操作沒有引入這項跨實作差異。

{history}
來源證據：官方 C ISO_532-1.c:1002-1015 先算 slope total／specific，再僅對 total 作時間加權；:553-574 保留低通歷史狀態，:607-614 合併 3.5 ms／70 ms 分支。固定 Rust iso532/src/zwtv/mod.rs:130-150 與 temporal_weighting.rs:40-55 亦分開處理並保留歷史狀態。因此，接近消失的尾點 specific 頻譜一致，仍可能伴隨 total 中較早差異的加權殘留。這是有狀態結構支持的目前判斷；**尚未隔離上游數值根因**，不歸因 F-03 係數。較早 specific 也存在差異，已在診斷中分列。

決策 memo 從同一實作的前綴決定性，延伸至跨 C/Rust total 的 1e-14 一致，是待證假說；本輪**未證實**。本輪支持維持 ceil 的前綴性及補零參考有效性，但不支持關閉較嚴格數值 gate。後續若另行追查，需對齊時間加權前 total 歷史與時間加權後輸出，才能定位根因或提出變更。本報告不修改既有決策或 audit 列。

## 7. 證據、重現與界線

{common_files}
依 [commands.md](commands.md) 與交付腳本，使用清單中的原始素材，在新 scratch／輸出目錄重現。只交付 UTF-8 文字；WAV／binary／完整原始陣列留 scratch 並以 hash 識別。去識別化前 harness hash 識別當時實跑原檔，最終交付 hash 識別去識別化文字，兩者不宣稱 bytes 相同。delivery-integrity.json 明確排除自身。

本輪為指定快照／工具鏈、四個訊號及八個形狀邊界的數值驗證，不是全面 ISO 認證、F-03 獨立結論、跨平台驗證或完整 C-01 audit closure。嚴格 total gate 仍未通過。
'''
for name,text in [('report.en.md',en),('report.md',zh)]: (p/name).write_text(text,encoding='utf8',newline='\n')
inventory={'meaning':'Original source/input/binary hashes, not hashes of redacted copies. Final delivered text is inventoried separately.',
 'tested_commit':r['tested_commit'],'source_hashes':r['source_hashes'],'binary_hashes':r['binary_hashes'],
 'calibration':r['calibration'],'signals':[{k:s[k] for k in ['signal','input','output_hashes']} for s in r['signals']],
 'boundary_base':r['boundary_base'],'boundary_inputs':[{k:s[k] for k in ['L','input_pressure_f64le_sha256','WAV_sha256']} for s in r['boundaries']],
 'executed_harness_hashes_before_redaction':r['harness_hashes_before_redaction'],'executed_runner_copy':'attempt-1-run_experiment.py.txt'}
(p/'source-input-hashes.json').write_text(json.dumps(inventory,indent=2,ensure_ascii=False)+'\n',encoding='utf8',newline='\n')
print('Bilingual reports and source/input inventory generated.')
