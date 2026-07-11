//! R3-P3 跨語言 bitwise 契約的凍結工具(手動執行)。
//! 重凍:cargo test --test py_contract_dump -- --ignored --nocapture
//! Python 對應物:tools/iso532_testkit.py(contract_signal / fnv1a_f64)。

#[allow(dead_code)]
mod common;

use common::fnv1a_f64;
use iso532::FieldType;

fn contract_signal() -> Vec<f64> {
    (0..48_000_u64)
        .map(|i| ((i * 2_654_435_761) % 96_001) as f64 / 96_000.0 * 0.02 - 0.01)
        .collect()
}

#[test]
fn fnv1a_known_answer_matches_python_testkit() {
    assert_eq!(fnv1a_f64(&[0.0, 1.0, 2.0, 3.0]), 0xb905_57cf_d5e8_3390);
}

#[test]
#[ignore = "manual: freeze constants for iso532-py/tests/test_smoke.py (R3-P3)"]
fn dump_py_bitwise_contract_hashes() {
    let r = iso532::loudness_zwtv(&contract_signal(), 48_000.0, FieldType::Free).unwrap();
    eprintln!(
        "py-contract: n={:#018x} time={:#018x} frames={}",
        fnv1a_f64(&r.n),
        fnv1a_f64(&r.time_axis),
        r.n.len()
    );
}
