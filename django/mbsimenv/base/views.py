import django
import json
import functools
import base
import importlib
import mimetypes
import octicons
from octicons.templatetags.octicons import octicon

# basic view with header and footer
class Base(django.views.generic.base.TemplateView):
  def get_context_data(self, **kwargs):
    context=super().get_context_data(**kwargs)
    context["navbar"]={
      "home": False,
      "download": False,
      "videos": False,
      "sourcecode": False,
      "buildsystem": False,
    }
    if not self.request.user.is_authenticated:
      # nobody is logged in -> use dummy avatar
      userAvatarEle=octicon("person", height="21")
    else:
      import allauth
      # someone is logged in
      try:
        # get avatar from social account (github)
        avatarUrl=allauth.socialaccount.models.SocialAccount.objects.get(user=self.request.user).get_avatar_url()
        userAvatarEle='<img height="21em" src="'+avatarUrl+'"/>'
      except allauth.socialaccount.models.SocialAccount.DoesNotExist:
        # its not a social account (github) -> use dummy avatar
        userAvatarEle=octicon("person", height="21")
    context['userAvatarEle']=userAvatarEle
    return context

# displays a TextField of a build dataset
class TextFieldFromDB(Base):
  template_name='base/textFieldFromDB.html'
  def get_context_data(self, **kwargs):
    context=super().get_context_data(**kwargs)
    context["navbar"]["buildsystem"]=True
    data=importlib.import_module(kwargs["app"]).models.__getattribute__(kwargs["model"]).\
         objects.get(id=kwargs["id"]).__getattribute__(kwargs["field"])
    context["data"]=data
    return context
# download a TextField of a build dataset
def textFieldFromDBDownload(request, app, model, id, field):
  data=importlib.import_module(app).models.__getattribute__(model).objects.get(id=id).__getattribute__(field)
  response=django.http.HttpResponse(data, content_type='text/plain')
  response['Content-Disposition']='attachment; filename="'+app+"_"+model+"_"+str(id)+"_"+field+'.txt"'
  return response

# download a file from the db
def fileDownloadFromDB(request, app, model, id, field):
  obj=importlib.import_module(app).models.__getattribute__(model).objects.get(id=id)
  f=obj.__getattribute__(field).open("rb")
  name=getattr(obj, field+"Name")
  return django.http.FileResponse(f, as_attachment=True, filename=name)

# the impresusm page
class Impressum(Base):
  template_name='base/impressum_disclaimer_datenschutz.html'
  def get_context_data(self, **kwargs):
    context=super().get_context_data(**kwargs)
    context["navbar"]["home"]=True

# dummy http page just to display all available octicons
class ListOcticons(Base):
  template_name='base/octicons.html'
  def get_context_data(self, **kwargs):
    context=super().get_context_data(**kwargs)
    context['OCTICON_DATA']=octicons.templatetags.OCTICON_DATA
    return context

# the user profile page
class UserProfile(Base):
  template_name='base/userprofile.html'
  def setup(self, request, *args, **kwargs):
    super().setup(request, *args, **kwargs)
    # provide a cache for github access
    self.gh=base.helper.GithubCache(request)
  def get_context_data(self, **kwargs):
    import allauth
    context=super().get_context_data(**kwargs)
    context["navbar"]["buildsystem"]=True
    if not self.request.user.is_authenticated:
      # nobody is logged in -> use large dummy avatar; no social user available
      userLargeAvatarEle=octicon("person", height="125")
      socialUser=None
    else:
      try:
        # get large avatar from social account (github); set social user varible
        socialUser=allauth.socialaccount.models.SocialAccount.objects.get(user=self.request.user)
        avatarUrl=socialUser.get_avatar_url()
        userLargeAvatarEle='<img height="125em" src="'+avatarUrl+'"/>'
      except allauth.socialaccount.models.SocialAccount.DoesNotExist:
        # its not a social account (github) -> use large dummy avatar; no social user available
        socialUser=None
        userLargeAvatarEle=octicon("person", height="125")
    context["clientID"]=allauth.socialaccount.models.SocialApp.objects.get(provider="github").client_id
    context["userLargeAvatarEle"]=userLargeAvatarEle
    context["socialUser"]=socialUser
    context["githubAccessTokenDummy"]="<not shown for security reasons>" if self.gh.getAccessToken() else None
    context["githubUserInMbsimenv"]=self.gh.getUserInMbsimenvOrg(base.helper.GithubCache.viewTimeout)
    sessionDBObj=list(django.contrib.sessions.models.Session.objects.filter(session_key=self.request.session.session_key))
    if len(sessionDBObj)>0:
      context["session"]={}
      context["session"]["id"]=sessionDBObj[0].session_key
      context["session"]["data"]=sessionDBObj[0].get_decoded()
      context["session"]["expire"]=sessionDBObj[0].expire_date
    return context

# on logout, log out and redirect to user profile
def userLogout(request):
  django.contrib.auth.logout(request)
  return django.shortcuts.redirect('base_userprofile')

# abstract base class to response to ajax requests of datatable
class DataTable(django.views.View):
  def setup(self, request, *args, **kwargs):
    super().setup(request, *args, **kwargs)
    # provide a cache for github access
    self.gh=base.helper.GithubCache(request)
  # default class attribute for a table row -> empty class
  def rowClass(self, ds):
    return ""
  # default database col name to be used for ordering (if no user defined ordering is requested by Datatables)
  def defaultOrderingColName(self):
    return "pk"
  # return json response to a ajax request of datatable
  def post(self, request, *args, **kwargs):
    # return the visibility state of the columns if the http query contains "columnsVisible"
    if "columnsVisible" in request.GET:
      if hasattr(self, "columnsVisibility"):
        return django.http.JsonResponse({"columnsVisibility": self.columnsVisibility()}, json_dumps_params={"indent": 2})
      else:
        return django.http.JsonResponse({"columnsVisibility": None}, json_dumps_params={"indent": 2})

    # else return the table data
    try:
      # get the request from datatable as json
      req=json.loads(request.body)
      # fitler the data of the table (returned from queryset())
      # the table column defined by searchField() is filtered using the serach string provided via json
      filteredData=self.queryset().filter(**{self.searchField()+"__contains": req["search"]["value"]})
      # sort the filtered data
      if len(req["order"])>0:
        # get the column to sort provided via json
        sortCol=req["columns"][req["order"][0]["column"]]["data"]
        # get the sort order provided via json
        sortDir=req["order"][0]["dir"]
        if hasattr(self, "colSortKey_"+sortCol):
          # if colSortKey_<colName>() is defined sort using these values as key
          sortColName="colSortKey_"+sortCol
        else:
          # if colSortKey_<colName>() is not defined sort using the data (colData_<colName>()) as key
          sortColName="colData_"+sortCol
        sortedData=sorted(filteredData, key=self.__getattribute__(sortColName), reverse=sortDir=="desc")
      else:
        # no sorting requested
        sortedData=filteredData.order_by(self.defaultOrderingColName())
      # prepare the response as json
      res={}
      res["draw"]=int(req["draw"]) # the datatable request ID needs just to be passed back
      res["recordsTotal"]=self.queryset().count() # number of rows before filtering
      res["recordsFiltered"]=filteredData.count() # nubmer of rows after filtering
      # generate a map from the column name to the column index (the json request just included the reverse map)
      columnNr={}
      colNr=0;
      for col in req["columns"]:
        columnNr[col["data"]]=colNr
        colNr=colNr+1
      # filter the data regarind the requeste pagination
      if req["length"]>=0:
        rangeSortedData=sortedData[req["start"]:req["start"]+req["length"]]
      else:
        rangeSortedData=sortedData
      # prepare the data response as json
      data=[] # a list for the rows
      for ds in rangeSortedData:
        DTColClass={}
        # we use the none datatable standard DT_ColClass to store the class attribute for the column
        # see base/script.hs - initDatatable(...) for details
        dtds={"DT_ColClass": DTColClass} # DT_ColClass stores the class attribute for each column
        dtds["DT_RowClass"]=self.rowClass(ds) # the class attribute for the tow
        for col_ in req["columns"]:
          col=col_["data"]
          # store the column data (this may be html code)
          dtds[col]=self.__getattribute__("colData_"+col)(ds)
          # if colClass_<columnName>() is defined use it as class attribute for the column (the key of DT_ColClass is the column idx)
          if hasattr(self, "colClass_"+col):
            DTColClass[columnNr[col]]=self.__getattribute__("colClass_"+col)(ds)
        data.append(dtds)
      res["data"]=data
      # return the json response
      return django.http.JsonResponse(res, json_dumps_params={"indent": 2})
    except:
      # error handling
      import traceback
      import mbsimenv
      res={}
      res["draw"]=int(req["draw"]) # the datatable request ID needs just to be passed back
      res["recordsTotal"]=1
      res["recordsFiltered"]=1
      dtds={"DT_ColClass": {}, "DT_RowClass": "table-danger"}
      first=True
      for col in req["columns"]:
        if first:
          if django.conf.settings.DEBUG:
            dtds[col["data"]]=traceback.format_exc()
          else:
            dtds[col["data"]]="Internal error: please report this site to the webmaster"
          first=False
        else:
          dtds[col["data"]]=""
      res["data"]=[dtds]
      return django.http.JsonResponse(res, json_dumps_params={"indent": 2})
