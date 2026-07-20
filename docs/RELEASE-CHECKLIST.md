# Release checklist

Run this checklist immediately before publishing a release or making the README public.

- [ ] Remove or rewrite the review-draft blockquote near the top of both `README.md` and `README.zh-TW.md`; no public README may say "not yet announced as a public release" or "尚未對外宣布發布".
- [ ] Re-run `tools/compare_mosqito.py` and update the date, environment, timing, and direct-parity values together.
- [ ] Run the commands under "Reproduce the evidence" / "重現驗證" from a locally regenerated golden environment.
- [ ] Confirm that `docs/GOLDEN-REGEN-SOP.md` still describes every prerequisite needed by a fresh clone.
- [ ] Check every capability and boundary statement against the tagged source and public artifacts.
- [ ] Review `THIRD_PARTY_NOTICES.md`, `CITATION.cff`, `SECURITY.md`, and community templates against the release tag and current repository settings.
- [ ] With the normal antivirus protection enabled, build and scan the release DLL/static library, wheel, and any plug-in bundle; record any detection by product, version, artifact hash, and exact build command. Do not treat a disabled-antivirus build as release evidence.
- [ ] Generate and publish SHA-256 checksums for every release artifact; verify downloaded artifacts against those checksums before smoke testing.
- [ ] Confirm that local-only files, archives, generated `data/`, credentials, and machine-specific paths are not staged.
