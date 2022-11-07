function loadDifferencePlot(url) {
  ajaxCall(url, {}, function(result) {
    // done

    // get min/max
    xMin=1e99;
    xMax=-1e99;
    if(result.current) {
      xMin=Math.min(xMin, result.current[0][0]);
      xMax=Math.max(xMax, result.current[result.current.length-1][0]);
    }
    if(result.reference) {
      xMin=Math.min(xMin, result.reference[0][0]);
      xMax=Math.max(xMax, result.reference[result.reference.length-1][0]);
    }
    
    // prepare signals
    signalSeries=[];
    if(result.reference) {
      signalSeries.push({
        name: 'Reference',
        lineWidth: 2.0,
        color: getComputedStyle(document.documentElement,null).getPropertyValue('--danger'),
        marker: { enabled: false },
        data: result.reference,
      });
    }
    if(result.current) {
      signalSeries.push({
        name: 'Current',
        lineWidth: 1.0,
        color: getComputedStyle(document.documentElement,null).getPropertyValue('--success'),
        marker: { enabled: false },
        data: result.current,
      });
    }
    // plot signals
    if(result.current || result.reference) {
      Highcharts.chart('signal', {
        boost: {
          seriesThreshold: 1,
        },
        chart: {
          zoomType: 'xy',
          seriesBoostThreshold: 100,
          panning: { enabled: true, type: 'xy' },
          panKey: 'ctrl',
        },
        plotOptions: { series: { states: { inactive: { opacity: 1.0 }}}},
        title: { text: 'Signal' },
        xAxis: { title: { text: 'Time [s]' } },
        yAxis: { title: { text: 'Value' } },
        series: signalSeries,
      });
    }
    else {
      $("#signal").text("No signal plot available since neither a current nor a reference signal found.").
                   addClass("alert alert-warning");
    }

    if(result.abs) {
      Highcharts.chart('signalAbs', {
        boost: {
          seriesThreshold: 1,
        },
        chart: {
          zoomType: 'xy',
          seriesBoostThreshold: 100,
          panning: { enabled: true, type: 'xy' },
          panKey: 'ctrl',
        },
        plotOptions: { series: { states: { inactive: { opacity: 1.0 }}}},
        title: { text: 'Absolute Error' },
        xAxis: { title: { text: 'Time [s]' } },
        yAxis: { title: { text: 'Abs. err.' } },
        series: [{
          name: 'Absolute error',
          lineWidth: 2.0,
          color: getComputedStyle(document.documentElement,null).getPropertyValue('--info'),
          marker: { enabled: false },
          data: result.abs,
        }, {
          name: 'Absolute tolerance',
          lineWidth: 0.5,
          color: getComputedStyle(document.documentElement,null).getPropertyValue('--secondary'),
          marker: { enabled: false },
          data: [[xMin,2e-5],[xMax,2e-5]],
        }],
      });
    }
    else {
      $("#signalAbs").text("No absolute tolerance plot available since not both signals found or the time data of both channels differ in size and/or datapoints.").
                      addClass("alert alert-warning");
    }

    if(result.rel) {
      Highcharts.chart('signalRel', {
        boost: {
          seriesThreshold: 1,
        },
        chart: {
          zoomType: 'xy',
          seriesBoostThreshold: 100,
          panning: { enabled: true, type: 'xy' },
          panKey: 'ctrl',
        },
        plotOptions: { series: { states: { inactive: { opacity: 1.0 }}}},
        title: { text: 'Relative Error' },
        xAxis: { title: { text: 'Time [s]' } },
        yAxis: { title: { text: 'Rel. err.' } },
        series: [{
          name: 'Relative error',
          lineWidth: 2.0,
          color: getComputedStyle(document.documentElement,null).getPropertyValue('--info'),
          marker: { enabled: false },
          data: result.rel,
        }, {
          name: 'Relative tolerance',
          lineWidth: 0.5,
          color: getComputedStyle(document.documentElement,null).getPropertyValue('--secondary'),
          marker: { enabled: false },
          data: [[xMin,2e-5],[xMax,2e-5]],
        }],
      });
    }
    else {
      $("#signalRel").text("No relative tolerance plot available since not both signals found or the time data of both channels differ in size and/or datapoints.").
                      addClass("alert alert-warning");
    }
  }, function(reason, msg) {
    //fail
    alert("Internal error in AJAX call loadDifferencePlot: "+reason+": "+msg);
  });
}
