# Sources and authority boundary / 來源及權威邊界

Access date / 查核日期：2026-11-03 (Asia/Taipei).

| Source | Evidence and limitation |
|---|---|
| [Zwicker et al., 1991, original journal PDF](https://www.jstage.jst.go.jp/article/ast1980/12/1/12_1_39/_pdf) | 4-page original publication, 542,165 bytes, SHA-256 `9ada5cbaf31122d72e734ceb7929edd9f3517de84ea7c7d4bf93e4305ee6559d`. Parent agent downloaded and visually checked printed pp.40–42; Astra independently viewed rendered p.42. p.40 BASIC 3270 gives row 13, column 5 as 0.22; pp.40–41 define/load the 18×8 USL table. p.42 lines 6570/6630/6670/6690 use table-selected slope, linear interpolation and trapezoidal integration. This is a primary historical algorithm, not the 2017 normative table or an independent equation deriving USL. |
| [ISO 532-1 official catalog](https://www.iso.org/standard/63077.html) | Parent agent live web check: Edition 1, 2017-06, corrected 2017-11. Identifies the edition, not the target cell. |
| [ANSI-hosted ISO preview](https://webstore.ansi.org/preview-pages/ISO/preview_ISO%2B532-1-2017.pdf) | Parent agent live web text check: printed iv states “Table A.9 has been corrected.” Printed v describes normative reference software and numerical instructions. Preview does not expose the target cell or a derivation. Direct download returned 403 and web screenshot cache failed; no claim of visual A.9 inspection. |

主代理當日網路查證前兩項書目／預覽；Astra 使用傳回的來源資訊並另外目視 1991 p.42 公式。1991 原刊 PDF 留在本機 `tmp/f03-hypothesis-sources/`，不隨交付散布。保留 C 檔不是本輪重新下載；以 hash 固定既有保存附件，不能由來源名稱直接證明它與 2017-11 修正版一致。公開 preview 指出參考軟體有規範角色，但保存附件版本對應仍待證。

## Fixed local implementation inputs / 固定的本機實作輸入

Exact hashes and code locations are machine-readable in `results.json:source_hashes/source_locations`. The original source hashes cover bytes as read, including original line endings; derived-source hashes cover isolated experiment copies. Delivery manifest hashes cover post-redaction delivered bytes. These meanings are deliberately distinct.

- Rust `tables.rs` and `core/calc_slopes.rs`: extracted with `git archive` from `aa379db8f3dc37f5048ac6c8b7a6d4ba2a6c3b76`, not a mutable working tree. USL is `[[f64;8];18]`, target literal `0.24`; lookup clamps band index to 7. Target 21-band fixture starts the falling segment after band 4, i.e. C `IdxCL=5` and `IdxCBN=4`.
- Preserved official `ISO_532-1.c`: SHA-256 `a74b45ed297cd09ac60701a923120341137d227e536f3109ae4ece810d834491`; USL `double[18][8]`, target literal `0.22f`, converted from binary32 to binary64. RNS also uses float-suffixed constants. Input copied from earlier preserved source; no assertion that the repository commit includes this external file.
- Local MoSQITo 1.2.1 source: SHA-256 `35f3af5f8ad285be2d5c1778be2c3ba38caff425c086a00ac06300a3f22f33f3`; `_calc_slopes.py` creates a NumPy array without explicit dtype, which yields float64 for these values; source target literal `0.24`. AST extraction verifies shape `(18,8)`. This round inspects the saved implementation, tests independent Python/NumPy arithmetic and runs the actual isolated slope stage. It does not rerun the full audio pipeline. The unchanged `_get_rns_index.py` helper has SHA-256 `224cc41204a1e47d772f9fff10d7365c368078d4a4778bd7a09429d45000b176`; the package import is replaced by namespace injection only, with the change documented in diffs.

The target source rows are printed in `results.json`. At row 12, the C decimal source row is `[0.40,0.33,0.26,0.24,0.22,0.22,0.22,0.22]`; Rust/Python use `[0.40,0.33,0.26,0.24,0.24,0.22,0.22,0.22]`. Float storage does not convert a written 0.22 into 0.24. Correct data layout does not select the correct normative literal for the author.

可讀來源採查表式算法。本輪未取得能獨立決定此格的規範方程，也未取得授權 Table A.9 全文；不能斷言完整 ISO 文件絕不存在其他可用資訊，不能將兩個條件式輸出當成標準正值裁決。
