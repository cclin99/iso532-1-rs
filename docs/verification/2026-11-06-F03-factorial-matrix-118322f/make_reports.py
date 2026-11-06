"""Bilingual finite-design interpretation and standalone scientific effect plots."""
from pathlib import Path
import json,re,datetime
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
O=Path(__file__).resolve().parent
read=lambda n:json.loads((O/n).read_text())
A=read('stationary-cell-results.json');E=read('paired-effects.json');W=read('full-walsh-decomposition.json');C=read('all-tv-cancellation.json');B=read('tv-cell-results.json');R=read('reconstruction-controls.json');RC=read('tv-rounding-controls.json');AC=read('stationary-rounding-controls.json');K=read('crop-controls.json');rank=read('stationary-rankings.json')
TE=read('tv-paired-effects.json')
f=lambda x:f'{x:.12g}'
def table(h,rows):
 esc=lambda x:str(x).replace('|','\\|')
 return '\n'.join(['| '+' | '.join(map(esc,h))+' |','|'+'|'.join(['---']*len(h))+'|']+['| '+' | '.join(map(esc,r))+' |' for r in rows])+'\n'
factors=['frontend_annex_minus_noct','calibration_cal_minus_sqrt','skip_0p2_minus_0','usl_024_minus_022']
main=[];hm=[]
for s in range(2,6):
 es=[next(x for x in E if x['signal']==s and x['backend']=='c' and x['factors']==[name])['paired_contrast']['N_signed'] for name in factors]
 interaction=max([x for x in E if x['signal']==s and x['backend']=='c' and x['order']==2],key=lambda x:abs(x['paired_contrast']['N_signed']))
 main.append([s,*map(f,es),' × '.join(interaction['factors']),f(interaction['paired_contrast']['N_signed'])]);hm.append(es)
main_table=table(['signal','Annex−noct','cal−sqrt','skip .2−0','USL .24−.22','largest pair interaction','DID (sone)'],main)
combo=[]
for s in range(2,6):
 cells=[next(x for x in A if x['domain']=='stationary' and x['signal']==s and x['frontend']==F and x['calibration']==G and x['backend']=='c' and x['skip_s']==.2 and x['usl']=='022') for F,G in [('noct','sqrt'),('noct','cal'),('annex','sqrt'),('annex','cal')]]
 combo.append([s,*[f(x['workbook']['N']['mean_signed']) for x in cells]])
combo_table=table(['signal','noct/sqrt','noct/cal','Annex/sqrt','Annex/cal'],combo)
point=next(x for x in C if x['signal']==15 and x['engine']=='mos')['fixed_audit_point'];crow=next(x for x in C if x['signal']==15 and x['engine']=='mos')
point_table=table(['quantity at signal15, 9.606 s','sone'],[['workbook reference',f(point['reference'])],['Mo N022',f(point['N022'])],['Mo e022',f(point['e022'])],['cell d=N024−N022',f(point['delta_024_minus_022'])],['Mo N024',f(point['N024'])],['Mo e024=e022+d',f(point['e024'])]])
tv8=table(['calibration','USL','rounding','N at 9.606 s','error vs workbook'],[[x['calibration'],x['usl'],x['backend'],f(x['fixed_9p606s']['N']),f(x['fixed_9p606s']['workbook_error'])] for x in B if x['signal']==15 and x['backend'].startswith('mos')])
round_table=table(['mode/control','maximum absolute N rounding effect (sone)','Nprime changed?'],[['stationary, all 64 matched pairs',f(max(abs(x['N_rounding_effect']) for x in AC)),'no; bitwise equal'],['TV representatives, all 16 matched pairs',f(max(x['N_rounding_effect']['max_abs'] for x in RC)),'no; bitwise equal']])
crop_table=table(['signal','frontend','crop/reset − post-filter skip N (sone)','max specific-loudness difference (sone/Bark)'],[[x['signal'],x['frontend'],f(x['crop_reset_minus_postfilter_skip']['N_signed']),f(x['crop_reset_minus_postfilter_skip']['Nprime_max_abs'])] for x in K])
ranking_table=table(['signal','backend','criterion vs workbook','best cell','best error','worst cell','worst error'],[[x['signal'],x['backend'],x['criterion'],x['best']['id'],f(x['best']['error']),x['worst']['id'],f(x['worst']['error'])] for x in rank if x['reference']=='workbook' and x['backend']=='mos-round'])
tvsummary=table(['signal','backend','min cell max |N error| vs workbook','max cell max |N error| vs workbook'],[[s,b,f(min(x['workbook']['N']['max_abs'] for x in B if x['signal']==s and x['backend']==b)),f(max(x['workbook']['N']['max_abs'] for x in B if x['signal']==s and x['backend']==b))] for s in [6,15,16,25] for b in ['c','sqat','mos-round','mos-noround']])
gu=[]
for b in ['c','sqat','mos-round','mos-noround']:
 n=max([x for x in TE if x['backend']==b and x['outcome']=='n' and x['contrast']=='calibration_x_USL'],key=lambda x:x['max_abs'])
 ns=max([x for x in TE if x['backend']==b and x['outcome']=='ns' and x['contrast']=='calibration_x_USL'],key=lambda x:x['max_abs'])
 gu.append([b,f(n['max_abs']),n['signal'],f(n['max_time_s']),f(ns['max_abs'])])
gutable=table(['backend','max |calibration × USL DID| N (sone)','signal','time (s)','max |DID| Nprime (sone/Bark)'],gu)
fig,axs=plt.subplots(1,2,figsize=(14,4.8),gridspec_kw={'width_ratios':[1.2,1]})
arr=np.array(hm);lim=max(abs(arr).max(),.001);im=axs[0].imshow(arr,cmap='RdBu_r',vmin=-lim,vmax=lim,aspect='auto')
axs[0].set_xticks(range(4),['Annex-noct','cal-sqrt','skip .2-0','USL .24-.22'],rotation=18,ha='right');axs[0].set_yticks(range(4),['signal2','signal3','signal4','signal5']);axs[0].set_title('Stationary: paired mean effects, C downstream\nSigned change in N; fixed reference cancels in contrast')
for i in range(4):
 for j in range(4):axs[0].text(j,i,f'{arr[i,j]:+.5f}',ha='center',va='center',color='white' if abs(arr[i,j])>lim*.6 else 'black',fontsize=9)
fig.colorbar(im,ax=axs[0],label='paired N effect (sone)',shrink=.8)
e0=point['e022'];d=point['delta_024_minus_022'];e1=point['e024'];axs[1].bar([0,1,2],[e0,d,e1],bottom=[0,e0,0],color=['#4477aa','#dd9933','#228833']);axs[1].plot([0,1],[e0,e0],'k--',lw=.8);axs[1].plot([1,2],[e1,e1],'k--',lw=.8)
axs[1].set_xticks([0,1,2],['.22 error','cell .24-.22','.24 error']);axs[1].set_ylabel('signed N error vs workbook (sone)');axs[1].set_title('Time-varying MoSQITo: cancellation\nsignal15 at the same 9.606 s coordinate')
for i,value in enumerate([e0,d,e1]):axs[1].text(i,(e0 if i==1 else value)+.0006,f'{value:+.9f}',ha='center',fontsize=9)
axs[1].set_ylim(0,max(e0,e1)*1.22);axs[1].grid(axis='y',alpha=.2);fig.tight_layout()
fig.savefig(O/'factorial-effects.svg',metadata={'Creator':'ISO532 independent numerical verification','Date':None});fig.savefig(O/'factorial-effects.png',dpi=160,metadata={'Software':'ISO532 independent numerical verification'});plt.close(fig)
maxrecon=max(x['max_reconstruction_error'] for x in R);higher=max(abs(x['paired_contrast']['N_signed']) for x in W if x['order']>=3 and x['backend']!='mos-five-factor')
now=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat()
shared=f'''## Stationary paired effects: C downstream, sone

{main_table}
## Same-window combination errors versus workbook

Fixed: post-filter skip=.2 s, C downstream, USL=.22. Values are signed N errors in sone.

{combo_table}
## Fixed-coordinate cancellation

{point_table}
## Calibration and rounding at that same coordinate

{tv8}
## Rounding isolation

{round_table}
## Crop/reset negative control

{crop_table}
## Separate N and Nprime rankings: Mo original-rounding downstream

{ranking_table}
## TV representative matrix range

{tvsummary}
## TV calibration × USL interaction

Pointwise paired DID; maximum absolute magnitude over the four representative signals.

{gutable}
'''
en=f'''# F03 — multi-factor numerical matrix

Completed {now}; product `118322f8300dc752f1d38a79db230a2db5ff2870`, repository HEAD `62e8559e8fe01350b9e07148784a6635d4522691`. Scope: **304 new evaluations** (256 stationary factorial + 8 crop controls + 40 TV cells), **24 verified reused TV cells**, plus reanalysis of **120 prior native TV output files** (overlapping those 24, not extra executions). All inputs are binary64 Pa. No product, DSP, formal-test, golden, old evidence, commit or push changes.

**The combinations show real cancellation and interaction; one coefficient change does not necessarily reduce the overall maximum error.** At Mo signal15/time9.606 s, the .22 signed error is +{f(e0)} sone, and switching to .24 adds {f(d)} sone, leaving +{f(e1)} sone. Thus the .24 coefficient partly cancels a pre-existing positive residual. Returning to .22 removes that cancellation and raises this measured error. This comparison uses the **same input, implementation, timestamp and workbook reference**, not a subtraction of unrelated maxima.

![Paired stationary effects and fixed-coordinate cancellation](factorial-effects.png)

{shared}
## What the matrix establishes

- Under the registered stationary design, **USL has exactly zero effect in all 128 matched pairs**. The chosen steady signals do not exercise this table cell. This says nothing about other possible stationary spectra; the prior synthetic sensitive case already demonstrates nonzero slope-stage effects.
- Filter and calibration dominate different signals. For C downstream, signal2's average Annex−noct effect is −.0228833436061 sone and cal−sqrt is +.0216286026111; their signs oppose. Signal5's corresponding effects are +.0786953423658 and +.0163602082209, reinforcing in N. Fixed-cell errors in the second table show why an altered calibration may reduce a noct residual on one signal but worsen an Annex result already near the workbook. This is a diagnosis of reference agreement, not proof which calibration is physically authoritative.
- Window and frontend are not independent additive knobs. Signal2's frontend×post-filter-window **paired DID = −.00271491349798 sone**. The complete Walsh decompositions retain all higher orders: largest registered order≥3 N contrast among four-factor groups is {f(higher)} sone, and maximum full reconstruction residual is {f(maxrecon)} sone. No high-order term is silently assumed zero.
- Main effect is the average matched high−low signed N difference; pairwise DID is average f11−f10−f01+f00. With ±1 coding, these equal 2×first-order and 4×second-order Walsh coefficients. Full coefficients and paired contrasts are separately labelled. Engine mode is categorical and contains multiple numerical decisions; differences between engine names are not interpreted as one isolated causal factor. No p-values or random-population claims are made.
- At signal15, .24 improves {crow['024_improves']} workbook N coordinates, worsens {crow['024_worsens']}, and leaves {crow['unchanged']} unchanged within 1e−12. The maximum-error coordinate favors .24 because of cancellation, while many other points favor .22. Detailed decomposition also distinguishes opposing-sign effects that overshoot, with full-grid Nprime against fixed C022 and available workbook Nprime trajectories separately reported.
- Removing Mo rounding preserves Nprime bitwise in all matched stationary and TV pairs. It does **not** eliminate the signal15 residual: the eight-cell fixed-coordinate table shows both increases and decreases in error. Rounding occurs after slope integration but before time weighting; its actual downstream effect is measured, not inferred from a .001/.01 nominal step.
- The two calibration factors are exactly 2sqrt(2) and .02/RMS(original calibration PCM)=2.835797716391444, a +.0226050990304 dB input-level change. The TV matrix has no stationary skip factor. At the shown signal15 coordinate, this calibration increase raises the residual by about .015 sone; it does not explain away the original roughly .023-sone discrepancy.
- Cropping before filtering is not equivalent to discarding the initial part of the already-filtered record. The negative-control table quantifies filter reset and (for noct) decimation effects. The primary matrix always filters the full input before post-filter RMS skipping.
- Best/worst ranks are separate for N and Nprime, within each signal/backend/reference. Rankings are limited to this finite grid, not recommended product settings. Tied best/worst cells may be multiple; tables show the first/last sorted representative, not a unique optimum. In particular, both USL values are equivalent throughout this stationary matrix. No conclusion is based on official-C-versus-itself zero; workbook comparisons and hybrid labels remain explicit.

## Native stages, controls and evidence boundaries

Mo noct is a **time-domain** decimate→Butterworth SOS→RMS frontend. The only audit adaptation adds post-filter RMS slicing. At skip0 all 28 levels match the original native API bitwise for all eight signal/calibration controls. Both frontends use the same post-filter time rule; no FFT surrogate is used. 32 primary level vectors feed three original implementations, with Mo no-round as a diagnostic mode. SQAT executes pinned v2.0 `.m` source directly in explicitly authorized GNU Octave 8.4.0; public method0 receives shared levels. Mo uses native main/slope stages; official C uses its native level API. These recombinations are **hybrid diagnoses**, not claims about unchanged public end-to-end behavior. B's native modes use original public time-domain pipelines; no-round is labelled diagnostic.

The first stationary harness attempt was correctly rejected by an exact-repeat assertion: official C's level API modifies its caller's level array. The adapter now supplies an independent copy and checks the shared input bytes after every call. The complete stationary experiment was rerun; original algorithms and repeat thresholds were not changed. The rejected log is retained. Skip0 parity, per-mode exact repeats, frozen-source isolation, input equality, full factor coverage, old-manifest integrity, time-grid checks and paired no-round Nprime controls are retained in machine-readable evidence.

C and SQAT returned timestamps must match their physical 2-ms grid; Mo's original endpoint-linspace labels are preserved and mapped by its fixed `[::24][::4]` source sample indices. Workbook time labels are asserted against the same grid. No fitted shift/interpolation is used. Extra tails are explicitly recorded. Nprime is 240 Bark bins at .1 Bark spacing; time/Bark coordinates accompany TV maxima. Workbooks contain full stationary Nprime profiles and only selected TV Bark trajectories for signals6–13; full-grid TV Nprime reference is C022, not an invented workbook matrix.

Relative errors exclude |reference|<1e−4 and count exclusions; where no denominator qualifies, relative error is null. RMS is over the stated coordinate set. Effects and errors use different reference meanings; zero-reference contrast summaries do not imply a meaningful relative percentage. Thresholds are numerical-control tolerances, not ISO conformity limits. Table A.9 authority remains unresolved. Results support diagnosis, not automatic DSP edits or standards claims.

## Reproducibility

See bilingual preregistration, `design-matrix.json`, `frozen-inputs.json`, `shared-levels.json`, `stationary-cell-results.json`, `paired-effects.json`, `full-walsh-decomposition.json`, `stationary-rankings.json`, `tv-cell-results.json`, `tv-paired-effects.json`, `all-tv-cancellation.json`, `all-tv-specific-cancellation.json`, `replay.md`, and `delivery-check.md`. Original SQAT commit, Mo source files, official-C binaries and all original-input hashes are frozen. Prior delivery hashes remain untouched. Large arrays/third-party files stay in the new scratch directory; only original scripts, metrics, reports and visual evidence are delivered. Delivery integrity hashes identify final redacted bytes, separately from raw source/input/output hashes.
'''
zh=f'''# F03 — 多因素組合數值矩陣

完成於 {now}；產品`118322f8300dc752f1d38a79db230a2db5ff2870`，repository HEAD `62e8559e8fe01350b9e07148784a6635d4522691`。**304個新運算格**（穩態256＋crop控制8＋TV40），另**24格已驗hash的TV引用**；再分析**120份舊原生TV輸出**（含上述24，不能當新增執行加總）。輸入全部binary64 Pa，未改產品/DSP/正式測試/golden/舊證據，未commit/push。

**排列組合確實出現誤差抵消與交互作用；改一格不保證整體最大誤差下降。** Mo第15號9.606秒，.22的signed誤差是+{f(e0)} sone，切換.24加入{f(d)} sone後剩+{f(e1)}。也就是.24局部抵消另一個既存正殘差；改回.22反而失去抵消，使該點測得誤差增加。這是在**同輸入、同實作、同時間、同工作簿參考**的配對結果，不是拿不同位置的max相減。

![穩態配對效應與固定時間誤差抵消](factorial-effects.png)

{shared}
## 矩陣可以支持的判斷

- 本次穩態設計的**128組匹配USL前後差全部精確為0**：這些穩態測試訊號未走到該格，不代表所有可能穩態頻譜都不敏感；前輪人工敏感向量已證明slope stage可以有影響。
- 濾波與校準的主導程度依訊號而異。C下游的第2號平均Annex−noct為−.0228833436061 sone，cal−sqrt為+.0216286026111，符號相反；第5號則分別+.0786953423658、+.0163602082209，同向增加N。第二表固定格子的誤差顯示：某校準改動能讓noct殘差看似改善，卻使已接近工作簿的Annex結果變差。這是對參考值符合程度的診斷，不是判定哪種校準在物理上最權威。
- window與前端不能一律當成可直接相加的獨立旋鈕。第2號前端×post-filter window的 **paired DID=−.00271491349798 sone**。完整Walsh展開保留所有高階；四因子各組之中，三階以上N contrast的最大絕對值為{f(higher)} sone，完整重建最大殘差{f(maxrecon)} sone，沒有偷偷假設高階為0。
- 主效應是其他設定相同的high−low signed N平均；二階DID是匹配的f11−f10−f01+f00平均。±1編碼下分別是Walsh一階係數的2倍、二階係數的4倍，機讀結果分欄。不同engine名稱包含多種數值決策，不把其差異當單一純因子；確定性實驗不報虛構p值或隨機母體推論。
- 第15號.24讓工作簿N的{crow['024_improves']}個座標改善、{crow['024_worsens']}個惡化、{crow['unchanged']}個在1e−12內不變。最大誤差所在點因抵消而偏向.24，但許多其他點偏向.22。詳細分解另區分反向作用卻overshoot，完整240Bark Nprime對固定C022與工作簿可用軌跡也分開呈現。
- 取消Mo rounding，在所有匹配穩態/TV組的Nprime都逐位元不變；卻**無法消除第15號主要殘差**，固定座標8格顯示誤差有升有降。原rounding位於slope積分之後、時間加權之前，這裡量測其實際下游影響，沒有直接拿.001/.01取整步距當響度誤差。
- 校準因子精確為2sqrt(2)及.02/原始校準PCM RMS=2.835797716391444，輸入聲級提高.0226050990304 dB。TV矩陣沒有穩態skip因子；圖示第15號點提高校準後殘差增加約.015 sone，不能把原約.023 sone殘差解釋掉。
- 先crop再filter-reset，不等同濾完整段後才跳過前段RMS。負控制表直接量出reset與noct decimation相關差異；主矩陣一律先濾完整輸入再post-filter skip。
- N與Nprime最佳/最差分開排名，限同訊號/模式/參考及本有限網格，不是推薦產品設定。同值最佳/最差可能多組；表列排序首個/末個代表，不是唯一最優，尤其本穩態矩陣的兩種USL等效。不拿官方C對自身為0宣稱C勝出，工作簿與hybrid界線均明列。

## 原生stage、控制與證據邊界

Mo noct實際為**時域**decimate→Butterworth SOS→RMS，唯一audit改動是最後RMS取窗。skip0時8組訊號/校準的全部28帶都與原API逐位元一致；沒有FFT替代品。32個主矩陣聲級向量進三套原生下游，Mo no-round另標診斷模式。SQAT固定v2.0 `.m`直接在明確授權的GNU Octave8.4.0執行，method0收共同levels；Mo用原生main/slope stages，官方C用原level API。前後端互換是**hybrid診斷**，不是宣稱未改公開端到端行為。B的native模式走原本公開時間訊號pipeline，no-round仍明標診斷。

第一次A harness被exact-repeat正確攔下：官方C的level API會就地修改caller array。adapter已改每次獨立copy並逐次查共同輸入bytes不變，整個A完整重跑；沒有改原算法或放寬repeat門檻，拒絕log保留。skip0 parity、每模式repeat、source隔離、輸入相同、factor coverage、舊manifest完整性、格線及matched no-round Nprime控制皆有機讀證據。

C/SQAT原回傳時間必須符合物理2ms格線；Mo保留原endpoint-linspace標籤，依原碼`[::24][::4]`固定sample index映射。工作簿時間也assert同格線，未擬合位移或插值，額外尾端另列。Nprime為240個.1Bark格點，TV最大誤差附time/Bark；工作簿只有完整穩態profile及6–13號部分TV軌跡，完整TV矩陣參考是C022，不虛構工作簿資料。

相對誤差排除|reference|<1e−4並計數；完全無可用分母則null。RMS依各表格點集合；效應與誤差的參考意義不同，零reference的contrast摘要不能解讀有意義百分比。控制門檻不是ISO合格門檻；Table A.9權威仍未定，結論限診斷，不自動改DSP或宣稱標準全部通過。

## 重播與交付

見雙語預登記、`design-matrix.json`、`frozen-inputs.json`、`shared-levels.json`、`stationary-cell-results.json`、`paired-effects.json`、`full-walsh-decomposition.json`、`stationary-rankings.json`、`tv-cell-results.json`、`tv-paired-effects.json`、`all-tv-cancellation.json`、`all-tv-specific-cancellation.json`、`replay.md`、`delivery-check.md`。固定SQAT commit、Mo原碼、官方C binary與原始input hash，保留舊交付hash。大型陣列/第三方檔僅留新tmp，只交付原創script、指標、報告與圖。去識別後交付hash與原始source/input/output hash分開。
'''
translations={'Stationary paired effects: C downstream, sone':'穩態配對效應：C下游，單位sone','Same-window combination errors versus workbook':'相同window下的組合誤差：對工作簿','Fixed-coordinate cancellation':'固定座標的誤差抵消','Calibration and rounding at that same coordinate':'相同座標的校準與rounding組合','Rounding isolation':'rounding隔離','Crop/reset negative control':'crop/reset負控制','Separate N and Nprime rankings: Mo original-rounding downstream':'N與Nprime分開排名：Mo原始rounding下游','TV representative matrix range':'TV代表矩陣範圍','TV calibration × USL interaction':'TV校準 × USL交互作用','Pointwise paired DID; maximum absolute magnitude over the four representative signals.':'逐點配對DID，表列四個代表訊號中最大絕對值。','Fixed: post-filter skip=.2 s, C downstream, USL=.22. Values are signed N errors in sone.':'固定post-filter skip=.2秒、C下游、USL=.22；表值為signed N誤差，單位sone。'}
for a,b in translations.items():zh=zh.replace(a,b)
(O/'report.en.md').write_text(en,encoding='utf8');(O/'report.md').write_text(zh,encoding='utf8')
print('Reports and SVG/PNG written',now)
