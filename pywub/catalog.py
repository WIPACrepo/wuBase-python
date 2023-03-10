from enum import Enum, IntEnum, auto
import struct
import os



# try:
#     import importlib.resources as pkg_resources
# except ImportError:
#     # Try backported to PY<37 `importlib_resources`.
#     import importlib_resources as pkg_resources
    
    
#Helper classes
class wubCMD_SERV(IntEnum):
    SERV_SLOW_CTRL = int("3030", 16)
    SERV_DATA = auto()

class wubCMD_RC(IntEnum):
    # Command response codes. 
    CMD_RC_OK = ord('a') #is a char because we can see it in the terminal directly. 
    CMD_RC_INVALID_COUNT = auto()
    CMD_RC_INVALID_COMMAND = auto()
    CMD_RC_INVALID_NUMBER = auto()
    CMD_RC_OUT_OF_RANGE = auto()
    CMD_RC_COMMAND_FAILED = auto()
    CMD_RC_BUSY = auto()
    CMD_RC_TIMEOUT = auto()
    CMD_RC_BADCRC = auto()
    CMD_RC_INVALID_UNPACK = auto()
    
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
        
    def __repr__(self):
        return f"ID: {hex(self.cmd_id)}\tCMD_NAME: {self.cmd_name:20s}\
                \tARGS: {self.args:5s}\tRETARGS: {self.retargs if len(self.retargs) > 0 else None}"
    
    def build(self, mode : str = 'b', *args) -> bytes:
        '''Build a bytes object from a wubCMD and related arguments. 
        
        Args:
            mode (str): comms mode (ascii || binary)
            *args: Variable length argument list to pass along with command. 
            
        Returns:
            bytes: formatted command object.
        
        '''
        
        command_str = ''
        arg_str = ''
        build = None
        if(mode.upper()[0] == 'A'): #Covers 'ascii, a, ASCII, asc, etc.'
            command_str = f"{self.name.upper()}"
            
            if self.args is not None:
                for i, fmt in enumerate(self.args):
#                    formatters = f" {{i}}"
                    arg_str += f" {args[i]}"

            build = (command_str + arg_str.format(*args)).encode('utf-8')
            
        else: #Binary
        
            command_str = struct.pack(f"!HH", 0, self.cmd_id) 
            arg_str = struct.pack(f"!{self.args}", *args)
            
            build = command_str + arg_str 
            
        return build + bytes('\n', 'utf-8')

    
class wubCMD_catalog():
    
    _return_codes = wubCMD_RC
    
    def __init__(self, cmd_list = []):
        
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

    def get_command(self, name:wubCMD_entry):
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
data_file = os.path.join(this_dir, "command_subset-csv.txt")


with open(data_file , 'r') as f:
    for line in f.readlines():
        cmd_dict = line.rstrip()[1:-2].split(",")
        #print(cmd_dict)
        command_set += [wubCMD_entry(*cmd_dict)]
        command_names += [cmd_dict[0].strip('\"')]
        
ctlg = wubCMD_catalog(command_set)

ctlg.set_reference('name')
#wubcmd.keys() 



