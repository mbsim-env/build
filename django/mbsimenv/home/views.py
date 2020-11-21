import base

# homepage
class Home(base.views.Base):
  def get_template_names(self):
    return ["home/"+self.kwargs["suburl"]]
