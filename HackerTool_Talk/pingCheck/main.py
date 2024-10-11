from machine import Pin, I2C, ADC
from ssd1306 import SSD1306_I2C
import socket
import framebuf
import utime
import time
import network
import random

WIDTH = 128
HEIGHT = 64

default_host = "8.8.8.8"


buffer = bytearray(b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x07\xe0\x00\x00\x01\xf8\x00\x0f\xfc\x00\x00\x0f\xfc\x00\x0f\xff\x00\x00?\xf8\x00\x0f\x7f\xc0\x00\xff<\x00\x0f\x07\xe1\x81\xf8<\x00\x0f\x01\xff\xff\xc0<\x00\x0f\x00\xfe\xff\xc0<\x00\x06\x03\xff\xff\xf08\x00\x07\x07\xf0\x03\xf88\x00\x07\x1f\x80\x00~8\x00\x07>\x00\x00\x1d8\x00\x07\xfc\x00\x00\x0fx\x00\x03\xf8\x00\x00\x07\xf0\x00\x03\xf0\x00\x00\x03\xf0\x00\x03\xe0\x00\x00\x01\xf0\x00\x03\xc1\x80\x00p\xf0\x00\x03\xcf\xe0\x01\xfc\xf0\x00\x07\x9f\xf8\x07\xfex\x00\x07\xbdx\x07\xffp\x00\x07x<\x0f\x07\xb8\x00\x07\xf3\x9c\x0es\xf8\x00\x0f\xe7\xdc\x0e\xfb\xfc\x00\x0f\xe7\x9c\x0e\xf9\xfc\x00\x0f\xc7\xdc\x0e\xf8x\x00\x0f\x81\x1c\x0e x\x00\x0f\x80\x1c\x0e\x00|\x00\x0f\x00\x1c\x0e\x00<\x00\x07\x00<\x0f\x008\x00\x07\x808\x07\x00x\x00\x07\x808\x07\x00x\x00\x03\xc09\xe7\x00\xf0\x00\x01\xf09\xe7\x03\xe0\x00\x00\xf81\xe7\x87\xc0\x00\x00~x\x07\xbf\x80\x00\x00?\xf8\x07\xff\x00\x00\x00\x07\xff\xff\xfc\x00\x00\x00\x03\xff\xff\xf0\x00\x00\x00\x00?\xff\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00')

fb = framebuf.FrameBuffer(buffer, 50, 50, framebuf.MONO_HLSB)

i2c = I2C(1, scl=Pin(12), sda=Pin(14),freq=200000)
oled = SSD1306_I2C(WIDTH, HEIGHT, i2c)

led = Pin(2, Pin.OUT)

# clear screen

def checksum(data):
    if len(data) & 0x1: # Odd number of bytes
        data += b'\0'
    cs = 0
    for pos in range(0, len(data), 2):
        b1 = data[pos]
        b2 = data[pos + 1]
        cs += (b1 << 8) + b2
    while cs >= 0x10000:
        cs = (cs & 0xffff) + (cs >> 16)
    cs = ~cs & 0xffff
    return cs

def ping(host, count=1, timeout=2500, interval=10, quiet=False, size=64):
    import utime
    import uselect
    import uctypes
    import usocket
    import ustruct
    import urandom

    # prepare packet
    assert size >= 16, "pkt size too small"
    pkt = b'Q'*size
    pkt_desc = {
        "type": uctypes.UINT8 | 0,
        "code": uctypes.UINT8 | 1,
        "checksum": uctypes.UINT16 | 2,
        "id": uctypes.UINT16 | 4,
        "seq": uctypes.INT16 | 6,
        "timestamp": uctypes.UINT64 | 8,
    } # packet header descriptor
    h = uctypes.struct(uctypes.addressof(pkt), pkt_desc, uctypes.BIG_ENDIAN)
    h.type = 8 # ICMP_ECHO_REQUEST
    h.code = 0
    h.checksum = 0
    h.id = urandom.getrandbits(16)
    h.seq = 1

    # init socket
    sock = usocket.socket(usocket.AF_INET, usocket.SOCK_RAW, 1)
    sock.setblocking(0)
    sock.settimeout(timeout/1000)
    addr = usocket.getaddrinfo(host, 1)[0][-1][0] # ip address
    sock.connect((addr, 1))
    not quiet and print("PING %s (%s): %u data bytes" % (host, addr, len(pkt)))

    seqs = list(range(1, count+1)) # [1,2,...,count]
    c = 1
    t = 0
    n_trans = 0
    n_recv = 0
    finish = False
    while t < timeout:
        if t==interval and c<=count:
            # send packet
            h.checksum = 0
            h.seq = c
            h.timestamp = utime.ticks_us()
            h.checksum = checksum(pkt)
            if sock.send(pkt) == size:
                n_trans += 1
                t = 0 # reset timeout
            else:
                seqs.remove(c)
            c += 1

        # recv packet
        while 1:
            socks, _, _ = uselect.select([sock], [], [], 0)
            if socks:
                resp = socks[0].recv(4096)
                resp_mv = memoryview(resp)
                h2 = uctypes.struct(uctypes.addressof(resp_mv[20:]), pkt_desc, uctypes.BIG_ENDIAN)
                # TODO: validate checksum (optional)
                seq = h2.seq
                if h2.type==0 and h2.id==h.id and (seq in seqs): # 0: ICMP_ECHO_REPLY
                    t_elasped = (utime.ticks_us()-h2.timestamp) / 1000
                    ttl = ustruct.unpack('!B', resp_mv[8:9])[0] # time-to-live
                    n_recv += 1
                    not quiet and print("%u bytes from %s: icmp_seq=%u, ttl=%u, time=%f ms" % (len(resp), addr, seq, ttl, t_elasped))
                    seqs.remove(seq)
                    if len(seqs) == 0:
                        finish = True
                        break
            else:
                break

        if finish:
            break

        utime.sleep_ms(1)
        t += 1

    # close
    sock.close()
    ret = (n_trans, n_recv)
    not quiet and print("%u packets transmitted, %u packets received" % (n_trans, n_recv))
    return (n_trans, n_recv)


def screenStuff(msg, x, y, **kwargs):
    oled.fill(0)
    oled.blit(fb, 32, 20)
    oled.invert(0)
    oled.text("Trash Panda", 15, 0)
    oled.text(msg, x, y)
    m2 = kwargs.get("m2","")
    x2 = kwargs.get("x2",0)
    y2 = kwargs.get("y2",0)
    oled.text(m2, x2, y2)
    oled.show()


def connect_wifi(ssid, password):
    print("[+] In wifi function")
    wlan = network.WLAN(network.STA_IF)
    wlan.active(False)
    wlan.active(True)
    print("[+] Starting connection process")
    wlan.connect(ssid, password)
    print("[+] Attempt 1")
    
    while not wlan.isconnected():
        print("Connecting to WiFi...")
        screenStuff(f"[Connecting]",8,8,m2=f"Please wait",x2=8,y2=16)
        utime.sleep(1)
    if wlan.isconnected():
        print("[+] Connected!")
        
    screenStuff(f"[Connected]",8,8,m2=f"YAY",x2=8,y2=16)
    print("Connected to WiFi:", wlan.ifconfig())
    

def ping_host(host):
    while True:
        try:
            # Create a socket connection to the host
            i = 1
            a, b = ping(host, count=i)
            print(f"[+] Transmitted: {a}")
            print(f"[+] Recieved: {b}")
            current_time = utime.localtime()
            formatted_time = "{:02}:{:02}:{:02}".format(current_time[3], current_time[4], current_time[5])
            if b != i:
                led.value(1)
                screenStuff(f"[{formatted_time}]",15,8,m2=f"{a}/{b}",x2=45,y2=16)
                print(f"[{formatted_time}] {a}/{b} packets transmitted/received.")
                sleepTime = 1
            else:
                led.value(0)
                screenStuff(f"[{formatted_time}]",15,8,m2=f"{a}/{b}",x2=45,y2=16)
                print(f"[{formatted_time}] {a}/{b} packets transmitted/received.")
                sleepTime = 5
                
            
        except Exception as e:
            # Get the current time and format it
            current_time = utime.localtime()
            formatted_time = "{:02}:{:02}:{:02}".format(current_time[3], current_time[4], current_time[5])
            screenStuff(f"[!{formatted_time}]",8,8,m2=f"{e}",x2=0,y2=16)
            print(f"[{formatted_time}] Error: {host} is not reachable. {e}")

        # Wait for 1 second before the next ping
        utime.sleep(sleepTime)


def main():
    screenStuff("is up <3", 25, 8)
    print("[+] Operational")
    ssid = ""
    password = ""

    print("[+] Starting wifi")
    # Connect to WiFi
    connect_wifi(ssid, password)

    ping_host(default_host)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        ap = network.WLAN(network.AP_IF)
        ap.active(False)
        screenStuff("Fuck... I died",8,8)
        print(f"[!] Error: {e}")

