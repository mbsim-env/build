import os
import random
import json
import string

# this function never throws a real exception it just throws a dummy exception if anything fails
# this is done to avoid that any secret is print using exceptions
# if this function is called it should also ensured that the returned secret is never printed in any exception
def getSecrets(*keys):
  try:
    # get a secret
    def get(*keys):
      ret=getSecrets.secrets
      for k in keys:
        try:
          ret=ret[k]
        except KeyError:
          return ""
      return ret
    # secrets already loaded, just return it
    if getSecrets.secrets is not None:
      return get(*keys)
    # if environment secrets exist use these instead of the from file
    envSecrets={}
    for e in os.environ:
      if e.startswith("mbsimenvsec_"):
        d=envSecrets
        eSplit=e.split("_")
        for k in eSplit[1:-1]:
          if k not in d:
            d[k]={}
          d=d[k]
        d[eSplit[-1]]=os.environ[e]
    if len(envSecrets)>0:
      getSecrets.secrets=envSecrets
      return get(*keys)
    # use a secrets file
    if os.path.isfile("/mbsim-config/secrets.json"):
      secretFile="/mbsim-config/secrets.json"
    else:
      secretFile=os.path.dirname(os.path.realpath(__file__))+"/secrets.json"
    if not os.path.exists(secretFile):
      print("No secrets file found. Generate a new random Django key. (only done the first time)")
      with open(secretFile, "w") as f:
        getSecrets.secrets={"djangoSecretKey": ''.join(random.choice(string.hexdigits) for i in range(50))}
        json.dump(getSecrets.secrets, f)
        return get(*keys)
    with open(secretFile, "r") as f:
      getSecrets.secrets=json.load(f)
    return get(*keys)
  except ex:
    raise RuntimeError("Original exception avoided in getSecrets to ensure that no secret is printed.")
getSecrets.secrets=None
