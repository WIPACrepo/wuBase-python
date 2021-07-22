from enum import Enum, IntEnum
import serial
import sys
import time
import numpy as np

from . import commands
from collections import deque

# cmd_list = list(np.genfromtxt("commands.txt", dtype=str))
# wubc = IntEnum('wubc', cmd_list)

cmd_dict = {}
for command in commands.cmd_list:
    method_name = "cmd_" + command.lower()
    cmd_dict[method_name] = command

    
class InvalidCommandException(Exception):
    """Raised when an invalid command is sent to the wuBase."""
    pass

class wuBaseCtl():
    
    def __init__(self, port, baudrate=1181818, mode="ascii", autobaud=True, timeout=0):
        self._s = None
        self._port = port
        self._baudrate = baudrate
        self._autobaud=True
        self._verbose = False        
        self._timeout=timeout
        
        self._send_recv_running = False
        
        self.nbytes_recv = 0
        
        #FIXME: When we have a binary mode, support it. 
        if mode.lower() != "ascii":
            print(f"CTL mode \"{mode}\" not supported.")
            print(f"Defaulting to ASCII.")
            
        try:
            self._s = serial.Serial(port, baudrate, timeout=self._timeout)
        except serial.SerialException: 
            print(f"Failed to open port \"{port}\"; exiting.")
            sys.exit(1)
            
    def __del__(self):
        if self._s:
            print("Shutting down serial connection.")
            self._s.close()
            
    def send(self, cmd):
        '''
        cmd: ascii command string
        
        returns: number of bytes written
        '''
        return self._s.write((cmd+"\n").encode('utf-8'))
    
    def recv(self):
        '''
        returns whatever bytes are waiting in the UART buffer. 
        '''
        return self._s.read(self._s.in_waiting)
    
    def send_recv_ascii(self, cmd, datafile=None):
        '''
        Send and receive data in ASCII mode. 
        
        cmd : command string
        datafile : output datafile for writing 
        
        If datafile is not None, the "answer" string is not populated
        and in stead the return strings are written to the file. 

        '''

        if self._verbose:
            print(f"{cmd}")
        
        answer = ""
        command_response_error=False
        nbytes_recv = 0
        response_deq = deque(maxlen=3)
        ok = "OK\n" 
        
        self._send_recv_running = True
        
        if self._autobaud: 
            cmd = "U" + cmd
            
        self._s.write((cmd+"\n").encode('utf-8'))

        tstart = time.time()
        #Wait for some return data to arrive. 
        while True:
            #blocking read of at least one byte:
            #if timeout, len(data) = 0
            data=self._s.read(self._s.in_waiting or 1).decode()
            response_deq.extend([data[i] for i in range(len(data))])   
            
            if self._verbose:
                print(f"data: {data}")
                print(f"data_deq: {response_deq}")
            
            if len(data)>0:
                if nbytes_recv == 0:
                #check for ? at beginning of response
                    if data[0]=='?': 
                        command_response_error=True
                        
                self.nbytes_recv += len(data)
                
                if datafile is not None:
                    datafile.write(data)
                else:
                    answer += data
                    
            else: #Timeout 
                if command_response_error == True: 
                    raise InvalidCommandException(f"{cmd}: {answer}")
                elif "".join(response_deq) == ok: 
                    break
                elif time.time() > tstart + self._timeout:
                    break
                    
                    
        if self._verbose and len(answer) > 0:
            print(f"Total answer: {answer}")
        
        self._send_recv_running = False
        
        # Strip out the delimeter. 
        return answer.replace(ok, '').rstrip('\n')

    ##############
    
    def batch_setup_commands(self, command_list, verbose=True):
        '''
        Run a batch of commands. 
        Best for slow control as does not support file IO (yet).
        '''
        responses = []
        for cmd in command_list:
            cmd_list = cmd.split(' ')
            name = cmd_list[0]
            args = cmd_list[1:]
            print(f"Command: {name}", *args)
            result = getattr(self, f"cmd_{name}")(*args)
            if result and verbose:
                print(result)
            responses += [result]
            
        return responses      
    
    def set_verbosity(self, verbosity):
        '''
        Should probably just bite the bullet and use logging 
        '''
        self._verbose = verbosity
    
    def enable_autobaud(self):
        response = self.send_recv_ascii("BAUD -1")
        self._autobaud = True
        return response

    def set_baud(self, baudrate):
        response = self.send_recv_ascii(f"BAUD {baudrate}")
        self._autobaud = False
        return response

    #Get some properties set up. 
    @property
    def baud(self):
        return self._baud

    @property
    def port(self):
        return self._port

    @property
    def autobaud(self):
        return self._autobaud

    @property
    def UID(self):
        cmd = "GET_UID"
        answer = self.send_recv_ascii(cmd)
        return answer
    
    @property
    def send_recv_running(self):
        return self._send_recv_running

def create_method(method_name, command):
    def new_method(self, *args, **kwargs):
        datafile = kwargs.pop('datafile', None)
        full_command = " ".join([command] + [str(a) for a in args])
        return self.send_recv_ascii(full_command, datafile)
    new_method.__name__ = method_name
    setattr(wuBaseCtl, method_name, new_method)

for method_name, command in cmd_dict.items():
    create_method(method_name, command)