"""Generate matching bilingual numerical reports from final metrics."""
from pathlib import Path
import json,datetime
P=Path(__file__).resolve().parent
S=json.loads((P/'summary.json').read_text());T=json.loads((P/'stratified-summary.json').read_text());M=json.loads((P/'common-stage-metrics.json').read_text());L=json.loads((P/'length-alignment.json').read_text());D=json.loads((P/'per-signal-metrics.json').read_text())
eng=['sqat','mos','c'];names={'sqat':'SQAT v2.0 / Octave 8.4.0','mos':'MoSQITo 1.2.1 / Python','c':'Official C / MSVC'}
def f(x):return '—' if x is None else f'{x:.12g}'
def where(m):
 a=m['max_abs_at'];s=f"sig{a['signal']} @ {a['time_s']:.4f} s"
 if 'bark' in a:s+=f", {a['bark']:.1f} Bark"
 return s
def tab(head,rows):
 esc=lambda x:str(x).replace('|','\\|')
 return '\n'.join(['| '+' | '.join(map(esc,head))+' |','|'+'|'.join(['---']*len(head))+'|']+['| '+' | '.join(map(esc,r))+' |' for r in rows])+'\n'
base=tab(['Implementation','max |ΔN|, sone','RMS ΔN, sone','max |ΔN′|, sone/Bark','max |ΔN| location'],[[names[e],f(S[e]['workbook']['N']['max_abs']),f(S[e]['workbook']['N']['rms']),f(S[e]['workbook']['Nprime']['max_abs']),where(S[e]['workbook']['N'])] for e in eng])
cell=tab(['Implementation','max |N(.24)−N(.22)|, sone','RMS ΔN, sone','max |ΔN′|, sone/Bark','max |ΔN| location'],[[names[e],f(S[e]['cell_024_minus_022']['N']['max_abs']),f(S[e]['cell_024_minus_022']['N']['rms']),f(S[e]['cell_024_minus_022']['Nprime']['max_abs']),where(S[e]['cell_024_minus_022']['N'])] for e in eng])
strata=tab(['Implementation','Input group','baseline max |ΔN| vs workbook','baseline RMS ΔN','cell max |ΔN|'],[[names[e],g,f(T[e][k]['workbook']['N']['max_abs']),f(T[e][k]['workbook']['N']['rms']),f(T[e][k]['cell_024_minus_022']['N']['max_abs'])] for e in eng for k,g in [('levels_1','1: levels'),('stationary_2_5','2–5: stationary'),('timevarying_6_25','6–25: time varying')]])
common=tab(['Implementation','N(.22)','N(.24)','original baseline N − C(.22)','own cell signed ΔN','cell max |ΔN′| @ 5.4 Bark'],[[names[e],f(M[e]['signal6-sensitive']['N022']),f(M[e]['signal6-sensitive']['N024']),f(M[e]['signal6-sensitive']['N022' if e=='c' else 'N024']-M['c']['signal6-sensitive']['N022']),f(M[e]['signal6-sensitive']['N_delta']),f(M[e]['signal6-sensitive']['Nprime_max_abs_delta'])] for e in eng])
synthetic=tab(['Implementation','N(.22)','N(.24)','signed whole-pattern ΔN','|ΔN′| @ 4.6 Bark'],[[names[e],f(M[e]['synthetic-band5-0p35']['N022']),f(M[e]['synthetic-band5-0p35']['N024']),f(M[e]['synthetic-band5-0p35']['N_delta']),f(M[e]['synthetic-band5-0p35']['Nprime_max_abs_delta'])] for e in eng])
cross=tab(['Implementation','baseline max |ΔN| vs C(.22)','baseline max |ΔN′| vs C(.22)','counterfactual max |ΔN| vs C(.22)','counterfactual max |ΔN′| vs C(.22)'],[[names[e],f(S[e]['official_c']['N']['max_abs']),f(S[e]['official_c']['Nprime']['max_abs']),f(S[e]['counterfactual_official_c']['N']['max_abs']),f(S[e]['counterfactual_official_c']['Nprime']['max_abs'])] for e in eng])
relative=tab(['Implementation','workbook max N error %, |ref|≥1e−4','workbook max N error %, |ref|≥1','cell max N change %, |N(.22)|≥1','cell changed N points (>1e−12)'],[[names[e],f(S[e]['workbook']['N']['max_relative_percent_ref_ge_1e4']),f(S[e]['workbook']['N']['max_relative_percent_ref_ge_1']),f(S[e]['cell_024_minus_022']['N']['max_relative_percent_ref_ge_1']),str(S[e]['cell_024_minus_022']['N']['above_1e12'])+'/'+str(S[e]['cell_024_minus_022']['N']['points'])] for e in eng])
spec=tab(['Implementation','workbook N′ RMS','cell N′ RMS','cell max N′ location','cell changed N′ points (>1e−12)'],[[names[e],f(S[e]['workbook']['Nprime']['rms']),f(S[e]['cell_024_minus_022']['Nprime']['rms']),where(S[e]['cell_024_minus_022']['Nprime']),str(S[e]['cell_024_minus_022']['Nprime']['above_1e12'])+'/'+str(S[e]['cell_024_minus_022']['Nprime']['points'])] for e in eng])
length=tab(['Implementation','extra output frames vs workbook (total)','max returned-label drift (s)','baseline routes / variants'],[[names[e],sum(x['extra_output_frames'] for x in L if x['engine']==e),f(max(x['reported_time_max_drift_s'] for x in L if x['engine']==e)),'25 / 2'] for e in eng])
controls={e:[s for s in [1,2,3,4,5,25] if D[e]['cell_024_minus_022'][str(s)]['N']['max_abs']==0 and D[e]['cell_024_minus_022'][str(s)]['Nprime']['max_abs']==0] for e in eng}
assert all(len(v)==6 for v in controls.values())
assert all(len(S[e]['workbook']['signals'])==25 and len(S[e]['cell_024_minus_022']['signals'])==25 for e in eng)
completed=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat()
shared=f'''## Baseline versus supplied official workbook values

{base}
## Native single-cell effect: 0.24 minus 0.22

{cell}
## Input groups: N discrepancies in sone

{strata}
## Same exact real-signal 21-band core vector

{common}
## Synthetic same-input slope case

{synthetic}
## Full-precision comparison with unmodified official C

{cross}
## Relative N metrics and affected coordinates

{relative}
## Specific-loudness detail

{spec}
## Length and time-label accounting

{length}
'''
en=f'''# F03 — native SQAT, MoSQITo and official-C error at USL[12][4]

**Numerical execution complete:** all three native implementations, both coefficient variants, all 24 Annex WAV signals (2–25) plus level-input case 1. Started 2026-11-05; completed {completed}. Product snapshot `118322f8300dc752f1d38a79db230a2db5ff2870`; repository HEAD `493fd595ef62aaded72ed57af1a75327ba14a5b0`. No product, formal test, golden, commit or push was changed.

The coefficient differs by **0.02**, or **9.090909% of 0.22**. This is a slope-coefficient difference, **not a loudness percentage error**. For a real common-input slope case, changing the cell from 0.22 to 0.24 within each implementation changes unweighted N by approximately **−0.016866 sone in SQAT and official C**, and **−0.017 sone in MoSQITo with its native rounding**. These are within-implementation cell effects; discrepancies from the official-C baseline are listed separately in the common-input table. Public end-to-end maximum cell effects are in the second table below.

Three quantities are kept separate: (1) original baseline discrepancy from the supplied rounded official workbooks, (2) original baseline discrepancy from freshly computed full-precision official C, and (3) the difference between two native runs that change only USL[12][4]. Baselines are SQAT=.24, MoSQITo=.24, official C=.22. Counterfactuals reverse that one cell. Baseline discrepancies also contain frontend, numerical-constant, sampling-boundary and rounding effects; they cannot all be assigned to USL.

{shared}
## Interpretation and limits

- SQAT was run by executing its pinned, unchanged `.m` files directly in **GNU Octave 8.4.0**, not by translating them to C or Python. MATLAB R2021a readiness was **BLOCKED** by expired license (Error −10). Therefore the numerical evidence is native SQAT source under Octave; MATLAB-runtime acceptance remains unverified.
- MoSQITo used its original public stationary/time-varying APIs for signals 2–25. For signal 1, which is already 28-band levels, the native private `_main_loudness` → `_calc_slopes` route was used; no public level-input API is claimed. Its slope function rounds N to .001 sone at N≤16 and .01 at N>16 before time weighting; this original behavior is retained.
- The largest MoSQITo baseline workbook N discrepancy is stationary signal 5: .0808 sone. Changing this USL cell has **zero** effect there. SQAT/official C stationary levels skip the first .2 s after filtering; the unchanged MoSQITo public stationary API uses its own frontend and whole-record average without a skip parameter. The discrepancy is not attributed solely to either frontend or skip, and is not a USL-cell error.
- Across the time-varying signals, MoSQITo baseline maximum workbook N discrepancy is {f(T['mos']['timevarying_6_25']['workbook']['N']['max_abs'])} sone; the .22 counterfactual maximum is {f(T['mos']['timevarying_6_25']['counterfactual_workbook']['N']['max_abs'])} sone. A one-cell change does not monotonically improve every aggregate maximum because other differences and cancellation remain.
- The real same-core case is signal 6 internal frame **13677**, **6.8385 s**. Selection was preregistered as the maximum raw, unweighted C cell effect over that signal's core frames. Every engine receives the identical 21 binary64 values in `common-core.json`; no frontend or temporal weighting is involved in this table. The SQAT slope wrapper mechanically extracts the original stage body; hashes and source-line boundaries are in `sqat-freeze.json`.
- The synthetic vector has only band 5 = .35 sone/Bark. Analytically, over a local .2-Bark segment, the specific difference is **.004 sone/Bark**, and its segment area difference is **.0004 sone**. These are not whole-pattern N differences. Official C and SQAT add .0001 Bark to ZUP, so the actual 4.6-Bark coordinate is .1999 Bark into the slope and yields about .003998; MoSQITo gives .004. The whole-pattern differences are separately tabulated above.
- Same-core zero-vector and stationary signal-2 negative controls have exactly zero cell effect in all three engines. Full native signals **1–5 and 25** likewise have zero N and N′ cell effect in every engine. Sensitive signals and affected counts are recorded separately; not every input exercises this coefficient.
- Input WAV integers were converted identically using `int16 / 32768 * 2*sqrt(2)` to double Pa, 48 kHz, mono; no output-driven calibration. Signal 15 uses diffuse field, all others free field. Workbooks are the supplied official four-decimal references: their comparison measures numeric discrepancy, not an assertion that those decimals are exact physical truth.
- Workbook N′ is available for full 240-Bark stationary profiles (1–5) and one selected Bark trajectory per signal 6–13. It is **not** a full 240×time reference for signals 6–25. Full-grid N′ differences in the C-reference and cell-effect tables use freshly executed outputs on all common coordinates. All N′ units are sone/Bark.
- MoSQITo's returned timestamps use endpoint-inclusive linspace and drift from its actual `[::24][::4]` data-sample grid. The initial exact-label assertion correctly failed; the documented deviation in `alignment-deviation.md` maps source-defined sample indices to physical 2-ms times, with **no interpolation, fitted shift, or loudness-value change**. Original reported timestamps remain in raw arrays; drift and unmatched tail frames are explicit. Tail values absent from workbooks are excluded only from workbook comparisons; common-C and within-engine comparisons retain their respective common/full grids.
- Relative error uses only |reference|≥1e−4; exclusions and the location of maximum relative error are in detailed JSON. Supplementary |N reference|≥1-sone figures were registered before metrics. RMS is coordinate-weighted over each stated pool. Counts `above_1e12` and `above_1e4` mean absolute error >1e−12 and >1e−4 respectively. The 1e−4 diagnostic reflects workbook precision and is **not** a normative acceptance threshold. Raw absolute-error maxima and percentage-error maxima generally occur at different coordinates.
- Source-level Table A.9 authority remains **PENDING**; this experiment does not resolve a normative table-versus-reference-code conflict, declare all standards requirements passed, or authorize changing product coefficients. Official-C-versus-itself zero is a reference identity, not independent proof.

## Provenance, replay and delivery

[SQAT v2.0](https://github.com/ggrecow/SQAT/releases/tag/v2.0), commit `94f489c053d1366da05d5e62838c3f54ac7715c3`, main source SHA-256 `1113ab411f8a6792bd0f7c972bc45124187324222ee8f7d43d9e0765fd57bd5b`; [MoSQITo 1.2.1](https://pypi.org/project/mosqito/), copied installed source frozen in `frozen-inputs.json`; original official C SHA-256 `a74b45ed297cd09ac60701a923120341137d227e536f3109ae4ece810d834491`. Official C was freshly rebuilt for this round with MSVC `/O2 /fp:precise`; no old numeric output was reused. The original C is included unchanged in an original wrapper that exports its native slope and core stages.

Read `replay.md`, `preregistration.md`, `preregistration-supplement.md`, `alignment-deviation.md`, `per-signal-metrics.json`, `stratified-summary.json`, `common-core.json`, `sqat-freeze.json`, `builds.json`, `raw-output-hashes.json`, `execution-audit.json` and `delivery-check.md`. Intentional worker scheduling restart and fixed harness-only preparation errors are retained in logs; they are distinguished from numerical outcomes. Full third-party sources, WAV, workbooks and large arrays remain in local tmp, with hashes; none is republished in this delivery. Delivery-file integrity hashes are computed after redaction and are distinct from original source/binary/input hashes.
'''
zh=f'''# F03 — SQAT、MoSQITo、官方 C 在 USL[12][4] 的實際誤差

**數值執行完成：**三套原生實作、兩種單格係數、全部24個 Annex WAV（2–25）加上第1號聲級輸入案例。開始於2026-11-05；完成於 {completed}。產品固定快照 `118322f8300dc752f1d38a79db230a2db5ff2870`；repository HEAD `493fd595ef62aaded72ed57af1a75327ba14a5b0`。未改產品、正式測試或golden，未commit/push。

這一格係數差 **0.02**，相對0.22為 **9.090909%**；這是斜率係數差，**不能當成響度誤差百分比**。對同一個真實21帶輸入向量，各實作自身將係數由0.22改為0.24後，未經時間加權的N變化：SQAT與官方C各約 **−0.016866 sone**，MoSQITo保留原生rounding後為 **−0.017 sone**。這些是各自的單格前後差；對官方C baseline的誤差另列於共同輸入表。完整端到端的單格最大影響另列第二表。

本報告分開三件事：①原樣baseline對官方四位小數工作簿的偏差；②原樣baseline對本輪重新計算之全精度官方C的偏差；③每套實作只改USL[12][4]一格後的原生前後差。Baseline：SQAT=.24、MoSQITo=.24、官方C=.22；counterfactual為反向單格版本。完整baseline偏差也含前端、常數精度、取樣尾端與rounding等差異，不能全部歸因於USL。

{shared}
## 解讀與證據邊界

- SQAT為固定版本、原樣`.m`檔在 **GNU Octave 8.4.0直接執行**，不是C/Python移植或C模擬品。MATLAB R2021a因授權過期Error −10而 **BLOCKED**，故本輪證據屬SQAT原生程式在Octave的數值實跑，不等於MATLAB runtime驗收。
- MoSQITo第2–25號使用原本公開stationary/time-varying API。第1號已是28帶聲級，走其原生private `_main_loudness` → `_calc_slopes`，不冒稱存在公開聲級輸入API。其slope stage原本就將N≤16取到.001 sone、N>16取到.01 sone，再進時間加權；本輪完整保留此行為。
- MoSQITo對工作簿的最大N偏差為穩態第5號 **.0808 sone**，而單格改動在此訊號的影響為 **0**。SQAT與官方C的穩態計算先濾波後跳過前.2秒，MoSQITo原樣公開穩態API則使用自身前端及全段平均、沒有skip參數。本輪未將該差異全部歸因於某一個前端或skip因素，也不能當成USL單格誤差。
- MoSQITo時變6–25號baseline最大工作簿N偏差為 {f(T['mos']['timevarying_6_25']['workbook']['N']['max_abs'])} sone；改成.22後最大值為 {f(T['mos']['timevarying_6_25']['counterfactual_workbook']['N']['max_abs'])} sone。由於其他差異與抵消仍存在，單格改動不保證每一種彙總最大誤差都下降。
- 真實共同core案例是第6號內部frame **13677、6.8385秒**，依預登記規則在該訊號全部官方C core frames選最大未加權N單格差。三套收到`common-core.json`中完全相同的21個binary64值，故此表排除前端與時間加權影響。SQAT stage wrapper直接機械抽取原本stage body，原碼行界與hash見`sqat-freeze.json`。
- 人工向量只有第5帶=.35 sone/Bark。解析上，局部.2 Bark區段的N′差是 **.004 sone/Bark**，該段面積差為 **.0004 sone**；這不是整體響度N的差。官方C/SQAT有ZUP+.0001 Bark，所以實際4.6 Bark點距起點.1999 Bark，差約.003998；MoSQITo則為.004。整個specific pattern積分的N差另外列於表中。
- 相同core的零向量與第2號穩態負控制，三套單格差都精確為0。完整原生訊號 **1–5及25** 的N和N′單格差也全部為0。是否真正走到該係數，取決於輸入與斜率區段，並非所有訊號都會受影響。
- 原始WAV一律`int16 / 32768 * 2*sqrt(2)`轉成double Pa、48kHz單聲道，沒有依輸出擬合校準。第15號diffuse，其餘free field。官方工作簿是四位小數參考值；比較的是數值偏差，不將小數顯示值視為無誤差物理真值。
- 工作簿N′涵蓋1–5號完整240 Bark profile、6–13號各一條指定Bark時間軌跡，**不是6–25號完整240×time參考矩陣**。對C及單格影響的全格點N′比較則使用本輪原生完整輸出。所有N′單位皆為sone/Bark。
- MoSQITo回傳時間標籤使用含終點的linspace，與實際`[::24][::4]`資料取樣格線有漂移。首次精確標籤assert已拒絕，後依`alignment-deviation.md`明記偏離原protocol，按原碼固定sample index映射2ms物理格線，**沒有插值、最佳配準位移或更動響度值**。原始回傳時間保留於raw arrays；漂移、額外尾端frame均列帳。工作簿未列的尾端只在工作簿比較排除，對C與同實作前後差各保留其共同或完整格線。
- 相對誤差只對|reference|≥1e−4計算，較小值的排除數與相對最大值座標均見詳細JSON；另補充預登記的|N reference|≥1 sone百分比。RMS按各表定義的格點池加權。JSON欄位`above_1e12`、`above_1e4`分別代表絕對誤差>1e−12、>1e−4。1e−4是工作簿精度診斷，**不是標準合格門檻**；最大絕對與最大相對誤差通常出現在不同座標。
- Table A.9權威原文判定仍 **PENDING**。這次不宣告標準全文所有要求通過、不處理規範表格與參考程式的權威衝突，也不授權修改產品係數。官方C對自身為0只是參考定義，不是額外獨立證明。

## 來源、重播與交付

[SQAT v2.0](https://github.com/ggrecow/SQAT/releases/tag/v2.0)，commit `94f489c053d1366da05d5e62838c3f54ac7715c3`、主檔SHA-256 `1113ab411f8a6792bd0f7c972bc45124187324222ee8f7d43d9e0765fd57bd5b`；[MoSQITo 1.2.1](https://pypi.org/project/mosqito/)，原始安裝source hash見`frozen-inputs.json`；官方C原碼SHA-256 `a74b45ed297cd09ac60701a923120341137d227e536f3109ae4ece810d834491`。官方C本輪以MSVC `/O2 /fp:precise`全新編譯，未沿用舊數值輸出；原創wrapper include原樣C並匯出其原生slope/core stages。

重播與細節見`replay.md`、`preregistration.md`、`preregistration-supplement.md`、`alignment-deviation.md`、`per-signal-metrics.json`、`stratified-summary.json`、`common-core.json`、`sqat-freeze.json`、`builds.json`、`raw-output-hashes.json`、`execution-audit.json`、`delivery-check.md`。刻意排程重啟與已修復的harness準備錯誤均留log，不當成數值失敗或隱藏。完整第三方原碼、WAV、工作簿、大型陣列只保留本機tmp與hash，不隨報告進庫。交付檔hash於去識別後計算，與原始來源/輸入/binary hash分開。
'''
translations={
 'Baseline versus supplied official workbook values':'原樣 baseline 對官方工作簿',
 'Native single-cell effect: 0.24 minus 0.22':'各原生實作的單格影響：0.24 減 0.22',
 'Input groups: N discrepancies in sone':'分組比較：N 偏差（sone）',
 'Same exact real-signal 21-band core vector':'相同真實21帶 core 向量',
 'Synthetic same-input slope case':'相同人工輸入的 slope 案例',
 'Full-precision comparison with unmodified official C':'對未改官方 C 的全精度比較',
 'Relative N metrics and affected coordinates':'相對 N 指標與受影響格點',
 'Specific-loudness detail':'比響度細節',
 'Length and time-label accounting':'長度與時間標籤列帳',
 'Implementation':'實作','Input group':'輸入組別','Official C / MSVC':'官方 C / MSVC',
 'original baseline N − C(.22)':'原樣 baseline N − 官方C(.22)',
 'own cell signed ΔN':'自身單格 signed ΔN',
 'baseline routes / variants':'baseline案例數 / 係數版本數',
 'extra output frames vs workbook (total)':'超出工作簿的frame總數',
 'max returned-label drift (s)':'回傳時間標籤最大漂移（秒）'}
for a,b in translations.items():zh=zh.replace(a,b)
(P/'report.en.md').write_text(en,encoding='utf8');(P/'report.md').write_text(zh,encoding='utf8')
print('Bilingual reports written',completed)
