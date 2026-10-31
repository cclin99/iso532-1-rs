//! V-01: unit and negative tests for the fail-closed Annex B verdict, the strict
//! CSV reader and the binary reader. Corrupted-file cases work on copies under a
//! unique temp directory; `data/` is never modified.

mod common;
use common::annexb_check::{
    annexb_csv, annexb_csv_path, annexb_dir, annexb_tolerance, annexb_verdict, InvalidReason,
    Verdict,
};
use common::read_bin_path;
use std::path::PathBuf;
use std::sync::atomic::{AtomicUsize, Ordering};

static COUNTER: AtomicUsize = AtomicUsize::new(0);

fn temp_file(stem: &str, bytes: &[u8]) -> PathBuf {
    let n = COUNTER.fetch_add(1, Ordering::Relaxed);
    let dir =
        std::env::temp_dir().join(format!("iso532-v01-{}-{}-{}", std::process::id(), n, stem));
    std::fs::create_dir_all(&dir).unwrap();
    let path = dir.join(stem);
    std::fs::write(&path, bytes).unwrap();
    path
}

fn pass(v: &Verdict) -> bool {
    matches!(v, Verdict::Pass { .. })
}

// ---------------------------------------------------------------- tolerance rule

#[test]
fn tolerance_is_max_not_additive() {
    // §6.1 control: 10.55 vs 10.0 passes the additive rule (0.55 <= 0.6) and must
    // fail the max rule (0.55 > 0.5).
    assert!(
        (10.55_f64 - 10.0).abs() <= 0.1 + 0.05 * 10.0,
        "additive rule control"
    );
    match annexb_verdict(&[10.55], &[10.0]) {
        Verdict::Fail {
            exceptions,
            points,
            worst_idx,
            worst_diff,
        } => {
            assert_eq!((exceptions, points, worst_idx), (1, 1, 0));
            assert!((worst_diff - 0.55).abs() < 1e-12);
        }
        other => panic!("expected Fail, got {other:?}"),
    }
}

#[test]
fn tolerance_floor_at_zero_reference() {
    assert_eq!(annexb_tolerance(0.0), 0.1);
    assert!(pass(&annexb_verdict(&[0.1], &[0.0])));
    assert!(!pass(&annexb_verdict(&[0.1000000001], &[0.0])));
}

#[test]
fn tolerance_at_the_crossover_reference_2() {
    // At ref = 2.0 both terms equal 0.1. The plan's literal 2.1 is not an exact
    // IEEE boundary (2.1 - 2.0 = 0.10000000000000009 > 0.1), so the cases use
    // exactly representable offsets on either side of the limit.
    assert_eq!(annexb_tolerance(2.0), 0.1);
    assert!(pass(&annexb_verdict(&[2.0625], &[2.0])));
    assert!(!pass(&annexb_verdict(&[2.125], &[2.0])));
}

#[test]
fn tolerance_relative_branch_reference_100() {
    assert_eq!(annexb_tolerance(100.0), 5.0);
    assert!(pass(&annexb_verdict(&[105.0], &[100.0])));
    assert!(!pass(&annexb_verdict(&[105.0000001], &[100.0])));
    // 106 fails both rules: a control that the max rule is not weaker.
    assert!(!pass(&annexb_verdict(&[106.0], &[100.0])));
}

#[test]
fn tolerance_relative_branch_reference_8() {
    assert_eq!(annexb_tolerance(8.0), 0.4);
    assert!(pass(&annexb_verdict(&[8.375], &[8.0])));
    // 8.5 passes the additive rule (0.5 <= 0.5) and fails the max rule.
    assert!(!pass(&annexb_verdict(&[8.5], &[8.0])));
}

#[test]
fn short_curves_are_compared_normally() {
    assert_eq!(annexb_verdict(&[1.0], &[1.0]), Verdict::Pass { points: 1 });
    assert_eq!(
        annexb_verdict(&[1.0, 2.0], &[1.0, 2.0]),
        Verdict::Pass { points: 2 }
    );
    match annexb_verdict(&[1.0, 2.5, 3.0], &[1.0, 2.0, 3.0]) {
        Verdict::Fail {
            exceptions,
            points,
            worst_idx,
            ..
        } => assert_eq!((exceptions, points, worst_idx), (1, 3, 1)),
        other => panic!("expected Fail, got {other:?}"),
    }
}

#[test]
fn worst_point_is_the_largest_excess() {
    // idx 1: diff 1.0, tol 0.1 (excess 0.9); idx 2: diff 6.0, tol 5.0 (excess 1.0).
    match annexb_verdict(&[0.0, 1.0, 106.0], &[0.0, 0.0, 100.0]) {
        Verdict::Fail {
            exceptions,
            worst_idx,
            worst_diff,
            ..
        } => {
            assert_eq!((exceptions, worst_idx), (2, 2));
            assert_eq!(worst_diff, 6.0);
        }
        other => panic!("expected Fail, got {other:?}"),
    }
}

// ----------------------------------------------------------------- fail-closed

#[test]
fn invalid_empty() {
    assert_eq!(
        annexb_verdict(&[], &[]),
        Verdict::Invalid(InvalidReason::Empty)
    );
    assert_eq!(
        annexb_verdict(&[1.0], &[]),
        Verdict::Invalid(InvalidReason::Empty)
    );
    assert_eq!(
        annexb_verdict(&[], &[1.0]),
        Verdict::Invalid(InvalidReason::Empty)
    );
}

#[test]
fn invalid_length_mismatch_has_no_common_range_pass() {
    assert_eq!(
        annexb_verdict(&[1.0, 1.0, 1.0], &[1.0, 1.0]),
        Verdict::Invalid(InvalidReason::LengthMismatch { got: 3, want: 2 })
    );
}

#[test]
fn invalid_non_finite_got() {
    assert_eq!(
        annexb_verdict(&[1.0, f64::NAN], &[1.0, 1.0]),
        Verdict::Invalid(InvalidReason::NonFinite {
            which: "got",
            idx: 1
        })
    );
    assert_eq!(
        annexb_verdict(&[f64::NEG_INFINITY], &[1.0]),
        Verdict::Invalid(InvalidReason::NonFinite {
            which: "got",
            idx: 0
        })
    );
}

#[test]
fn invalid_non_finite_reference() {
    assert_eq!(
        annexb_verdict(&[1.0, 1.0], &[1.0, f64::NAN]),
        Verdict::Invalid(InvalidReason::NonFinite {
            which: "reference",
            idx: 1
        })
    );
    // §6.1: an infinite reference used to pass the additive rule. Any got value
    // against +Inf is now Invalid, not Pass.
    assert_eq!(
        annexb_verdict(&[0.0, 1.0], &[0.0, f64::INFINITY]),
        Verdict::Invalid(InvalidReason::NonFinite {
            which: "reference",
            idx: 1
        })
    );
}

#[test]
fn invalid_negative_reference() {
    assert_eq!(
        annexb_verdict(&[0.0, -0.5], &[0.0, -0.5]),
        Verdict::Invalid(InvalidReason::NegativeReference { idx: 1 })
    );
}

// -------------------------------------------------------------------- CSV reader

fn signal3_csv_bytes() -> Vec<u8> {
    std::fs::read(annexb_dir().join("test_signal_3.csv"))
        .expect("data/annexb/test_signal_3.csv (run tools/setup_env.sh)")
}

fn with_row_replaced(bytes: &[u8], data_row_1based: usize, replacement: &str) -> Vec<u8> {
    // Line 0 is the header; data rows are 1-based after it.
    let text = String::from_utf8(bytes.to_vec()).unwrap();
    let mut lines: Vec<String> = text.lines().map(str::to_owned).collect();
    lines[data_row_1based] = replacement.to_owned();
    let mut out = lines.join("\n");
    out.push('\n');
    out.into_bytes()
}

#[test]
fn csv_copy_of_signal3_matches_the_name_based_reader_bitwise() {
    let copy = temp_file("test_signal_3.csv", &signal3_csv_bytes());
    let from_copy = annexb_csv_path(&copy);
    let from_name = annexb_csv("test_signal_3.csv");
    assert_eq!(from_copy.len(), 240);
    assert_eq!(from_copy.len(), from_name.len());
    for (i, (a, b)) in from_copy.iter().zip(&from_name).enumerate() {
        assert_eq!(a.to_bits(), b.to_bits(), "row {i}");
    }
}

#[test]
fn csv_header_bom_is_tolerated() {
    let bytes = signal3_csv_bytes();
    assert_eq!(
        &bytes[..3],
        b"\xef\xbb\xbf",
        "fixture is expected to carry a BOM"
    );
    let copy = temp_file("bom.csv", &bytes);
    assert_eq!(annexb_csv_path(&copy).len(), 240);
}

#[test]
#[should_panic(expected = ":121: cannot parse \"abc\"")]
fn csv_unparsable_row_panics_with_line_number() {
    let bytes = with_row_replaced(&signal3_csv_bytes(), 120, "abc");
    let copy = temp_file("bad_row.csv", &bytes);
    let _ = annexb_csv_path(&copy);
}

#[test]
#[should_panic(expected = ":121: blank line")]
fn csv_blank_row_panics_not_skipped() {
    let bytes = with_row_replaced(&signal3_csv_bytes(), 120, "   ");
    let copy = temp_file("blank_row.csv", &bytes);
    let _ = annexb_csv_path(&copy);
}

#[test]
#[should_panic(expected = ":121: BOM outside the header line")]
fn csv_bom_on_a_data_row_panics() {
    let bytes = with_row_replaced(&signal3_csv_bytes(), 120, "\u{feff}0.000");
    let copy = temp_file("bom_row.csv", &bytes);
    let _ = annexb_csv_path(&copy);
}

#[test]
fn csv_missing_row_is_caught_by_the_callers_row_count_check() {
    let text = String::from_utf8(signal3_csv_bytes()).unwrap();
    let mut lines: Vec<&str> = text.lines().collect();
    lines.pop();
    let mut short = lines.join("\n");
    short.push('\n');
    let copy = temp_file("short.csv", short.as_bytes());
    let got = annexb_csv_path(&copy);
    assert_eq!(got.len(), 239, "strict reader returns every row it parsed");
    // The Annex B tests assert exactly 240 Bark rows; replicate that check and
    // make sure its message names the expected count.
    let r = std::panic::catch_unwind(|| {
        assert_eq!(
            got.len(),
            240,
            "Annex B specific loudness must have 240 rows"
        );
    });
    let payload = r.expect_err("239 rows must not satisfy the 240-row check");
    let msg = payload
        .downcast_ref::<String>()
        .cloned()
        .or_else(|| payload.downcast_ref::<&str>().map(|s| s.to_string()))
        .unwrap_or_default();
    assert!(msg.contains("240"), "panic message: {msg}");
}

// ------------------------------------------------------------------ bin reader

#[test]
fn bin_whole_words_are_read() {
    let one = 1.5_f64.to_le_bytes();
    let p8 = temp_file("eight.bin", &one);
    assert_eq!(read_bin_path(&p8), vec![1.5]);
    let mut two = one.to_vec();
    two.extend_from_slice(&(-2.25_f64).to_le_bytes());
    let p16 = temp_file("sixteen.bin", &two);
    assert_eq!(read_bin_path(&p16), vec![1.5, -2.25]);
}

macro_rules! bin_trailing_bytes_panics {
    ($name:ident, $len:expr) => {
        #[test]
        #[should_panic(expected = "trailing bytes")]
        fn $name() {
            let bytes = vec![0x11_u8; $len];
            let path = temp_file(concat!(stringify!($name), ".bin"), &bytes);
            let _ = read_bin_path(&path);
        }
    };
}

bin_trailing_bytes_panics!(bin_1_byte_panics, 1);
bin_trailing_bytes_panics!(bin_7_bytes_panics, 7);
bin_trailing_bytes_panics!(bin_9_bytes_panics, 9);
bin_trailing_bytes_panics!(bin_15_bytes_panics, 15);
bin_trailing_bytes_panics!(bin_17_bytes_panics, 17);
