#[test]
fn stream_does_not_initialize_rayon_pool() {
    let signal = vec![0.001; 48_000];
    let mut stream = iso532::ZwtvStream::new(iso532::FieldType::Free);
    let mut out = vec![iso532::StreamFrame::default(); 64];
    for chunk in signal.chunks(480) {
        stream.push(chunk, &mut out);
    }
    stream.flush(&mut out);
    assert!(
        rayon::ThreadPoolBuilder::new()
            .num_threads(1)
            .build_global()
            .is_ok(),
        "stream initialized Rayon global pool"
    );
}
