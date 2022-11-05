import django

class BaseConfig(django.apps.AppConfig):
  name = 'base'

  def ready(self):
    # read the robots flag from all URLs and create a robots.txt file
    robotsPath={}
    # walk all URLResolvers recursively and collect robots path and there value
    def printURLResolver(resolver, rootPath="/"):
      for pattern in resolver.url_patterns:
        path=rootPath+str(pattern.pattern)
        idx=path.find("<")
        if idx>=0:
          path=path[0:idx]
        robots=True if not hasattr(pattern, "robots") else pattern.robots
        # check if the same path is added twice with different robots value
        if path in robotsPath and robots!="recFalse" and robotsPath[path]!="recFalse" and robotsPath[path]!=robots:
          raise RuntimeError("The path "+path+" is added twice with different robots values "+str(robotsPath[path])+", "+str(robots))
        if path!="/":
          if path in robotsPath and robotsPath[path]=="recFalse":
            pass
          else:
            robotsPath[path]=robots
        if isinstance(pattern, django.urls.URLResolver):
          printURLResolver(pattern, rootPath=rootPath+str(pattern.pattern))
        elif isinstance(pattern, django.urls.URLPattern):
          pass
        else:
          raise RuntimeError("Unknown URL object type")
    printURLResolver(django.urls.get_resolver())
    # create robots.txt file as a string
    self.robotsTXT="User-agent: *\n"
    for path in robotsPath:
      robots=robotsPath[path]
      if robots==True and robots!="recFalse":
        # check if a parent is is False but a child path True
        pathSplit=path.split("/")
        for n in range(len(pathSplit)-2, 0, -1):
          parentPath="/".join(pathSplit[0:n])+"/"
          for p in robotsPath:
            if p==parentPath and robotsPath[p]==False and robotsPath[p]!="recFalse":
              raise RuntimeError("The path "+path+" has robots=True but the parent path "+parentPath+" has robots=False")
        self.robotsTXT+="#  Allow: "+path+"\n"
      else:
        # add path to robots.txt file
        self.robotsTXT+="Disallow: "+path+"\n"
