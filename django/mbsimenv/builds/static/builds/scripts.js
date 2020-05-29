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
    'lengthMenu': [ [1, 5, 10, -1], [1, 5, 10, 'All'] ],
    'pageLength': -1, 'stateSave': true
  });
}
