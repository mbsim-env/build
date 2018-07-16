if($(location).attr('href').startsWith("https://www.mbsim-env.de")>=0) {
  $(document).ready(function() {
    if(!localStorage.getItem('cookieWarning')) {
      $("body").prepend(
  `<nav class="navbar navbar-inverse navbar-fixed-bottom" id="COOKIEWARNING">
    <div class="container-fluid">
      <p class="navbar-text">This website uses Cookies. We assume you are fine with this.
      <a href="/mbsim/html/impressum_disclaimer_datenschutz.html#datenschutz">Read more.</a></p>
      <button type="button" id="COOKIEBUTTON" class="btn btn-default navbar-btn">OK</button>
    </div>
  </nav>`);
    }
    $("#COOKIEBUTTON").click(function() {
      $("#COOKIEWARNING").addClass("hidden");
      localStorage.setItem('cookieWarning', 'doNotShowAgain');
    })
  })
}
