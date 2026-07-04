use std::time::Duration;

use criterion::{black_box, criterion_group, criterion_main, BenchmarkId, Criterion, Throughput};
use iso532::zwtv::third_octave_levels::third_octave_levels;
use iso532::{loudness_zwtv, simd, FieldType};

const FS: f64 = 48_000.0;
const BENCH_SECS: usize = 10;
const SIGNAL_LEN: usize = 48_000 * BENCH_SECS;

fn bench_signal() -> Vec<f64> {
    (0..SIGNAL_LEN)
        .map(|i| {
            let t = i as f64 / FS;
            0.25 * (2.0 * std::f64::consts::PI * 440.0 * t).sin()
                + 0.10 * (2.0 * std::f64::consts::PI * 1_760.0 * t).sin()
                + 0.04 * (2.0 * std::f64::consts::PI * 6_400.0 * t).sin()
        })
        .collect()
}

fn auto_dispatch_label() -> &'static str {
    if simd::avx2_available() {
        "avx2"
    } else {
        "auto_scalar_fallback"
    }
}

fn bench_third_octave_filter_bank(c: &mut Criterion) {
    let signal = bench_signal();
    let mut group = c.benchmark_group("filter_bank_10s");
    group.sample_size(10);
    group.measurement_time(Duration::from_secs(6));
    group.throughput(Throughput::Elements(signal.len() as u64));

    group.bench_function(BenchmarkId::new("scalar", signal.len()), |b| {
        simd::set_force_scalar(true);
        b.iter(|| {
            let (levels, n_time) = third_octave_levels(black_box(signal.as_slice()));
            black_box((levels, n_time));
        });
        simd::set_force_scalar(false);
    });

    group.bench_function(BenchmarkId::new(auto_dispatch_label(), signal.len()), |b| {
        simd::set_force_scalar(false);
        b.iter(|| {
            let (levels, n_time) = third_octave_levels(black_box(signal.as_slice()));
            black_box((levels, n_time));
        });
    });

    simd::set_force_scalar(false);
    group.finish();
}

fn bench_zwtv_pipeline(c: &mut Criterion) {
    let signal = bench_signal();
    let mut group = c.benchmark_group("zwtv_10s");
    group.sample_size(10);
    group.measurement_time(Duration::from_secs(6));
    group.throughput(Throughput::Elements(signal.len() as u64));

    group.bench_function(BenchmarkId::new("scalar", signal.len()), |b| {
        simd::set_force_scalar(true);
        b.iter(|| {
            let result = loudness_zwtv(black_box(signal.as_slice()), FS, FieldType::Free)
                .expect("benchmark signal is a valid 48 kHz ZWTV input");
            black_box(result);
        });
        simd::set_force_scalar(false);
    });

    group.bench_function(BenchmarkId::new(auto_dispatch_label(), signal.len()), |b| {
        simd::set_force_scalar(false);
        b.iter(|| {
            let result = loudness_zwtv(black_box(signal.as_slice()), FS, FieldType::Free)
                .expect("benchmark signal is a valid 48 kHz ZWTV input");
            black_box(result);
        });
    });

    simd::set_force_scalar(false);
    group.finish();
}

criterion_group!(benches, bench_third_octave_filter_bank, bench_zwtv_pipeline);
criterion_main!(benches);
