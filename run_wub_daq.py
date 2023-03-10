#!/usr/bin/env python 

import sys, time
import serial
import threading
import logging 

logger = logging.getLogger()

import pywub

import struct
import inspect 
#from pywub import control 
#from pywub import catalog

from pywub.control import wubCTL
from pywub.catalog import ctlg as wubcmd_ctlg
from pywub.catalog import wubCMD_RC as wubCMD_RC


def main(args):

    port = args.port
    baud = args.baud
    outputfile = args.ofile
    mode = args.commsmode
    datafile = args.ofile
    runtime = args.runtime

    wubctl = wubCTL(port, baudrate=baud, mode=mode, timeout=10)

    print(wubctl.cmd_ok())
    status = wubctl.cmd_status()

    logger.info(status)        
    #return
    setup_command_list = pywub.control.parse_setup_config(args.config)

    retries = 0
    for setup_cmd in setup_command_list[0::]:
        while True:
            setup_cmd_name = str.upper(setup_cmd['name'])
            setup_cmd_args = setup_cmd['args']
            sleeptime = setup_cmd['sleeptime']
            logger.info(f"COMMAND: {setup_cmd_name}")
            logger.info(f"Args: {setup_cmd_args}")

        #    getattr(self, f"cmd_{name}")(*args)

            #cmd = getattr(wubcmd_ctlg, f"{setup_cmd_name.lower()}")
            cmd = wubcmd_ctlg.get_command(setup_cmd_name)
            response = None
            # logger.debug(cmd)
            # logger.debug(setup_cmd_args)

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
    
    wubctl.cmd_pulser_start(100)
    #logger.info(wubctl.batchmode_recv(2, 1))

    # Now start the batchmode recieve thread. 
    rx_thread=threading.Thread(target=wubctl.batchmode_recv, args=(-1, 1), kwargs=dict(datafile=datafile))

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
        logger.warning("KeyboardInterrupt detected. Exiting batch readout.")
        wubctl.request_abort = True
        
            

    # make sure the reception thread is really gone
    rx_thread.join(5)
    if rx_thread.is_alive():
        logger.error(f"{time.ctime(time.time())}  Error: rx thread failed to complete")


    wubctl.set_autobaud()

    #logger.info(wubctl.cmd_status()['response'])    
    logger.info(wubctl.cmd_ok())
    if datafile is not None: 
        datafile.close()
    logger.info("Exiting....")    

    sys.exit(0)


    
if __name__ == "__main__": 
    
    import argparse
    parser = argparse.ArgumentParser(description="Take wuBase Test Data")
    parser.add_argument("--port", type=str, required=True, 
                        help="UART port of wuBase")
    
    parser.add_argument("--baud", type=int, default=115200, 
                        help="Baudrate to use during acquisition.")
    parser.add_argument("--runtime", type=int, default=10, 
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
    

    


