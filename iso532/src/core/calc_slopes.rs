use crate::tables::{RNS, USL, ZUP};

pub fn calc_slopes(nm: &[f64; 21]) -> (f64, [f64; 240]) {
    let zup_ea = zup_indices();
    let mut n_specific = [0.0; 240];

    for i in 0..21 {
        for item in &mut n_specific[prev_zup_index(&zup_ea, i)..zup_ea[i]] {
            *item = nm[i];
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
                        n_specific[j] = n1_aux - (z_array - z1_aux) * usl[j];
                    }

                    if !mask_z_bigger_z2_1 {
                        n_specific[j] = n1_aux - (z_array - z1_aux) * usl[j];
                    }
                    z_array += 0.1;
                    if mask_z_bigger_z2_1 {
                        mask_n1_bigger_nm = false;
                    }
                } else {
                    n_specific[j] = n1_aux - (z_array - z1_aux) * usl[j];
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

    (total, n_specific)
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
