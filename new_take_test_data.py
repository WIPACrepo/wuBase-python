#!/usr/bin/env python 

import sys, time
import serial
import threading

from pywub import wubctl

def main(port, baudrate, npulses, outputfile):
    
    wub = wubctl.wuBaseCtl(port, baudrate, timeout=0.5)
    uid = wub.UID
    print(f"wuBase UID: {uid}")
    print(f"wuBase status: {wub.cmd_status()}")

    #Grabbed from Chris' code; will want to rework this. 
    sleeptime = 0.1
    runtime = 30

    setup_commands = [
        "status", 
        "pulser_setup 20000 0.3", 
        "dac 1 2000", 
        "fpgaload",
        "adcconfig",
        "fpgaload", 
        "flush_events", 
        "fpgatrig 0",    
        "fpgatrig 1",
        "pulser_start 10",
    ]

    #Execute slow control commands. 
    for cmd in setup_commands:
        cmd_list = cmd.split(' ')
        name = cmd_list[0]
        args = cmd_list[1:]
        print(f"Command: {name}", *args)
        result = getattr(wub, f"cmd_{name}")(*args)
        if result:
            print(result)
            
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
    args = parser.parse_args()    
    
    #print(args)
    #print(args.ofile)
    main(args.port, args.baud, args.npulses, args.ofile)
    


