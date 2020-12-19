import base

# homepage
class Home(base.views.Base):
  def get_template_names(self):
    return ["home/"+self.kwargs["suburl"]]
  def get_context_data(self, **kwargs):
    context=super().get_context_data(**kwargs)
    videos=[
      {"file": "home/videos/xml_mbsim_logo.webm"         , "title": "MBSim-Logo"     , "example": "xml/mbsim_logo"         },
      {"file": "home/videos/xml_woodpecker.webm"              , "title": "Woodpacker"     , "example": "xml/woodpecker"         },
      {"file": "home/videos/xml_rack_contact.webm"       , "title": "Rack"           , "example": "xml/rack_contact"       },
      {"file": "home/videos/xml_bevel_gear_contact.webm" , "title": "Bevel Gear"     , "example": "xml/bevel_gear_contact" },
      {"file": "home/videos/xml_planar_gear_contact.webm", "title": "Planar Gear"    , "example": "xml/planar_gear_contact"},
      {"file": "home/videos/xml_planetary_gear.webm"     , "title": "Planetary Gear" , "example": "xml/planetary_gear"     },

      {"file": "home/videos/xml_chaintensioner.webm"     , "title": "Chain Tensioner", "example": "xml/chaintensioner"     },
      {"file": "home/videos/xml_constraints.webm"        , "title": "Constraints"    , "example": "xml/constraints"        },
      {"file": "home/videos/xmlflat_tippe_top.webm"      , "title": "Tippe-Top"      , "example": "xmlflat/tippe_top"      },
      {"file": "home/videos/xml_pumptrack.webm"          , "title": "Pump-Track"     , "example": "xml/pumptrack"          },
      {"file": "home/videos/xml_rocking_rod.webm"        , "title": "Rocking-Rod"    , "example": "xml/rocking_rod"        },
      {"file": "home/videos/xml_rolling.webm"            , "title": "Rolling"        , "example": "xml/rolling"            },
    ]
    context["videos"]=[]
    for idx in range(0,len(videos),2):
      context["videos"].append({"col1": videos[idx], "col2": videos[idx+1] if idx<len(videos)-1 else None})
    return context
