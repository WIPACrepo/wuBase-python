#!/usr/bin/env python 

import sys, time
import serial
import threading
import logging 

logger = logging.getLogger()

from pywub import wubctl

def main(port, baudrate, npulses, outputfile):
    
    wub = wubctl.wuBaseCtl(port, baudrate, timeout=0.5)
    uid = wub.UID
    logger.info(f"wuBase UID: {uid}")
    logger.info(f"wuBase status: {wub.cmd_status()}")

    #Grabbed from Chris' code; will want to rework this. 
    sleeptime = 0.1
    runtime = 30

    setup_commands = [
        ["status", 0.1],
        ["pulser_setup 20000 0.3", 0.1],
        ["dac 1 2000", 0.1],
        ["fpgaload", 0.1],         
        ["adcconfig", 0.1],
        ["fpgaload", 0.1],
        ["flush_events", 0.1],
        ["fpgatrig 0", 0.1],
        ["fpgatrig 1", 0.1],
        [f"pulser_start {npulses}", 0.1]
    ]

    results = wub.batch_setup_commands(setup_commands)
    
    datafile = None
    if outputfile:
        datafile = open(outputfile, "w")
    

    #Generate main data acquisition thread, run until the buffer is empty.  
    print(f"{time.ctime(time.time())}  Start run, {runtime} seconds", flush=True)
    rx_thread=threading.Thread(target=wub.cmd_send_batch,args=(-1, 1),kwargs=dict(datafile=datafile))
    rx_thread.start()
    
    tlast = time.time()
    while True:
        tnow = time.time()
        if  tnow - tlast > 1: 
            tlast = tnow
            if not wub.send_recv_running:
                print("send_recv not running.")
                break
            print(f"{time.ctime(time.time())}  Progress: {wub.nbytes_recv:8.2e} bytes", flush=True)

    # make sure the reception thread is really gone
    rx_thread.join(5)
    if rx_thread.is_alive():
        print(f"{time.ctime(time.time())}  Error: rx thread failed to complete", flush=True)

    print(wub.cmd_status())    
    if datafile is not None: 
        datafile.close()
    print("Exiting....")
    sys.exit(0)
    
if __name__ == "__main__": 
    
    import argparse
    parser = argparse.ArgumentParser(description="Take wuBase Test Data")
    parser.add_argument("--port", type=str, required=True, help="UART port of wuBase")
    parser.add_argument("--baud", type=str, default=115200, help="Baudrate to use during acquisition.")
    parser.add_argument("--ofile", type=str, default=None, help="Output file for test data.")
    parser.add_argument("--npulses", type=int, default=1000, help="Number of test pulses to send.")
    parser.add_argument("--loglevel", type=str, default="DEBUG", help="Logger level")
    args = parser.parse_args()    
    
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
    main(args.port, args.baud, args.npulses, args.ofile)
    


