# Delivery check / 交付檢查

This is artifact review of the independent Astra root-cause experiment, not another numerical run. The primary agent finalized this delivery after Astra stopped writing. No production source, test, golden, prior evidence, decision memo or audit closure row was changed. The verification index is outside this delivery and was updated separately.

本輪主要原因已量化；較小的斜率分段／比較殘差尚未完全隔離。取消逐影格捨入仍不符合 1e-14，因此不宣告 production 修復或 C-01 結案。

## Redaction and coverage / 去識別化與範圍

Both repository redaction passes were executed. Recorded precheck and final outputs are in redaction-final.log; skipped files and warnings are not treated as success. Every final file is strictly decoded as UTF-8, its extension is checked against the actual tool's supported set, and every text is independently checked with the tool's path rules. Unsupported extensions, non-UTF-8 files and skipped directories: none. No WAV or binary is delivered; native source and diffs use supported .txt extensions.

After all text/log writing, both redaction commands are repeated and must report zero changes and clean before the final integrity manifest is generated. Any subsequent change requires renewed redaction and hashes. The integrity manifest excludes only itself.

## Consistency and diff / 一致性與差異

Paired report tables match, preregistered design hashes match run-start.json, and all four primary baseline/replay and ordered-decomposition controls pass. The primary agent separately verified 28 ordered tail decimal/bit representations, residual threshold decisions and contribution sums. The failed rounding-removal-only gate is retained. Old C-01 delivery hashes remain unchanged.

diff-review.json records new-file diffs against NUL, with itself excluded from its own captured inventory. Every final text, including the diff log and integrity manifest, is checked again read-only after finalization. For git diff --no-index --check, exit 1 with empty diagnostic stdout means expected file differences. An initial artifact-QA run stopped on embedded unified-diff whitespace after applying redaction; those first redaction outputs were not retained. The repeat recorded passes verify the final state. Eight .diff.txt artifacts were individually reviewed: unified-diff blank context markers and preserved original/derived source whitespace trigger trailing-whitespace or EOF warnings. Their exact patch bytes are intentionally preserved; this is a documented artifact-format exception, not a numerical exception. Every such warning and file is recorded. All other files must have no whitespace diagnostic. Git's LF/CRLF future-conversion warnings are retained in the log, not interpreted as numerical failures.

## Hash meaning / Hash 語意

Raw input, source, binary, original execution and stage-array hashes preserve their original meaning. Diagnostic variants and transformations are separately labeled; they are not production changes. Post-redaction delivery bytes are identified only by delivery-integrity.json. These hashes do not assert equality to the unredacted source/input/binary files. The finalizer script is an artifact QA helper, not numerical evidence.
