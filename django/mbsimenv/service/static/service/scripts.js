"use strict";

// example table
function initCIBranchesTable(url) {
  return initDatatable('cibranchesTable', url, [
    "remove",
    "fmatvecBranch",
    "hdf5serieBranch",
    "openmbvBranch",
    "mbsimBranch",
  ], {
    "paging": false,
    "searching": false,
    "info": false,
  });
}

function loadBranches(url) {
  // get branches
  ajaxCall(url, {}, function(outData) {
    // done
    const repoList=['fmatvec', 'hdf5serie', 'openmbv', 'mbsim'];
    repoList.forEach(function(repo) {
      var sel=$("#SELECTBRANCH_"+repo);
      sel.empty();
      outData[repo+"Branch"].forEach(function(branch) {
        sel.append('<option>'+branch+'</option> ');
      });
      if(outData.enable)
        sel.removeAttr("disabled");
      else
        sel.attr("disabled", "disabled");
    });
    if(outData.enable)
      $("#ADDBRANCH").removeAttr("disabled");
    else
      $("#ADDBRANCH").attr("disabled", "disabled");
  }, function(reason, msg) {
    //fail
    alert("Internal error: "+reason+": "+msg);
  });
}

function addBranchCombination(url) {
  const repoList=['fmatvec', 'hdf5serie', 'openmbv', 'mbsim'];

  $("#ADDBRANCH").prop("disabled", true);
  repoList.forEach(function(repo) {
    $("#SELECTBRANCH_"+repo).prop("disabled", true);
  });
  var noti=new Notification("<small>Pending save of branch combination</small>");
  ajaxCall(url, {
    // data
    fmatvecBranch: $('#SELECTBRANCH_fmatvec').val(),
    hdf5serieBranch: $('#SELECTBRANCH_hdf5serie').val(),
    openmbvBranch: $('#SELECTBRANCH_openmbv').val(),
    mbsimBranch: $('#SELECTBRANCH_mbsim').val()
  }, function() {
    // done
    ciBranchesTableObj.ajax.reload();
    noti.success("<small>Stored branch combination</small>");
  }, function(reason, msg) {
    //fail
    noti.fail(reason, "The new branch combination for CI was not stored.<br/>"+msg);
  }, function() {
    // always
    $("#ADDBRANCH").removeAttr("disabled");
    repoList.forEach(function(repo) {
      $("#SELECTBRANCH_"+repo).removeAttr("disabled");
    });
  });
}

function deleteBranchCombination(self, url) {
  self.prop("disabled", true);
  var noti=new Notification("<small>Pending delete of branch combination</small>");
  ajaxCall(url, {}, function() {
    // done
    ciBranchesTableObj.ajax.reload();
    noti.success("<small>Removed branch combination</small>");
  }, function(reason, msg) {
    //fail
    noti.fail(reason, "The branch combination for CI was not deleted.<br/>"+msg);
  }, function() {
    // always
    self.removeAttr("disabled");
  });
}
