/* C smoke test for the committed include/iso532.h (spec §9).
 * Compiled by CI with gcc (ubuntu) and MSVC cl (windows) against the cdylib.
 * 注意:C 連結不檢查簽名——header 與 Rust 的同步由 CI 的 cbindgen 再生
 * 比對步驟把關;本檔案負責呼叫慣例與行為煙霧測試。 */
#include <math.h>
#include <stdint.h>
#include <stdio.h>

#include "iso532.h"

#define LEN 48000
#define FRAMES 500 /* ceil(ceil(48000/24)/4) */

static double signal[LEN];
static double out_n[FRAMES];
static double out_spec[240 * FRAMES];
static double out_bark[240];
static double out_time[FRAMES];

int main(void) {
    size_t frames;
    int32_t code;
    size_t i;

    for (i = 0; i < LEN; i++) {
        /* 與 Rust 測試同款整數演算訊號,~54 dB SPL,無錯誤路徑 */
        signal[i] = (double)(i % 480) / 480.0 * 0.02 - 0.01;
    }

    frames = iso532_zwtv_out_frames(LEN);
    if (frames != FRAMES) {
        fprintf(stderr, "frames: got %zu want %d\n", frames, FRAMES);
        return 1;
    }

    code = iso532_loudness_zwtv(signal, LEN, 48000.0, ISO532_FIELD_FREE, out_n, out_spec,
                                out_bark, out_time);
    if (code != 0) {
        fprintf(stderr, "zwtv: code %d\n", (int)code);
        return 1;
    }
    for (i = 0; i < FRAMES; i++) {
        if (!isfinite(out_n[i]) || out_n[i] < 0.0) {
            fprintf(stderr, "zwtv: out_n[%zu] = %f\n", i, out_n[i]);
            return 1;
        }
    }
    if (out_bark[0] < 0.09 || out_bark[0] > 0.11 || out_bark[239] < 23.9 ||
        out_bark[239] > 24.1) {
        fprintf(stderr, "bark axis: [%f, %f]\n", out_bark[0], out_bark[239]);
        return 1;
    }

    code = iso532_loudness_zwst(signal, LEN, 48000.0, ISO532_FIELD_FREE, out_n, out_spec,
                                out_bark);
    if (code != 0) {
        fprintf(stderr, "zwst: code %d\n", (int)code);
        return 1;
    }
    if (!isfinite(out_n[0]) || out_n[0] <= 0.0) {
        fprintf(stderr, "zwst: n = %f\n", out_n[0]);
        return 1;
    }

    /* 錯誤碼 smoke:fs 不支援 → 3(字面值,不依賴 #define) */
    code = iso532_loudness_zwtv(signal, LEN, 44100.0, 0, out_n, out_spec,
                                out_bark, out_time);
    if (code != 3) {
        fprintf(stderr, "error mapping: got %d want 3\n", (int)code);
        return 1;
    }

    printf("smoke ok: frames=%zu zwtv_n0=%f\n", frames, out_n[0]);
    return 0;
}
