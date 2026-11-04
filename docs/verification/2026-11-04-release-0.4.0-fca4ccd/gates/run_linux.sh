set -eu
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq curl build-essential ca-certificates
curl -sSf https://sh.rustup.rs -o /tmp/rustup.sh
sh /tmp/rustup.sh -y -q --profile minimal --default-toolchain 1.99.1
. "$HOME/.cargo/env"
rustc -Vv
cargo -V
ldd --version
mkdir /work
cd /work
tar -xf /input/source.tar
export REQUIRE_AVX2=1 HASH_GATE_DUMP_ONLY=0
cargo test -p iso532 --lib
cargo test -p iso532 --test hash_gate -- --nocapture
cargo test -p iso532 --test py_contract_dump -- --ignored --nocapture
cargo test -p iso532 --test simd_parity --test simd_dispatch --test determinism --test api_errors --test low_freq_correction --test stream_alloc --test stream_no_rayon --test stream_scalar --test nl_zero_init
