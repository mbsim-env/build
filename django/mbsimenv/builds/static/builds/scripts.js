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
  });
}
