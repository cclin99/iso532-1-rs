# Phase 5：基準測試與收尾

**主計畫：** `docs/superpowers/plans/2026-07-03-iso532-rust-avx.md` 的 **Task 16–17** 與驗收清單。

## 範圍

| 主計畫任務 | 內容 |
|---|---|
| Task 16 | criterion 基準：zwtv 全 pipeline 與 filter bank 單獨，scalar vs AVX2，結果存 `docs/bench-results.txt` |
| Task 17 | `examples/cli.rs`（讀 48 kHz WAV 輸出響度）、README、crate-level rustdoc、clippy 乾淨 |

## 前置條件

- Phase 4 完成且全綠。

## 驗收

```bash
cd iso532
cargo bench 2>&1 | tee ../docs/bench-results.txt   # filter bank AVX2 目標 >= 2.5x scalar
cargo run --example cli -- "../data/annexb/Test signal 5 (pinknoise 60 dB).wav" --calib 2.8284271247461903
                                                    # N ≈ 10.42 sone（golden annexb_sig5/N.bin = 10.418）
cargo test && cargo doc --no-deps && cargo clippy -- -D warnings
```

最後對照主計畫底部的「驗收清單（對照 spec）」逐項打勾。

## 注意事項

- benchmark 若 AVX2 加速 <1.5×，主計畫 Task 16 有排查方向（store 分支移出內迴圈、批次化 lane 抽取），修完重測再記錄。
- README 的 benchmark 數字用真實測量值，不得填估計值。
- 收尾時處理 `cargo fmt --check`：`tables_noct.rs` 為生成物、非 rustfmt 格式——在 `tools/gen_tables.py` 輸出的兩個 `pub const` 前各加一行 `#[rustfmt::skip]` 後重新生成（不要手動 fmt 生成檔，否則下次重生又髒）；另 `src/lib.rs` 缺檔尾換行。
- 完成後參考 `docs/ROADMAP.md`——後續擴充（C-ABI、Python binding、串流 API、其他標準）的架構預留已在該文件說明，本 phase 不實作。
