import base
import os

# homepage
class Home(base.views.Base):
  def get_template_names(self):
    return ["home/"+self.kwargs["suburl"]]
  def get_context_data(self, **kwargs):
    context=super().get_context_data(**kwargs)
    context["navbar"]["home"]=True
    return context

class Videos(base.views.Base):
  template_name='home/videos.html'
  def get_context_data(self, **kwargs):
    context=super().get_context_data(**kwargs)
    context["navbar"]["videos"]=True
    videos=[
    #        path to video in django static                       title                link external link href (abs or rel to mbsim/examples)
    {"file": "home/videos/xml_motorcycle_drift.webm"   , "title": "Motorcycle drift" , "ext": True , "href": "https://github.com/TUMFTM/motorcycle_model" },
    {"file": "home/videos/xml_humanoid_robot.webm"     , "title": "Humanoid robot"   , "ext": False, "href": "xml/humanoid_robot"                         },
    {"file": "home/videos/xml_flexible_conrod.webm"    , "title": "Flexible conrod"  , "ext": False, "href": "xml/flexible_conrod"                        },
    {"file": "home/videos/xml_mbsim_logo.webm"         , "title": "MBSim-Logo"       , "ext": False, "href": "xml/mbsim_logo"                             },
    {"file": "home/videos/xml_woodpecker.webm"         , "title": "Woodpecker"       , "ext": False, "href": "xml/woodpecker"                             },
    {"file": "home/videos/xml_rack_contact.webm"       , "title": "Rack"             , "ext": False, "href": "xml/rack_contact"                           },
    {"file": "home/videos/xml_bevel_gear_contact.webm" , "title": "Bevel Gear"       , "ext": False, "href": "xml/bevel_gear_contact"                     },
    {"file": "home/videos/xml_planar_gear_contact.webm", "title": "Planar Gear"      , "ext": False, "href": "xml/planar_gear_contact"                    },
    {"file": "home/videos/xml_planetary_gear.webm"     , "title": "Planetary Gear"   , "ext": False, "href": "xml/planetary_gear"                         },
    {"file": "home/videos/xml_chaintensioner.webm"     , "title": "Chain Tensioner"  , "ext": False, "href": "xml/chaintensioner"                         },
    {"file": "home/videos/xml_constraints.webm"        , "title": "Constraints"      , "ext": False, "href": "xml/constraints"                            },
    {"file": "home/videos/xmlflat_tippe_top.webm"      , "title": "Tippe-Top"        , "ext": False, "href": "xmlflat/tippe_top"                          },
    {"file": "home/videos/xml_pumptrack.webm"          , "title": "BMX/MTB Pumptrack", "ext": False, "href": "xml/pumptrack"                              },
    {"file": "home/videos/xml_rocking_rod.webm"        , "title": "Rocking-Rod"      , "ext": False, "href": "xml/rocking_rod"                            },
    {"file": "home/videos/xml_rolling.webm"            , "title": "Rolling"          , "ext": False, "href": "xml/rolling"                                },
    ]
    # add poster and fix href
    for v in videos:
      v["poster"]=os.path.splitext(v["file"])[0]+".png"
      if v["ext"]==False:
        v["href"]="https://github.com/mbsim-env/mbsim/tree/master/examples/"+v["href"]
    context["videos"]=[]
    for idx in range(0,len(videos),2):
      context["videos"].append({"col1": videos[idx], "col2": videos[idx+1] if idx<len(videos)-1 else None})
    return context
