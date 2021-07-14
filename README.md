# wuBase-python

Python driver for interacting with a wuBase.

## Usage

### Instantiation 



wubctl.py contains the main driver; instantiate it using

```
from pywub import wubctl
wub = wubctl.wuBaseCtl(device_port, baudrate)
```

The wuBase will operate in autobaud mode untill commanded not to using 

`wub.set_baud()` 

which will set the baudrate on the wuBase to that of the serial port when the `wuBaseCtl` object was instantiated. 

### Commanding

The driver implements a method factory to generate commands for sending to the wubase. 
`commands.py` contains a list of ASCII commands from which to generate the functions.
Each method is defined as `cmd_<ascii_command>`, e.g. `cmd_status()`, `cmd_getuid()`, `cmd_start_pulser()`. 

Arguments can be passed to commands as strings:

`wub.cmd_pulser_setup("2000", "0.3")`


## Known Issues

The code to capture wuBase responses is a little bit janky.