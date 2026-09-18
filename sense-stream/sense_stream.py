#!/usr/bin/env python3
# Copyright 2020-2026 Cochl.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.

"""sense-stream: real-time microphone inference tutorial (Python).

Captures the microphone with sounddevice (PortAudio) and streams it to the SDK
chunk-by-chunk (mirrors the C++ sense-stream tutorial, which uses miniaudio).
Ctrl-C to stop.

Usage:
    python sense_stream.py

Setup (see README.md):
    python -m venv .venv && . .venv/bin/activate
    pip install sense-<ver>-cp3XY-cp3XY-linux_<arch>.whl
    pip install sounddevice            # needs system PortAudio (libportaudio2)

Set PROJECT_KEY below. A config.json in the working directory is used if present.
"""

import json
import sys

import sense

try:
    import sounddevice as sd
except ImportError:
    sys.exit(
        "sounddevice is required: pip install sounddevice (and system libportaudio2)"
    )

# >>> Set your project key here before running. <<<
PROJECT_KEY = "YOUR_PROJECT_KEY"

NUM_CHANNELS = 1

# Fallback inference hop (seconds), used only when config.json is unavailable or
# omits "default_hopsize"; otherwise the value from config.json wins (see
# parse_hop_size). Mirrors the cpp/android tutorials, which also read the hop
# from config.json instead of hardcoding it.
DEFAULT_HOP_SIZE = 1.0


def _fmt_num(value: float) -> str:
    """6 significant digits, trailing zeros dropped."""
    return f"{float(value):.6g}"


class ResultPrinter(sense.ResultListener):
    """Fires once per inference window. Must outlive the processor."""

    # Class-level default; set per instance via set_processor() (avoids adding
    # an __init__ to a SWIG director subclass).
    _processor = None

    def set_processor(self, processor) -> None:
        """Attach after creation so on_result can read the live feature state."""
        self._processor = processor

    def on_result(self, frame: sense.Result) -> None:
        if not frame.is_ok():
            print(f"[error] {frame.error}", file=sys.stderr)
            return
        if self._processor is not None and self._processor.result_summary_enabled:
            for line in frame.summaries:
                print(line)
            return
        self._print_json(frame)

    def _print_json(self, frame: sense.Result) -> None:
        lines = [
            "{",
            f'  "start_time": {_fmt_num(frame.start_time)},',
            f'  "end_time": {_fmt_num(frame.end_time)},',
            f'  "prediction_time_ms": {_fmt_num(frame.prediction_time_ms)},',
        ]
        if len(frame.tags) == 0:
            lines.append('  "tags": []')
        else:
            lines.append('  "tags": [')
            last = len(frame.tags) - 1
            for i, tag in enumerate(frame.tags):
                lines.append("    {")
                lines.append(f'      "name": "{tag.name}",')
                lines.append(f'      "probability": {_fmt_num(tag.probability)}')
                lines.append("    }" if i == last else "    },")
            lines.append("  ]")
        lines.append("}")
        print("\n".join(lines))


def parse_hop_size(config: str) -> float:
    """Reads "default_hopsize" (seconds) from config.json content.

    Returns DEFAULT_HOP_SIZE when the key is absent, non-positive, or the JSON is
    unparseable, so the mic read stays aligned with the SDK's inference hop
    without a hardcoded value.
    """
    try:
        value = float(json.loads(config).get("default_hopsize", DEFAULT_HOP_SIZE))
    except (ValueError, TypeError):
        return DEFAULT_HOP_SIZE
    return value if value > 0.0 else DEFAULT_HOP_SIZE


def read_config(path: str) -> str:
    try:
        with open(path, encoding="utf-8") as f:
            return f.read()
    except OSError:
        print(f"[warn] could not read {path}; using default settings.", file=sys.stderr)
        return ""


def main() -> int:
    config = read_config("config.json")
    hop_size = parse_hop_size(config)  # seconds; from config.json (or fallback)

    listener = ResultPrinter()
    with sense.session(PROJECT_KEY, config):
        processor = sense.create_stream_processor(listener)
        listener.set_processor(processor)  # lets on_result read the live state

        # Optional runtime controls (safe after creation; AAD/AGC are stream-mode only):
        #   processor.sensitivity = "HIGH"       # VERY_LOW|LOW|NORMAL|HIGH|VERY_HIGH
        #   processor.set_tag_sensitivity("Footstep", "LOW")
        #   processor.result_summary_enabled = True
        #   processor.audio_activity_detection = True   # stream-mode only
        #   processor.automatic_gain_control = True     # stream-mode only

        # Capture at the model's rate so no resampling is needed. A higher device
        # rate also works (the SDK downsamples to the model rate). Capture rates
        # BELOW the model rate are not supported (upsampling cannot recover the
        # missing high frequencies the model needs), so this tutorial always
        # captures at the model rate.
        rate = processor.model_sample_rate()

        # Read one hop of audio per push, matching the SDK's inference cadence
        # (config.json "default_hopsize"). The SDK still buffers pushed audio in
        # its own FIFO, so this only sets how much we read per loop.
        block_frames = max(1, int(rate * hop_size))
        print(
            f"Recording at {rate} Hz (int16, mono), {hop_size:g}s hop -- "
            "Ctrl-C to stop.",
            file=sys.stderr,
        )

        # Audio bit depth. dtype sets what the mic (sounddevice/PortAudio)
        # captures and MUST match the SampleFormat passed to push() below.
        #   SDK-supported formats:           FLOAT32, INT16, INT32, FLOAT64.
        #   This tutorial's mic (PortAudio): FLOAT32 ("float32"), INT16
        #                                    ("int16"), INT32 ("int32").
        # FLOAT64 is a valid SDK format, but PortAudio has no 64-bit-float
        # capture, so it cannot be used for live mic here (use it only for file /
        # pre-recorded input). dtype="int16" -> little-endian PCM16 bytes that
        # map directly to SampleFormat.INT16.
        mic = sd.RawInputStream(samplerate=rate, channels=NUM_CHANNELS, dtype="int16")
        with mic, processor:  # mic open; processor.start() arms the stream
            try:
                while True:
                    data, _overflowed = mic.read(block_frames)
                    processor.push(
                        bytes(data), NUM_CHANNELS, sense.SampleFormat.INT16, rate
                    )
            except KeyboardInterrupt:
                print("\nstopped.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
