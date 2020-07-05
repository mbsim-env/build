import os
import random
import json
import string

def getSecrets():
  if getSecrets.secrets is not None:
    return getSecrets.secrets
  if os.path.isfile("/mbsim-config/secrets.json"):
    secretFile="/mbsim-config/secrets.json"
  else:
    secretFile=os.path.dirname(os.path.realpath(__file__))+"/secrets.json"
  if not os.path.exists(secretFile):
    print("No secrets file found. Generate a new random Django key. (only done the first time)")
    with open(secretFile, "w") as f:
      getSecrets.secrets={"djangoSecretKey": ''.join(random.choice(string.hexdigits) for i in range(50))}
      json.dump(getSecrets.secrets, f)
      return getSecrets.secrets
  with open(secretFile, "r") as f:
    getSecrets.secrets=json.load(f)
  return getSecrets.secrets
getSecrets.secrets=None
