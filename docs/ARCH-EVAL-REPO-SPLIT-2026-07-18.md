# Architecture evaluation: three delivery options and the repo split (2026-07-18)
> 對照／Pair: [中文版](ARCH-EVAL-REPO-SPLIT-2026-07-18.zh-TW.md) · source: zh · synced 2026-11-01

> Question under evaluation: if all three options are offered to users at the same time, is the current architecture viable? Split into 3 repos or 2?
>
> 1. Stationary computation + C-ABI + Python bindings
> 2. Time-varying engine + C-ABI + Python interface
> 3. Time-varying engine + display panel (GUI / VST)

## Conclusion

**The current architecture is viable; no refactor is needed to ship the three options together. Split into 2 repos**: the existing <REPO> becomes the "engine repo" and carries options 1+2; the display panel gets a separate "application repo". Splitting into 3 is the wrong direction.

## Current state

`iso532-ffi` and `iso532-py` both depend directly on the same core crate via `path = "../iso532"`; inside the core, the stationary path (zwst) and the time-varying path (zwtv batch + `ZwtvStream`) share the same filterbank/loudness kernels.

| Delivery surface | Stationary (option 1) | Time-varying (option 2) |
|---|---|---|
| Rust core | ✅ | ✅ |
| C-ABI (iso532.h) | ✅ | ✅ `iso532_stream_*` (v1 frozen) |
| Python | ✅ `loudness_zwst` | ⚠️ batch `loudness_zwtv` only; `ZwtvStream` not yet bound as a pyclass (purely additive gap, not a structural problem) |

## Why options 1 and 2 are not separated (against 3 repos)

- Both share the kernels of the same core crate. Separating them means either duplicating the DSP or introducing a fragile cross-repo core dependency.
- **The v1-frozen header is a single artifact that covers both the stationary and the streaming functions.** Splitting the repo would cut one frozen surface into two halves that evolve independently.
- CI gates such as hash gate 12/12 and parity 18/18 are shared. Splitting would require duplicating the whole gate set, for zero benefit.

## Why the panel becomes a second repo

Option 3 is by nature an **application**, not a library:

- **Dependency weight**: a GUI framework (egui/iced, or JUCE/nih-plug on the VST route) drags a large number of dependencies into the lockfile, pollutes the engine's deterministic build environment, and doubles CI time.
- **Release cadence**: the engine follows a "frozen + bit-exact determinism" discipline: slow changes, every change through the hash gate. The panel is UI iteration: fast changes, no bit-exact gate. Mixing them makes each hold the other back.
- **Clean consumption**: the panel consumes the engine through the frozen C-ABI (or a git-tag dependency on the Rust crate). It is exactly the first real user of the v1 frozen surface and validates the ABI design from the other side.
- **Licence isolation**: if the VST route uses JUCE (GPL / commercial dual licence), a separate repo keeps the engine licence clean.

## Final shape

```
repo A（現有 <REPO>）— 引擎
  iso532        core（靜態+動態 kernel）
  iso532-ffi    C-ABI → iso532.h + dll/lib（方案1+2 的 C 出口）
  iso532-py     wheel（方案1+2 的 Python 出口）

repo B（新開）— 面板/VST
  依賴 repo A 的 tagged release（C-ABI binary 或 crates.io/git dep）
```

One CI run of repo A produces every library artifact (crate, header+dll, wheel); users of the three options take what they need.

## To do (not urgent)

- The three crates in repo A are sibling directories with no root workspace `Cargo.toml`. Add one before the panel work starts, so that `cargo test --workspace` covers everything.
- The Python streaming interface for option 2 (`ZwtvStream` bound as a pyclass) is purely additive and can be scheduled for the next Codex round.
