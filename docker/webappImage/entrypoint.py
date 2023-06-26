#!/usr/bin/env python3

import websockify.token_plugins
import websockify.auth_plugins
import os
import requests
import http.cookies
import time
import threading
import uuid
import sys
import contextlib
import socket
import subprocess

# configuration
DEBUG=False

def waitForOpenPort(host, port, timeout):
  def portOpen(host, port):
    with contextlib.closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
      try:
        if sock.connect_ex((host, port)) == 0:
          return True
        else:
          return False
      except:
        return False
  for i in range(0,timeout*10):
    if portOpen(host, port):
      return
    time.sleep(0.1)
  raise RuntimeError("Waiting for port "+str(port)+" on host "+host+" timed out.")

websockify.logger_init()
if DEBUG:
  websockify.logging.getLogger(websockify.WebSocketProxy.log_prefix).setLevel(websockify.logging.DEBUG)

# a global variable to pass over data from token plugin to auth plugin
globalVar={}

# the Websockify token plugin
class MBSimWebappToken(websockify.token_plugins.BasePlugin):
  def lookup(self, token):
    global globalVar
    # save the token for later use in the auth module
    globalVar["token"]=token
    # create a unique hostname and save for later user in the auth module
    hostname="webapp-run-"+uuid.uuid4().hex
    globalVar["hostname"]=hostname
    # vnc is running at hostname on display 1 = port 5901
    return (hostname, 5901)

# the Websockify auth plugin
class MBSimWebappAuth(websockify.auth_plugins.BasePlugin):
  def authenticate(self, headers, target_host, target_port):
    # check authentification

    # for for cookie
    if 'Cookie' not in headers: # error if not Cookie is defined
      raise websockify.auth_plugins.AuthenticationError(log_msg="No cookie provided.")
    # get cookie (as CookieJar)
    cj=requests.cookies.RequestsCookieJar()
    cj.update(http.cookies.SimpleCookie(headers['Cookie']))
    # call the server to check for valid user
    response=requests.get("https://"+os.environ['MBSIMENVSERVERNAME']+"/service/checkvaliduser/", cookies=cj)
    # if the response is not OK than the user is not allowed
    if response.status_code!=200:
      raise websockify.auth_plugins.AuthenticationError(log_msg="User not authorized.")

    token=globalVar["token"]
    hostname=globalVar["hostname"]

    # start vnc and other processes in a new container (being reachable as hostname)
    # start this in a seperate process which stops the container if the parent (this process) terminates
    networkID=sys.argv[1]
    subprocess.Popen(["/context/webapprun.py", networkID, token, hostname])
    waitForOpenPort(hostname, 5901, 10)

class MyWebSocket(websockify.websockifyserver.CompatibleWebSocket):
  def __init__(self):
    websockify.websockifyserver.CompatibleWebSocket.__init__(self)
    self.lastPing = time.time()
    threading.Thread(target=self.checkKill).start()
  def checkKill(self):
    while True:
      time.sleep(5)
      if time.time()-self.lastPing>30:
        websockify.logging.getLogger(websockify.WebSocketProxy.log_prefix).info('Client seems to be dead. No ping since 30sec. Killing now.')
        os._exit(0)
  def handle_pong(self, data):
    self.lastPing = time.time()

class MyPRH(websockify.websocketproxy.ProxyRequestHandler):
  SocketClass=MyWebSocket

server = websockify.websocketproxy.WebSocketProxy(
  RequestHandlerClass=MyPRH,
  listen_host='webapp',
  listen_port=10080,
  heartbeat=10,
  token_plugin=MBSimWebappToken(None),
  auth_plugin=MBSimWebappAuth(None),
)
server.start_server()
