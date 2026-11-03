use crate::tables::{RNS, USL, ZUP};

pub fn calc_slopes(nm: &[f64; 21]) -> (f64, [f64; 240]) {
    let mut n_specific = [0.0; 240];
    let total = calc_slopes_into(nm, &mut n_specific);
    (total, n_specific)
}

pub fn calc_slopes_into(nm: &[f64; 21], n_specific: &mut [f64]) -> f64 {
    assert_eq!(
        n_specific.len(),
        240,
        "calc_slopes_into expects 240 Bark steps"
    );
    calc_slopes_impl(nm, Some(n_specific))
}

pub fn calc_slopes_n_only(nm: &[f64; 21]) -> f64 {
    calc_slopes_impl(nm, None)
}

fn calc_slopes_impl(nm: &[f64; 21], mut n_specific: Option<&mut [f64]>) -> f64 {
    let zup_ea = zup_indices();
    if let Some(spec) = n_specific.as_mut() {
        for i in 0..21 {
            for item in &mut spec[prev_zup_index(&zup_ea, i)..zup_ea[i]] {
                *item = nm[i];
            }
        }
    }
    let mut n2 = [1.0; 240];
    let mut z2 = [1.0; 240];
    let mut usl = [1.0; 240];
    let mut dz = [1.0; 240];
    let mut rns_values = [1.0; 240];

    let mut rns_ind = [0usize; 21];
    let mut rns_for_nm = [0.0; 21];
    let mut usl_for_nm = [0.0; 21];
    for i in 0..21 {
        rns_ind[i] = get_rns_index(nm[i], false);
        rns_for_nm[i] = RNS[rns_ind[i]];
        usl_for_nm[i] = usl_value(rns_ind[i], i);
    }

    for i in 0..21 {
        let band_dz = if i < 2 { ZUP[1] } else { ZUP[i] - ZUP[i - 1] };
        for j in prev_zup_index(&zup_ea, i)..zup_ea[i] {
            n2[j] = nm[i];
            dz[j] = band_dz;
            z2[j] = ZUP[i];
            usl[j] = usl_for_nm[i];
            rns_values[j] = rns_for_nm[i];
        }
    }

    let mut total = 0.0;
    let mut n1_aux = 0.0;
    let mut z1_aux = 0.0;

    for i in 0..21 {
        let j0 = prev_zup_index(&zup_ea, i);
        // F-06: band 0 starts from N1 = 0 (Annex A), so it never has a slope
        // to continue and must not look at band 20 through a wrap-around.
        let mut mask_n1_bigger_nm = false;
        let mut before = j0;
        if i > 0 {
            before = j0 - 1;
            let idx = get_rns_index(n2[before], false);
            rns_values[j0] = RNS[idx];
            usl[j0] = usl_value(idx, i - 1);
            mask_n1_bigger_nm = r8(n2[before]) > r8(nm[i]);
        }
        if !mask_n1_bigger_nm {
            total += n2[j0] * (z2[j0] - z1_aux);
            n1_aux = n2[j0];
            z1_aux = z2[j0];
        }

        if mask_n1_bigger_nm {
            let max_rns_nm = rns_values[before].max(nm[i]);
            z2[j0] = ((n1_aux - max_rns_nm) / usl[j0] + z1_aux).min(ZUP[i]);
            dz[j0] = z2[j0] - z1_aux;
            n2[j0] = n1_aux - dz[j0] * usl[j0];

            total += dz[j0] * (n1_aux + n2[j0]) / 2.0;

            let mut z_array = ZUP[i - 1] + 0.1;
            let mut last_mask_z_bigger_z2 = false;
            let mut last_j = j0;

            for j in j0..zup_ea[i] {
                last_j = j;
                if j != j0 {
                    z2[j] = z2[j - 1];
                    n2[j] = n2[j - 1];
                    dz[j] = dz[j - 1];
                    usl[j] = usl[j - 1];
                    rns_values[j] = rns_values[j - 1];
                }

                let mask_z_bigger_z2 = mask_n1_bigger_nm && r8(z2[j]) <= r8(z_array);
                last_mask_z_bigger_z2 = mask_z_bigger_z2;
                if mask_z_bigger_z2 {
                    let idx = get_rns_index(n2[j], true);
                    rns_values[j] = RNS[idx];
                    usl[j] = usl_value(idx, i.wrapping_sub(1));
                    n1_aux = n2[j];
                    z1_aux = z2[j];

                    let mask_z_bigger_z2_1 = r8(n1_aux) <= r8(nm[i]);
                    if mask_z_bigger_z2_1 {
                        n2[j] = nm[i];
                        z2[j] = ZUP[i];
                        dz[j] = z2[j] - z1_aux;
                        total += n2[j] * (z2[j] - z1_aux);
                    } else {
                        let max_rns_nm = rns_values[j].max(nm[i]);
                        z2[j] = ((n1_aux - max_rns_nm) / usl[j] + z1_aux).min(ZUP[i]);
                        dz[j] = z2[j] - z1_aux;
                        n2[j] = n1_aux - dz[j] * usl[j];
                        total += dz[j] * (n1_aux + n2[j]) / 2.0;
                        if let Some(spec) = n_specific.as_mut() {
                            spec[j] = n1_aux - (z_array - z1_aux) * usl[j];
                        }
                    }

                    if !mask_z_bigger_z2_1 {
                        if let Some(spec) = n_specific.as_mut() {
                            spec[j] = n1_aux - (z_array - z1_aux) * usl[j];
                        }
                    }
                    z_array += 0.1;
                    if mask_z_bigger_z2_1 {
                        mask_n1_bigger_nm = false;
                    }
                } else {
                    if let Some(spec) = n_specific.as_mut() {
                        spec[j] = n1_aux - (z_array - z1_aux) * usl[j];
                    }
                    z_array += 0.1;
                }

                z1_aux = z2[j];
                n1_aux = n2[j];

                if !mask_n1_bigger_nm {
                    break;
                }
            }

            let last = zup_ea[i] - 1;
            if mask_n1_bigger_nm && z2[last] < ZUP[i] {
                // F-05: the grid loop ran out of 0.1 Bark cells while the slope
                // was still active. Complete the band the Annex A way, from the
                // end of the last segment up to ZUP[i]; the specific loudness of
                // the band is already final and is not touched.
                let (z_end, n_end) = complete_band(nm[i], i, z2[last], n2[last], &mut total);
                z2[last] = z_end;
                n2[last] = n_end;
            }
            z1_aux = z2[last];
            n1_aux = n2[last];

            if last_mask_z_bigger_z2 {
                let idx = get_rns_index(n2[last_j], true);
                rns_values[last_j] = RNS[idx];
                usl[last_j] = usl_value(idx, i.wrapping_sub(1));
            }
        }
    }

    // F-04: no per-frame rounding of the total (Annex A has none); only the
    // negative clamp is kept.
    if total < 0.0 {
        total = 0.0;
    }

    total
}

/// Annex A band completion (F-05): starting at `(z1, n1)` inside band `band`,
/// keep attaching upper-slope segments until the slope meets the core loudness
/// `nm_band` (then add the flat remainder `nm_band * (ZUP - z)`) or reaches
/// ZUP[band] (last segment clamped to ZUP). Each segment adds
/// `dz * (n1 + n2) / 2` to `total`. Returns the end point of the band.
///
/// Every slope segment ends at the next RNS boundary, so the loop finishes in
/// at most `RNS.len()` segments plus the flat remainder; the bound only guards
/// direct callers of the public `calc_slopes*` with negative core loudness.
fn complete_band(nm_band: f64, band: usize, z1: f64, n1: f64, total: &mut f64) -> (f64, f64) {
    let zup = ZUP[band];
    let (mut z, mut n) = (z1, n1);
    for _ in 0..=RNS.len() + 1 {
        if r8(n) <= r8(nm_band) {
            *total += nm_band * (zup - z);
            return (zup, nm_band);
        }
        let idx = get_rns_index(n, true);
        let slope = usl_value(idx, band - 1);
        let max_rns_nm = RNS[idx].max(nm_band);
        let z_next = ((n - max_rns_nm) / slope + z).min(zup);
        let dz = z_next - z;
        let n_next = n - dz * slope;
        *total += dz * (n + n_next) / 2.0;
        z = z_next;
        n = n_next;
        if z >= zup {
            break;
        }
    }
    (z, n)
}

fn zup_indices() -> [usize; 21] {
    let mut indices = [0; 21];
    for (idx, zup) in ZUP.iter().enumerate() {
        indices[idx] = (zup * 10.0) as usize;
    }
    indices
}

fn prev_zup_index(zup_ea: &[usize; 21], idx: usize) -> usize {
    if idx == 0 {
        0
    } else {
        zup_ea[idx - 1]
    }
}

fn get_rns_index(value: f64, equal_too: bool) -> usize {
    let value = r8(value);
    let mut index = 0;
    for &rns in &RNS {
        let rns = r8(rns);
        if if equal_too { value <= rns } else { value < rns } {
            index += 1;
        }
    }
    index.min(RNS.len() - 1)
}

fn usl_value(rns_idx: usize, band_idx: usize) -> f64 {
    USL[rns_idx][band_idx.min(7)]
}

fn r8(value: f64) -> f64 {
    (value * 100_000_000.0).round() / 100_000_000.0
}

#[cfg(test)]
mod tests {
    use super::{calc_slopes, calc_slopes_into, calc_slopes_n_only};

    #[test]
    fn n_only_matches_into_for_edge_and_random_frames() {
        let mut frames: Vec<[f64; 21]> = vec![
            [0.0; 21],
            spike(0, 8.0),
            spike(10, 8.0),
            spike(20, 8.0),
            ramp(0.0, 10.0),
            ramp(10.0, 0.0),
            alternating(6.0, 0.05),
        ];
        let mut state = 0x1234_5678_9abc_def0_u64;
        for _ in 0..200 {
            let mut frame = [0.0; 21];
            for value in frame.iter_mut() {
                state = state
                    .wrapping_mul(6364136223846793005)
                    .wrapping_add(1442695040888963407);
                *value = (state >> 11) as f64 / (1u64 << 53) as f64 * 12.0;
            }
            frames.push(frame);
        }

        for (idx, nm) in frames.iter().enumerate() {
            let mut spec = [f64::NAN; 240];
            let with_spec = calc_slopes_into(nm, &mut spec);
            let n_only = calc_slopes_n_only(nm);
            assert_eq!(
                n_only.to_bits(),
                with_spec.to_bits(),
                "frame {idx}: n_only={n_only} with_spec={with_spec}"
            );
        }
    }

    fn spike(band: usize, value: f64) -> [f64; 21] {
        let mut frame = [0.0; 21];
        frame[band] = value;
        frame
    }

    fn ramp(from: f64, to: f64) -> [f64; 21] {
        std::array::from_fn(|i| from + (to - from) * i as f64 / 20.0)
    }

    fn alternating(high: f64, low: f64) -> [f64; 21] {
        std::array::from_fn(|i| if i % 2 == 0 { high } else { low })
    }
    #[test]
    fn n_only_matches_full_calc_slopes_total() {
        let nm = sample_main_loudness();

        let (full_n, _) = calc_slopes(&nm);
        let n_only = calc_slopes_n_only(&nm);

        assert_eq!(n_only, full_n);
    }

    #[test]
    fn calc_slopes_into_writes_same_specific_loudness() {
        let nm = sample_main_loudness();
        let (full_n, full_spec) = calc_slopes(&nm);
        let mut spec = [f64::NAN; 240];

        let n = calc_slopes_into(&nm, &mut spec);

        assert_eq!(n, full_n);
        assert_eq!(spec, full_spec);
    }

    /// Annex B signal 23, frame 3893 (NL loudness, Rust pipeline at `aa379db`;
    /// cross-analysis `docs/verification/2026-11-03-C01-cross-analysis-aa379db/`
    /// §3.3). Band 3 starts a slope segment at its last 0.1 Bark cell and meets
    /// the core loudness at Z = 3.438, before ZUP = 3.5.
    const SIG23_FRAME3893: [f64; 21] = [
        0.0,
        0.09591180735716698,
        0.16833504054822399,
        0.09948491987338776,
        0.3233949923141389,
        0.22772788115184733,
        0.1431873258089412,
        0.13681489675458033,
        0.24888795267053007,
        0.16349381128989549,
        0.16619398143785133,
        0.18463027349402386,
        0.292104681120268,
        0.30724002086646746,
        0.28346493604659934,
        0.27811900938216066,
        0.23453330895606994,
        0.17703989122604918,
        0.0814303217458846,
        0.018764949048978314,
        0.0,
    ];

    #[test]
    fn f05_last_cell_remainder_is_integrated() {
        // Expected value: `sliver_check.py::rust_slopes_fixed` with USL[12][4] = 0.24
        // (the Annex A band completion restored); the C port with epsilon = 0 and
        // binary64 tables gives 4.750843403589338 for the same frame.
        let want = 4.750_843_403_589_338_5;
        let got = calc_slopes_n_only(&SIG23_FRAME3893);
        assert!(
            (got - want).abs() <= 1e-12,
            "N {got:.17} vs Annex A {want:.17}, |diff| = {:e}",
            (got - want).abs()
        );
        let mut spec = [f64::NAN; 240];
        assert_eq!(
            calc_slopes_into(&SIG23_FRAME3893, &mut spec).to_bits(),
            got.to_bits()
        );
    }

    #[test]
    fn f04_total_is_not_rounded() {
        for (name, nm) in [
            ("sig23_frame3893", SIG23_FRAME3893),
            ("sample", sample_main_loudness()),
            ("ramp", ramp(0.3, 7.0)),
        ] {
            let got = calc_slopes_n_only(&nm);
            assert!(got > 0.0, "{name}: non-zero frame expected");
            let step = if got <= 16.0 { 1000.0 } else { 100.0 };
            let rounded = (got * step).round() / step;
            assert_ne!(
                got.to_bits(),
                rounded.to_bits(),
                "{name}: N = {got:.17} is still rounded to 1/{step}"
            );
        }
    }

    #[test]
    fn f06_band0_ignores_band20() {
        let mut nm = [0.0; 21];
        nm[20] = 1.0;
        let mut spec = [f64::NAN; 240];
        let got = calc_slopes_into(&nm, &mut spec);
        assert_eq!(got, 1.0 * (24.0 - 23.6), "band 0 must start from N1 = 0");
        assert_eq!(calc_slopes_n_only(&nm).to_bits(), got.to_bits());
        assert!(
            spec[0..9].iter().all(|&v| v == 0.0),
            "band 0 specific loudness must stay 0: {:?}",
            &spec[0..9]
        );
        assert!(spec.iter().all(|&v| v >= 0.0), "negative specific loudness");
    }

    /// Annex B signal 18, frame 1564 (NL loudness, Rust pipeline at `aa379db`,
    /// `tmp/c01-tail-root-cause-aa379db-run2/signal-18/R-pipeline/nl.bin`).
    /// Band 4 starts with a slope from N1 = nm[3] at Z = 3.5: USL 0.63 down to
    /// RNS 0.82 at Z = 3.6002, then USL 0.50 down to the core loudness nm[4] at
    /// Z = 3.6124, then flat.
    const SIG18_FRAME1564: [f64; 21] = [
        6.43992114652731096e-02,
        5.99842137688217036e-01,
        8.08837572799405269e-01,
        8.83134246474833851e-01,
        8.13879371664140705e-01,
        3.57705753641196944e-01,
        2.20569571587427210e-01,
        2.46142650453736456e-01,
        3.93134195201309600e-01,
        3.51847485801889681e-01,
        2.76104071380374294e-01,
        2.58339113853283397e-01,
        3.38786597848122206e-01,
        3.65479352730189611e-01,
        2.57648123606176893e-01,
        1.96771441338274927e-01,
        1.38028800770865573e-01,
        6.49358452068741349e-02,
        2.95640883251312723e-03,
        7.11993604699323124e-04,
        0.00000000000000000e+00,
    ];

    /// Total of `SIG18_FRAME1564` before F-07 (commit 9301c0d); F-07 only
    /// changes the specific pattern, so the total must stay bitwise identical.
    const SIG18_FRAME1564_TOTAL_BITS: u64 = 0x401f_c356_fc47_a15a;

    #[test]
    fn f07_sample_after_segment_end_is_core_or_next_segment() {
        let nm = SIG18_FRAME1564;
        let mut spec = [f64::NAN; 240];
        let total = calc_slopes_into(&nm, &mut spec);
        assert_eq!(
            total.to_bits(),
            SIG18_FRAME1564_TOTAL_BITS,
            "total {total:.17e} moved"
        );
        assert_eq!(calc_slopes_n_only(&nm).to_bits(), total.to_bits());
        // Cell 35 (Z = 3.6) lies inside the first segment (ends at 3.6002).
        let want35 = nm[3] - 0.1 * 0.63;
        assert!(
            (spec[35] - want35).abs() <= 1e-12,
            "spec[35] {:.17e} vs {want35:.17e}",
            spec[35]
        );
        // Cell 36 (Z = 3.7) lies after the second segment (ends at 3.6124 on
        // the core loudness): Annex A writes the core loudness there, the
        // MoSQITo-derived rule extrapolated the second segment to 0.77011.
        assert_eq!(
            spec[36].to_bits(),
            nm[4].to_bits(),
            "spec[36] {:.17e} vs nm[4] {:.17e}",
            spec[36],
            nm[4]
        );
        for (j, v) in spec.iter().enumerate().take(44).skip(37) {
            assert_eq!(v.to_bits(), nm[4].to_bits(), "spec[{j}] {v:.17e}");
        }
    }

    /// Synthetic band-4 frame whose slope segments end on RNS boundaries and
    /// continue with another slope segment (never on the core loudness inside
    /// a cell): nm[3] = 0.45, nm[4] = 0.1, all other bands 0.
    ///
    /// Expected values by hand from the Annex A segment chain (binary64
    /// tables): from Z = 3.5, USL[11][3] = 0.50 down to RNS 0.42 at Z = 3.56,
    /// USL[12][3] = 0.24 down to 0.30 at Z = 4.06, USL[13][3] = 0.18 clamped at
    /// ZUP = 4.4 (N = 0.2388); band 5 continues with USL[13][4] = 0.17 down to
    /// 0.22 at Z = 4.5106 and USL[14][4] = 0.11 after that.
    ///
    /// Cross-check: the official C (`tmp/c01-tail-root-cause-aa379db-run2/c/
    /// stages.dll`, `rc_slopes`, n = 1) gives 0.41042398052005946,
    /// 0.29281798859491043, 0.22181698491381224 and 0.21017569557691812 for
    /// cells 35, 40, 44 and 45: the same chain shifted by its `_ZUP += .0001f`
    /// band-edge epsilon (1e-4 Bark x USL, <= 2.4e-5 here).
    #[test]
    fn f07_slope_followed_by_slope_keeps_the_segment_values() {
        let mut nm = [0.0; 21];
        nm[3] = 0.45;
        nm[4] = 0.1;
        let mut spec = [f64::NAN; 240];
        let total = calc_slopes_into(&nm, &mut spec);
        assert_eq!(calc_slopes_n_only(&nm).to_bits(), total.to_bits());
        let n_zup4 = 0.30 - (4.4 - 4.06) * 0.18;
        let z_rns13_band5 = 4.4 + (n_zup4 - 0.22) / 0.17;
        for (j, want) in [
            (35, 0.42 - (3.6 - 3.56) * 0.24),
            (39, 0.42 - (4.0 - 3.56) * 0.24),
            (40, 0.30 - (4.1 - 4.06) * 0.18),
            (43, n_zup4),
            (44, n_zup4 - 0.1 * 0.17),
            (45, 0.22 - (4.6 - z_rns13_band5) * 0.11),
        ] {
            assert!(
                (spec[j] - want).abs() <= 1e-12,
                "spec[{j}] {:.17e} vs {want:.17e}",
                spec[j]
            );
        }
        let c = [
            (35, 0.410_423_980_520_059_46),
            (40, 0.292_817_988_594_910_43),
            (44, 0.221_816_984_913_812_24),
            (45, 0.210_175_695_576_918_12),
        ];
        for (j, want) in c {
            assert!(
                (spec[j] - want).abs() <= 1e-4 * 0.24,
                "spec[{j}] {:.17e} vs official C {want:.17e}",
                spec[j]
            );
        }
    }

    fn sample_main_loudness() -> [f64; 21] {
        let mut nm = [0.0; 21];
        for (band, value) in nm.iter_mut().enumerate() {
            *value = ((band as f64 + 1.0) * 0.07).sin().abs() * 2.5;
        }
        nm
    }
}
