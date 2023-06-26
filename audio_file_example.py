#!/usr/bin/env python3
""" Sense SDK audio file example v1.3.0
"""
import sys
from sense import AudioSourceFile, Parameters, SenseInit, SenseTerminate

try:
    file_path = sys.argv[1]
except IndexError:
    print("Usage: python3 audio_file_example.py <PATH_TO_AUDIO_FILE>")
    sys.exit()

params = Parameters()

# if <= 0. will use all the threads available on the machine
params.num_threads = -1

# Metrics
params.metrics.retention_period = 0   # days
params.metrics.free_disk_space = 100  # MB
params.metrics.push_period = 30       # seconds
params.log_level = 0

params.device_name = "Testing device"

if SenseInit("Your project key",
             params) < 0:
    sys.exit(-1)

file = AudioSourceFile()
if file.Load(file_path) < 0:
    sys.exit(-1)

result = file.Predict()
print(result.to_string())

SenseTerminate()
