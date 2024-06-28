from __future__ import annotations

from enum import IntEnum, auto
import struct
import os
from cobs import cobs

from dataclasses import dataclass

def mask_to_base_numbers(bitmask: int) -> list[int]:
    '''
    Returns a list of length 18 (maximum number of bases).
    The order is inverted -- flags[0] is the LSB in the bitmask 
    '''
    flags = list(f'{bitmask:018b}')[::-1]
    return [int(index) for index,i in enumerate(flags) if int(i) == 1]

def parse_setup_config(filename:str):

    with open(filename, 'r') as f:
        config = f.read()

    setup_command_list = []
    for setting in config.split("\n"):

        if len(setting) > 0 and setting[0] != '#':
            spl = setting.split(" ")
            
            for s in spl:
                s.strip()

            mask = None 
            try: 
                mask = int(spl[0], 16)
                offset = 1
            except ValueError:
                offset = 0

            command = spl[0 + offset]
            sleeptime = spl[1 + offset]
            modified_command_args = None
            
            if len(spl) > 2: 
                command_args = spl[(2 + offset)::]
                modified_command_args = []
                for arg in command_args:
                    if arg.isnumeric():
                        modified_command_args += [int(arg)]
                    else:
                        modified_command_args += [float(arg)]

            cmd_line = dict(name=command, sleeptime=sleeptime, args=modified_command_args, mask=mask)
            setup_command_list += [cmd_line]
        else:
            continue
        
    return dict(setup=setup_command_list)    
    
    
#Helper classes
class wubCMD_SERV(IntEnum):
    SERV_SLOW_CTRL = int("3030", 16)
    SERV_DATA = auto()

class wubCMD_RC(IntEnum):
    # Command response codes. 
    CMD_RC_OK = ord('a') #is a char because we can see it in the terminal directly. 
    CMD_RC_INVALID_ARGUMENT_COUNT = auto()
    CMD_RC_INVALID_COMMAND = auto()
    CMD_RC_INVALID_NUMBER = auto()
    CMD_RC_OUT_OF_RANGE = auto()
    CMD_RC_COMMAND_FAILED = auto()
    CMD_RC_BUSY = auto()
    CMD_RC_TIMEOUT = auto()
    CMD_RC_BADCRC = auto()
    CMD_RC_INVALID_UNPACK = auto()
    CMD_RC_WAITING = auto()
    CMD_RC_RESP_TIMEOUT = auto()
    CMD_RC_INVALID = auto()

    
class wubCMD_entry():
    
    #Static variables. 
    #They can be overwritten, because Python, so don't overwrite them. 
    _services = wubCMD_SERV
    
    _num_cmd = 0 #total number of commands.
    _cmd_baseid = int("3030", 16) #An ASCII "00" which makes debugging easier. 
    
    def __init__(self, name, service, cmd_name, args, retargs):
        #Get the command name, service ID.
        self.name = name.strip('\"') #FIXME: This should be modified to work like below.        
        self.service = self.__class__._services[service.strip(' ')]
        
        #Get the command name.
        self.cmd_name = cmd_name.strip(' ')        
        
        #Get the command ID based on the number of total commands and update the num_cmd static variable. 
        self.cmd_id = self.__class__._cmd_baseid + self.__class__._num_cmd        
        self.__class__._num_cmd += 1        
        
        #Parse messy strings. 
        self.args = args.replace('"', '').strip(' ')
        self.retargs = retargs.replace('"', '').strip(' ')

        #Fix the VERSION command format string:
        if self.cmd_name.lower() == "cmd_version":
            self.retargs = "30sb30sb"
        
    def __repr__(self):
        return f"ID: {hex(self.cmd_id)} CMD_NAME: {self.cmd_name:25s} \
                ARGS: {self.args if len(self.args) > 0 else None} RETARGS: {self.retargs if len(self.retargs) > 0 else None}"
    
    def build(self, mode : str = 'b', args: list = []) -> bytes:
        '''Build a bytes object from a wubCMD and related arguments. 
        
        Args:
            mode (str): comms mode (ascii || binary)
            args (list): Variable length argument list to pass along with command. 
            
        Returns:
            bytes: formatted command object with delimeter. 
        
        '''
        command_str = ''
        arg_str = ''
        build = None
        if(mode.upper()[0] == 'A'): #Covers 'ascii, a, ASCII, asc, etc.'
            command_str = f"{self.name.upper()}"

            if self.args is not None:
                for i, fmt in enumerate(self.args):
                    arg_str += f" {args[i]}"

            build = (command_str + arg_str.format(*args))

            return build 
            
        else: #Binary
            
            command_str = struct.pack("!HH", 0, self.cmd_id) 
            arg_str = struct.pack("!{self.args}", *args)
            #print(self.args)
            build = command_str + arg_str

            build = cobs.encode(build)

            return build
            
@dataclass
class wubCMD_resp:
    base: int
    cmd: wubCMD_entry
    args: list = None

    #Binary
    rc: wubCMD_RC = None
    retargs: list = None

    #ASCII 
    retstr : str = ""

    def __post_init__(self):
        #Populate the return string if only binary data were produced.
        if self.rc is not None:
            self.retstr = f"CMD_RC: {wubCMD_RC(self.rc).name}"
            if self.retargs is not None and len(self.retargs) > 0:
                self.retstr += f" RETARGS: {self.retargs}"

@dataclass
class wubCMD_ask:
    cmd: wubCMD_entry
    args: list = None

@dataclass
class wubCMD_mask_ask:
    mask: int
    cmd: wubCMD_entry
    args: list = None

@dataclass(init = False)
class wubCMD_mask_resp:
    mask: int
    resp: list[wubCMD_resp]

    def __init__(self, mask:int, resp: list[wubCMD_resp]):
        self.mask = mask
        self.resp = resp

        cmd_rc = []
        cmd_retargs = []
        bases = mask_to_base_numbers(self.mask)
        for index, base in enumerate(bases):
            base_resp = self.resp[index]

            cmd_rc += [base_resp.rc]

            if len(base_resp.cmd.retargs) > 0: 
                if base_resp.retargs is not None and len(base_resp.retargs) > 0:
                    cmd_retargs += [base_resp.retargs]
                else: 
                    cmd_retargs += [None]
            else:
                cmd_retargs = None

        self.rc = cmd_rc
        self.retargs = cmd_retargs




class wubCMD_catalog():
    
    _return_codes = wubCMD_RC
    
    def __init__(self, cmd_list : list = []):
        
        #These are used as part of indexing.
        self.name_dict = {}
        self.id_dict = {}
        self._dict = {}
        self.command_names = []
        # Doing it this way allows to index by command name or by index.
        for cmd in cmd_list:
            self.command_names += [cmd.name]
            self.name_dict[cmd.name] = cmd
            self.id_dict[cmd.cmd_id] = cmd
            #Set command attributes: 
            new_attr = cmd
            new_attr.__name__ = cmd.name.lower()
            setattr(self, new_attr.__name__ , new_attr)                
            
        self.reference = 'name'
        self._dict = self.name_dict

    def get_command(self, name:str) -> wubCMD_entry:
        return getattr(self, f"{name.lower()}")
        
    def set_reference(self, ref:str):
        '''
        Allows users to index commands by command name or command ID.
        '''
        ref = ref.lower()
        if ref not in ['name', 'id']:
            raise ValueError(f"{ref} not an acceptable target: name, id")
        elif ref == 'name':
            self._dict = self.name_dict
            self.reference = 'name'
        else:
            self._dict = self.id_dict
            self.reference = 'id'           
            
    def keys(self):
        return self._dict.keys()
                        
    def __getitem__(self, key):
        return self._dict[key]    
    
   
#load command list.
command_set = []
command_names = []

this_dir, this_filename = os.path.split(__file__)
data_file = os.path.join(this_dir, "wubase_commands.txt")

with open(data_file , 'r') as f:
    for line in f.readlines():
        cmd_dict = line.rstrip()[1:-2].split(",")
        command_set += [wubCMD_entry(*cmd_dict)]
        command_names += [cmd_dict[0].strip('\"')]
        
ctlg = wubCMD_catalog(command_set)

ctlg.set_reference('name')
