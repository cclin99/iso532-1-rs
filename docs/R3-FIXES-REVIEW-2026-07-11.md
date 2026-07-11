# R3 審查修復:回歸審查報告(2026-07-11)

**審查對象:** Codex 依 `docs/superpowers/plans/2026-07-11-r3-review-fixes.md` 的實作(工作區未提交變更 15 檔 +229/−121,另 5 個新檔)
**實作紀錄:** `docs/R3-REVIEW-FIXES-IMPLEMENTATION-2026-07-11.md`;**前次審查:** `docs/R3-REVIEW-2026-07-11.md`
**方法:** 7 個 finder 角度並行(cross-file tracer 因 session 上限中斷,其檢查面由主審以第一手 grep/閱讀補齊)+ 主審逐項 inline 驗證(偏差:未用獨立 verifier agent,以第一手程式碼證據定判)
**結論 TL;DR — 計畫 13 個 task 全數落地且忠實,凍結契約(N/TIME hash、frames=500、錯誤碼表)逐位不變,原發現 #1–#9 全部收掉。新發現 10 項:前 4 項是「修復本身留下的同類缺口」(多數可溯源到計畫層級,非 Codex 走樣),建議入版前一併收掉(合計 diff 很小);其餘為效率/清理。無任何阻擋入版的正確性錯誤。**

---

## 1. 計畫符合度

Task 1–13 逐項核對全數落地:core `zwtv_out_frames`/`OUT_DECIM`/邊界測試、`Iso532Error::code()`/`FieldType` 轉換/凍結測試、ffi 常數/轉發/release 硬檢查/Safety 文件、header 再生、CI cbindgen 閘、GIL 前輸入複製、`parse_field` 走 core、importorskip、manifest 3.11 守衛、setup_env 三守衛+SOP、testkit(known-answer 互鎖)、py_contract_dump 遷移+CI 列入、smoke/bench 改吃 testkit。

**與計畫的偏差(均非缺陷):**
- 未依計畫做 per-task commit——全部工作留在工作區,一次也未提交。
- 額外交付 `.codex/skills/iso532-r3-verification/`(驗證方法固化,加分項;但見發現 #3)。
- Task 1 測試基底訊號公式與計畫略異(任何合法安靜訊號皆可,無影響)。
- 計畫文字「178 個 golden files」與現行 manifest 175 不符且 175 全數 match——計畫筆誤,非實作問題。

**入版警示:** `tools/iso532_testkit.py`、`iso532/tests/py_contract_dump.rs` 目前是**未追蹤**新檔。commit 時若只 `git add -u` 會漏掉,CI 立即紅(`--test py_contract_dump` 目標不存在;py smoke import 失敗)。`.codex/` 同為未追蹤。

## 2. 正式發現(10 項,依嚴重度排序)

| # | 位置 | 判定 | 摘要 |
|---|---|---|---|
| 1 | `iso532-ffi/src/lib.rs:138` | CONFIRMED | **內部不變量硬檢查只做了一半。**zwtv 的 `ISO532_ERR_INTERNAL` 守衛只驗 `n`/`n_specific`,隨後仍無檢查地複製 `bark_axis`(240)與 `time_axis`(frames);zwst 路徑完全沒有守衛就複製 `n_specific`/`bark_axis` 各 240。未來 core 打破這些長度不變量時,同一類 release 越界讀取(原發現 #2 的場景)在這些路徑依舊是 UB 而非 -4。修法:zwtv 補 `r.bark_axis.len() != 240 \|\| r.time_axis.len() != frames`;zwst 補 `r.n_specific.len() != 240 \|\| r.bark_axis.len() != 240`。*(計畫層級缺口——計畫只寫了 zwtv 的 n/n_specific。)* |
| 2 | `tools/setup_env.sh:16` | CONFIRMED | **3.11 守衛放在 `python -m venv .venv` 之後。**錯版本的系統 python 會先改寫既有 .venv 的 pyvenv.cfg 與直譯器(site-packages 仍是 3.11 的)再被守衛擋下——守衛要防的破壞已經發生。修法:守衛改查 `$PY_BOOT` 版本並移到 venv 建立之前。*(計畫層級缺口——計畫把守衛放在 venv 之後。)* |
| 3 | `.codex/skills/iso532-r3-verification/SKILL.md:34` | CONFIRMED | **skill 的 header 再生步驟未 pin cbindgen 0.29.4**,而 CI 閘 pin 死。本機 cbindgen 版本不同 → 再生出無害差異,skill 失敗規則(「有 diff 即 header 過期」)引導開發者提交它,CI 的 0.29.4 再生反過來紅——版本乒乓。修法:skill 步驟加 `cbindgen --version` 檢查為 0.29.4(或指示 `cargo install cbindgen --version 0.29.4 --locked`)。 |
| 4 | `tools/iso532_testkit.py:25` | CONFIRMED | **跨語言移植守衛用模組層 `assert`**——`python -O`/`PYTHONOPTIMIZE` 下被剝除,守衛靜默消失。修法:改 `if fnv1a_f64(...) != KNOWN_ANSWER: raise RuntimeError(...)`。*(計畫層級缺口——計畫指定 assert。)* |
| 5 | `iso532-py/tests/test_parity_mosqito.py:18` | PLAUSIBLE | **`importorskip("iso532")` 的反面代價:**受測物本身壞掉/忘 build 時整把 parity 傘靜默 SKIP 而非紅。這是原發現 #5 修法的已知取捨(SUT 不是 optional dep)。低成本補強:golden 環境跑 parity 的入口(SKILL.md 步驟 5 / SOP)明訂「skipped 計數非零即失敗」,或支援 `ISO532_REQUIRE_PARITY=1` 時改 fail。 |
| 6 | `.github/workflows/ci.yml:69` | CONFIRMED(效率) | **`cargo install cbindgen` 在 cache miss 時從源碼編譯 2–4 分鐘**(rust-cache 的 key 隨每次 stable toolchain 版本與 Cargo.lock 滾動)。改 `taiki-e/install-action@v2`(`tool: cbindgen@0.29.4`)拉預編譯二進位,~5 秒且不吃 cache 狀態。 |
| 7 | `iso532-ffi/tests/ffi.rs:184` | CONFIRMED(效率) | **200 輪 property test(15–90 s)如今在重驗 core 已單一來源化的公式**——core 新增的邊界測試已覆蓋「公式==pipeline」,ffi 層只需驗轉發:`iso532_zwtv_out_frames(len) == iso532::zwtv_out_frames(len)` 掃幾個點即可。與前次審查 §4 的 CI 效率清理項重疊,可併入該 chore PR。 |
| 8 | `tools/setup_env.sh:39` | CONFIRMED(低) | **tarball SHA256 在 requirements.lock 標頭與 setup_env.sh 各有一份手抄。**重 pin 時改了 lock 忘了腳本,守衛會拒絕合法新 tarball(或反向:守衛驗舊值而 lock 宣稱新值)。至少在兩處互相註明對方位置;或腳本從 lock 標頭 grep 出來。 |
| 9 | `iso532-py/tests/test_smoke.py:8` | CONFIRMED(低) | **tools/ 的 sys.path bootstrap 三處各自手刻**(test_smoke.py、test_parity_mosqito.py、bench_binding.py;且 bench 以 script 執行時 `sys.path[0]` 已是 tools/,該行是死碼)。iso532-py/tests/ 放一個 conftest.py 統一插入即可。 |
| 10 | `iso532-ffi/src/lib.rs:24` | CONFIRMED(低) | **整併後殘渣:**`error_code()` 已淪為 `e.code()` 的一行轉手(暗示 ffi 仍自有映射,誘導未來在錯層修碼);ffi 測試裡仍有約 10 處裸寫 0/1/2 場型字面值未改用新常數。刪 wrapper、測試改用 `ISO532_FIELD_*`。 |

## 3. 已駁回的候選(記錄理由)

| 候選 | 理由 |
|---|---|
| ffi 守衛硬編 240 應改用 `N_BARK_STEPS` | 駁回:240 在此是 **ABI v0 的凍結緩衝契約**(header 明文 240×frames),不是 core 內部不變量。core 若改 Bark 格線,對 C 端就是 ABI break,守衛回 -4 拒絕才是正確行為;讓守衛「跟著 core 走」反而會靜默寫爆呼叫端緩衝。py 側 `Array2::from_shape_vec((240,...))` 不符時安全報錯。 |
| `FieldType` 錯誤型別設計(FromStr 的 `Err(())` 太瘦 / TryFrom 的 `Err(i32)` 太肥) | 兩個角度互相拉反方向,恰證明是品味題:兩個 payload 都無承載者,行為已被凍結測試釘住,無可觀察缺陷。R5 動 core API 時若要正規 error type 再一併。 |
| setup_env.sh 的 Python heredoc 應改 `sha256sum -c` 一行 | 駁回:heredoc 走 venv python 是刻意的跨平台選擇(sha256sum/shasum 在各平台不一致),tarball 107 KB 讀入記憶體無感。 |
| CI 列入 `--test py_contract_dump` 多付一個 test binary 連結(10–30 s) | 駁回:讓手動重凍工具在 CI 持續編譯,防 bit-rot(要用時才發現編不過)是值得的保險;known-answer 測試折進 hash_gate 會失去這層。 |
| `OUT_DECIM` 可從 `pub(crate)` 降 private | 屬實但瑣碎,併入 #10 類清理即可。 |

## 4. 凍結契約驗證(採 Codex 回報 + 本審抽核)

Python 契約 `n=0x44e6822074554786 / time=0xf076bcb342595537 / frames=500` 不變;R1 四組 frozen hashes 不變;錯誤碼 1/2/3/-1/-2/-3 不變、新增 -4 僅擴充;FNV known-answer `0xB90557CFD5E83390` 雙語言互鎖成立(removed-behavior 角度逐位比對遷移前後演算法一致)。三 crate fmt/clippy/test 全綠、parity 18/18、manifest 175/175 為 Codex 本機結果;**CI 雙平台狀態仍待 push 後確認**(含新 cbindgen 閘與 C smoke)。

## 5. 處置建議

- **入版前順手修(diff 極小):** #1(補 4 個長度條件)、#2(守衛移前改查 $PY_BOOT)、#3(skill 加版本檢查)、#4(assert→raise)。
- **提交時注意:** 未追蹤新檔必須入 commit(見 §1 警示);建議按計畫的 phase 邊界拆 commit 而非一顆大球。
- **併入既定 chore PR:** #6、#7(與前次審查 §4 重疊)。
- **低優先清理:** #5、#8、#9、#10。

---

## 6. 回歸修復複審與提交前驗證(2026-07-11 追加)

Codex 依 §2 完成回歸修復(紀錄於實作文件「R3 回歸修復追加」節)。本節為主審第一手複審與本機 gate 實測。

### 6.1 發現逐項核對

| # | 狀態 | 第一手證據 |
|---|---|---|
| 1 | ✅ 收掉 | zwtv 守衛驗全四項(`n`/`n_specific`/`bark_axis`/`time_axis`,lib.rs:78–82);zwst 驗兩個 240(lib.rs:133)。皆在任何 unsafe copy 之前,違反回 -4 且不寫緩衝。 |
| 2 | ✅ 收掉 | 3.11 守衛改查 `${PY_BOOT[@]}` 並移到 `python -m venv` 之前(setup_env.sh:16–24)。 |
| 3 | ✅ 收掉 | SKILL.md 明訂 cbindgen 0.29.4 + `--locked` 安裝指令,與 CI 閘一致。 |
| 4 | ✅ 收掉 | testkit 改 `raise RuntimeError`;`python -O` 匯入實測通過;test_env_guards 以 AST 斷言全檔無 `assert`。 |
| 5 | ✅ 以選項 A 收掉(留一殘渣) | SKILL.md 步驟 5 明訂「18 passed、zero skipped 否則失敗」——即本報告建議的 SOP 路線。**殘渣:** SKILL.md 同時設定 `ISO532_REQUIRE_PARITY=1`,但測試碼並無任何程式讀這個變數(全 repo grep 僅 SKILL.md 兩處)——它是 no-op,誤導讀者以為有機械強制。建議下次順手從 SKILL.md 移除該行,或真的在 conftest 實作它。 |
| 6 | ✅ 收掉 | CI 改 `taiki-e/install-action@v2`(tool: cbindgen@0.29.4)。 |
| 7 | ✅ 收掉 | 200 輪 property test 改為 11 個代表性邊界的 core 轉發檢查 + 短長度不 panic 檢查(ffi.rs:183–193)。 |
| 8 | ✅ 收掉 | setup_env.sh 以 regex 從 requirements.lock header 讀 SHA,強制恰一筆;test_env_guards 斷言腳本不再內嵌 hash 字面值。lock header 格式與 regex 實測吻合。 |
| 9 | ⚠️ 部分/紀錄不符 | 實作紀錄稱「bootstrap 集中於 conftest」,但 **iso532-py/tests/conftest.py 不存在**;test_smoke.py 與 test_parity_mosqito.py 仍各自手刻 `sys.path.insert`。實際只修了 bench_binding.py(改插 `parent`,語意正確)。原判定即為低優先,現狀可接受,但實作紀錄該句與現實不符,留待下輪清理時一併訂正。 |
| 10 | ✅ 收掉 | `error_code()` wrapper 已刪,`Err(e) => e.code()` 直呼;ffi 測試改用 `ISO532_FIELD_FREE/DIFFUSE` 常數,並新增 `field_constants_are_frozen`。 |

新增交付 `tools/test_env_guards.py`(3 個靜態契約測試鎖住 #2/#4/#8 的修法)——加分項,防止守衛被未來重構默默移回錯位置。

### 6.2 本機 gate 實測(主審執行)

- core:fmt/clippy 乾淨,`cargo test` 全綠(13 個 target 全 ok,含 hash_gate 與 py_contract_dump known-answer)。
- ffi:fmt/clippy(--all-features)乾淨,`cargo test --features test-panic` 10/10。
- py:fmt/clippy 乾淨,smoke 6/6(含 `test_bitwise_contract_n_and_time_axis`——N/TIME 凍結 hash 逐位不變)。
- 工具鏈:`bash -n` 通過;test_env_guards 3/3;testkit `-O` 匯入通過;`golden_manifest --verify` 175/175。
- header:本機 cbindgen 0.29.4 再生前後檔案相同,SHA256 `540c8138…dd55fd0` 與 Codex 回報一致;`git diff --check` 乾淨。(注意:header 在工作區已有變更時,`git diff --exit-code` 對 HEAD 必然非零——本機驗法是「再生前後 diff」,CI 驗法才是對已提交版本 diff。)
- parity 傘:主審重跑 18/18 passed、0 skipped(zwtv+zwst × 9 訊號,65.8s)。

### 6.3 判定

**可提交。** 10 項發現中 9 項確實收掉、1 項(#9)為低優先部分完成且僅實作紀錄措辭不符;凍結契約(R1 hashes、N/TIME、錯誤碼表、FNV 互鎖、header SHA)全部逐位不變;三 crate 與工具鏈 gate 本機全綠。殘留事項均不阻擋:
1. `ISO532_REQUIRE_PARITY` no-op 措辭(§6.1 #5)與 #9 的紀錄訂正——併入下輪清理。
2. push 後確認 GitHub Actions 雙平台全綠(cbindgen 閘、gcc/MSVC C smoke、py wheel job)——本機無法代驗的唯一缺口。

**推進判斷:** R3 出場條件在 2ee126a 已記錄達成,本輪審查修復+回歸修復閉環完成 → 提交並 push,CI 雙平台綠燈後即可展開 R4;#10 之 core error type 與既定 chore 項(見 §5)按原規劃分別遞延 R5 / chore PR,不構成 R4 前置。
