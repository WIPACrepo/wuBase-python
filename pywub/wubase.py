import logging
logger = logging.getLogger(__name__)


WUBASE_DEFAULT_BAUD = 9600
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
    def __init__(self, basenumber, baud=WUBASE_DEFAULT_BAUD):
        #Base info
        self._basenumber = basenumber
        self._ispowered = False
        
        #UART mode
        self._autobaud = True
        self._commsbaud = baud
        
        #ASCII or Binary
        self._comms_mode = "ASCII"

    @property
    def basenumber(self) -> int:
        return self._basenumber

    @property
    def ispowered(self) -> bool :
        return self._ispowered

    def setpowered(self, state: bool):
        self._ispowered = state


    
    @property
    def autobaud(self) -> bool:
        return self._autobaud
    
    def setautobaud(self, state: bool):
        self._autobaud = state
    
    @property
    def baud(self) -> bool:
        return self._baud
    
    def setbaud(self, baud: int):
        if baud < 0:
            self.baud = WUBASE_DEFAULT_BAUD
            self.setautobaud(True)
        else:
            self._baud = baud
            self.setautobaud(False)

    
    @property
    def comms_mode(self) -> str:
        return self._comms_mode

    @property 
    def isascii(self) -> bool :
        if (self._comms_mode.upper())[0] == 'A':
            return True
        else:
            return False
        
    def set_comms_mode(self, mode:str):
        if (mode.upper())[0] == 'A':
            #self.cmd_asciimode()
            self._comms_mode = 'ASCII'
        else:
            #self.cmd_binarymode()
            self._comms_mode = 'BINARY'