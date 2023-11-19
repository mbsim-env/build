$(document).ready(function() {
  $("._expandcollapsecontent").click(function() {
    // get data
    var td = $(this).parent();
    var tr = td.parent();
    var expanded = td.children("span._triangleright").hasClass("_displaynone");
    var indent = parseInt(tr.attr("data-indent"));
    // toggle expanded/collapsed icon
    td.children("span._triangledown").toggleClass("_displaynone");
    td.children("span._triangleright").toggleClass("_displaynone");
    // loop throught lines
    tr = tr.next();
    while(parseInt(tr.attr("data-indent")) >= indent+1) {
      if(expanded) {
        tr.attr("data-hiddencount", parseInt(tr.attr("data-hiddencount")) + 1);
        tr.addClass("_displaynone");
      }
      else {
        var newValue = parseInt(tr.attr("data-hiddencount")) - 1;
        tr.attr("data-hiddencount", newValue);
        if(newValue == 0)
          tr.removeClass("_displaynone");
      }
      tr = tr.next();
    }
  });
});
