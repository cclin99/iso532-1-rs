# Observed timestamp-label deviation

2026-11-05 23:54 Asia/Taipei. The initial comparison assertion rejected MoSQITo's returned timestamps as off the exact 2 ms grid. No metrics had been emitted by that aborted comparison.

MoSQITo 1.2.1 `_third_octave_levels.py` creates `time_axis = linspace(0, len(sig)/fs, num=len(sig[::24]))`, including the input duration endpoint. Its data instead takes the actual samples `[::24]`; `loudness_zwtv.py` then takes `[::4]` for both data and labels. At 48 kHz the data therefore corresponds to input indices 0, 96, 192, ... and physical times 0, .002, .004, ... . The endpoint-inclusive linspace labels drift from that grid.

For meaningful numerical comparison, retain the original returned labels in the raw output and report their drift in length-alignment.json; use the source-defined sample-index grid for matching workbook and official C data. This is a documented deviation from the original strict returned-label matching rule. It does not interpolate, shift, resample, or change any loudness value. The mapping is fixed by decimation code, not optimized from output agreement. All comparisons clearly refer to the physical sample-index grid.
