#!/usr/bin/env python3
""" Sense SDK audio stream example v1.5.0
"""
import queue
import signal
import sys
import pyaudio
import numpy as np
from sense import AudioSourceStream, Parameters, FrameResult, SenseInit, SenseTerminate, SenseGetParameters

running = True
SAMPLE_RATE = 22050

class SenseSdkError(Exception):
    """ Sense SDK Error exception
    """
    def __init__(self, message):
        self.msg = message
        super().__init__(self.msg)

    def __str__(self):
        return self.msg

SenseSdkErrorClass = SenseSdkError

class Stream:
    """ A class designed to catch audio data in real time and make predictions at a frequency of
        1 second
    """
    def __init__(self):
        self._audio_interface = None
        self._audio_stream = None
        self._chunk = int(SAMPLE_RATE)
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
            if len(data) != self._chunk:
                raise SenseSdkErrorClass(f'The audio length is invalid : {len(data)}')
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

    def predict(self, data) -> FrameResult:
        """ Predict for the data parameter(1 sceond of audio data) and return the result
        """
        return self._core_audio_source_stream.Predict(data)

def StreamPrediction() -> bool:
    half_second = True
    sense_params = SenseGetParameters()
    result_abbreviation = sense_params.result_abbreviation.enable
    with Stream() as stream:
        def handler(signum, frame):
            """ Signals handling
            """
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

            if result_abbreviation:
                for abbreviation in frame_result.abbreviations:
                    print(abbreviation)
                # Even if you use the result abbreviation, you can still get precise
                # results like below if necessary:
                # print(frame_result.to_string())
            else:
                print("---------NEW FRAME---------")
                print(frame_result.to_string())  

    return False if running else True

if __name__ == "__main__":
    sense_params = Parameters()

    # if <= 0. will use all the threads available on the machine
    sense_params.num_threads = -1

    # Metrics
    sense_params.metrics.retention_period = 0   # range, 1 to 31 days
    sense_params.metrics.free_disk_space = 100  # range, 0 to 1,000,000 MB
    sense_params.metrics.push_period = 30       # range, 1 to 3,600 seconds
    sense_params.log_level = 0

    sense_params.device_name = "Testing device"

    sense_params.sensitivity_control.enable = True
    sense_params.result_abbreviation.enable = True

    if SenseInit("Your project key",
                 sense_params) < 0:
        sys.exit(-1)

    if (not StreamPrediction()):
        print("Stream prediction failed")
    SenseTerminate()
