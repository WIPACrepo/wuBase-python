#!/usr/bin/env python 

import sys, time
import serial
import threading
import logging 

logger = logging.getLogger()

import pywub
from pywub import wubctl

def main(args):

    port = args.port
    baud = args.baud
    npulses = args.npulses
    outputfile = args.ofile
    runtime = args.runtime
    sleeptime = args.sleeptime 

    
    wub = wubctl.wuBaseCtl(port, baud, timeout=0.5)
    uid = wub.UID
    wub.set_baud(baud)
    logger.info(f"wuBase UID: {uid}")
    logger.info(f"wuBase status: {wub.cmd_status()}")
    
    setup_commands = [
        ["status", sleeptime],
        ["pulser_setup 20000 0.3", sleeptime],
        ["dac 1 2000", sleeptime],
        ["fpgaload", sleeptime],         
        ["adcconfig", sleeptime],
        ["fpgaload", sleeptime],
        ["flush_events", sleeptime],
        ["fpgatrig 0", sleeptime],
        ["fpgatrig 1", sleeptime],
        [f"pulser_start {npulses}", sleeptime]
    ]

    results = wub.batch_setup_commands(setup_commands)
    
    datafile = None
    if outputfile is not None:
        datafile = open(outputfile, "w")
    

    #Generate main data acquisition thread, run until the buffer is empty.  
    logger.info(f"Beginning run; maximum run duration {runtime} s.")
    rx_thread=threading.Thread(target=wub.cmd_send_batch,args=(-1, 1),kwargs=dict(datafile=datafile))
    rx_thread.start()
    
    tlast = time.time()
    tstart = time.time()
    try:
        while True:
            
            tnow = time.time()
            if  tnow - tlast > 1: 
                tlast = tnow
                if not wub.send_recv_running:
                    logger.info("End of batch data readout. Exiting.")
                    break
                logger.info(f"Progress: {wub.nbytes_recv:8.2e} bytes")
            if runtime > 0 and tnow - tstart > runtime:
                logger.info("DAQ runtime exceeded... Exiting.")
                wub.request_stop = True

                break
    except KeyboardInterrupt: 
        logger.warning("KeyboardInterrupt detected. Exiting batch readout.")
        wub.request_abort = True
        
        

    # make sure the reception thread is really gone
    rx_thread.join(5)
    if rx_thread.is_alive():
        logger.error(f"{time.ctime(time.time())}  Error: rx thread failed to complete")
    wub.enable_autobaud()       
    status = wub.cmd_status()

    logger.info(status)    

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
    parser.add_argument("--ofile", type=str, default=None, 
                        help="Output file for test data.")
    parser.add_argument("--npulses", type=int, default=1000, 
                        help="Number of test pulses to send.")
    parser.add_argument("--loglevel", type=str, default="INFO",
                        help="Logger level")
    parser.add_argument("--runtime", type=int, default=60, 
                        help="Run will end if DAQ runs longer than this. timeout < 0 means no timeout. ")
    parser.add_argument("--config", type=str, default='config/cfg_test_data.cfg', 
                        help="Delay between command when executing batch commands.")    
    
    
    
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
    

    


