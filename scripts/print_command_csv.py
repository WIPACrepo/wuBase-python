#!/usr/bin/env python 

import time
import sys
import threading
from collections import deque 


from pywub.catalog import ctlg as wubCMD_catalog


for name in wubCMD_catalog.command_names:
    args = wubCMD_catalog[f"{name}"].args
    retargs = wubCMD_catalog[f"{name}"].retargs
    print(f"{name},{args},{retargs}")