#!/usr/bin/env python 

import sys, time
import serial
import threading

from pywub import wubctl

def main(port, baudrate):
    
    wub = wubctl.wuBaseCtl(port, baudrate, timeout=0.5)
    uid = wub.UID
    print(f"wuBase UID: {uid}")
    print(f"wuBase status: {wub.cmd_status()}")

    #Grabbed from Chris' code; will want to rework this. 
    setup_lines=[("status",2.,0.1),
                ("pulser_setup 20000 0.3",0.5,0.1),
                ("dac 1 2000",0.5,0.1),
                ("fpgaload",0.5,0.1),
                ("adcconfig",0.5,0.1),
                ("fpgaload",0.5,0.1),
                ("flush_events",0.5,0.1),
                ("fpgatrig 0",0.5,0.1), #Turn off triggering
                ("fpgatrig 1",0.5,0.1), #Turn on discriminator 
                ("pulser_start 1000",0.5,0.1)
                ]


    for (sendline,timeout,sleeptime) in setup_lines:
        cmd_list = sendline.split(' ') #Capture arguments
        cmd = cmd_list[0]
        args = cmd_list[1:]
        print(cmd, *args)
        result = getattr(wub, f"cmd_{cmd}")(*args)
        if result:
            print(result)
        time.sleep(sleeptime)

    
if __name__ == "__main__": 
    
    import argparse
    parser = argparse.ArgumentParser(description="Take wuBase Test Data")
    #parser.add_argument("port", type=int, help="Port number to use for command socket")
    parser.add_argument("--port", type=str, required=True, help="UART port of wuBase")
    parser.add_argument("--baud", type=str, default=115200, help="Baudrate to use during acquisition.")

    args = parser.parse_args()    
    
    main(args.port, args.baud)
    


