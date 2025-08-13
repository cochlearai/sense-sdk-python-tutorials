#!/usr/bin/env python3
""" Sense SDK audio file example v1.6.0
"""
import sys
from sense import (
    AudioSourceFile,
    Parameters,
    SenseInit,
    SenseTerminate,
    SenseGetParameters,
    SenseGetSelectedTags,
)

def file_prediction(file_path: str) -> bool:
    # Create a sense audio file instance
    file = AudioSourceFile()
    result_summary: bool = SenseGetParameters().result_summary.enable

    if file.Load(file_path) < 0:
        return False

    # Run the prediction, and it will return a 'Result' object containing
    # multiple 'FrameResult' objects.
    result = file.Predict()
    if not result:
        print(result.error)
        return False

    if result_summary:
        print("<Result summary>")
        if not result.summaries:
            print("There are no detected tags.")
        else:
            for summary in result.summaries:
                print(summary)
            # Even if you use the result summary, you can still get precise
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
    project_key = "Your project key"
    config_file_path = "./config.json"
    if SenseInit(project_key, config_file_path) < 0:
        sys.exit(-1)

    if not file_prediction(file_path):
        print("File prediction failed")
    SenseTerminate()
