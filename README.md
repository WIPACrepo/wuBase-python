# wuBase-python

Python drivers for interacting with a wuBase.

## Instantiation 

Begin by installing the required Python packages, followed by the package itself. 

```
cd wuBase-python
pip install . 
```

## Data Acquisition

### LOM-style MFH usage

Some documentation will live here. [STM32Tools](https://github.com/WIPACrepo/STM32Tools) contains a LOM interface script which makes signfiicant usage of this module, so look over there. 

### wuBase "D" module operation

`run_wub_daq.py` is your go-to script (use the `--help` flag for information). It takes a configuration file (example given in `config/cfg_test_data.cfg`) which is a list of commands to execute before entering the batchmode reciever thread. 

### More Involved Usage

wubctl.py contains the main driver; instantiate it using

```
from pywub import wubctl
wub = wubctl.wuBaseCtl(device_port, baudrate)
```

Note the wuBase will operate in autobaud mode until told otherwise. This is handled seamlessly in the main DAQ script. 

#### Commanding

The driver implements a method factory to generate commands for sending to the wubase. 
`wubase_commands.txt` contains a list of ASCII commands from which to generate the functions.
Each method is defined as `cmd_<command name>`, e.g. `cmd_status()`, `cmd_getuid()`, `cmd_start_pulser()`. 

Arguments can be passed to commands as strings or numbers:

`wub.cmd_pulser_setup("1", "2000", "0.3")`
`wub.cmd_pulser_setup(1, 2000, 0.3)`


#### Known Issues

Aborting a run in BINARY comms mode can be wonky if there are data in the buffer. As a result, the last frame captured may be incorrect. 
