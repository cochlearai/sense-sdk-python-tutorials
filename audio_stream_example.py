#!/usr/bin/env python3
""" This code example checks audio data predictions every second
"""
import queue
import signal
import sys
import pyaudio
import numpy as np
from sense import AudioSourceStream, Parameters, SenseInit, SenseTerminate

SAMPLE_RATE = 22050

class Stream:
    """ A class designed to read audio data and make predictions at a frequency of one second
    """
    def __init__(self):
        self._audio_interface = None
        self._audio_stream = None
        self._chunk = int(SAMPLE_RATE / 2)
        self._buff = queue.Queue()
        self._core_audio_source_stream = None
        self._running = False
        self._temp_buff = None

    def __enter__(self):
        self._audio_interface = pyaudio.PyAudio()
        self._audio_stream = self._audio_interface.open(
            format=pyaudio.paFloat32,
            channels=1,
            rate=SAMPLE_RATE,
            input=True,
            frames_per_buffer=self._chunk,
            stream_callback=self._fill_buffer)
        self._core_audio_source_stream = AudioSourceStream()
        self._running = True

        return self

    def __exit__(self, exc_type, value, traceback):
        self._running = False
        self._buff.put(None)
        self._audio_stream.stop_stream()
        self._audio_stream.close()
        self._audio_interface.terminate()
        self._core_audio_source_stream = None

    def _fill_buffer(self, in_data, frame_count, time_info, status_flags):
        # pylint: disable=unused-argument
        self._buff.put(np.frombuffer(in_data, dtype=np.float32))

        return None, pyaudio.paContinue

    def stop(self):
        """ Stop the audio stream prediction.
        """
        self._running = False

    def generator(self):
        """ Returns the audio stream generator.
        """
        while self._running:
            data = self._buff.get()
            assert len(data) == self._chunk
            yield data

    def record(self, generator):
        """ Record the audio stream

        Arguments:
            generator: audio stream generator
        """
        for data in generator:
            if self._temp_buff is None:
                data = np.concatenate((data, data), axis=None)
                self._temp_buff = data
            else:
                self._temp_buff[0:self._chunk] = self._temp_buff[self._chunk:2*self._chunk]
                self._temp_buff[self._chunk:2*self._chunk] = data[:]
                yield self._temp_buff

    def predict(self, data):
        """ Predict for the data parameter(1 sceond of audio data) and return the result
        """
        return self._core_audio_source_stream.Predict(data).to_string()

params = Parameters()

# if <= 0. will use all the threads available on the machine
params.num_threads = -1

# Metrics
params.metrics.retention_period = 0   # days
params.metrics.free_disk_space = 100  # MB
params.metrics.push_period = 30       # seconds

params.device_name = "Testing device"

if SenseInit("{your-project-key}", params) < 0:
    sys.exit(-1)

with Stream() as stream:
    def handler(signum, frame):
        """ Signals handling
        """
        # pylint: disable=unused-argument
        stream.stop()

    signal.signal(signal.SIGINT, handler)

    audio_generator = stream.generator()
    for stream_data in stream.record(audio_generator):
        result = stream.predict(stream_data)
        print(result)

SenseTerminate()
