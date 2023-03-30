#!/usr/bin/env python 

import sys, time
import serial
import threading

from collections.abc import Iterable

import pywub

import struct
import inspect 
#from pywub import control 
#from pywub import catalog

from pywub.control import wubCTL
from pywub.catalog import ctlg as wubcmd_ctlg
from pywub.catalog import wubCMD_RC as wubCMD_RC

import logging 
logger = logging.getLogger()
from pywub.control import CustomFormatter



def main(args):

    port = args.port
    baud = args.baud
    outputfile = args.ofile
    mode = args.commsmode
    datafile = args.ofile
    runtime = args.runtime
  
    config = pywub.control.parse_config(args.config)
    logger.info(config)
    setup_commands = config['setup']

    wubctl = wubCTL(port, baudrate=baud, mode=mode, timeout=args.timeout)

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

    retries = 0
    for setup_cmd in setup_commands:
        while True:
            setup_cmd_name = str.upper(setup_cmd['name'])
            setup_cmd_args = setup_cmd['args']
            sleeptime = setup_cmd['sleeptime']
            logger.info(f"COMMAND: {setup_cmd_name}")
            logger.info(f"Args: {setup_cmd_args}")

            cmd = wubcmd_ctlg.get_command(setup_cmd_name)
            response = None

            if setup_cmd_args is not None:
                response = wubctl.send_recv(cmd, *setup_cmd_args)
            else:
                response = wubctl.send_recv(cmd)

            if wubctl.isascii:
                logger.info(f"Command response:\n{response['response']}")
                break
            else:

                logger.info(f"CMD_RC:      {wubCMD_RC(response['CMD_RC']).name}")

                if response['CMD_RC'] == wubCMD_RC.CMD_RC_OK:
                    #print(f"CMD_RC:      {wubCMD_RC(response['CMD_RC']).name}\r\n"
                    logger.info(f"\tCMD_retargs: {response['retargs']}")        
                    break
                else:
                    logger.warning(f"Issue executing command. Retrying {retries+1}/10.")
                    if retries > 10:
                        logger.error(f"\tERROR: Number of retries exceeds threshold. Exiting...")
                        sys.exit(1)
                    retries+=1

        time.sleep(float(sleeptime))
        print("-----------------------------------------")    
    
    #wubctl.cmd_pulser_start(100)
    #logger.info(wubctl.batchmode_recv(2, 1))

    output_handler = None
    if datafile is not None:
        logger.info(f"Opening {datafile} for data logging.")
        output_handler = open(datafile, "w")
    # Now start the batchmode recieve thread. 
    rx_thread=threading.Thread(target=wubctl.batchmode_recv, args=(args.ntosend, 1), kwargs=dict(datafile=output_handler))

    rx_thread.start()
        
    tlast = time.time()
    tstart = time.time()
    try:
        while True:
            
            tnow = time.time()
            if  tnow - tlast > 1: 
                tlast = tnow
                if not wubctl._batch_mode_running:
                    logger.info("End of batch data readout. Exiting.")
                    break
                logger.info(f"Progress: {wubctl.nbytes_recv:8.2e} bytes")
            if runtime > 0 and tnow - tstart > runtime:
                logger.info("DAQ runtime exceeded... Exiting.")
                wubctl.request_stop = True          
                break
    except KeyboardInterrupt: 
        logger.info("KeyboardInterrupt detected. Exiting batch readout.")
        wubctl.request_abort = True
        
    time.sleep(1)

    # make sure the reception thread is really gone
    rx_thread.join(5)
    if rx_thread.is_alive():
        logger.error(f"Rx thread failed to complete")


    wubctl.set_autobaud()
    # print(wubctl.cmd_ok())
    # print(wubctl.cmd_ok())
    # print(wubctl.cmd_ok())
    # print(wubctl.cmd_ok())
    #logger.info(wubctl.cmd_status()['response'])    
    logger.info(wubctl.cmd_ok()['response'])
    if output_handler is not None: 
        output_handler.close()
    logger.info("Exiting....")    


    sys.exit(0)


    
if __name__ == "__main__": 
    
    import argparse
    parser = argparse.ArgumentParser(description="Take wuBase Test Data")
    parser.add_argument("--port", type=str, required=True, 
                        help="UART port of wuBase")
    
    parser.add_argument("--baud", type=int, default=115200, 
                        help="Baudrate to use during acquisition.")
    parser.add_argument("--timeout", type=int, default=10, 
                        help="Socket-level timeout time to wait for a byte.")      
    parser.add_argument("--runtime", type=int, default=5, 
                        help="Maximum runtime before aborting DAQ.")    
    
    parser.add_argument("--ofile", type=str, default=None, 
                        help="Output file for test data.")

    parser.add_argument("--commsmode", type=str, default='ascii',
                        help="Comms mode (ascii or binary)")
    
#     parser.add_argument("--npulses", type=int, default=1000, 
#                         help="Number of test pulses to send.")
    
    parser.add_argument("--loglevel", type=str, default="INFO",
                        help="Logger level")
    
#     parser.add_argument("--runtime", type=int, default=60, 
#                         help="Run will end if DAQ runs longer than this. "
#                              "timeout < 0 means no timeout. ")
    
    parser.add_argument("--config", type=str, default='config/cfg_test_data.cfg', 
                        help="Batch commands to execute ")

    parser.add_argument("--ntosend", type=int, default=-1,
                        help="Number of hits to send in batchmode. Negative means send all available.")

    
    
    args = parser.parse_args()  
    print(args)
    numeric_level = getattr(logging, args.loglevel.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError('Invalid log level: %s' % args.loglevel)
     
    logger.setLevel(args.loglevel.upper())
    ch = logging.StreamHandler()
    ch.setFormatter(CustomFormatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))     
    logger.addHandler(ch)
        
    # create console handler and set level to debug

    #exit(0)
    main(args)
    

    


