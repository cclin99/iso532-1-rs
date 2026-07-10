# G0' CI 上線除錯紀錄：hash gate 的跨平台 bitwise 契約校準

日期:2026-07-10
範圍:G0' 證據硬化 Task 7(首個 GitHub Actions workflow 上線)
結果:windows-latest + ubuntu-latest 全綠,G0' Exit Gate 全數達成
相關 commit:`e49de49` → `d67c5e6` → `fa728e7`

---

## 1. 背景

G0' 計畫(`docs/superpowers/plans/phases/phase-g0-evidence-hardening.md`)的 Task 7 要求
CI 在兩個平台全綠才算 R-12 收口。Codex 完成了 workflow 檔案與本機模擬,但當時 repo
沒有 remote,push 與 CI 驗證停在那裡。本文記錄 remote 打通後三輪 CI 迭代的除錯過程。

核心受測物是 `iso532/tests/hash_gate.rs`:對合成訊號跑完整 zwtv pipeline,把
`(fnv1a(n), fnv1a(n_specific), fnv1a(time_axis))` 與凍結常數做 bitwise 比對,
作為 refactor invariance gate(風險報告 R-13/§8.4)。

## 2. 除錯時間線

### Round 0:推送前的基礎設施問題

| 問題 | 根因 | 處置 |
|---|---|---|
| `ssh -T git@github.com` 被拒 | 私鑰是 PuTTY 格式(`2026key-pri.ppk`),OpenSSH 讀不了 | 發現 pageant 常駐(SourceTree 內建),改用其 plink:`git config core.sshCommand` 指向 plink、`ssh.variant plink` |
| 遠端已有一個 commit(`785188c`,只含 Apache LICENSE) | GitHub 建 repo 時初始化 | **不能 rebase**——本地 commit hash 被文件引用(R4 snapshot 註記 `e96dffa` 等),改用 `merge --allow-unrelated-histories` 保留全部歷史(`e49de49`) |

### Round 1:ubuntu hash_gate 失敗(計畫預期內)

**現象**:exit code 101,ubuntu job 的 hash_gate 在 scalar assert 失敗。

**根因**:Windows UCRT 與 glibc 的 `sin`/`powf`/`log10` 有 ULP 級差異
(計畫 Task 7 Step 5 預判的情況)。

**解法上的關鍵決策——不等 CI 來回,本機重現**:
GitHub `ubuntu-latest` = Ubuntu 24.04。本機 Docker 跑 `ubuntu:24.04` 容器
(同版 glibc)直接算出 Linux 端 hash 值,一輪就凍結完成,不用「push → 等 CI →
抄 log → 再 push」的慢迴圈:

```
docker run --rm -v D:/ISO532:/work -w /work/iso532 -e CARGO_TARGET_DIR=/tmp/target \
  ubuntu:24.04 bash -c "apt-get install curl build-essential && rustup(minimal) && \
  cargo test --test hash_gate -- --nocapture"
```

注意事項:`CARGO_TARGET_DIR` 必須指到容器內路徑,避免 Linux 編譯產物污染
Windows 的 `target/`;Git Bash 下 docker 路徑參數要加 `MSYS_NO_PATHCONV=1`。

**順手修掉計畫的一個結構缺陷**:原測試在 scalar assert 失敗就中止,AVX2 的值
永遠印不出來,凍結新平台要跑兩輪。重構為「先算完並印出兩個 backend,最後才
assert」,一次失敗 log 就能拿到全部凍結值。

**產出**(`d67c5e6`):per-OS `cfg` 常數,Linux 值凍結自 ubuntu:24.04 容器實測。

### Round 2:windows runner hash_gate 失敗(計畫預期外,最有價值的發現)

**現象**:換 **windows job** 失敗,而且連 **scalar 路徑**的 `n_specific` hash
都與本機不同:

| 環境 | scalar spec hash | avx2 spec hash |
|---|---|---|
| 本機 Win10 / AMD Ryzen 5 3600 | `0xff98c57f3018ef94` | `0x3f241da3fe334097` |
| GitHub windows runner(Server/Intel) | `0x21ae529ebbe66622` | `0x2649927faed57e75` |

**根因**:Windows UCRT 的超越函數**按 CPU 特性在執行期分派實作**,且
ucrtbase 版本隨 OS build 不同。同是 Windows,AMD 開發機與 Intel Server runner
的 libm 結果就是不同。結論:**「hash 常數 per-OS 凍結」的假設在 Windows 不成立,
實際契約是 per-環境(OS build + CPU)**。

**否決的方案**:凍結 GitHub runner 的常數(用 `GITHUB_ACTIONS` 環境變數切換)。
理由:GitHub hosted runner 是異質硬體池,UCRT 也隨 runner 映像更新——凍結了
必然間歇性失敗(flaky),flaky 的 gate 比沒有 gate 更糟(會訓練人忽略紅燈)。

**採用的方案**(`fa728e7`):把契約改誠實——
- **Linux CI 維持硬 assert**(glibc 值已實測跨機器穩定:本機 AMD 容器 = GitHub Intel runner)。
- **Windows CI 改 dump-only**:`HASH_GATE_DUMP_ONLY=1`(ci.yml 內依 matrix.os 設定),
  照跑完整 pipeline、照印 hash,只跳過凍結值比對。
- **本機 Windows 維持硬 assert**:開發機的凍結常數仍是 refactor invariance 的
  第一道防線;換開發機時依測試註解重新凍結。

## 3. 意外的正面發現:主輸出跨平台逐位相同

三輪量測下來,跨**所有**環境(Win10/AMD、Windows Server/Intel、Ubuntu 24.04
glibc、scalar 與 AVX2 兩種 backend):

- `n`(總響度時間序列)與 `time_axis`:**bitwise 完全相同**(`n=0xf3215787aaa48fbe`、
  `time=0xf076bcb342595537` 從未變過)。
- 只有 `n_specific` 帶 libm ULP 噪音——而它在 bark 積分求和的捨入中被洗掉,
  不會傳染到 `n`。

**對 R3 的直接意義**:Python binding 的跨平台驗收可以直接對 `n`/`time_axis`
用 bitwise 比對當驗收條件,`n_specific` 用容差比對。這比原本預期的
「全部只能容差比對」強得多。

## 4. 解題思路總結(方法論)

1. **預測性計畫**:計畫在 Task 7 就內建了「ubuntu libm 差異」的條件處置步驟,
   Round 1 發生時不需要診斷,直接執行既定劇本。預期外的只有 Round 2。
2. **本機重現優於 CI 來回**:每輪 CI 要等 5–10 分鐘且 log 存取受限(私有
   repo、無 gh CLI)。Docker 同版容器把「取 Linux 實測值 → 凍結 → 驗證」壓縮
   成一輪本機操作。
3. **失敗時最大化資訊量**:重構測試為「全部算完印完才 assert」,讓單次失敗
   log 攜帶完整凍結資訊——這是對未來新平台的投資。
4. **契約寬窄要跟著證據走**:bitwise gate 的正確範圍不是想出來的,是三輪
   實測校準出來的(per-backend → per-OS → per-環境)。發現假設錯誤時,修改
   契約的宣告範圍,而不是追著不穩定的環境凍結常數。
5. **flaky gate 比沒有 gate 更糟**:否決「凍結 runner 常數」的核心理由。
   dump-only 是誠實的降級:它明確宣告「此環境不在凍結契約內」,同時保留
   完整執行與可觀測性。

## 5. 最終狀態

- CI:windows-latest + ubuntu-latest 全綠(`fa728e7`),`REQUIRE_AVX2=1` 生效,
  SIMD 測試不可能 silent skip——R-12 收口。
- hash gate 三層防線:本機 Windows 硬 assert(開發迭代)、Linux CI 硬 assert
  (自動化 refactor invariance)、Windows CI dump-only(執行覆蓋 + 可觀測)。
- G0' Exit Gate 5/5 達成,依風險報告 §11 進入 R3(C-ABI + Python binding)。
