# G0' CI go-live debugging record: calibrating the cross-platform bitwise contract of the hash gate
> 對照／Pair: [中文版](CI-HASH-GATE-DEBUG-2026-07-10.zh-TW.md) · source: zh · synced 2026-11-01

Date: 2026-07-10
Scope: G0' evidence hardening, Task 7 (first GitHub Actions workflow goes live)
Result: windows-latest + ubuntu-latest all green; G0' Exit Gate fully met
Related commits: `e49de49` → `d67c5e6` → `fa728e7`

---

## 1. Background

Task 7 of the G0' plan (`docs/superpowers/plans/phases/phase-g0-evidence-hardening.md`) requires CI to be green on both platforms before R-12 can be closed. Codex had finished the workflow file and a local simulation, but at that time the repo had no remote, so the push and the CI verification stopped there. This document records the debugging process over three CI rounds after the remote was connected.

The core object under test is `iso532/tests/hash_gate.rs`: it runs the full zwtv pipeline on a synthetic signal and compares `(fnv1a(n), fnv1a(n_specific), fnv1a(time_axis))` bitwise against frozen constants, as a refactor invariance gate (risk report R-13 / §8.4).

## 2. Debugging timeline

### Round 0: infrastructure problems before the push

| Problem | Root cause | Action |
|---|---|---|
| `ssh -T git@github.com` rejected | The private key is in PuTTY format (`key`), which OpenSSH cannot read | Found pageant resident (bundled with SourceTree); switched to its plink: `git config core.sshCommand` pointing at plink, `ssh.variant plink` |
| The remote already had one commit (`785188c`, Apache LICENSE only) | GitHub initialised it when the repo was created | **Must not rebase**: local commit hashes are referenced by documents (R4 snapshot notes such as `e96dffa`). Used `merge --allow-unrelated-histories` instead to keep the whole history (`e49de49`) |

### Round 1: ubuntu hash_gate failure (anticipated by the plan)

**Symptom**: exit code 101; the hash_gate of the ubuntu job fails on the scalar assert.

**Root cause**: ULP-level differences in `sin`/`powf`/`log10` between Windows UCRT and glibc (the case anticipated in plan Task 7 Step 5).

**Key decision in the solution: reproduce locally instead of round-tripping through CI.**
GitHub `ubuntu-latest` = Ubuntu 24.04. Running an `ubuntu:24.04` container in local Docker (same glibc version) computes the Linux-side hash values directly; the freeze is done in one round, without the slow loop of "push → wait for CI → copy the log → push again":

```
docker run --rm -v <REPO>:/work -w /work/iso532 -e CARGO_TARGET_DIR=/tmp/target \
  ubuntu:24.04 bash -c "apt-get install curl build-essential && rustup(minimal) && \
  cargo test --test hash_gate -- --nocapture"
```

Notes: `CARGO_TARGET_DIR` must point to a path inside the container, so that Linux build products do not pollute the Windows `target/`; under Git Bash the docker path arguments need `MSYS_NO_PATHCONV=1`.

**A structural defect in the plan was fixed along the way**: the original test aborted on the scalar assert failure, so the AVX2 value was never printed and freezing a new platform needed two rounds. It was restructured to "compute and print both backends first, assert last", so a single failure log carries all freeze values.

**Output** (`d67c5e6`): per-OS `cfg` constants; the Linux values were frozen from the measurement in the ubuntu:24.04 container.

### Round 2: windows runner hash_gate failure (not anticipated by the plan; the most valuable discovery)

**Symptom**: now the **windows job** fails, and even the `n_specific` hash of the **scalar path** differs from the local machine:

| Environment | scalar spec hash | avx2 spec hash |
|---|---|---|
| Local Win10 / AMD Ryzen 5 3600 | `0xff98c57f3018ef94` | `0x3f241da3fe334097` |
| GitHub windows runner (Server/Intel) | `0x21ae529ebbe66622` | `0x2649927faed57e75` |

**Root cause**: the transcendental functions of Windows UCRT **dispatch their implementation at run time by CPU feature**, and the ucrtbase version varies with the OS build. Even on the same Windows, the AMD development machine and the Intel Server runner produce different libm results. Conclusion: **the assumption "hash constants frozen per OS" does not hold on Windows; the actual contract is per environment (OS build + CPU).**

**Rejected option**: freeze the constants of the GitHub runner (switching on the `GITHUB_ACTIONS` environment variable). Reason: GitHub hosted runners are a heterogeneous hardware pool, and UCRT changes with runner image updates. Frozen values would fail intermittently (flaky), and a flaky gate is worse than no gate (it trains people to ignore red).

**Adopted option** (`fa728e7`): make the contract honest.
- **Linux CI keeps the hard assert** (the glibc values have been measured to be stable across machines: local AMD container = GitHub Intel runner).
- **Windows CI becomes dump-only**: `HASH_GATE_DUMP_ONLY=1` (set per matrix.os in ci.yml). It still runs the full pipeline and still prints the hashes; only the comparison against frozen values is skipped.
- **Local Windows keeps the hard assert**: the frozen constants on the development machine remain the first line of defence for refactor invariance; when changing development machines, re-freeze according to the test comments.

## 3. Unexpected positive discovery: the main outputs are bitwise identical across platforms

Over the three rounds of measurement, across **all** environments (Win10/AMD, Windows Server/Intel, Ubuntu 24.04 glibc, scalar and AVX2 backends):

- `n` (total loudness time series) and `time_axis`: **bitwise identical** (`n=0xf3215787aaa48fbe`, `time=0xf076bcb342595537` never changed).
- Only `n_specific` carries libm ULP noise, and that noise is washed out in the rounding of the Bark integration sum, so it does not propagate into `n`.

**Direct consequence for R3**: cross-platform acceptance of the Python binding can use bitwise comparison on `n`/`time_axis` as the acceptance condition and tolerance comparison on `n_specific`. This is much stronger than the originally expected "everything by tolerance only".

## 4. Summary of the approach (methodology)

1. **Predictive planning**: the plan built the conditional handling for "ubuntu libm differences" into Task 7. When Round 1 happened no diagnosis was needed; the prepared script was executed. Only Round 2 was unexpected.
2. **Local reproduction beats CI round trips**: each CI round takes 5–10 minutes and log access is restricted (private repo, no gh CLI). A same-version Docker container compressed "obtain Linux measurements → freeze → verify" into one local round.
3. **Maximise information on failure**: restructuring the test to "compute and print everything, then assert" lets a single failure log carry the complete freeze information. This is an investment for future new platforms.
4. **The width of the contract follows the evidence**: the correct scope of the bitwise gate was not thought up; it was calibrated by three rounds of measurement (per-backend → per-OS → per-environment). When an assumption turns out wrong, change the declared scope of the contract instead of chasing frozen constants for an unstable environment.
5. **A flaky gate is worse than no gate**: the core reason for rejecting "freeze the runner constants". Dump-only is an honest downgrade: it declares explicitly "this environment is outside the frozen contract" while keeping full execution and observability.

## 5. Final state

- CI: windows-latest + ubuntu-latest all green (`fa728e7`); `REQUIRE_AVX2=1` is in effect, so SIMD tests cannot silently skip. R-12 closed.
- Three lines of defence for the hash gate: local Windows hard assert (development iteration), Linux CI hard assert (automated refactor invariance), Windows CI dump-only (execution coverage + observability).
- G0' Exit Gate 5/5 met; proceeding to R3 (C-ABI + Python binding) per risk report §11.
