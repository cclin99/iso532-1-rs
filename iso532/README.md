# iso532

Rust implementation of ISO 532-1:2017 Zwicker loudness for calibrated pressure signals.

## Scope

- Stationary loudness: `loudness_zwst`
- Time-varying loudness: `loudness_zwtv`
- Input sample rate: 48 kHz only
- Output units: total loudness in sone and specific loudness in sone/Bark
- SIMD: AVX2+FMA dispatch for the time-varying filter bank and nonlinear decay kernels when supported by the host CPU

The implementation is validated against mosqito-generated golden data and ISO 532-1 Annex B reference checks in the repository tests.

## Usage

```rust
use iso532::{loudness_zwst, FieldType};

# fn main() -> Result<(), iso532::Iso532Error> {
let signal = vec![0.0; 48_000];
let loudness = loudness_zwst(&signal, 48_000.0, FieldType::Free)?;
println!("N = {:.3} sone", loudness.n);
# Ok(())
# }
```

```rust
use iso532::{loudness_zwtv, FieldType};

# fn main() -> Result<(), iso532::Iso532Error> {
let signal = vec![0.0; 48_000];
let loudness = loudness_zwtv(&signal, 48_000.0, FieldType::Free)?;
println!("{} time samples", loudness.n.len());
# Ok(())
# }
```

## CLI Example

```powershell
cargo run --example cli -- "../data/annexb/Test signal 5 (pinknoise 60 dB).wav" --calib 2.8284271247461903
```

Expected output is about `10.418 sone` for that WAV/calibration path.

## Validation

```powershell
cargo test
cargo doc --no-deps
cargo clippy -- -D warnings
cargo fmt -- --check
```

Golden data and generated coefficient tables are reproducible with:

```powershell
..\.venv\Scripts\python.exe ..\tools\gen_golden.py
..\.venv\Scripts\python.exe ..\tools\gen_tables.py
```

Run those commands from the `iso532` crate directory or adjust paths from the repository root.

## Benchmarks

Run:

```powershell
cargo bench 2>&1 | tee ../docs/bench-results.txt
```

The Phase 5 benchmark groups are `filter_bank_10s` and `zwtv_10s`, each comparing forced scalar dispatch with automatic AVX2 dispatch. These results were measured on 2026-07-04 on this machine and are also recorded in `docs/bench-results.txt`.

| Benchmark | Scalar median | AVX2 median | Speedup |
|---|---:|---:|---:|
| `filter_bank_10s` | 244.37 ms | 19.854 ms | 12.31x |
| `zwtv_10s` | 574.51 ms | 258.79 ms | 2.22x |

## Non-goals

- No non-48 kHz resampling in the public API
- No C ABI, Python binding, streaming API, VST plugin, or NEON kernel in this phase
- No implementation of other loudness standards beyond ISO 532-1