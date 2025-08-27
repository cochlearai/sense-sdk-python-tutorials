#!/usr/bin/env python3
""" Sense SDK audio stream example v1.6.0
"""
import queue
import signal
import sys
import pyaudio
import numpy as np
from sense import (
    AudioSourceStream,
    Parameters,
    FrameResult,
    SenseInit,
    SenseTerminate,
    SenseGetParameters,
    SenseGetSelectedTags,
)

running = True
SAMPLE_RATE = 22050
CHANNELS = 1


class SenseSdkError(Exception):
    """Sense SDK Error exception"""

    def __init__(self, message):
        self.msg = message
        super().__init__(self.msg)

    def __str__(self):
        return self.msg


SenseSdkErrorClass = SenseSdkError


class Stream:
    """
    A class designed to catch audio data in real time and make predictions at a frequency of 1 second
    """

    def __init__(self):
        self._audio_interface = None
        self._audio_stream = None
        self._chunk = None
        self._buff = queue.Queue()
        self._core_audio_source_stream = None
        self._running = False
        self._temp_buff = None

    def __enter__(self):
        self._audio_interface = pyaudio.PyAudio()
        self._core_audio_source_stream = AudioSourceStream()
        self._chunk = int(
            SAMPLE_RATE * CHANNELS * self._core_audio_source_stream.get_hop_size()
        )
        self._audio_stream = self._audio_interface.open(
            format=pyaudio.paFloat32,
            channels=CHANNELS,
            rate=SAMPLE_RATE,
            input=True,
            frames_per_buffer=int(
                SAMPLE_RATE * self._core_audio_source_stream.get_hop_size()
            ),
            stream_callback=self._fill_buffer,
        )
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
        """Stop the audio stream prediction."""
        self._running = False

    def generator(self):
        """Returns the audio stream generator."""
        while self._running:
            data = self._buff.get()
            if len(data) != self._chunk:
                raise SenseSdkErrorClass(f"The audio length is invalid : {len(data)}")
            yield data

    def record(self, generator):
        """Record the audio stream

        Arguments:
            generator: audio stream generator
        """
        for data in generator:
            if self._temp_buff is None:
                data = np.concatenate((data, data), axis=None)
                self._temp_buff = data
            else:
                self._temp_buff[0 : self._chunk] = self._temp_buff[
                    self._chunk : 2 * self._chunk
                ]
                self._temp_buff[self._chunk : 2 * self._chunk] = data[:]
                yield self._temp_buff

    def predict(self, data) -> FrameResult:
        """Predict for the data parameter(1 sceond of audio data) and return the result"""
        return self._core_audio_source_stream.Predict(data, SAMPLE_RATE)


def stream_prediction() -> bool:
    sense_params = SenseGetParameters()
    result_summary = sense_params.result_summary.enable
    with Stream() as stream:

        def handler(signum, frame):
            """Signals handling"""
            # pylint: disable=unused-argument
            stream.stop()
            global running
            running = False

        signal.signal(signal.SIGINT, handler)

        audio_generator = stream.generator()
        for stream_data in stream.record(audio_generator):
            frame_result = stream.predict(stream_data)
            if frame_result.error:
                print(frame_result.error)
                break

            if result_summary:
                for summary in frame_result.summaries:
                    print(summary)
                # Even if you use the result summary, you can still get precise
                # results like below if necessary:
                # print(frame_result.to_string())
            else:
                print("---------NEW FRAME---------")
                print(frame_result.to_string())

    return False if running else True


if __name__ == "__main__":
    project_key = "Your project key"
    config_file_path = "./config.json"
    if SenseInit(project_key, config_file_path) < 0:
        sys.exit(-1)

    if not stream_prediction():
        print("Stream prediction failed")
    SenseTerminate()
