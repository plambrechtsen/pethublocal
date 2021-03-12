import os, requests, sys, json
from datetime import datetime, timezone
from flask import Flask, request, send_file, make_response
from werkzeug.serving import WSGIRequestHandler
app = Flask(__name__)
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 1

port=443
hostname='0.0.0.0'
directory='/web/creds/'
#hostname='192.168.20.242'
#directory=''

#Define the IP address directly as you can't rely on local DNS.
surehubio='54.146.28.80'

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

@app.route("/")
def hello():
    return "You should be sending a POST request!"

#@app.after_request
#def apply_caching(response):
#    response.headers["Content-Length"] = filelength
#    return response

# Get Image file Routing
@app.route("/api/credentials",methods = ['POST'])
def get_image():
    print("Post payload : " + json.dumps(request.form), file=sys.stderr)
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

if __name__ == "__main__":
    WSGIRequestHandler.protocol_version = "HTTP/1.1"
    app.run(host=hostname,port=port,ssl_context=('hub.pem', 'hub.key'))

