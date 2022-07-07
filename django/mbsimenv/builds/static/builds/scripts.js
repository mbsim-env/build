"use strict";

// tool table
function initToolTable(url) {
  return initDatatable('toolTable', url, [
    "tool",
    "configure",
    "make",
    "makeCheck",
    "doc",
    "xmldoc",
  ], {
    "paging": false,
    "order": [],
    "language": {
      "search": "Filter 'Tool':",
    },
  });
}

function releaseDistribution(url) {
  $("#releaseButton").click(function() {
    // check if all checkboxes are checked
    var checkBoxUnchecked=false;
    $(".RELEASECHECK").each(function() {
      if(!$(this).prop("checked"))
        checkBoxUnchecked=true;
    });
    if(checkBoxUnchecked) {
      new Notification("").fail("Unchecked checkboxes!", "You need to check all the 'release distribution' checkboxes.");
    }
    else {
      $("#releaseButton").attr("disabled", "disabled");
      var noti=new Notification("<small>Pending release distribution</small>");
      ajaxCall(url, {releaseVersion: $("#releaseVersion").val()}, function() {
        // done
        noti.success("<small>Successfully released</small>");
      }, function(reason, msg) {
        //fail
        noti.fail(reason, "Releasing failed:<br/>"+msg);
      }, function() {
        // always
        $("#releaseButton").removeAttr("disabled");
      });
    }
  });
}

$(document).ready(function() {

  // reset the form
  $("#releaseForm").trigger("reset");

  // if the releaseVersion input is edited then update RELSTR in the document
  $("#releaseVersion").keyup(function() {
    var curRelStr=$("#releaseVersion").val();
    $(".RELSTR").each(function() {
      $(this).text(curRelStr);
    })
  });

});
