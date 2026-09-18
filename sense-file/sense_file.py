#!/usr/bin/env python3
# Copyright 2020-2026 Cochl.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.

"""sense-file: file-mode inference tutorial (Python).

Loads a local audio file (WAV/MP3/...) and runs inference to completion
(mirrors the C++ sense-file tutorial).

Usage:
    python sense_file.py <audio_file_path>

Setup (see README.md):
    python -m venv .venv && . .venv/bin/activate
    pip install sense-<ver>-cp3XY-cp3XY-linux_<arch>.whl

Set PROJECT_KEY below. A config.json in the working directory is used if present
(missing is non-fatal).
"""

import sys

import sense

# >>> Set your project key here before running. <<<
PROJECT_KEY = "YOUR_PROJECT_KEY"


def _fmt_num(value: float) -> str:
    """Formats a number like C++'s default ostream (6 significant digits,
    trailing zeros dropped) so the output matches the C++ tutorial exactly."""
    return f"{float(value):.6g}"


class ResultPrinter(sense.ResultListener):
    """Fires once per inference window. Runs on the inference thread, so keep it
    cheap. Must outlive the processor.

    Output mirrors the C++ tutorial: pretty-printed JSON per window when result
    summary is OFF, otherwise the summary lines ("At X.X-Y.Ys, [tag] was
    detected"). The mode is read from the live feature state, like C++."""

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


def read_config(path: str) -> str:
    try:
        with open(path, encoding="utf-8") as f:
            return f.read()
    except OSError:
        print(f"[warn] could not read {path}; using default settings.", file=sys.stderr)
        return ""


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: sense_file.py <audio_file_path>", file=sys.stderr)
        return 1
    audio_path = sys.argv[1]
    config = read_config("config.json")

    listener = ResultPrinter()
    with sense.session(PROJECT_KEY, config):  # init() ... terminate()
        processor = sense.create_file_processor(audio_path, listener)
        listener.set_processor(processor)  # lets on_result read the live state
        # Optional runtime controls (safe after creation):
        #   processor.sensitivity = "HIGH"       # VERY_LOW|LOW|NORMAL|HIGH|VERY_HIGH
        #   processor.set_tag_sensitivity("Footstep", "LOW")
        #   processor.result_summary_enabled = True
        processor.start()  # blocks until the whole file is processed
    return 0


if __name__ == "__main__":
    sys.exit(main())
