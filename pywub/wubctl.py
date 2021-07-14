from enum import Enum
import serial
import time

from . import commands

cmd_dict = {}

for command in commands.cmd_list:
    method_name = "cmd_" + command.lower()
    cmd_dict[method_name] = command

    
class wuBaseCtl():
    
    def __init__(self, port, baudrate=1181818, mode="ascii", autobaud=True):
        
        self._port = port
        self._baudrate = baudrate
        self._autobaud=True
        
        #FIXME: When we have a binary mode, support it. 
        if mode.lower() != "ascii":
            print(f"CTL mode \"{mode}\" not supported.")
            print(f"Defaulting to ASCII.")
        try:
            self.s = serial.Serial(port, baudrate, timeout=1)
        except serial.SerialException: 
            print(f"Failed to open port \"{port}\"; exiting.")
            #raise serial.SerialException("") 
            

            
    def send(self, cmd):
        '''
        cmd: ascii command string
        
        returns: number of bytes written
        '''
        return self.s.write((cmd+"\n").encode('utf-8'))
    
    def recv(self):
        return wub.s.read(wub.s.in_waiting)
    
    def send_recv_ascii(self, cmd, delay=0.3):
        '''
        Send and receive an ASCII string. 
        
        cmd : command string

        '''
        #Define the delimeters
        
        if self._autobaud: 
            cmd = "U" + cmd
        print(f"{cmd}")
        self.s.write((cmd+"\n").encode('utf-8'))
        

        time.sleep(delay)
        answer = self.s.read(self.s.in_waiting).decode()
        return answer
     
    def enable_autobaud(self):
        response = self.send_recv_ascii("BAUD -1")
        self._autobaud = True
        return response

    def set_baud(self):
        response = self.send_recv_ascii(f"BAUD {self.baudrate}")
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
        return self.send_recv_ascii(cmd, 0.01)

def create_method(method_name, command):
    def new_method(self, *args):
        full_command = " ".join([command] + list(args))
        return self.send_recv_ascii(full_command, delay=0.2)
    new_method.__name__ = method_name
    setattr(wuBaseCtl, method_name, new_method)

for method_name, command in cmd_dict.items():
    create_method(method_name, command)