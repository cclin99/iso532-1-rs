"""Generate synchronized bilingual reports from fresh experiment metrics."""
from pathlib import Path
import json
D=Path(__file__).resolve().parent
f=json.loads((D/'factorial.json').read_text()); c=json.loads((D/'calibration.json').read_text())
def matrix():
    out=['| Signal | noct, 2sqrt2 | Annex, 2sqrt2 | noct, calibration WAV | Annex, calibration WAV |','|---|---:|---:|---:|---:|']
    for s,x in f.items():
        cells=[]
        for cal,front in [('sqrt','noct'),('sqrt','annex'),('cal','noct'),('cal','annex')]:
            a=x[cal][front];cells.append(f"{a['n']:.9f} ({a['signed_error_percent']:+.7f}%)")
        out.append('| '+s+' | '+' | '.join(cells)+' |')
    return '\n'.join(out)
def delta():
    out=['| Signal | Method delta, 2sqrt2 | Filter delta, same skip 0.2 s | Filter delta, same skip 0 s | Absolute-error improvement, same skip 0.2 s |','|---|---:|---:|---:|---:|']
    for s,x in f.items():
        a=x['sqrt'];m=a['matched_skip_filter_effects']
        out.append(f"| {s} | {a['frontend_method_delta_sone']:+.9f} | {m['0.2']['filter_only_delta_sone']:+.9f} | {m['0.0']['filter_only_delta_sone']:+.9f} | {m['0.2']['abs_error_improvement_factor']:.1f}x |")
    return '\n'.join(out)
common=matrix(); effects=delta()
zh='''# F-03 與 ZWST 前端獨立驗證

> [English](report.en.md) · Astra (`gpt-6-astra`) · 2026-11-05 Asia/Taipei

受驗產品：`v0.4.0`，`118322f8300dc752f1d38a79db230a2db5ff2870`。本輪以新建 C CLI/DLL、獨立 Rust harness，從原始 WAV／XLSX 重新計算；未改產品 DSP、測試、表格或 golden，未 commit／push／release。

## 判定

| 項目 | 判定 | 本輪發現 |
|---|---|---|
| 0.22 與工作簿精度一致性 | PASS | 原範圍 49,675 點全部差 ≤1e-4；加入時變 N′ 後 72,875 點亦然 |
| 0.22／0.24 可區分點數與完全相等數 | PASS | 12,287 點；11,174 等於 0.22，0 等於 0.24 |
| Opus「12,109 點比較接近 0.22」 | FAIL | 正確為 12,062；另 225 等距、0 接近 0.24。舊浮點判斷誤分類 47 個等距點 |
| 四 WAV 改用 Annex 前端方法大幅減少總響度誤差 | PASS（限定範圍） | 固定 2sqrt2 換算，現行 noct→Annex+0.2 s 的絕對誤差改善 317–2,922 倍；同 skip 0.2 s 的純前端比較改善 317–2,062 倍 |
| 「四個總響度誤差都 ≤0.001%」 | FAIL（嚴格主張） | 訊號 4 為 −0.001337644%；其他三個通過 |
| 「skip 影響 ≤0.002%，可排除」 | FAIL（方法歸因） | 保留濾波歷史後，Annex 訊號 3 的 skip 0→0.2 s 改變 −0.094881%；舊方法切掉輸入後重設濾波器 |
| 前端候選與同輸入 C 的 N／N′ ≤1e-4 | PARTIAL | N 全過；訊號 2 的 N′ 最大差 0.000150004（2.9 Bark），位準相同仍存在於下游 |
| 校準檔造成另約 +0.15% 的偏移 | PASS（四個穩態訊號） | 2sqrt2→校準檔在 Annex 方法增加相對工作簿 +0.1426～+0.1629 個百分點 |
| 正式 corrected 2017-11 Table A.9 權威 | PENDING | 未取得該版頁級原文；數值一致性不能取代正式權威 |
| 工作簿歷史生成程式、一般化精度、新 API／發布驗收 | PENDING／未測 | 本輪沒有足夠證據裁定 |

本輪的 FAIL 指精確主張或預登記門檻不成立，**不是產品回歸或完整 ISO 不合格判定**。尤其 N′ 的 1e-4 是本輪精度主張，不能冒充前輪 full-series 3e-4 等其他驗收門檻。

## 1. 凍結、重算與格線

[預登記](preregistration.md)、[凍結清單](frozen-inputs.json) 記錄 39 份原始材料及 44 份產品檔。工作樹與 tag 在 git 上無差異，但部分檔案有 CRLF；本輪改用 `git show` 抽出的逐位元 tag 快照建置。實際依賴 lock、工具版本與 binary hash 已交付，未使用先前 wheel 或既有 CLI。

官方 C 原始檔 SHA-256 起首 `a74b45ed`；僅改 `USL[12][4]` 的副本起首 `739af24d`。完整 hash 在 [builds.json](builds.json)。兩份以相同 MSVC `/O2 /fp:precise` 建置；原碼未重新分發。所有原始 hash 在計算前重驗。

24 個 PCM16 WAV 重新轉成 `int16/32768 × 2sqrt2` float32 Pa；2–5 用 stationary、skip 0.2 s；6–25 用 time-varying，15 為 diffuse，其餘 free。工作簿以唯讀 `data_only` 載入，不儲存。原有 conditional-formatting 警告不影響讀取的數值，也未改工作簿。

N(t) 與 N′(t) 以整數 0.0001 s tick 對齊，確認 0.002 s 格線、無重複與缺列，未插值或截索引。直接 C DLL 是 2 kHz，採樣 frame = time_tick/5；CLI 是其 2 ms 輸出點。20 個時變工作簿的全部列均精確覆蓋，未匹配 CLI 尾列均為 0；非 24/96 整除的實際 WAV 長度保留在 [alignment.json](alignment.json)，不補零偷換時軸。

四穩態比較包含 N 及各 240 格 N′；6–13 補驗工作簿指定 Bark（2.5、8.5 或 17.5）的 23,200 格 N′。這些新增 N′ 兩個 USL 版本完全一致、最大工作簿誤差 1e-4，**不具區分 USL 的能力**。未聲稱比對每一時刻全部 240 Bark。訊號 1 的旁路控制另外 241 格，與工作簿四位小數全部一致，未混入 72,875 主計數。

## 2. F-03 數值結論與浮點等距錯誤

[工作簿比較](workbook-comparison.json)、[彙總](summary.json)：原 49,675 點中 15,801 點兩版不同；其中 14,277 點等於 0.22、411 點等於 0.24。後者全是僅差最後一位的情況。0.22 最大誤差 0.0001；0.24 最大 0.0169（訊號 6）。

| 兩版差距門檻（sone） | 可區分點 | 等於 0.22 | 等於 0.24 | 較近 0.22 | 等距 |
|---|---:|---:|---:|---:|---:|
| 0.0002 | 12,287 | 11,174 | 0 | 12,062 | 225 |
| 0.0003 | 9,940 | 9,052 | 0 | 9,940 | 0 |
| 0.0005 | 6,930 | 6,335 | 0 | 6,930 | 0 |

[rounding-audit.json](rounding-audit.json) 從新 CSV 完整重現舊算法 12,109；十進位顯示值乘 10,000 化為整數後，47 點其實等距。舊 `>=2e-4-1e-9` mask 本身沒有漏掉邊界；錯在後續 `d22<d24` 的 binary float 距離比較。正確較近比例為 98.17%，不是 98.6%。數據仍強烈支持 **0.22 比 0.24 更符合這批保存工作簿**。

這不能證明工作簿歷史上「就是由該 C 程式生成」。C 與 XLSX 同屬保存附件，非已證明獨立的兩個來源；保存包的 ISO_DIS／2016 標記與 corrected 2017-11 版之關係仍待正式文件。不得據此修改產品係數或 golden。

## 3. 前端 × 校準矩陣與純前端效果

數值單位為 sone，括號為對工作簿的有號百分比誤差。noct 是現行完整輸入 RMS（skip 0）；Annex 是保留完整濾波歷史後 skip 0.2 s。下游均固定為 tag 的 Rust main/slopes（USL=0.24）。因此此主矩陣比較的是完整**前端方法**，包括 RMS 區間，不可把全部差值叫純濾波器效果。

MATRIX

所有絕對／相對誤差、改善倍數及兩種校準的 matched-skip 2×2 表均在 [factorial.json](factorial.json)。固定 2sqrt2 下，下面分開列完整方法與相同 skip 的濾波器差值（Annex−noct，sone）：

EFFECTS

訊號 4 的 Annex N=1.54937927455，對 1.5494 的絕對差為 0.00002072545，百分比 −0.001337644%。印成 −0.001% 不能當作 `≤0.001%` 證據；本輪不放寬門檻。這也接近工作簿四位小數的量化解析度，不能推導引擎超出完整 ISO 容差。

校準係數是 CALFACT Pa/FS，2sqrt2 是 2.82842712474619；位準差 DBDELTA dB。固定 Annex 方法，校準變化的 ΔN（訊號 2–5）為 +0.021598644、+0.006545850、+0.002236461、+0.016419807 sone。它不屬於濾波器改善。兩因子的交互項非零，完整方法的交互 ΔN 為 −4.4866e-5、−5.4916e-5、−9.2579e-6、+1.1921e-4；不能稱最終響度「互不相干」。

## 4. Skip、下游殘差與負控制

舊 `noct_skip0p2` 是先切掉 9,600 個輸入樣本，再從零狀態濾波，並非同一完整濾波輸出丟棄前 0.2 s。新 [skip-and-band-sensitivity.json](skip-and-band-sensitivity.json) 同時記錄兩種方法，並測 0／0.1／0.2／0.4 s。真實 full-filter RMS skip 0→0.2 s 的相對變化：

| 訊號 | noct | Annex |
|---|---:|---:|
| 2 | −0.068873% | −0.087410% |
| 3 | −0.083260% | −0.094881% |
| 4 | +0.000102% | −0.000137% |
| 5 | +0.017318% | +0.018412% |

這不否定濾波器主效應，但排除了「時間區間可忽略」的泛稱。特別是 skip 0 的 Annex 誤差仍達訊號 2 +0.087490%、訊號 3 +0.093939%；改善結果依賴所指定的 skip。

[c-fullprecision-controls.json](c-fullprecision-controls.json) 用未量化 double-Pa 輸入確認 Annex 位準與原 C 極近；四訊號的總 N 與 C 差最大約 1.59e-5 sone。訊號 2、2.9 Bark 的候選 N′ 與 C 差 0.00015000364；把相同 28 帶位準送 C 下游仍保留此差，故有下游殘差，不能說所有 N／N′ 誤差全部來自前端。兩 C USL 版本在四穩態訊號完全一致，這個殘差不是 F-03 單格造成。未在本輪追溯更細的下游數值機制。

| 控制 | 結果與邊界 |
|---|---|
| 錯誤校準／時間偏移 | 校準檔使四個 Annex 結果遠離工作簿；故意偏移一個 2 ms frame 破壞非恆定 N 的 1e-4 精度，逐訊號數字已保留 |
| 不觸發 USL／旁路前端 | 訊號 1、全 0 dB 與單一 1 kHz 60 dB 位準兩 C 版本相同；訊號 1 的 241 格與工作簿 round4 相同 |
| 長度／空 RMS | 真實訊號 3 的 4,800／9,600／19,200 樣本前綴 × 四種 skip，共 12 案；skip≥長度時候選 harness 拒絕，C 回 −4；非公開 API 驗收 |
| 單頻帶替換 | 全 28 帶位準、逐帶 ΔN 已保留。原方法比較的替換加總非精確可加：訊號 2 差 0.0009061、訊號 5 差 0.0004158 sone |
| float32 輸入量化 | 6／9／14／15 的直接 f32 C round4 全部重現 CLI；f64↔f32 在 9／14／15 分別改變 1／9／11 個四位小數結果；訊號 14 最大 N 差 8.42e-5 |
| 理論頻率響應／有效噪音頻寬 | SKIPPED：未重新驗證舊報告全部 ENBW／bilinear 機制數字；本輪實際 noct 包含其降採樣，不能以省略降採樣的理論曲線宣稱普遍機制已證實 |

float32 在四位小數「沒有影響」不成立；但 6、9 換成 f64 後仍大量未與工作簿 round4 相等，因此它也不能單獨解釋所有殘差。詳見 [float-precision-controls.json](float-precision-controls.json)。本輪只增加這四個代表控制，不把它擴大為所有訊號證明。

## 5. 證據強度與交付

「四個 Annex B 穩態 WAV，在指定校準與 skip 下大幅改善總響度」有實測支持。「所有穩態輸入都一樣改善」、「所有誤差都來自前端」、「工作簿確由此程式生成」、「此附件足以決定 corrected Table A.9」均超出證據。校準、前端、skip、USL 必須分開敘述，有限樣本的零 USL 效應不等於普遍無交互作用。

[replay.md](replay.md) 提供重播方式；[delivery-check.md](delivery-check.md) 記錄環境修復、去識別化及完整性檢查。原始 WAV／XLSX／完整 C／大型 CLI 結果僅留 tmp，交付 hash 不冒稱可取代原始資料。沒有執行無關效能或完整發布測試。
'''
en='''# Independent F-03 and stationary frontend verification

> [繁體中文](report.md) · Astra (`gpt-6-astra`) · 2026-11-05 Asia/Taipei

Tested product: `v0.4.0`, `118322f8300dc752f1d38a79db230a2db5ff2870`. Fresh C CLI/DLL builds and an independent Rust harness recomputed original WAV/XLSX material. Product DSP, tests, tables and goldens were not changed. No commit, push or release was performed.

## Decisions

| Item | Status | Independent result |
|---|---|---|
| Workbook precision agreement of 0.22 | PASS | All original 49,675 points differ by ≤1e-4; all 72,875 points after adding time-varying N′ do too |
| Decisive count and exact matches | PASS | 12,287 points; 11,174 equal 0.22, zero equal 0.24 |
| Opus: 12,109 points closer to 0.22 | FAIL | Correct count 12,062; 225 ties, none closer to 0.24. Binary-float comparison misclassified 47 ties |
| Large stationary total-loudness improvement | PASS, bounded | At fixed 2sqrt2, current noct→Annex with 0.2 s skip improves absolute error 317–2,922x; filter-only with both skips 0.2 s improves 317–2,062x |
| All four total errors ≤0.001% | FAIL, strict claim | Signal 4 is −0.001337644%; the other three pass |
| Skip effect ≤0.002%, hence negligible | FAIL, attribution method | Preserving filter history, Annex signal 3 changes −0.094881% from skip 0 to 0.2 s; the old test cropped input and restarted filters |
| Candidate versus same-input C N/N′ within 1e-4 | PARTIAL | All total N pass; signal 2 N′ differs by 0.000150004 at 2.9 Bark, persisting with identical backend input levels |
| Separate approximately +0.15% calibration bias | PASS, four stationary signals | Calibration-WAV scaling adds +0.1426 to +0.1629 percentage points relative to workbook N under the Annex method |
| Corrected-2017-11 Table A.9 authority | PENDING | No page-level text obtained; numeric agreement cannot replace formal authority |
| Historical generation, generalization, public API/release acceptance | PENDING/unmeasured | Not established by this experiment |

FAIL denotes a precise claim or preregistered gate, **not a product regression or complete ISO nonconformance**. In particular, this round's 1e-4 N′ claim gate must not replace previous full-series 3e-4 or other acceptance thresholds.

## 1. Frozen inputs, fresh computation and alignment

[Preregistration](preregistration.md) and [frozen manifest](frozen-inputs.json) cover 39 original material files and 44 product files. Git showed no crate difference from the tag, but some working files used CRLF. A byte-exact `git show` extraction was therefore built in isolation. The actual dependency lock, tool versions and binary hashes are delivered. No pre-existing wheel or CLI supplied the new numbers.

Original C SHA-256 starts `a74b45ed`; the isolated, single-cell `USL[12][4]` variant starts `739af24d`. [builds.json](builds.json) holds complete hashes. Both used identical MSVC `/O2 /fp:precise` settings. Full original C is not redistributed. Frozen hashes were checked before computation.

All 24 PCM16 WAVs were freshly converted using `int16/32768 × 2sqrt2` to float32 Pa. Signals 2–5 used stationary mode and 0.2 s skip; 6–25 used time-varying mode, diffuse for 15 and free field otherwise. Workbooks were opened read-only with cached numeric values, never saved. The conditional-formatting warning does not alter these read values.

Integer 0.0001 s ticks enforce exact alignment, a 0.002 s grid, unique timestamps and full coverage, without interpolation or clipped indices. Direct C DLL output is at 2 kHz and uses frame=time_tick/5; the CLI presents 2 ms samples. Every workbook time row was matched; all 20 signals have zero unmatched CLI tail rows. [alignment.json](alignment.json) records actual, sometimes non-divisible-by-24/96 input lengths; no padding was substituted.

Stationary coverage includes N and all 240 N′ bins for each of four WAVs. Added coverage is 23,200 N′ points for signals 6–13 at the workbook's specified Bark coordinate (2.5, 8.5 or 17.5). Those added traces are identical between USL variants and within 1e-4 of the workbooks: **they cannot discriminate the disputed cell**. This is not every Bark at every time. A separate signal-1 bypass control adds 241 round4-exact workbook points outside the primary 72,875 count.

## 2. F-03 and the floating-point tie error

[Workbook comparison](workbook-comparison.json) and [summary](summary.json): 15,801 of the original 49,675 points differ between variants; 14,277 of those equal 0.22 and 411 equal 0.24. All 411 are one-last-digit separations. Maximum workbook errors are 0.0001 for 0.22 and 0.0169 for 0.24 (signal 6).

| Variant separation (sone) | Decisive points | Equal 0.22 | Equal 0.24 | Closer to 0.22 | Ties |
|---|---:|---:|---:|---:|---:|
| 0.0002 | 12,287 | 11,174 | 0 | 12,062 | 225 |
| 0.0003 | 9,940 | 9,052 | 0 | 9,940 | 0 |
| 0.0005 | 6,930 | 6,335 | 0 | 6,930 | 0 |

[rounding-audit.json](rounding-audit.json) reproduces the legacy 12,109 count from fresh CSVs. Comparing integer ten-thousandths instead identifies 47 exact decimal ties. The legacy `>=2e-4-1e-9` selection mask did not miss the boundary; the later binary-float `d22<d24` predicate was the problem. Correct closer fraction: 98.17%, not 98.6%. The data still strongly favor **0.22 as the better match to these preserved workbooks**.

Agreement cannot prove which program historically generated the workbook. C and XLSX share preserved attachment provenance; independence has not been established. The ISO_DIS/2016 marking and relationship to corrected 2017-11 remain unresolved. Product coefficients and goldens must not be changed on the authority of this numerical result alone.

## 3. Frontend × calibration matrix and filter-only effect

Values are sone, with signed workbook-relative error in parentheses. Noct denotes the current full-input RMS, skip 0; Annex retains full filter history and skips 0.2 s before RMS. Both use the same tag Rust main/slopes backend (USL=0.24). Thus this primary matrix compares complete **frontend methods**, including RMS interval; its full delta is not filter-only.

MATRIX

[factorial.json](factorial.json) records absolute/relative errors, improvement factors and matched-skip matrices under both calibrations. With fixed 2sqrt2, the following separates method changes from same-skip filter changes (Annex−noct, sone):

EFFECTS

Signal 4 gives Annex N=1.54937927455 versus workbook 1.5494: absolute difference 0.00002072545, relative −0.001337644%. Displaying this as −0.001% cannot establish `≤0.001%`; the gate was not relaxed. The residual is also near workbook quantization resolution and does not establish failure of full ISO tolerance.

The calibration-WAV coefficient is CALFACT Pa/FS versus 2.82842712474619 for 2sqrt2, a DBDELTA dB offset. With fixed Annex method, calibration-only ΔN for signals 2–5 is +0.021598644, +0.006545850, +0.002236461 and +0.016419807 sone. It is not a filter benefit. The method/calibration interaction is nonzero: −4.4866e-5, −5.4916e-5, −9.2579e-6, +1.1921e-4 sone. Separate stages do not imply unrelated final outputs.

## 4. Skip, backend residuals and controls

The old `noct_skip0p2` cropped 9,600 input samples and restarted the filters. It did not discard the first 0.2 s of the same filtered output. [skip-and-band-sensitivity.json](skip-and-band-sensitivity.json) records both interpretations, testing 0, 0.1, 0.2 and 0.4 s. True full-filter RMS changes from skip 0 to 0.2 s are:

| Signal | noct | Annex |
|---|---:|---:|
| 2 | −0.068873% | −0.087410% |
| 3 | −0.083260% | −0.094881% |
| 4 | +0.000102% | −0.000137% |
| 5 | +0.017318% | +0.018412% |

This does not negate the filter effect, but disproves the negligible-interval claim. Without skip, Annex errors are still +0.087490% for signal 2 and +0.093939% for signal 3; the claimed near-workbook result depends on skip selection.

[c-fullprecision-controls.json](c-fullprecision-controls.json) verifies extremely close Annex frontend levels against original C on double-Pa input; maximum total-N difference over the four signals is about 1.59e-5 sone. Signal 2 at 2.9 Bark has a 0.00015000364 N′ residual, retained when exactly the same 28 levels enter the C backend. A downstream residual therefore exists: not all N/N′ error comes from the frontend. Both C USL variants are identical on these four stationary signals, so this residual is not the disputed F-03 cell. Further backend numerical root-cause analysis was outside scope.

| Control | Outcome and boundary |
|---|---|
| Wrong calibration / shifted time | Calibration-WAV scaling moves all four Annex results away from workbooks; deliberate one-frame (2 ms) displacement breaks precision on nonconstant N; per-signal metrics retained |
| USL-insensitive / frontend bypass | Signal 1, all-zero-dB levels and a single 1 kHz 60 dB band give identical C variants; signal 1 matches all 241 workbook round4 values |
| Length / empty RMS | Real signal-3 prefixes of 4,800, 9,600 and 19,200 samples × four skips, 12 cases; skip≥length is rejected by the harness and returns −4 in C; not public-API acceptance |
| Single-band substitution | All 28 levels and per-band ΔN retained. Sums are not strictly additive: discrepancy 0.0009061 for signal 2 and 0.0004158 sone for signal 5 in the original method comparison |
| Float32 input quantization | Direct f32 C reproduces CLI round4 for 6/9/14/15; f64↔f32 changes 1/9/11 rounded results in 9/14/15. Signal 14 maximum N delta is 8.42e-5 |
| Theoretical response / equivalent noise bandwidth | SKIPPED: not all prior ENBW/bilinear assertions were recomputed. Actual noct runs include decimation; a theory curve omitting it cannot establish the complete mechanism generally |

The assertion that float32 has no fourth-decimal impact is false. Yet many workbook discrepancies remain on signals 6 and 9 with f64 input, so quantization does not by itself explain every residual. See [float-precision-controls.json](float-precision-controls.json). These are four representative controls, not all-input proof.

## 5. Evidence strength and delivery

The four Annex B stationary WAVs show large total-loudness improvement at the specified scaling and skip. The data do not establish universal improvement, exclusively frontend error, historical workbook generation, or corrected Table A.9 authority. Calibration, frontend, skip and USL must be distinguished; a zero USL effect in limited signals does not prove universal absence of interactions.

[replay.md](replay.md) provides reproduction commands; [delivery-check.md](delivery-check.md) records environment repair, redaction and integrity checks. Original WAV/XLSX/full C and large outputs remain in tmp; delivery hashes do not substitute for original files. No unrelated performance or full-release testing was performed.
'''
for name,text in [('report.md',zh),('report.en.md',en)]:
    text=text.replace('MATRIX',common).replace('EFFECTS',effects).replace('CALFACT',f"{c['factors']['cal']:.12f}").replace('DBDELTA',f"{c['db_delta']:.9f}")
    (D/name).write_text(text,encoding='utf8')
print('Synchronized reports generated.')
