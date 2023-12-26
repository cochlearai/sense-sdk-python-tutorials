#!/usr/bin/env python3
""" Sense SDK audio file example v1.4.0
"""
import sys
from sense import AudioSourceFile, Parameters, SenseInit, SenseTerminate, SenseGetParameters

def FilePrediction(file_path: str) -> bool:
    # Create a sense audio file instance
    file = AudioSourceFile()
    result_abbreviation: bool = SenseGetParameters().result_abbreviation.enable

    if file.Load(file_path) < 0:
        return False

    # Run the prediction, and it will return a 'Result' object containing
    # multiple 'FrameResult' objects.
    result = file.Predict()
    if (not result):
        print(result.error)
        return False

    if (result_abbreviation):
        print("<Result summary>")
        if (not result.abbreviations):
            print("There are no detected tags.")
        else:
            for abbreviation in result.abbreviations:
                print(abbreviation)
            # Even if you use the result abbreviation, you can still get precise
            # results like below if necessary:
            # print(result.to_string())
    else:
        print(result.to_string())

    return True
    
if __name__ == "__main__":
    try:
        file_path = sys.argv[1]
    except IndexError:
        print("Usage: python3 audio_file_example.py <PATH_TO_AUDIO_FILE>")
        sys.exit()

    sense_params = Parameters()

    # if <= 0. will use all the threads available on the machine
    sense_params.num_threads = -1

    # Metrics
    sense_params.metrics.retention_period = 0   # range, 1 to 31 days
    sense_params.metrics.free_disk_space = 100  # range, 0 to 1,000,000 MB
    sense_params.metrics.push_period = 30       # range, 1 to 3,600 seconds
    sense_params.log_level = 0

    sense_params.device_name = "Testing device"

    sense_params.hop_size_control.enable = True
    sense_params.sensitivity_control.enable = True
    sense_params.result_abbreviation.enable = True
    sense_params.label_hiding.enable = False  # stream mode only

    if SenseInit("Your project key",
                sense_params) < 0:
        sys.exit(-1)

    if (not FilePrediction(file_path)):
        print("File prediction failed")
    SenseTerminate()
