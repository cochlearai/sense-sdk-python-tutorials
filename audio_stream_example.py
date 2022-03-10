#!/usr/bin/env python3
from sense import *
import queue
import pyaudio
import numpy as np

SAMPLE_RATE = 22050

class Stream:
    def __init__(self, *args, **kwargs):
        self.__counter = 0
        self._chunk = int(SAMPLE_RATE / 2)
        self.closed = True
        self.__temp_buf = None
        self.__do_rec = True
        self.__audio_buf_idx = 0
        self.__audio_buf = None
        self._buff = queue.Queue()
        self._core_audio_source_stream = None

    def __enter__(self):
        self._audio_interface = pyaudio.PyAudio()
        self._audio_stream = self._audio_interface.open(
                format=pyaudio.paFloat32,
                channels=1, rate=SAMPLE_RATE,
                input=True, frames_per_buffer=self._chunk,
                stream_callback=self._fill_buffer,
                )

        self.closed = False
        self._core_audio_source_stream = sense.AudioSourceStreamFloat()
        return self

    def __exit__(self, exc_type, value, traceback):
        self._audio_stream.stop_stream()
        self._audio_stream.close()
        self.closed = True
        self._buff.put(None)
        self._audio_interface.terminate()
        self._core_audio_source_stream = None

    def _fill_buffer(self, in_data, frame_count, time_info, status_flags):
        self._buff.put(in_data)
        return None, pyaudio.paContinue

    def stop(self):
        """Stop the audio stream prediction.
        """
        self.closed = True

    def generator(self, input_device=None, input_sensitivity=None):
        """Returns the audio stream generator.

        Arguments:
            input_device: Input audio device name
            input_sensitivity: Input sensitivity to reduce unnecessary noise
                               inference (0 <= x < 1, volume size ratio)
        """
        while not self.closed:
            chunk = self._buff.get()
            if chunk is None:
                return
            data = [chunk]
            while True:
                try:
                    chunk = self._buff.get(block=False)
                    if chunk is None:
                        return
                    data.append(chunk)
                except queue.Empty:
                    break
            yield b''.join(data)

    def record(self, generator):
        """Record the audio stream

        Arguments:
            generator: audio stream generator
        """
        for raw_data in generator:
            data = np.frombuffer(raw_data, dtype=np.float32)
            self.__counter += 1
            if self.__counter == 1:
                self.__temp_buf = data
            elif self.__counter == 2:
                self.__temp_buf = np.concatenate(
                    (self.__temp_buf, data), axis=None)
                if self.__do_rec:
                    yield self.__temp_buf
            else:
                self.__temp_buf = np.concatenate(
                    (self.__temp_buf[self._chunk:], data), axis=None)
                if self.__do_rec:
                    yield self.__temp_buf[len(self.__temp_buf) - SAMPLE_RATE:]

    # pylint: disable=W0221
    def predict(self, stream_data):
        sig = np.asarray(stream_data)
        sig = sig.astype('float32')
        sig = sig/float(1 << ((32)-1))
        return self._core_audio_source_stream.Predict(stream_data).to_string()

params = sense.Parameters()
# Default, Emergency, Human_Interaction, Human_Status, Home_Context
params.service = sense.Human_Interaction
# AF_UINT8 AF_INT8 AF_INT16 AF_INT32 AF_DOUBLE AF_FLOAT32
params.audio_format = sense.AF_FLOAT32

# if <= 0. will use all the threads available on the machine
params.num_threads = -1

sense.SenseInit("I6ggTaG9HYeMPk/0ICeaCEgxUFaktpCZzEsDrEqm+co=", params)

with Stream() as stream:
    audio_generator = stream.generator()
    for stream_data in stream.record(audio_generator):
        result = stream.predict(stream_data)
        print(result)