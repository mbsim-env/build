function loadDifferencePlot(url) {
  ajaxCall(url, {}, function(result) {
    // done
    xMin=result.current[0][0];
    xMax=result.current[result.current.length-1][0];
    
    signalSeries=[];
    if(result.reference) {
      signalSeries.push({
        name: 'Reference',
        lineWidth: 2.0,
        color: "#FF0000",
        marker: { enabled: false },
        data: result.reference,
      });
    }
    signalSeries.push({
      name: 'Current',
      lineWidth: 1.0,
      color: "#00FF00",
      marker: { enabled: false },
      data: result.current,
    });
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
          color: "#0000FF",
          marker: { enabled: false },
          data: result.abs,
        }, {
          name: 'Absolute tolerance',
          lineWidth: 0.5,
          color: "#444444",
          marker: { enabled: false },
          data: [[xMin,2e-5],[xMax,2e-5]],
        }],
      });
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
          color: "#0000FF",
          marker: { enabled: false },
          data: result.rel,
        }, {
          name: 'Relative tolerance',
          lineWidth: 0.5,
          color: "#444444",
          marker: { enabled: false },
          data: [[xMin,2e-5],[xMax,2e-5]],
        }],
      });
    }
  }, function(reason, msg) {
    //fail
    alert("Internal error in AJAX call loadDifferencePlot: "+reason+": "+msg);
  });
}
