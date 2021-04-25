import os, requests, sys, json, threading, time
from datetime import datetime, timezone
from flask import Flask, request, send_file, make_response
from werkzeug.serving import WSGIRequestHandler
app = Flask(__name__)
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 1

#This could be useful in the future ... just saying. ;)
SupportFirmware = False
bootloader='1.177' #Bootloader value sent by hub during firmware update

httpsport=443
httpport=80
hostname='0.0.0.0'
directory='/web/creds/'
#directory=''

#Load SUREHUBIO from environment variable
if os.environ.get('SUREHUBIO') is not None:
    print("SUREHUBIO from environment set in config.ini")
    surehubio=os.environ.get('SUREHUBIO')
else:
    print("SUREHUBIO hard-coded in app.py")
    surehubio='18.233.141.2'

#Log stderr to screen and file, as stderr is logged by default in docker compose
te = open(directory + 'https.log','a', buffering=1)

class Unbuffered:
  def __init__(self, stream):
    self.stream = stream

  def write(self, data):
    self.stream.write(data)
    self.stream.flush()
    te.write(data)

sys.stderr=Unbuffered(sys.stderr)

def dlfirmware(serialnumber,page):
    page=str(page)
    url = 'http://'+surehubio+'/api/firmware'
    headers = {'User-Agent': 'curl/7.22.0 (x86_64-pc-linux-gnu) libcurl/7.22.0 OpenSSL/1.0.1 zlib/1.2.3.4 libidn/1.23 librtmp/2.3', 'Content-Type':'application/x-www-form-urlencoded', 'Host':'hub.api.surehub.io', 'Connection': None, 'Accept-Encoding': None }
    postdata='serial_number='+serialnumber+'&page='+page+'&bootloader_version='+bootloader
    response = requests.post(url, data = postdata, headers=headers, verify=False)
    response.raise_for_status() # ensure we notice bad responses
    payload=response.content
    filename=directory+serialnumber+'-'+bootloader+'-'+str(page).zfill(2)+'.bin'
    file = open(filename, "wb")
    file.write(payload)
    file.close()

@app.route("/")
def hello():
    return "You should be sending a POST request!"

# Credentials Routing to download the credentials file if it hasn't been done already.
@app.route("/api/credentials",methods = ['POST'])
def credentials():
    print("Post payload : " + json.dumps(request.form), file=sys.stderr)
    #Download hub firmware for backup purposes.
    if SupportFirmware:
        firmware=directory+request.form['serial_number']+'-'+bootloader+'-00.bin'
        if not os.path.isfile(firmware):
            #Download header firmware file
            print("Download first firmware record")
            dlfirmware(request.form['serial_number'],0)
            with open(firmware, "rb") as f:
                #Read the header
                byte = f.read(36).decode("utf-8").split()
                #Record count in hex
                recordcount=int(byte[2], 16)+6
                print("Count ",recordcount)
                for counter in range(1,recordcount):
                    print("Download remaining record ",counter)
                    dlfirmware(request.form['serial_number'],counter)
        else:
            print("Firmware already downloaded " + firmware, file=sys.stderr)

    filename=directory+request.form['serial_number']+'-'+request.form['mac_address']+'-'+request.form['firmware_version']+'.bin'
    if not os.path.isfile(filename):
        print("Credentials file is missing, downloading from Surepet hub.api.surehub.io IP address", file=sys.stderr)
        url = 'https://'+surehubio+'/api/credentials'
        headers = {'User-Agent': 'curl/7.22.0 (x86_64-pc-linux-gnu) libcurl/7.22.0 OpenSSL/1.0.1 zlib/1.2.3.4 libidn/1.23 librtmp/2.3', 'Host':'hub.api.surehub.io'}
        response = requests.post(url, data = request.form, headers=headers, verify=False)
        response.raise_for_status() # ensure we notice bad responses
        payload=response.content
        #Creating original file from https response
        file = open(filename.replace("bin","original.bin"), "wb")
        file.write(payload)
        file.close()
        #Updating payload dns entry so that you don't need the aws api endpoint and everything points to hub.api.surepet.io which is the locally hosted mqtt instance and use a consistent topic of surepetlocal
        payloadsplit=payload.decode('utf-8').split(':')
        payloadsplit[6]='pethublocal' #Update topic name
        payloadsplit[7]='hub.api.surehub.io' #Update dns entry
        newpayload=':'.join(payloadsplit)
        print("Updated credentials with topic name pethublocal and MQTT endpoint also to hub.api.surehub.io so it is local local - "+newpayload, file=sys.stderr)
        file = open(filename, "w")
        file.write(newpayload)
        file.close()
    response = make_response(send_file(filename,mimetype='application/x-www-form-urlencoded',add_etags=False,cache_timeout=-1,last_modified=None))
    #This has to be done mangling the headers as the hub for whatever reason needs the Content-Length as the last value in the headers otherwise it won't work :(
    del response.cache_control.max_age
    del response.headers['Last-Modified']
    del response.headers['Expires']
    del response.headers['Cache-Control']
    cl = response.headers['Content-Length']
    del response.headers['Content-Length']
    utctime = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S %Z")
    #response.headers['Pragma'] = 'no-cache'
    h = {
       'Cache-Control': 'private, must-revalidate',
       'Date': utctime,
       'Pragma': 'no-cache',
       'Expires': '-1',
       'Server': 'nginx',
       'Content-Length': cl
    }
    response.headers.extend(h)
    return response

# Firmware update
@app.route("/api/firmware",methods = ['POST'])
def firmware():
    print("Post payload : " + json.dumps(request.form), file=sys.stderr)
    page=str(request.form['page']).zfill(2)
    filename=request.form['serial_number']+'-'+request.form['bootloader_version']+'-'+page+'.bin'
    response = make_response(send_file(filename,mimetype='text/html',add_etags=False,cache_timeout=-1,last_modified=None))
    del response.cache_control.max_age
    del response.headers['Last-Modified']
    del response.headers['Expires']
    del response.headers['Cache-Control']
    cl = response.headers['Content-Length']
    del response.headers['Content-Length']
    del response.headers['Server']
    del response.headers['Content-Type']
    utctime = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S %Z")
    #response.headers['Pragma'] = 'no-cache'
    h = {
       'Server': 'nginx/1.18.0 (Ubuntu)',
       'Date': utctime,
       'Content-Type': 'text/html; charset=utf-8',
       'Content-Length': cl,
       'Connection': 'keep-alive',
       'Cache-Control': 'no-cache, private'
    }
    response.headers.extend(h)
    return response

def runhttp():
    app.run(host=hostname,port=httpport)

def runhttps():
    app.run(host=hostname,port=httpsport,ssl_context=('hub.pem', 'hub.key'))

if __name__ == "__main__":
    WSGIRequestHandler.protocol_version = "HTTP/1.1"
    httpsstart = threading.Thread(target=runhttps)
    httpsstart.start()
    if SupportFirmware:
        httpstart = threading.Thread(target=runhttp)
        httpstart.start()
