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
        if mode.lower != "ascii":
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
    
    def send_recv_ascii(self, cmd, delay=0.1):
        '''
        Send and receive an ASCII string. 
        
        cmd : command string

        '''
        #Define the delimeters
        
        if self._autobaud: 
            cmd = "U" + cmd
        print(f"{cmd}")
        self.s.write((cmd+"\n").encode('utf-8'))
        

        time.sleep(0.3)
        answer = wub.s.read(wub.s.in_waiting).decode()
        return answer
        
        #Wait for some return data to arrive. 
        #collect the response and write to file, also watch for terminator
#         command_response_error = False
#         nbytes_recv = 0
#         while True:
#             #blocking read of at least one byte:
#             data=self.s.read(s.in_waiting or 1)
#             ndata=len(data)
#             if ndata>0:
#                 #check for ? at beginning of response
#                 if send_and_receive_nbytes==0: 
#                     if data[0]==b'?': 
#                         command_response_error=True
                        
#                 nbytes_recv+=ndata
                
#                 if ndata>response_length:
#                     response_buffer[:response_length]=data[-response_length:]
#                     response_n=response_length
#                 else:
#                     if response_n>response_half_full:
#                         nold=response_length-ndata
#                         response_buffer[:nold]=response_buffer[response_n-nold:response_n]
#                         response_buffer[nold:nold+ndata]=data
#                         response_n=response_length
#                     else:
#                         response_buffer[response_n:response_n+ndata]=data
#                         response_n+=ndata 
#                 else:
#                     if response_buffer[response_n-ok_bytes_len:response_n]==ok_bytes:
#                         if stop_reception_requested==False: break
#                         if response_buffer[response_n-okok_bytes_len:response_n]==okok_bytes: break
#                     if send_and_receive_nbytes>reftime_nbytes:
#                         reftime=time.time()
#                         reftime_nbytes=send_and_receive_nbytes
#                     else:
#                         if time.time()>reftime+timeout: break



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
            if self._autobaud:
                cmd = "U" + cmd

            return self.send_recv_ascii(cmd, 0.01)

def create_method(method_name, command):
    def new_method(self, *args):
        full_command = " ".join([command] + list(args))
        return self.send_recv_ascii(full_command, delay=0.2)
    new_method.__name__ = method_name
    setattr(wuBaseCtl, method_name, new_method)

for method_name, command in cmd_dict.items():
    create_method(method_name, command)