import os
import json
import datetime
import glob
import re

import ffmpeg
import enum


videoname = "SHINOBI-FUHGA3-Base-Takemori-Linear_Insert_Tool-Downward_Gray_90cm-1(1)"
if re.fullmatch(r".+\(1\)", videoname) is not None:
    print("match")
else:
    print("not match")
