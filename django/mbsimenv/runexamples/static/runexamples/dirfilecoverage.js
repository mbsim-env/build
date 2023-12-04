var stateStorageID = "runexamples_run_dirfilecoverage_state_" + window.location.href;
var state = null;

function saveScrollState() {
  state.scrollState = window.pageYOffset;
  sessionStorage.setItem(stateStorageID, JSON.stringify(state));
}

$(document).ready(function() {
  // restore table state
  state = JSON.parse(sessionStorage.getItem(stateStorageID));
  if(!state) {
    // not table state exists -> use state from html
    state={tableState: [], scrollState: 0};
    var tr = $("#dirfiletable tr:first-child");
    var lineNr = 0;
    while(tr.length) {
      state.tableState.push({
        collapsed: !tr.children("td").children("span._triangleright").hasClass("_displaynone"),
        hiddencount: parseInt(tr.attr("data-hiddencount"))
      });
      tr = tr.next();
      lineNr = lineNr + 1;
    }
  }
  else {
    // use state from storage and adapt html
    var tr = $("#dirfiletable tr:first-child");
    var lineNr = 0;
    while(tr.length) {
      tr.attr("data-hiddencount", state.tableState[lineNr].hiddencount);
      if(state.tableState[lineNr].hiddencount>0)
        tr.addClass("_displaynone");
      else
        tr.removeClass("_displaynone");
      if(state.tableState[lineNr].collapsed) {
        tr.children("td:first-child").children("span._triangledown").addClass("_displaynone");
        tr.children("td:first-child").children("span._triangleright").removeClass("_displaynone");
      }
      else {
        tr.children("td:first-child").children("span._triangledown").removeClass("_displaynone");
        tr.children("td:first-child").children("span._triangleright").addClass("_displaynone");
      }
      tr = tr.next();
      lineNr = lineNr + 1;
    }
    window.scrollTo(0, state.scrollState);
  }

  $("._expandcollapsecontent").click(function() {
    // get data
    var td = $(this).parent();
    var tr = td.parent();
    var collapsed = !td.children("span._triangleright").hasClass("_displaynone");
    var indent = parseInt(tr.attr("data-indent"));
    // get storage
    var lineNr = tr.prevAll().length;
    // toggle expanded/collapsed icon
    td.children("span._triangledown").toggleClass("_displaynone");
    td.children("span._triangleright").toggleClass("_displaynone");
    state.tableState[lineNr].collapsed = !collapsed; // save new (toggeled) state
    // loop throught lines
    tr = tr.next();
    lineNr = lineNr + 1;
    while(parseInt(tr.attr("data-indent")) >= indent+1) {
      if(!collapsed) {
        var newValue = parseInt(tr.attr("data-hiddencount")) + 1;
        tr.attr("data-hiddencount", newValue);
        tr.addClass("_displaynone");
        state.tableState[lineNr].hiddencount = newValue;
      }
      else {
        var newValue = parseInt(tr.attr("data-hiddencount")) - 1;
        tr.attr("data-hiddencount", newValue);
        if(newValue == 0)
          tr.removeClass("_displaynone");
        state.tableState[lineNr].hiddencount = newValue;
      }
      tr = tr.next();
      lineNr = lineNr + 1;
    }
    state.scrollState = window.pageYOffset;
    sessionStorage.setItem(stateStorageID, JSON.stringify(state));
  });
});
