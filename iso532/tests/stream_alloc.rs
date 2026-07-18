mod common;

use std::alloc::{GlobalAlloc, Layout, System};
use std::sync::atomic::{AtomicU64, Ordering};

struct Counting;
static ALLOCS: AtomicU64 = AtomicU64::new(0);

unsafe impl GlobalAlloc for Counting {
    unsafe fn alloc(&self, layout: Layout) -> *mut u8 {
        ALLOCS.fetch_add(1, Ordering::Relaxed);
        unsafe { System.alloc(layout) }
    }
    unsafe fn dealloc(&self, pointer: *mut u8, layout: Layout) {
        unsafe { System.dealloc(pointer, layout) }
    }
}

#[global_allocator]
static ALLOCATOR: Counting = Counting;

#[test]
fn push_and_flush_do_not_allocate() {
    let signal = common::synth_signal();
    let mut stream = iso532::ZwtvStream::new(iso532::FieldType::Free);
    let mut out = vec![iso532::StreamFrame::default(); 64];
    let before = ALLOCS.load(Ordering::Relaxed);
    for chunk in signal.chunks(480) {
        stream.push(chunk, &mut out);
    }
    stream.flush(&mut out);
    stream.reset();
    assert_eq!(ALLOCS.load(Ordering::Relaxed), before);
}
