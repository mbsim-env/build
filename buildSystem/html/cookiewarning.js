if($(location).attr('href').startsWith("https://www.mbsim-env.de")>=0) {
  $(document).ready(function() {
    if(!localStorage.getItem('cookieWarning')) {
      $("body").prepend(
  `<nav class="navbar navbar-inverse navbar-fixed-top" id="COOKIEWARNING">
    <div class="container-fluid">
      <p class="navbar-text">This website uses Cookies. We assume you are fine with this.
      <a href="/mbsim/html/impressum_disclaimer_datenschutz.html#datenschutz">Read more.</a>
      <button type="button" id="COOKIEBUTTON" class="btn btn-default navbar-btn">OK</button></p>
    </div>
  </nav>`);
    }
    $("#COOKIEBUTTON").click(function() {
      $("#COOKIEWARNING").addClass("hidden");
      localStorage.setItem('cookieWarning', 'doNotShowAgain');
    })
  })
}
