use std::env;
use std::error::Error;
use std::path::PathBuf;

use hound::{SampleFormat, WavReader};
use iso532::{loudness_zwst, FieldType};

fn main() {
    if let Err(err) = run() {
        eprintln!("error: {err}");
        std::process::exit(1);
    }
}

fn run() -> Result<(), Box<dyn Error>> {
    let args: Vec<String> = env::args().skip(1).collect();
    let (path, calib) = parse_args(&args)?;
    let (signal, fs) = read_wav_mono(path, calib)?;
    let result = loudness_zwst(&signal, fs as f64, FieldType::Free)?;
    println!("N = {:.6} sone", result.n);
    Ok(())
}

fn parse_args(args: &[String]) -> Result<(PathBuf, f64), Box<dyn Error>> {
    if args.is_empty() {
        return Err("usage: cli <wav-path> [--calib <float>]".into());
    }

    let path = PathBuf::from(&args[0]);
    let mut calib = 1.0;
    let mut i = 1;
    while i < args.len() {
        match args[i].as_str() {
            "--calib" => {
                let value = args.get(i + 1).ok_or("--calib requires a value")?;
                calib = value.parse::<f64>()?;
                if !calib.is_finite() {
                    return Err("--calib must be finite".into());
                }
                i += 2;
            }
            other => return Err(format!("unknown argument: {other}").into()),
        }
    }

    Ok((path, calib))
}

fn read_wav_mono(path: PathBuf, calib: f64) -> Result<(Vec<f64>, u32), Box<dyn Error>> {
    let mut reader = WavReader::open(path)?;
    let spec = reader.spec();
    let channels = usize::from(spec.channels);
    if channels == 0 {
        return Err("WAV file has zero channels".into());
    }

    let samples = match spec.sample_format {
        SampleFormat::Float => reader
            .samples::<f32>()
            .map(|s| s.map(f64::from))
            .collect::<Result<Vec<_>, _>>()?,
        SampleFormat::Int => {
            let bits = u32::from(spec.bits_per_sample);
            if bits == 0 || bits > 32 {
                return Err(format!("unsupported integer WAV bit depth: {bits}").into());
            }
            let scale = (1_u64 << (bits - 1)) as f64;
            reader
                .samples::<i32>()
                .map(|s| s.map(|v| f64::from(v) / scale))
                .collect::<Result<Vec<_>, _>>()?
        }
    };

    let mono = if channels == 1 {
        samples.into_iter().map(|s| s * calib).collect()
    } else {
        samples
            .chunks_exact(channels)
            .map(|frame| frame.iter().sum::<f64>() * calib / channels as f64)
            .collect()
    };

    Ok((mono, spec.sample_rate))
}
