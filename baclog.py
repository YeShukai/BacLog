#!/usr/bin/python
## BacLog Copyright 2010 by Timothy Middelkoop licensed under the Apache License 2.0

import socket
import select
import binascii


def main():
    print "BacLog.main>"
    ## Invoke 1{8}, Read property, BO instance 20 (0x14), present-value (85).
    message = "810a001101040003010c0c010000141955"

    s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
    s.bind(('192.168.23.53',47808))
    s.setblocking(0)

    send=3
    recv=send
    
    while(send+recv>0):
        if send:
            (sr,sw,se) = select.select([s],[s],[s])
        else:
            (sr,sw,se) = select.select([s],[],[s])
        print sr,sw,se
        ## Send
        if sw and send:
            print "BacLog.main> send:", send
            s.sendto(binascii.unhexlify(message),('192.168.83.100',47808))
            send-=1
        ## Recv
        if sr and recv:
            (response,source)=s.recvfrom(1500)
            ## Expect 810a0014010030010c0c0100001419553e91003f
            print "BacLog.main> recv:", recv, source, binascii.b2a_hex(response)
            recv-=1
        if se:
            print "BacLog.main> error", se
            
    s.close()

if __name__=='__main__':
    main()

