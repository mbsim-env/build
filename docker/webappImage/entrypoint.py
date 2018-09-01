#!/usr/bin/python

import websockify.token_plugins
import websockify.auth_plugins
import os
import subprocess
import requests
import Cookie
import time
import threading
import uuid
import docker
import sys

# configuration
DEBUG=True
dockerClient=docker.from_env()

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
    if 'Cookie' not in headers: # error if not Cookie is defined
      raise websockify.auth_plugins.AuthenticationError(log_msg="No cookie provided.")
    # get cookie and get the mbsimenvsessionid form the cookie
    cookie=headers['Cookie']
    c=Cookie.SimpleCookie(cookie)
    if 'mbsimenvsessionid' not in c:
      raise websockify.auth_plugins.AuthenticationError(log_msg="No mbsimenvsessionid provided in cookie.")
    sessionid=c['mbsimenvsessionid'].value
    # call the server to check to session ID (we can do this my checking the config file of the server directly
    # but this file is not readable for this user for security reasons)
    response=requests.post("https://"+os.environ['MBSIMENVSERVERNAME']+"/cgi-bin/mbsimBuildServiceServer.py/checkmbsimenvsessionid",
      json={'mbsimenvsessionid': sessionid})
    # if the response is OK and success is true than continue
    if response.status_code!=200:
      raise websockify.auth_plugins.AuthenticationError(log_msg="Checking session ID failed.")
    d=response.json()
    if 'success' not in d:
      raise websockify.auth_plugins.AuthenticationError(log_msg="Invalid response from mbsim server.")
    if not d['success']:
      raise websockify.auth_plugins.AuthenticationError(log_msg=d['message'])

    token=globalVar["token"]
    hostname=globalVar["hostname"]

    # start vnc and other processes in a new container (being reachable as hostname)
    networkID=sys.argv[1]
    network=dockerClient.networks.get(networkID)
    webapprun=dockerClient.containers.run(image="mbsimenv/webapprun",
      init=True,
      command=[token],
      volumes={
        'mbsimenv_mbsim-linux64-ci':           {"bind": "/mbsim-env-linux64-ci",           "mode": "ro"},
        'mbsimenv_mbsim-linux64-dailydebug':   {"bind": "/mbsim-env-linux64-dailydebug",   "mode": "ro"},
        'mbsimenv_mbsim-linux64-dailyrelease': {"bind": "/mbsim-env-linux64-dailyrelease", "mode": "ro"},
      },
      detach=True, stdout=True, stderr=True)
    network.connect(webapprun, aliases=[hostname])
    time.sleep(5)#mfmf
    #mfmf how to log webapprun
    #mfmf how to exit webapprun
    # wait for container to setup webapprun
    #mfmf

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
