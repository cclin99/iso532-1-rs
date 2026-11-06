# Delivery check

- PASS: 150 native route/variant output files (three implementations × two variants × 25 cases) passed finite-value and shape checks; raw arrays remain in tmp.
- PASS: MoSQITo and SQAT baseline sources match frozen hashes; each isolated coefficient variant differs by exactly one ASCII digit. Fresh official-C wrapper outputs are bitwise identical to fresh evaluations through the prior original-C DLL on all 25 cases.
- PASS: original input/source hashes preserved. No product/formal-test/golden changes; no commit or push. Prior-round delivery is retained.
- PASS: matching English/Traditional-Chinese numeric tables, valid escaped Markdown table separators, parseable JSON. Report references native Octave explicitly; MATLAB remains BLOCKED. Table A.9 authority remains PENDING.
- PASS: ran the repository redactor, then --check. Inspected all delivery suffixes and UTF-8 decodability separately: no unsupported formats, no non-UTF-8/skipped files, no residual identifying paths. MATLAB's entire license-search-path was manually replaced with `<MATLAB_LICENSE_SEARCH_PATH>`; no machine/license identifier remains. Original log hash is separately labelled in execution-audit.json.
- PASS: inspected the new delivery report diff plus command/log/provenance content. Scripts are original orchestration/wrappers; no complete third-party source, WAV, workbook, DLL or numeric array is in the delivery.
- PASS: delivery-integrity.json covers every final delivery file except itself, using post-redaction SHA-256 and byte size. Original input/source/binary/raw-output hashes have not been rewritten as if they identified redacted copies.

Detailed audit: delivery-audit.json; native controls: numeric-controls.json; execution deviations: execution-audit.json and alignment-deviation.md. This is scoped numerical evidence, not blanket standards or MATLAB-runtime acceptance.
