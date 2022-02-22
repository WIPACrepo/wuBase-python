from enum import Enum, IntEnum
import serial
import sys
import time
import numpy as np
import struct

import logging

logger = logging.getLogger(__name__)

from . import catalog

wubCMD_entry = catalog.wubCMD_entry
   
def parse_setup_config(filename):

    with open(filename, 'r') as f:
        config = f.read()

    setup_command_list = []
    for setting in config.split("\n"):
        spl = setting.split(" ")
        command = spl[0]
        sleeptime = spl[1]
        modified_command_args = None
        if len(spl) > 2: 
            command_args = spl[2::]
            modified_command_args = []
            for arg in command_args:
                if arg.isnumeric():
                    modified_command_args += [int(arg)]
                else:
                    modified_command_args += [float(arg)]

        cmd_line = dict(name=command, sleeptime=sleeptime, args=modified_command_args)
        setup_command_list += [cmd_line]
        
    return setup_command_list    

    
class InvalidCommandException(Exception):
    """Raised when an invalid command is sent to the wuBase."""
    pass

class wubCTL():
    
    def __init__(self, port, baudrate=1181818, mode="binary", autobaud=True, timeout=1):
        
        self._s = None
        self._port = port
        self._baudrate = baudrate
        self._autobaud=True
        
        #self._verbose = False        
        self._timeout=timeout
        
        #wuBase operation mode
        self._mode = mode.upper()
        
        #DAQ settings (ASCII mode)
        self._send_recv_running = False #ASCII send-recv 
        self.request_abort = False #Flag 
        self.request_stop = False
        self._abort_requested = False
        self._stop_requested = False
        
        #DAQ settings (BINARY mode)
        self._batch_mode_running = False
        
        self.nbytes_recv = 0
        
        if mode.lower() != "ascii" and mode.lower() != 'binary':
            logger.error(f"CTL mode \"{mode}\" not supported.")
            logger.error(f"Defaulting to ASCII.")
            self._mode = "ascii"
        else:
            self._mode = mode
            
        try:
            self._s = serial.Serial(port, baudrate, timeout=self._timeout)
            self._s.flushInput()
            self._s.flushOutput()
            
        except serial.SerialException: 
            logger.error(f"Failed to open port \"{port}\"; exiting.")
            exit(1)
            #raise serial.SerialException("") 
            
        logger.info(f"Done creating {self.__class__.__name__} object on port {port} with baudrate {baudrate}.")
            
    def __del__(self):
        if self._s:
            logger.info("Shutting down serial connection.")
            self._s.close()
            
    @property 
    def mode(self):
        return self._mode
    
    @property
    def byte_in_waiting(self):
        return self._s.in_waiting
    
    def set_comms_mode(self, mode):
        if (mode.upper())[0] == 'A':
            self._mode = 'ASCII'
        else:
            self._mode = 'BINARY'
            
        
            
    def send(self, cmd):
        '''Sends a LF-terminated command. 
        
        Args: 
            cmd (bytes): LF-terminated, utf-8-encoded bytes object to be sent. 
        
        Returns: 
            int: The number of bytes written. 
        '''
        return self._s.write(cmd)
        
    def recv(self, size:int = None) -> bytes:
        '''Returns bytes waiting in the UART buffer. 
        
        Args:
            size (int): Number of bytes to read. If None, whatever is in the buffer is returned.
        
        Returns: 
            bytes: Whatever is waiting in the UART buffer.
            
        '''
        return self._s.read(size=self._s.in_waiting)
    
    def read(self, size):
        '''Just simplifies reading from the serial port.
        
        '''
        return self._s.read(size=size)

    def unpack_readback(self, command: wubCMD_entry, readback: bytes) -> dict:
        '''Unpack a readback object per the command that issued it.
        
        Args:
            command (wubCMD_entry):  Which command was issued prior to receiving the readback buffer.
            readback (bytes): The readback buffer. 
            
        Returns:
            dict: Return code and return arguments
            
        '''
        
        
        cmd_return_args_size = struct.calcsize(command.retargs)
        cmd_return_code = readback[-1]
        retargs = []

        if len(command.retargs) > 0:
            #print(f"Number of return arguments: {len(command.retargs)}")
            retargs = [f"{i}" for i in struct.unpack(f'>{command.retargs}', readback[-(cmd_return_args_size+1):-1])]
            #print(retargs)
        
        return dict(CMD_RC=cmd_return_code, retargs=retargs)
    
    def send_recv(self, command: wubCMD_entry, *args) -> dict:
        
        if self._mode == 'ASCII':
            
            deq = deque(['0','0','0'], maxlen=3)
            
            wubctl.send(command.build('a'))
            recv_buf = []
            
#             while not wubctl._s.in_waiting:
#                 continue
#             time.sleep(0.001) #For good measure, let more bytes trickle in.

            while("".join(deq) != 'OK\n'):
                response = wubctl._s.read(size=wubctl._s.in_waiting)
                recv_buf += response
                for i in response.decode():
                    deq.append(i)
                
            
            if command == wubcmd.binarymode:
                self._mode = "BINARY"
            
            return dict(response=recv_buf.decode())
            
        else:  
            if command == wubcmd.send_batch:
                self._batch_mode_running = True
            rval = self.send_recv_binary(command, *args)
            
            if command == wubcmd.asciimode:
                self._mode = "ASCII"
                
            return rval
                
        
        
    
    def send_recv_binary(self, command: wubCMD_entry, *args) -> dict:
        '''Send a binary-formatted command and return the response.
        
        Blocks until there is at least one byte in the readback buffer. 
        
        Args:
            command (wubCMD): wubCMD object. 
            *args: Variable length argument list to pass along with command. 
        
        '''
        command_bytes = command.build(self.mode, *args)
        nsent = self.send(command_bytes)
        logger.debug(f"nsent: {nsent}\t len(command_bytes): {len(command_bytes)}")
        
        cmd_return_args_size = struct.calcsize(command.retargs)
        #print(cmd_return_args_size)
        while self._s.in_waiting != cmd_return_args_size + 1:
            continue
            
        #readback = self._s.read(size=self._s.in_waiting)
        readback = self._s.read(size=cmd_return_args_size + 1) #+1 for the CMD_RC
        if len(readback) != cmd_return_args_size + 1:
            readback2 = self._s.read(size=cmd_return_args_size + 1 - len(readback)) 
            readback = readback + readback2
        response = self.unpack_readback(command, readback)
        
#         logger.debug("---------------")
#         logger.debug(f"Readback: {readback}")
#         logger.debug("---------------")
# #         logger.debug("*** Decoded: ")
# #         logger.debug(readback[0:-(cmd_return_args_size+1)].decode())
#         logger.debug("*** Unpacked: ")
# #        print(response)
#         logger.debug(f"***\tCMD_RC: {wubCMD_RC(response['CMD_RC']).name}")
#         logger.debug(f"***\tRetargs: {response['retargs']}")
#         logger.debug("---------------")
        return response



    def binary_batchmode_recv(self, datafile=None):
        '''
            Binary batchmode receiver.
        '''
       
        self._batch_mode_running = True

        nframes = 0
        
        tstart = time.time()
        #Wait for some return data to arrive. 
        while True:
            
            if self.request_abort and not self._abort_requested:
                #e.g. if we control+C'd out of the batch.
                logger.info("Abort requested.")
                self._abort_requested = True
                break
            elif self.request_stop and not self._stop_requested:
                #Tell the wuBase to stop sending data. 
                logger.info("Stop requested.")
                self._stop_requested = True
                #FIXME: Add whatever binay command is required to stop transmission.
#                 self._s.write(ok.encode('utf-8'))
            
            
            
            #blocking read of two bytes. 
            #This will be the total size of the 
            #if timeout, len(data) = 0
            data=self.read(2)
            
            if len(data)>0:
                nframes += 1
                nsamples = struct.unpack("<H", data)
                payload_len_total = 2 + 6 + 8 + 4*nsamples
                logger.info(f"Received frame; nsamples = {nsamples}")
                
                data = self.read(payload_len_total-2) #We've already read 2 bytes of the toal length. 
                
                if len(data) != payload_len_total - 2: #timeout?
                    logger.error(f"readback was not the right length: {len(data)} vs {payload_len_total-2}")
                    break
                
                
                self.nbytes_recv += len(data)
                
                if datafile is not None:
                    datafile.write(data)
#                 else: 
#                     answer += data
                    
            else: #Timeout 
                if time.time() > tstart + self._timeout:
                    break
                    
                
        logger.info(f"Total number of frames received: {nframes}")
        logger.info(f"Total number of bytes received:  {self.nbytes_recv}")
        self._batch_mode_running = False
        
        return 0