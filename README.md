# sense-sdk-python-tutorials

- `sense_file.py` - file-mode: load a local audio file and run inference to completion.
- `sense_stream.py` - stream-mode: capture the microphone and infer in real time.

## 1. Virtual environment + dependencies

```bash
# Create and activate an isolated environment
python -m venv .venv
. .venv/bin/activate

# Install the Sense wheel for your interpreter/arch (built by the release pipeline)
pip install sense/sense-<ver>-cp3XY-cp3XY-linux_<arch>.whl

# Extra deps for the tutorials (microphone capture for sense_stream.py)
pip install -r sense-stream/requirements.txt
```

`sense_stream.py` uses **sounddevice**, which needs the system PortAudio library:

```bash
sudo apt-get install -y libportaudio2      # Debian/Ubuntu
```

The Sense wheel itself has **no** dependencies.

## 2. Run

Set `PROJECT_KEY` at the top of each script. Run from the repository root so the `config.json` there is used if present (missing is non-fatal).

```bash
python sense-file/sense_file.py audio-files/siren.wav   # file mode
python sense-stream/sense_stream.py                     # mic mode (Ctrl-C to stop)
```

## 3. API

```python
import sense

with sense.session(project_key, config_json):         # init() / terminate()
    p = sense.create_file_processor(path, listener)   # or create_stream_processor(listener)
    p.sensitivity = "HIGH"                            # property (get/set)
    p.result_summary_enabled = True                   # write-only config properties
    with p:                                           # start() on enter, stop() on exit
        p.push(pcm, channels, sense.SampleFormat.INT16, rate)   # stream mode
```

- **Constants:** `sense.SampleFormat.{FLOAT32,INT16,INT32,FLOAT64}` (an `IntEnum`; pass a member straight to `push`).
- **Results:** subclass `sense.ResultListener` and override `on_result(frame)`. `frame` has `tags` (`.name`, `.probability`), `start_time`, `end_time`, `prediction_time_ms`, `summaries`, `error`, and `is_ok()`.
- The underlying snake_case methods (`get_sensitivity()`, `stop()`, ...) remain available; the properties/context-managers are idiomatic aliases.
