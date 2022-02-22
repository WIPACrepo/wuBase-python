#!/usr/bin/env python 

import sys, time
import serial
import threading
import logging 

logger = logging.getLogger()

import pywub

import struct
#from pywub import control 
#from pywub import catalog

from pywub.control import wubCTL
from pywub.catalog import ctlg as wubcmd
from pywub.catalog import wubCMD_RC as wubCMD_RC

def main(args):

    port = args.port
    baud = args.baud
    outputfile = args.ofile

    wubctl = wubCTL(port, baudrate=baud, mode='binary', timeout=0)
    
    setup_command_list = pywub.control.parse_setup_config(args.config)
    
    retries = 0
    for setup_cmd in setup_command_list[0::]:
        while True:
            setup_cmd_name = str.upper(setup_cmd['name'])
            setup_cmd_args = setup_cmd['args']
            sleeptime = setup_cmd['sleeptime']
            print(f"COMMAND: {setup_cmd_name}")
            print(f"\tArgs: {setup_cmd_args}")

        #    getattr(self, f"cmd_{name}")(*args)

            cmd = getattr(wubcmd, f"{setup_cmd_name.lower()}")
            response = None
            if setup_cmd_args is not None:
                #cmd.build(wubctl.mode, *setup_cmd_args)
                response = wubctl.send_recv_binary(cmd, *setup_cmd_args)
            else:
                response = wubctl.send_recv_binary(cmd)


            print(f"\tCMD_RC:      {wubCMD_RC(response['CMD_RC']).name}")

            if response['CMD_RC'] == wubCMD_RC.CMD_RC_OK:
                #print(f"CMD_RC:      {wubCMD_RC(response['CMD_RC']).name}\r\n"
                print(f"\tCMD_retargs: {response['retargs']}")        
                break
            else:
                print(f"\tERROR executing command. Retrying {retries+1}/10.")
                if retries > 10:
                    print(f"\tERROR: Number of retries exceeds threshold. Exiting...")
                retries+=1


            time.sleep(float(sleeptime))
            print("-----------------------------------------")    
    
    sys.exit(0)
    
if __name__ == "__main__": 
    
    import argparse
    parser = argparse.ArgumentParser(description="Take wuBase Test Data")
    parser.add_argument("--port", type=str, required=True, 
                        help="UART port of wuBase")
    
    parser.add_argument("--baud", type=int, default=115200, 
                        help="Baudrate to use during acquisition.")
    
    parser.add_argument("--ofile", type=str, default=None, 
                        help="Output file for test data.")
    
#     parser.add_argument("--npulses", type=int, default=1000, 
#                         help="Number of test pulses to send.")
    
    parser.add_argument("--loglevel", type=str, default="INFO",
                        help="Logger level")
    
#     parser.add_argument("--runtime", type=int, default=60, 
#                         help="Run will end if DAQ runs longer than this. "
#                              "timeout < 0 means no timeout. ")
    
    parser.add_argument("--config", type=str, default='config/cfg_test_data.cfg', 
                        help="Batch commands to execute ")    
    
    
    args = parser.parse_args()  
    print(args)
    numeric_level = getattr(logging, args.loglevel.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError('Invalid log level: %s' % args.loglevel)
     
    logger.setLevel(args.loglevel.upper())
    # create console handler and set level to debug
    ch = logging.StreamHandler()
    #ch.setLevel(args.loglevel.upper())
    # create formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    # add formatter to ch
    ch.setFormatter(formatter)     
    
    # add ch to logger
    logger.addHandler(ch)
    
    #exit(0)
    main(args)
    

    


