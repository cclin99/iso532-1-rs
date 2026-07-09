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
        let before = prev_grid_index(j0);
        let idx = get_rns_index(n2[before], false);
        rns_values[j0] = RNS[idx];
        usl[j0] = usl_value(idx, i.wrapping_sub(1));

        let mut mask_n1_bigger_nm = r8(n2[before]) > r8(nm[i]);
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

            let mut z_array = if i == 0 { ZUP[20] } else { ZUP[i - 1] } + 0.1;
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

            z1_aux = z2[zup_ea[i] - 1];
            n1_aux = n2[zup_ea[i] - 1];

            if last_mask_z_bigger_z2 {
                let idx = get_rns_index(n2[last_j], true);
                rns_values[last_j] = RNS[idx];
                usl[last_j] = usl_value(idx, i.wrapping_sub(1));
            }
        }
    }

    if total < 0.0 {
        total = 0.0;
    }
    if total <= 16.0 {
        total = (total * 1000.0 + 0.5).floor() / 1000.0;
    } else {
        total = (total * 100.0 + 0.5).floor() / 100.0;
    }

    total
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

fn prev_grid_index(idx: usize) -> usize {
    if idx == 0 {
        239
    } else {
        idx - 1
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

    fn sample_main_loudness() -> [f64; 21] {
        let mut nm = [0.0; 21];
        for (band, value) in nm.iter_mut().enumerate() {
            *value = ((band as f64 + 1.0) * 0.07).sin().abs() * 2.5;
        }
        nm
    }
}
