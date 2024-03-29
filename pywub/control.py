import serial
import sys
import time
#import numpy as np
import struct
from enum import IntEnum, auto
from io import TextIOWrapper
#import yaml
import threading



from . import parser as parser
from collections import deque 
from queue import Queue

from . import catalog
from .catalog import ctlg as wubCMD_catalog
from .catalog import wubCMD_RC

wubCMD_entry = catalog.wubCMD_entry

import logging
logger = logging.getLogger(__name__)

class readout_state(IntEnum):
    waiting_on_start_word = ord('a') #is a char because we can see it in the terminal directly. 
    waiting_on_nsamples = auto()
    waiting_on_payload = auto()


class CustomFormatter(logging.Formatter):
    """Logging colored formatter, adapted from https://stackoverflow.com/a/56944256/3638629"""

    grey = '\x1b[38;21m'
    green = '\x1b[38;5;82m'
    blue = '\x1b[38;5;39m'
    yellow = '\x1b[38;5;226m'
    red = '\x1b[38;5;196m'
    bold_red = '\x1b[31;1m'
    reset = '\x1b[0m'

    def __init__(self, fmt):
        super().__init__(datefmt="%Y-%m-%d %H:%M")
        self.fmt = fmt
        self.FORMATS = {
            logging.DEBUG: self.green + self.fmt + self.reset,
            logging.INFO: self.blue + self.fmt + self.reset,
            logging.WARNING: self.yellow + self.fmt + self.reset,
            logging.ERROR: self.red + self.fmt + self.reset,
            logging.CRITICAL: self.bold_red + self.fmt + self.reset
        }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)


   


    
class InvalidCommandException(Exception):
    """Raised when an invalid command is sent to the wuBase."""
    pass

   


class wubCTL():
    '''
    Base class for running wuBase via USB UART. 
    '''
    
    def __init__(self, port=None, baud=1181818, mode="ascii", 
                 autobaud=True, timeout=1, verbosity=False,
                 store_mode='bulk', parity=False):
        
        self._s = None
        self._port = port
        self._baudrate = baud
        self._parity = serial.PARITY_EVEN if parity else serial.PARITY_NONE

        self._timeout=timeout
      
        #DAQ settings
        self._store_mode = store_mode
        self._batch_mode_running = False
        self.request_abort = False #Flag 
        self.request_stop  = False
        self._abort_requested = False
        self._stop_requested = False        

        #wuBase operation mode
        self._autobaud=autobaud
        self._mode = mode.upper()

        #DAQ settings (ASCII mode)
        
        #DAQ settings (BINARY mode)
        self._binaryverbosity = verbosity        
        
        #Number or received bytes (both modes)
        self.nbytes_recv = 0
        self.nframes_binary = 0

        self.catalog = wubCMD_catalog
        
        if mode.lower() != "ascii" and mode.lower() != 'binary':
            logger.warning(f"CTL mode \"{mode}\" not supported.")
            logger.warning(f"Defaulting to ASCII.")
            self._mode = "ascii"
        else:
            self._mode = mode
            
        try:
            self._s = serial.Serial(self._port, self._baudrate, 
                                    timeout=self._timeout, 
                                    stopbits=1, 
                                    parity =self._parity, 
                                    bytesize = 8)
            self._s.flushInput()
            self._s.flushOutput()
                       
            
        except serial.SerialException: 
            logger.error(f"Failed to open port \"{port}\"; exiting.")
            exit(1)
            #raise serial.SerialException("") 

        def create_method(command:wubCMD_entry):
            def new_method(self, *args, **kwargs):
                return self.send_recv(command, *args)

            name = f"cmd_{command.name.lower()}"
            new_method.__name__ = name
        
            setattr(wubCTL, name, new_method)

        logger.info(f"Generating {len(self.catalog.keys())} methods from catalog")
        for cmd in self.catalog.keys():
            create_method(self.catalog[cmd])

        logger.info(f"Done creating {self.__class__.__name__} object on port {port} with baudrate {self._baudrate}.")
        logger.info(f"Operations mode: {self._mode}")
            


    def __del__(self):
        if self._s:
            if not self.isascii:
                logger.info("Reverting to ASCII mode.")
                self.cmd_asciimode()
            if not self.autobaud:
                logger.info("Reverting to autobaud mode.")
                self.set_autobaud()

            logger.info("Shutting down serial connection.")
            self._s.close()

    @property
    def binaryverbose(self):
        return self._binaryverbosity
    @property
    def autobaud(self):
        return self._autobaud

    @property 
    def mode(self):
        return self._mode

    @property 
    def isascii(self):
        if (self.mode.upper())[0] == 'A':
            return True
        else:
            return False        
        
    @property
    def batch_mode_running(self):
        return self._batch_mode_running
    
    @property
    def bytes_in_waiting(self):
        return self._s.in_waiting
    
    def set_comms_mode(self, mode:str):
        if (mode.upper())[0] == 'A':
            #self.cmd_asciimode()
            self._mode = 'ASCII'
        else:
            #self.cmd_binarymode()
            self._mode = 'BINARY'

    def set_baud(self, baud:int):
        if baud < 1: 
            ret = self.cmd_baud(-1)
            self._autobaud = True
        else:
            ret = self.cmd_baud(baud)
            self._autobaud = False

        return ret
    
    def set_autobaud(self):
        return self.set_baud(-1)
        
            
    def send(self, cmd:bytes) -> int:
        '''Sends a LF-terminated command. 
        
        Args: 
            cmd (bytes): LF-terminated, utf-8-encoded bytes object to be sent. 
        
        Returns: 
            int: The number of bytes written. 
        '''
        if self.autobaud:
            #print("autobaud")
            self._s.write('U'.encode())
        return self._s.write(cmd)
        
    def recv(self, size:int = None) -> bytes:
        '''Returns bytes waiting in the UART buffer. 
        
        Args:
            size (int): Number of bytes to read. If None, whatever is in the buffer is returned.
        
        Returns: 
            bytes: Whatever is waiting in the UART buffer.
            
        '''
        if size is None: 
            return self._s.read(size=self._s.in_waiting)
        else:
            return self._s.read(size=size)
    
    def read(self, size:int) -> bytes:
        '''Just simplifies reading from the serial port. 
        
        '''
        data = self._s.read(size=size)
        #self.nbytes_recv += len(data)
        return data

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
        logger.debug(readback)
        if len(command.retargs) > 0:
            retargs = [i for i in struct.unpack(f'>{command.retargs}', readback[-(cmd_return_args_size+1):-1])]
        
        return dict(CMD_RC=cmd_return_code, retargs=retargs)
    
               
    def send_recv_ascii(self, command: wubCMD_entry, *args) -> dict:    
        '''Send a ASCII-formatted command and return the response.
        
        Blocks until there is at least one byte in the readback buffer. 
        
        Args:
            command (wubCMD): wubCMD object. 
            *args: Variable length argument list to pass along with command. 
        
        '''
        logger.debug("ASCII send_recv")
        deq = deque(['0','0','0'], maxlen=3)
            
        cmd = command.build('a', *args)
        logger.debug(f"Command string being sent: {cmd}")
        self.send(cmd)
        recv_buf = []
        
        error_found = False
        #FIXME: Add a timeout here.
        while("".join(deq) != 'OK\n' and not error_found):
            response = self._s.read(size=self._s.in_waiting)
            recv_buf += response
            for i in response.decode():
                if i == '?':
                    error_found = True
                deq.append(i)
        
        if command == wubCMD_catalog.binarymode:
            self.set_comms_mode("BINARY")
        elif command == wubCMD_catalog.baud:
            if args[0] == -1:
                self._autobaud = True
                self._s.baudrate = self._baudrate
            else:
                self._autobaud = False
                self._s.baudrate = args[0]
                self._baudrate = args[0]            
        
        logger.debug(f"Command response bytes: {recv_buf}")
        
        return dict(response=bytes(recv_buf).decode())
    
    def send_recv_binary(self, command: wubCMD_entry, *args) -> dict:
        '''Send a binary-formatted command and return the response.
        
        Blocks until there is at least one byte in the readback buffer. 
        
        Args:
            command (wubCMD): wubCMD object. 
            *args: Variable length argument list to pass along with command. 
        
        '''
        command_bytes = command.build('b', *args)
        
        nsent = self.send(command_bytes)

        #logger.debug(f"nsent: {nsent}\t len(command_bytes): {len(command_bytes)}")
        #print([f"{b:x}" for b in command_bytes])
        cmd_return_args_size = struct.calcsize(command.retargs)
        #while self._s.in_waiting != cmd_return_args_size + 1:
        #Wait for at least one byte (the return code).
    
        #FIXME: Need to catch case where insufficient bytes are transmitted. 
        readback = None       
        if self.binaryverbose:
            time.sleep(0.5) #Ensure we have everything. 

            readback = self._s.read(size=self._s.in_waiting)

            logger.debug("Verbose mode bytes captured: ")
            verbose_output = readback[0:-(cmd_return_args_size + 1)]
            if(len(verbose_output) > 0):
                logger.debug(verbose_output.decode())
            else:
                logger.debug("No verbose response.")

            
        else:
            readback = self._s.read(size=cmd_return_args_size + 1) #+1 for the CMD_RC

            #This is a lazy way to do this. 
            # FIXME: make this a for loop, try it a few times, and throw an error if it fails
            if len(readback) != cmd_return_args_size + 1:
                readback2 = self._s.read(size=cmd_return_args_size + 1 - len(readback)) 
                readback = readback + readback2

        response = self.unpack_readback(command, readback[-(cmd_return_args_size + 1)::])
        #logger.debug(f"Command: {command.name}"
        logger.debug("---------------")
        logger.debug(f"Readback: {readback}")
        logger.debug("---------------")
        # logger.debug("*** Decoded: ")
        # logger.debug(readback[0:-(cmd_return_args_size+1)].decode())
        logger.debug("*** Unpacked: ")
        try:
            logger.debug(f"***\tCMD_RC: {wubCMD_RC(response['CMD_RC']).name}")
            logger.debug(f"***\tRetargs: {response['retargs']}")
        except ValueError:
            logger.warning(f"*** Invalid RC code in response (likely due to verbosity)\n")
            
        logger.debug("---------------")

        if command == wubCMD_catalog.asciimode:
            self.set_comms_mode("ASCII")

        return dict(response=response)
    
    def send_recv(self, command: wubCMD_entry, *args) -> dict:       
       
        if self.isascii:
            resp = self.send_recv_ascii(command, *args)
        else:  
            if command == wubCMD_catalog.send_batch:
                self._batch_mode_running = True
            resp = self.send_recv_binary(command, *args)

        #Catch special cases and set internal flags:             
        if command == wubCMD_catalog.asciimode:
            self.set_comms_mode("ASCII")
        elif command == wubCMD_catalog.binarymode:
            self.set_comms_mode("BINARY")
        elif command == wubCMD_catalog.verbose:
            self._binaryverbosity = args[0]
        elif command == wubCMD_catalog.baud:
            if args[0] == -1:
                self._autobaud = True
                self._s.baudrate = self._baudrate
            else:
                self._autobaud = False
                self._s.baudrate = args[0]
                self._baudrate = args[0]

        return resp



    def ascii_batchmode_recv(self, ntosend:int, modenostop:bool, datafile:TextIOWrapper=None) -> dict:
        '''
            ASCII batchmode receiver.
        '''

        logger.debug("Entering ASCII batchmode receiver.")
        self._batch_mode_running = True
        logger.info(f"Issuing batchmode send with ntosend = {ntosend} and modenostop = {modenostop}")
        # Hard-code this bit to allow the while loop to execute.
        self.send(f"send_batch {ntosend} {modenostop}\n".encode())

        nbytes_recv = 0
        response_deq = deque(maxlen=3)

        command_response_error=False
        ok = "OK\n" 
        answer = ""
        data = ""

        tstart = time.time()
        #Wait for some return data to arrive. 
        while True:
            logger.debug(f"request_abort : {self.request_abort}")
            logger.debug(f"request_stop  : {self.request_stop}")

            if self.request_abort and not self._abort_requested:
                #e.g. if we control+C'd out of the batch.
                logger.warning("Abort requested.")
                self._abort_requested = True
                break
            elif self.request_stop and not self._stop_requested:
                #Tell the wuBase to stop sending data. 
                logger.warning("Stop requested.")
                self._stop_requested = True
                resp = self.cmd_ok()['response']
                logger.debug(resp)
                response_deq.extend([resp[i] for i in range(len(resp))])   
                break
            
            #blocking read of at least one byte:
            #if timeout, len(data) = 0
            data=self._s.read(self._s.in_waiting or 1).decode()
            response_deq.extend([data[i] for i in range(len(data))])   
            
#            if self._verbose:
            logger.debug(f"batchmode data: {data}")
            logger.debug(f"batchmode data_deq: {response_deq}")

            if len(data)>0:
                # if nbytes_recv == 0:
                # #check for ? at beginning of response to catch that an inva
                #     if data[0]=='?': 
                #         command_response_error=True
                        
                self.nbytes_recv += len(data)
                
                if datafile is not None:
                    datafile.write(data)
                else: 
                    answer += data
                    
            else: #Socket timeout 
                if "".join(response_deq) == ok: 
                    logger.debug("EOL detected")
                    break
                elif time.time() > tstart + self._timeout:
                    logger.debug(f"Socket timeout detected.")
                    #break

            # if "".join(response_deq) == ok: 
            #     logger.debug("EOL detected")
            #     break
                
         
        logger.info(f"Total number of bytes received:  {self.nbytes_recv}")

        self._batch_mode_running = False        
        return dict(response=answer)
    
    def binary_stop_batch(self):

        self.send(wubCMD_catalog.ok.build('b'))
        time.sleep(0.25) #Wait long enough for the most recent frame to be done.,
        resp = self.read(self._s.in_waiting) #Flush

        self.send(wubCMD_catalog.ok.build('b'))
        time.sleep(0.01) #Wait long enough for the most recent frame to be done.,
        resp = self.read(self._s.in_waiting) #Flush

        resp_rc = resp[-1]             
        logger.debug(f"Stop return bytes: {resp}")
        logger.info(wubCMD_RC(resp_rc).name)



    def binary_batchmode_recv(self, ntosend:int, modenostop:bool, datafile:TextIOWrapper=None) -> dict:
        '''
            Binary batchmode receiver.
        '''
       
        logger.debug("Entering BINARY batchmode reciever.")
        self._batch_mode_running = True
        self.nframes_binary = 0
        logger.info(f"Issuing batchmode send with ntosend = {ntosend} and modenostop = {modenostop}")
        self.nframes_binary = 0
        
        resp = self.cmd_send_batch(ntosend, modenostop)['response']
        try:
            logger.info(f"***\tCMD_RC: {wubCMD_RC(resp['CMD_RC']).name}")
        except ValueError:
            logger.warning(f"*** Invalid RC code in response (likely due to verbosity); full response: {resp}\n")

        tstart = time.time()
        #Wait for some return data to arrive. 
        resp['CMD_RC'] = wubCMD_RC.CMD_RC_WAITING
         
        start_word = []
        start_bytes = []
        nstartwords_remaining = 2
        
        pipeline_buffer = Queue()
        nsamples = 0
        waiting_for_header = True

        self.ro_state = readout_state.waiting_on_start_word

        logger.info(f"Note: data storage being done using '{self._store_mode}' method.")
        while True:
           
            if self.request_abort and not self._abort_requested:
                #e.g. if we control+C'd out of the batch.
                logger.info("Abort requested. This may leave the wuBase in a weird state.")
                self._abort_requested = True
                self.binary_stop_batch()
                break
            elif self.request_stop and not self._stop_requested:
                #Tell the wuBase to stop sending data. 
                self._stop_requested = True
                logger.info("Stop requested.")                
                self.binary_stop_batch()
                break


            if self._store_mode == "sb":
                ## Start byte method.

                if self.ro_state == readout_state.waiting_on_start_word:
                    #logger.debug("Waiting on start byte...")

                    if self.bytes_in_waiting >= parser.START_BYTE_WIDTH:
                        start_byte = self.read(parser.START_BYTE_WIDTH)
                        self.nbytes_recv += len(start_byte)
                    else:
                        continue

                    dc = struct.unpack("<B", start_byte)[0]
                    if dc  != parser.START_BYTE:
                        logger.warning(f"Start byte not read at expected spot! {dc:x}") 
                        self.ro_state = readout_state.waiting_on_start_word
                    else:
                        self.ro_state = readout_state.waiting_on_nsamples

                elif self.ro_state == readout_state.waiting_on_nsamples:
                    logger.debug("Waiting on nsamples...")

                    if self.bytes_in_waiting >= parser.NSAMPLES_WIDTH:
                        nsamples_bytes = self.read(parser.NSAMPLES_WIDTH)
                        self.nbytes_recv += len(nsamples_bytes)

                        nsamples = parser.unpack_nsamples(nsamples_bytes)
                        hex_nsamples = [f"{i:x}" for i in nsamples_bytes]
                        logger.debug(f"Decoded nsamples: {nsamples}; bytes = {hex_nsamples}")
                        
                        self.ro_state = readout_state.waiting_on_payload

                        if datafile is not None:
                            datafile.write(nsamples_bytes)

                    else:
                        continue

                elif self.ro_state == readout_state.waiting_on_payload:


                    frame_size = parser.calc_frame_size(nsamples)
                    logger.debug(f"Waiting on payload... Required/In waiting: {frame_size - parser.NSAMPLES_WIDTH } / {self.bytes_in_waiting}")

                    
                    if self.bytes_in_waiting >= frame_size - parser.NSAMPLES_WIDTH:

                        readout = self.read(frame_size - parser.NSAMPLES_WIDTH)
                        self.nbytes_recv += len(readout)


                        header = (nsamples_bytes + readout)[0:parser.HEADER_SIZE]
                        #logger.debug(header)
                        nsamples, frame_id, fpga_ts, fpga_tdc = parser.unpack_header(header)

                        logger.debug(f"{nsamples:4X} {frame_id:4X} {fpga_ts:8X} {fpga_tdc:16X}");
                        
                        payload = (nsamples_bytes + readout)[parser.HEADER_SIZE::]
                        payload_hex = [f"{i:x}" for i in payload]
                        logger.debug(f"Payload size: {parser.calc_payload_size(nsamples)}")
                        logger.debug(f"Payload hex:  {payload_hex}")
                        self.ro_state = readout_state.waiting_on_start_word

                        if datafile is not None:
                            datafile.write(readout)

                        self.nframes_binary += 1
                    else: 
                        continue
                        
            elif self._store_mode == "bulk":
                ## BASIC DUMP METHOD
                data = self.read(self.bytes_in_waiting)
                if datafile is not None:
                    #datafile.write(start_word)
                    datafile.write(data)
                self.nbytes_recv += len(data)                        

            else:  #FIXME: Need to deal with start byte!
                ## ORIGINAL METHOD
                if(self.bytes_in_waiting > parser.NSAMPLES_WIDTH):
                # blocking read of bytes. 
                # This will be the number of samples in the payload.
                # if timeout, len(data) != nstartwords_remaining, or 0 if nothing recieved.

                    start_bytes=self.read(parser.NSAMPLES_WIDTH)

                    start_word = start_bytes

                    # if len(start_bytes) == parser.NSAMPLES_WIDTH:
                    #     start_word = start_bytes
                    # else:
                    #     start_word += [i for i in start_bytes]
                    #     nstartwords_remaining -= len(start_bytes)
                    #     continue
                    
                    if len(start_word)==parser.NSAMPLES_WIDTH:
                        
                        bt = [f"{i:x}" for i in start_word]
                        logger.debug(f"nsamples hex values: {bt}")
                        self.nframes_binary += 1
                        #nsamples = struct.unpack("<H", start_word)[0]
                        nsamples = parser.unpack_nsamples(start_word)
                        # Payload total = 
                        # n_samples + fpga_timestamp (48 bits) + fpga_tdcword (64 bits) + adc_data (16 bits per sample)
                        payload_len_total = parser.calc_frame_size(nsamples)

                        logger.debug(f"nsamples = {nsamples}; payload_length = {payload_len_total}")              
                        logger.debug(f"self.bytes_in_waiting: {self.bytes_in_waiting}")
                        data = self.read(payload_len_total-parser.NSAMPLES_WIDTH) #We've already read 2 bytes of the toal length. 
                    
                        header = bytearray(start_word + data)[0:parser.HEADER_SIZE]
                        logger.debug(header)
                        nsamples, frame_id, fpga_ts, fpga_tdc = parser.unpack_header(header)
                        logger.debug(f"{nsamples:4X} {frame_id:4X} {fpga_ts:8X} {fpga_tdc:16X}");
                        # frame_size = calc_frame_size(nsamples)
                        # payload_size = calc_payload_size(nsamples)                

                        if len(data) != payload_len_total - parser.NSAMPLES_WIDTH: #timeout?
                            logger.error(f"Readback was not the right length: {len(data)} vs {payload_len_total-parser.NSAMPLES_WIDTH}")
                            logger.error(f"nsamples_bytes: {bt}\t ")
                            #logger.error(data)
                            if datafile is not None:
                                datafile.write(start_word)
                                datafile.write(data)

                            self.binary_stop_batch()
                            break
                        
                        self.nbytes_recv += len(data) + parser.NSAMPLES_WIDTH
                        
                        if datafile is not None:
                            datafile.write(start_word)
                            datafile.write(data)

                        start_bytes = []
                        start_word = []
                        nstartwords_remaining = parser.NSAMPLES_WIDTH



                else: #Socket timeout 
                    if time.time() > tstart + self._timeout:
                        logger.debug(f"Readout timeout detected.")
                    elif resp['CMD_RC'] == wubCMD_RC.CMD_RC_OK:
                        logger.debug("Received exit code from wuBase.")
                        break
                    
        if self._store_mode != "bulk":
            logger.info(f"Frames received: {self.nframes_binary} (0x{self.nframes_binary:X})")
        logger.info(f"Bytes received:  {self.nbytes_recv} (0x{self.nbytes_recv:X})")
        self._batch_mode_running = False
        
        self.read(self._s.in_waiting)

        return 0


    def batchmode_recv(self, ntosend:int, modenostop:bool, datafile:TextIOWrapper=None) -> dict:
        '''
        Args: 
            ntosend (int): how many to send, or negative to send all available
            modenostop (bool): = 0: sending will stop when no more hits are available in
                 * memory = 1: sending will not stop until count is satisfied, or a new command is
                 * received; this means there can be pauses in the transmitted data while waiting
                 * for events to be readied

        
        '''

        modenostop = 1 if modenostop else 0

        if self.isascii:
            return self.ascii_batchmode_recv(ntosend, modenostop, datafile)
        else:
            return self.binary_batchmode_recv(ntosend, modenostop, datafile)
        







            # self.wubctl.send(f"BINARYMODE\n".encode())
            # logger.debug("ASCII send_recv")
            # deq = deque(['0','0','0'], maxlen=3)
            
            # recv_buf = []
                
            # while("".join(deq) != 'OK\n'):
            #     response = wubctl._s.read(size=wubctl._s.in_waiting)
            #     recv_buf += response
                
            #     for i in response.decode():
            #         deq.append(i)

            #     #print(deq)
            # logger.debug(f"Command response bytes: {recv_buf}")
            

        # status = wubctl.cmd_status()
        # logger.info(status)

        # YAML version below. 
        # for cmd in setup_command_dict.keys():
        #     entry = setup_command_dict[cmd]
        #     logger.debug(f"Executing command for entry '{cmd}'")
        #     while True:
        #         setup_cmd_name = str.upper(cmd)
        #         setup_cmd_args = entry['args']
        #         sleeptime = entry['sleeptime']
        #         logger.info(f"COMMAND: {setup_cmd_name}")
        #         logger.info(f"\tArgs: {setup_cmd_args}")            
        #         logger.info(f"\tsleeptime: {sleeptime}")    

        #         cmd = wubcmd_ctlg.get_command(setup_cmd_name)
        #         response = None 
        #         if setup_cmd_args is not None:
        #             response = wubctl.send_recv(cmd, *setup_cmd_args)
        #         else:
        #             response = wubctl.send_recv(cmd)            

        #         if wubctl.isascii:
        #             logger.info(f"Command response:\n{response['response']}")
        #             break
        #         else:
        #             continue 
        #         break

        #     logger.debug(f"Sleepiong for {entry['sleeptime']}")

        #     time.sleep(float(entry['sleeptime']))
        #     print("-----------------------------------------")           
        # return         
