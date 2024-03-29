#!/usr/bin/env python 

import time
import sys
import threading
from collections import deque 


from pywub.control import wubCTL as wubCTL
from pywub.catalog import parse_setup_config
from pywub.catalog import ctlg as wubCMD_catalog
from pywub.catalog import wubCMD_RC

import logging 


logger = logging.getLogger()

from pywub.control import CustomFormatter

def main(cli_args):   

    wubctl = wubCTL(cli_args.port, baud=cli_args.baud, 
                    mode=cli_args.commsmode, timeout=cli_args.timeout, 
                    verbosity=cli_args.verbose,
                    store_mode=cli_args.store_mode, 
                    parity=cli_args.parity)

    config = parse_setup_config(cli_args.config)
    setup_commands = config['setup']

    #The following two commands override send_recv because of the way commsmode is set up.
    # The device boots in autobaud mode and this doesn't work at higher baudrates, so:
    logger.info("Setting wuBase baud rate to fixed...")
    resp = wubctl.send_recv_ascii(wubCMD_catalog.baud, cli_args.baud)
    logger.debug(f"Response: {resp['response']}")
    #Check if the device was already in autobaud mode: 
    if resp['response'][0] == '?':
        logger.warning("Invalid command response; possibly the device was already in fixed baud mode. ")
    
    # The device boots in asciimode, so ensure that it is operating in the right mode: 
    if not wubctl.isascii:
        logger.info("Sending BINARYMODE command to wuBase.")
        resp = wubctl.send_recv_ascii(wubCMD_catalog.binarymode)
        logger.debug(f"Response: {resp['response']}")


    retries = 0
    error_detect = False
    logger.info("Executing setup commands...")
    for setup_cmd in setup_commands:
        while True:
            setup_cmd_name = str.upper(setup_cmd['name'])
            setup_cmd_args = setup_cmd['args']
            sleeptime = setup_cmd['sleeptime']
            logger.info(f"COMMAND: {setup_cmd_name}\tArgs: {setup_cmd_args}")           

            cmd = wubCMD_catalog.get_command(setup_cmd_name)
            response = None

            

            if setup_cmd_args is not None:
                response = wubctl.send_recv(cmd, *setup_cmd_args)
            else:
                response = wubctl.send_recv(cmd)
           
            if wubctl.isascii:
                if response['response'][0] != '?':
                    logger.info(f"Command response: {response['response']}")
                    retries = 0
                    break
                else:
                    logger.warning(f"Issue executing command. Retrying {retries+1}/10.")
                    if retries > 10:
                        logger.error(f"\tERROR: Number of retries exceeds threshold. Exiting...")
                        error_detect = True
                        break
                    retries+=1
            else:
                response = response['response'] #Strip out this layer.
                logger.info(f"CMD_RC: {wubCMD_RC(response['CMD_RC']).name}")

                if response['CMD_RC'] == wubCMD_RC.CMD_RC_OK:
                    logger.info(f"CMD_retargs: {response['retargs']}")       
                    retries = 0 
                    break
                else:
                    logger.warning(f"Issue executing command. Retrying {retries+1}/10.")
                    if retries > 10:
                        logger.error(f"\tERROR: Number of retries exceeds threshold. Exiting...")
                        error_detect = True
                        break
                    retries+=1
                
            time.sleep(float(sleeptime))

        
        print("-----------------------------------------")    

    output_handler = None
    if cli_args.ofile is not None:
        logger.info(f"Opening {cli_args.ofile} for data logging.")
        if wubctl.isascii:
            output_handler = open(cli_args.ofile, "w")
        else: 
            output_handler = open(cli_args.ofile, "wb")
    # Now start the batchmode recieve thread. 
    rx_thread=threading.Thread(target=wubctl.batchmode_recv, args=(cli_args.ntosend, 1), kwargs=dict(datafile=output_handler))

    rx_thread.start()

    bytes_tracker = deque(['0','0','0'], maxlen=3)
    maxruntime = cli_args.runtime    
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

                if wubctl.isascii:
                    info_str = f"Progress: {wubctl.nbytes_recv:8.4e} bytes"
                else:
                    #{wubctl.nframes_binary} frames 
                    info_str = f"Progress: {wubctl.nbytes_recv:8.4e} bytes -- bytes in_waiting: {wubctl.bytes_in_waiting}"

                    
                bytes_tracker.append(wubctl.nbytes_recv)
                logger.info(info_str)
                
                if(len(set(bytes_tracker)) == 1):
                    logger.warning("No new data in the last second.")

            if maxruntime > 0 and tnow - tstart > maxruntime:
                logger.info("DAQ runtime exceeded... Exiting.")
                wubctl.request_stop = True          
                break

    except KeyboardInterrupt: 
        wubctl.request_abort = True
        logger.info("KeyboardInterrupt detected. Exiting batch readout.")
        
    time.sleep(1)

    # make sure the reception thread is really gone
    rx_thread.join(5)
    if rx_thread.is_alive():
        logger.error(f"Rx thread failed to complete!")

    if not wubctl.isascii:
        logger.info(wubctl.cmd_ok())

        logger.info("Getting binary stats from wuBase.")
        resp = wubctl.cmd_binary_stats();
        
        rc = wubCMD_RC(resp['response']['CMD_RC']).name
        nhits_tx =  int(resp['response']['retargs'][0])
        nbytes_tx =  int(resp['response']['retargs'][1])
        logger.info(f"Hits transmitted by wuBase:  {nhits_tx} (0x{nhits_tx:X})")
        logger.info(f"Bytes transmitted by wuBase: {nbytes_tx} (0x{nbytes_tx:X})")

        logger.info("Sending ASCIIMODE command to wuBase.")        
        #logger.debug(wubctl.cmd_ok())
        resp = wubctl.cmd_asciimode()
        rc = wubCMD_RC(resp['response']['CMD_RC']).name
        logger.info(rc)
        

    logger.info("Re-enabling autobaud.")    
    #logger.info(wubctl.send_recv_ascii(wubCMD_catalog.baud, -1)['response'])
    resp = wubctl.set_autobaud()
    logger.info(resp['response'])

    if output_handler is not None: 
        output_handler.flush()
        output_handler.close()
    logger.info("Exiting....")    

    sys.exit(0)    





 
if __name__ == "__main__": 
    
    import argparse
    parser = argparse.ArgumentParser(description="Take wuBase Test Data",
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("--port", type=str, required=True, 
                        help="UART port of wuBase")
    
    parser.add_argument("--baud", type=int, default=115200, 
                        help="Baudrate to use during acquisition.")
    
    parser.add_argument("--timeout", type=int, default=1, 
                        help="Socket-level timeout time to wait for a byte.")      
    
    parser.add_argument("--runtime", type=int, default=5, 
                        help="Maximum runtime before aborting DAQ.")    
    
    parser.add_argument("--ofile", type=str, default=None, 
                        help="Output file for test data.")

    parser.add_argument("--commsmode", type=str, default='ascii',
                        help="Comms mode (ascii or binary)")
    
    parser.add_argument("--verbose", type=int, default=0,
                        help="Binary mode comms verbosity.")
    
#     parser.add_argument("--npulses", type=int, default=1000, 
#                         help="Number of test pulses to send.")
    
    parser.add_argument("--loglevel", type=str, default="INFO",
                        help="Logger level")
        
    parser.add_argument("--config", type=str, default='config/cfg_test_data.cfg', 
                        help="Batch commands to execute ")

    parser.add_argument("--ntosend", type=int, default=-1,
                        help="Number of hits to send in batchmode. Negative means send all available.")
    
    parser.add_argument("--store_mode", type=str, default='bulk', 
                        help="Choose which method of recieving and processing hits.")
    
    parser.add_argument("--debug", action='store_true',
                        help="Override loglevel to debug")
    
    parser.add_argument("--parity", action='store_true',
                    help="Set serial interface to use positive parity bit")    

    
    LOGGING_STREAM_FORMAT = "%(asctime)s - %(levelname)s - %(name)s - %(funcName)s - %(message)s"
    
    cli_args = parser.parse_args()  

    if cli_args.debug: 
        cli_args.loglevel = "debug"

    numeric_level = getattr(logging, cli_args.loglevel.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError('Invalid log level: %s' % cli_args.loglevel)
     
    loglevel = cli_args.loglevel.upper()
    logger.setLevel(cli_args.loglevel.upper())

    ch = logging.StreamHandler()
    format_stream = "%(asctime)s - %(levelname)s - %(name)s - %(funcName)s - %(message)s" #"%(asctime)s - %(name)s %(funcName)s():%(lineno)d\t%(message)s"
    #ch.setFormatter(CustomFormatter(format_stream))
    ch.setFormatter(logging.Formatter(format_stream))
    

    FIELD_STYLES = dict(
        asctime=dict(color='green'),
        hostname=dict(color='magenta'),
        #levelname=dict(color='green'),
        filename=dict(color='magenta'),
        name=dict(color='blue'),
        funcName=dict(color='blue'),
        threadName=dict(color='green')
    )

    LEVEL_STYLES = dict(
        debug=dict(color='green'),
        info=dict(color='blue'),
        verbose=dict(color='cyan'),
        warning=dict(color='yellow'),
        error=dict(color='red'),
        critical=dict(color='red')
    )    

    try: 
        import coloredlogs

        coloredlogs.install(
        level=cli_args.loglevel.upper(),
        fmt=LOGGING_STREAM_FORMAT,
        datefmt="%H:%M:%S",
        level_styles=LEVEL_STYLES,
        field_styles=FIELD_STYLES,
        )

    except ImportError: 
        print("coloredlogs not found; using default logging in stead.")
      
        ch = logging.StreamHandler()
        ch.setLevel(loglevel.upper())
        formatter = logging.Formatter(LOGGING_STREAM_FORMAT, datefmt="%H:%M:%S")
        ch.setFormatter(formatter)
        logger.addHandler(ch)   


    if cli_args.ofile is not None:        
        fh = logging.FileHandler(cli_args.ofile + '.cmd_log')
        fh.setLevel(logging.INFO)
        fh.setFormatter(logging.Formatter(format_stream))
        logger.addHandler(fh)
    
    main(cli_args)
    


