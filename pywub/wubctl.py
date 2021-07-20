from enum import Enum
import serial
import time

from . import commands
from collections import deque

cmd_dict = {}

for command in commands.cmd_list:
    method_name = "cmd_" + command.lower()
    cmd_dict[method_name] = command

class InvalidCommandException(Exception):
    """Raised when an invalid command is sent to the wuBase."""
    pass

class wuBaseCtl():
    
    def __init__(self, port, baudrate=1181818, mode="ascii", autobaud=True, timeout=0):
        

        self._port = port
        self._baudrate = baudrate
        self._autobaud=True
        self._verbose = False        
        self._timeout=timeout
        
        #FIXME: When we have a binary mode, support it. 
        if mode.lower() != "ascii":
            print(f"CTL mode \"{mode}\" not supported.")
            print(f"Defaulting to ASCII.")
            
        try:
            self._s = serial.Serial(port, baudrate, timeout=self._timeout)
        except serial.SerialException: 
            print(f"Failed to open port \"{port}\"; exiting.")
            #raise serial.SerialException("") 
                        
    def send(self, cmd):
        '''
        cmd: ascii command string
        
        returns: number of bytes written
        '''
        return self._s.write((cmd+"\n").encode('utf-8'))
    
    def recv(self):
        return self._s.read(self._s.in_waiting)
    
    
    
    def send_recv_ascii(self, cmd):
        '''
        Send and receive an ASCII string. 
        
        cmd : command string

        '''
        #Define the delimeters
        answer = ""
        
        if self._autobaud: 
            cmd = "U" + cmd
        if self._verbose:
            print(f"{cmd}")
            
        self._s.write((cmd+"\n").encode('utf-8'))
        
        # define character sequence that denotes end of command response
        # (error responses will be handled by timeout)    
        command_response_error=False

        nbytes_recv = 0
        response_deq = deque(maxlen=3)
        ok = "OK\n"
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
                        
                nbytes_recv += len(data)
                answer += data
            else: #Timeout 
                if command_response_error == True: 
                    raise InvalidCommandException(cmd)
                elif "".join(response_deq) == ok: 
                    break
                elif time.time() > tstart + self._timeout:
                    break
        if self._verbose:
            print(f"Total answer: {answer}")
            
        return answer.replace(ok, '').rstrip('\n')

    ##############
    
    def set_verbosity(self, verbosity):
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

def create_method(method_name, command):
    def new_method(self, *args):
#        full_command = " ".join([command] + list(args))
        full_command = " ".join([command] + [str(a) for a in args])
        return self.send_recv_ascii(full_command)
    new_method.__name__ = method_name
    setattr(wuBaseCtl, method_name, new_method)

for method_name, command in cmd_dict.items():
    create_method(method_name, command)