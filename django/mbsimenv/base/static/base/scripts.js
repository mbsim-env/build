"use strict";

$(document).ready(function() {
  // show a cookie warning for this site
  if($(location).attr('href').startsWith("https://"+window.location.hostname)>=0) {
    if(!localStorage.getItem('cookieWarning')) {
      $("body").prepend(
       `<div class="alert alert-info fixed-bottom" id="COOKIEWARNING" style="margin: 1em" role="alert">
          <strong>This website uses required Cookies only, like session ID and user-settings!</strong>
          Read more in on the impressum/disclaimer page.
          <button type="button" id="COOKIEBUTTON" class="close" data-dismiss="alert">OK</button>
        </div>`);
    }
    $("#COOKIEBUTTON").click(function() {
      localStorage.setItem('cookieWarning', 'doNotShowAgain');
    })
  }

  // convert timedate to local timedate
  $('.DATETIME').each(function() {
    $(this).text(moment($(this).text()).tz(moment.tz.guess()).format("ddd, YYYY-MM-DD - HH:mm:ss z"));
  });
}); 

// initialize a datatable for use with the base.DataTable view
// id: the id of the table element to use
// url: the url from where the data is get
// colNames: the column names of the table
//   [ "colname1", "colname2", ... ]
// args: additional argument passed to datatable
// doneCallback is called, if given, after a successfull ajax request
function initDatatable(id, url, colNames, args, doneCallback) {
  var columns=[];
  for(var i=0; i<colNames.length; ++i)
    columns.push({"data": colNames[i], "name": colNames[i]});
  var arg1={
    serverSide: true,
    ajax: {
      "url": url,
      "contentType": "application/json",
      "type": "POST",
      "data": function(d) {
        return JSON.stringify(d);
      }
    },
    "columnDefs": [
      {
        "targets": "_all",
        "createdCell": function (td, cellData, rowData, row, col) {
          $(td).addClass(rowData.DT_ColClass[col]);
        }
      }
    ],
    "columns": columns,
    "stateSave": true,
    "stateDuration": 10 * 60,
  };
  var table=$("#"+id).DataTable(Object.assign({}, arg1, args));
  ajaxCall(url+"?columnsVisible=1", {}, function(data) {
    // done
    if(data.columnsVisibility)
      for(var col in data.columnsVisibility)
        table.column(col+":name").visible(data.columnsVisibility[col]);
    if(doneCallback!==undefined)
      doneCallback(data);
  },
  function(reason, msg) {
    //fail
    alert("Internal error in AJAX call initDatatable::columnsVisible=1: "+reason+": "+msg);
  });
  return table
}

// make a ajax call.
// url: the url to call
// inData: json object send to the server
// doneFunc: called on success as doneFunc(outData) with outData the json result of the server
// failFunc: called on failure as failFunc(reason, message) with reason the http error code string and message the http content
// alwaysFunc: called in any case [optional] as alwaysFunc()
function ajaxCall(url, inData, doneFunc, failFunc, alwaysFunc) {
  $.ajax({
    url: url,
    method: "POST",
    contentType: "application/json",
    data: JSON.stringify(inData),
  }).done(function(outData) {
    doneFunc(outData);
  }).fail(function(jqXHR, errorThrown, textStatus) {
    failFunc(textStatus, "responseText: " + jqXHR.responseText + "\n" +
                         "status: "       + jqXHR.status + "\n" +
                         "statusText: "   + jqXHR.statusText + "\n" +
                         "readyState: "   + jqXHR.readyState + "\n" +
                         "errorThrown: "  + errorThrown);
  }).always(function() {
    if(alwaysFunc!==undefined)
      alwaysFunc();
  });
}

// shown notification (as bootstrap toasts) to the user
class Notification {
  // pops up a info toast with the message pendingMsg until success or fail is called.
  constructor(pendingMsg) {
    this.pendingEle=$("#TOASTS").prepend(`
      <div style="opacity: 0.75;" class="toast bg-info" data-autohide="false">
        <div class="toast-body">
          `+pendingMsg+`
          <button type="button" class="close" data-dismiss="toast">
            <span>&times;</span>
          </button>
        </div>
      </div>`
    ).children().first();
    this.pendingEle.toast("show");
  }
  // replaces the info toast (from the constructor) by a success toast with message successMsg.
  // This toast is only shown for 1sec.
  success(successMsg) {
    this.pendingEle.remove(); // this removes the pending toast if already shown or not (event shown.bs.toast)
    var finishedEle=$("#TOASTS").prepend(`
      <div style="opacity: 0.75;" class="toast bg-success" data-autohide="true" data-delay="1000">
        <div class="toast-body">
          `+successMsg+`
          <button type="button" class="close" data-dismiss="toast">
            <span>&times;</span>
          </button>
        </div>
      </div>`
    ).children().first();
    finishedEle.toast("show");
  }
  // replaces the info toast (from the constructor) by a fail toast with message header failReason and message body failMsg.
  // This toast must be closed by the user.
  fail(failReason, failMsg) {
    this.pendingEle.remove(); // this removes the pending toast if already shown or not (event shown.bs.toast)
    var finishedEle=$("#TOASTS").prepend(`
      <div style="opacity: 0.925;" class="toast bg-danger" data-autohide="false">
        <div class="toast-header">
          <strong class="mr-auto">Action failed: `+failReason+`</strong>
          <button type="button" class="close" data-dismiss="toast">
            <span>&times;</span>
          </button>
        </div>
        <div class="toast-body">
          `+failMsg+`
        </div>
      </div>`
    ).children().first();
    finishedEle.toast("show");
  }
};
