"use strict";

// example table
function initExampleTable(url) {
  return initDatatable('exampleTable', url, [
    "example",
    "run",
    "time",
    "refTime",
    "guiTest",
    "ref",
    "webApp",
    "dep",
    "xmlOut",
  ], {
    'lengthMenu': [ [10, 25, 50, 100, -1], [10, 25, 50, 100, 'All'] ],
    'pageLength': 25,
    "order": [],
  });
}

function changeRefUpdate(input, url, exampleName) {
  var noti=new Notification("<small>Pending save of '"+exampleName+"'</small>");
  ajaxCall(url, {
    // inData
    update: input.prop("checked")
  }, function() {
    // done
    noti.success("<small>Stored reference update for '"+exampleName+"'</small>");
  }, function(reason, msg) {
    // fail
    noti.fail(reason, "The new reference update state for the example '"+exampleName+"' was not stored.<br/>"+msg);
  }, function() {
    // allways
    input.prop("disabled", false);
  });
}

// valgrind error table
function initValgrindErrorTable(url) {
  return initDatatable('valgrindErrorTable', url, [
    "kind",
    "detail",
  ], {
    'lengthMenu': [ [10, 25, 50, 100, 250, -1], [10, 25, 50, 100, 250, 'All'] ],
    'pageLength': 25,
    'order': [],
    'drawCallback': function() {
      $("#valgrindErrorTable").children("tbody").first().children("tr").each(function() {
        var id=$(this).children("td").first().next().children("table").attr("id");
        if(id) {
          var url=$(this).children("td").first().next().children("table").attr("data-url");
          initValgrindStackTable(id, url);
        }
      });
    },
  });
}

// valgrind stack table
function initValgrindStackTable(id, url) {
  return initDatatable(id, url, [
    "fileLine",
    "function",
    "library",
  ], {
    'lengthMenu': [ [1, 2, 5, 10, 20, -1], [1, 2, 5, 10, 20, 'All'] ],
    'pageLength': 5,
    'ordering': false,
    'searching': false,
  });
}

// xmloutput table
function initXMLOutputTable(url) {
  return initDatatable('xmloutputTable', url, [
    "file",
    "result",
  ], {
    'lengthMenu': [ [10, 25, 50, 100, -1], [10, 25, 50, 100, 'All'] ],
    'pageLength': 25,
    'order': [],
  });
}

// compareresult table
function initCompareResultTable(url) {
  return initDatatable('compareresultTable', url, [
    "h5file",
    "dataset",
    "label",
    "result",
  ], {
    'lengthMenu': [ [10, 25, 50, 100, -1], [10, 25, 50, 100, 'All'] ],
    'pageLength': 25,
    'order': [],
  });
}
