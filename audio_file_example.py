#!/usr/bin/env python3
from sense import *
import os
from os import path
import sox
from pydub import AudioSegment
import numpy as np

LIST_OF_FILE_FORMATS = ['mp3', 'wav', 'ogg', 'flac', 'mp4']
SAMPLE_RATE = 22050

class __SenseSDKError(Exception):
    """Sense SDK Error exception"""
    def __init__(self, message):
        # super(__SenseSDKError, self).__init__(message)
        self.msg = message
        super().__init__(self.msg)
        #3.8?
        # super(__SenseSDKError, self).__init__(message)

    def __str__(self):
        return self.msg
SenseSDKError = __SenseSDKError

class File:
    def __load_audio_file(self, file_name, file_format):
        resampled_file_name = '/tmp/resampled.' + file_format

        tfm = sox.Transformer()
        tfm.rate(SAMPLE_RATE, quality='v')
        tfm.remix(remix_dictionary=None, num_output_channels=1)
        tfm.build(file_name, resampled_file_name)

        sound = AudioSegment.from_file(resampled_file_name, file_format)
        os.unlink(resampled_file_name)
        sig = np.asarray(sound.get_array_of_samples())
        sig = sig.astype('float' + str(8*sound.sample_width))
        sig = sig/np.float(1 << ((8*sound.sample_width)-1))

        return sig

    def __get_fileformat(self, file_name):
        _, file_ext = os.path.splitext(file_name)
        file_format = file_ext[1:]
        if file_format not in LIST_OF_FILE_FORMATS:
            raise SenseSDKError('Wrong File Format : {}'.format(file_format))
        return file_format

    def predict(self, file_path):
        file_exists = path.exists(file_path)
        if not file_exists:
            raise SenseSDKError("Could not find '" + file_path + "' file")

        file_format = self.__get_fileformat(file_path)
        # Load input data from audio file
        input_data = self.__load_audio_file(file_path, file_format)
        audio_source = sense.AudioSourceFileFloat()
        return audio_source.Predict(input_data).to_string()

params = sense.Parameters()
# Default, Emergency, Human_Interaction, Human_Status, Home_Context
params.service = sense.Human_Interaction
# AF_UINT8 AF_INT8 AF_INT16 AF_INT32 AF_DOUBLE AF_FLOAT32
params.audio_format = sense.AF_FLOAT32

# if <= 0. will use all the threads available on the machine
params.num_threads = -1

if sense.SenseInit("{your-project-key}", params) <= 0:
    exit(-1)

file = File()

print(file.predict("./audio_files/whistle.wav"))
