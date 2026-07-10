# Golden 資料再生 SOP(R-14)

`data/` 是 gitignored;本文是換機器、venv 損毀、或需要重生 golden 時的唯一程序。
**核心觀念:`tools/golden.sha256` 是 per-環境契約**——golden 位元組取決於生成
機器的 libm(scipy/numpy 底層),跨機器 SHA256 不同是預期行為,不是錯誤
(佐證:`docs/CI-HASH-GATE-DEBUG-2026-07-10.md`)。

## A. 同機器重生(venv 損毀 / data 誤刪)

前置:repo 根有 `mosqito-1.2.1.tar.gz`(sha256 見 `tools/requirements.lock` 標頭)。

    bash tools/setup_env.sh                                   # 建 .venv(從 requirements.lock 安裝)+ 抓 Annex B
    .venv/Scripts/python.exe tools/gen_golden.py              # 重生 data/golden(約 5–15 分鐘)
    .venv/Scripts/python.exe tools/golden_manifest.py --verify
    cd iso532 && cargo test --test golden_core --test golden_dsp --test golden_zwst --test golden_zwtv --test annexb

四步全過 = 鏈健在。`--verify` 失敗 ⇒ 環境已漂移(檢查 Python 小版本、
requirements.lock 是否被動過、mosqito tarball sha256)。

## B. 換新機器(SHA256 預期 mismatch)

1. 跑 A 的前兩步。
2. `--verify` **預期失敗**(libm 不同)。此時改跑 golden 測試:
   `cargo test --test golden_core --test golden_dsp --test golden_zwst --test golden_zwtv --test annexb`
3. 測試全綠 ⇒ 新環境的 golden 有效。重新凍結契約:
   `.venv/Scripts/python.exe tools/golden_manifest.py --generate`
   commit `tools/golden.sha256`,commit 訊息記錄新環境(OS/CPU)。
4. 測試有紅 ⇒ 不是環境噪音,是真回歸或上游版本漂移——停下來調查,
   不得直接重新凍結。

## C. 什麼會讓鏈斷掉(維護清單)

| 依賴 | 固化方式 |
|---|---|
| numpy/scipy 版本 | `tools/requirements.lock`(pip freeze 全鎖) |
| mosqito 1.2.1 | 本地 tarball + sha256(lock 標頭) |
| Annex B wav/xlsx | SHA256 在 `tools/golden.sha256`;來源是 MoSQITo GitHub repo tag v1.2.1(setup_env.sh) |
| Python 小版本 | 3.11(lock 標頭註記) |
| golden 位元組 | `tools/golden.sha256`(per-環境) |
