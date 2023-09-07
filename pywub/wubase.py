import logging
logger = logging.getLogger(__name__)

# def parse_device_config(filename:str):

#     with open(filename, 'r') as f:
#         config = f.read()

#     setup_command_list = []
#     for setting in config.split("\n"):
#         if setting[0] != '#':
#             spl = setting.split(" ")
            
#             command = spl[0]
#             mask = spl[1]            
#             sleeptime = spl[2]
#             modified_command_args = None
#             if len(spl) > 3: 
#                 command_args = spl[3::]
#                 modified_command_args = []
#                 for arg in command_args:
#                     if arg.isnumeric():
#                         modified_command_args += [int(arg)]
#                     else:
#                         modified_command_args += [float(arg)]

#             cmd_line = dict(device_mask=mask, name=command, sleeptime=sleeptime, args=modified_command_args)
#             setup_command_list += [cmd_line]
#         else:
#             continue
        
#     return dict(setup=setup_command_list)


class wuBase():
    def __init__(self, basenumber=None, baud=9600):
        self._basenumber = basenumber
        self._autobaud = False
        self._commsbaud = baud
        self._mode = "A"

    @property
    def basenumber(self):
        return self._basenumber

    @property
    def mode(self):
        return self._mode
    
    @property
    def autobaud(self):
        return self._autobaud
    
    @property 
    def isascii(self) -> bool :
        if (self._mode.upper())[0] == 'A':
            return True
        else:
            return False   
