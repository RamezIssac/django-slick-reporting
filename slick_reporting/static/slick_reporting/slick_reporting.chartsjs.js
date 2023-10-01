// type / title_source / data_source,
// title

(function ($) {


    var COLORS = ['#7cb5ec', '#f7a35c', '#90ee7e', '#7798BF', '#aaeeee', '#ff0066', '#eeaaee', '#55BF3B', '#DF5353', '#7798BF', '#aaeeee'];

    let _chart_cache = {};

    function is_time_series(response, chartOptions) {
        if (chartOptions.time_series_support === false) return false;
        return response['metadata']['time_series_pattern'] !== ""
    }

    function getTimeSeriesColumnNames(response) {
        return response['metadata']['time_series_column_names'];
    }

    function createChartObject(response, chartOptions, extraOptions) {
        // let chartOptions = $.slick_reporting.getObjFromArray(response.chart_settings, 'id', chartId, true);
        let extractedData = extractDataFromResponse(response, chartOptions);

        let chartObject = {
            type: chartOptions.type,
            'data': {
                labels: extractedData.labels,
                datasets: extractedData.datasets,

                // datasets: [{
                //     'label': chartOptions.title,
                //     // 'label': extractedData.labels,
                //     'data': extractedData.data,
                //     'borderWidth': 1,
                //
                //     backgroundColor: [
                //         window.chartColors.red,
                //         window.chartColors.orange,
                //         window.chartColors.yellow,
                //         window.chartColors.green,
                //         window.chartColors.blue,
                //     ],
                // }]
            },
            'options': {
                'responsive': true,
                title: {
                    display: true,
                    text: chartOptions.title,
                },
                tooltips: {
                    mode: 'index',
                    // intersect: false
                },
            }
        };

        if (chartOptions.type === 'pie') {
            chartObject['options'] = {
                responsive: true,
            }
        }
        if (chartOptions.stacked === true) {
            chartObject['options']['scales'] = {
                yAxes: [{stacked: true,}],
                XAxes: [{stacked: true,}],
            }
        }
        return chartObject
    }

    function getGroupByLabelAndSeries(response, chartOptions) {

        let legendResults = [];
        let datasetData = [];
        let dataFieldName = chartOptions['data_source'];
        let titleFieldName = chartOptions['title_source'];

        for (let i = 0; i < response.data.length; i++) {
            let row = response.data[i];
            if (titleFieldName !== '') {
                let txt = row[titleFieldName];
                txt = $(txt).text() || txt; // the title is an <a tag , we want teh text only
                legendResults.push(txt)
            }
            datasetData.push(row[dataFieldName])
        }
        return {
            'labels': legendResults,
            "series": datasetData,
        }
    }

    function extractDataFromResponse(response, chartOptions) {
        let dataFieldName = chartOptions['data_source'];
        let titleFieldName = chartOptions['title_source'];
        let isTimeSeries = is_time_series(response, chartOptions);
        let datasets = [];
        let legendResults = [];
        let datasetData = [];

        if (isTimeSeries) {
            legendResults = response.metadata['time_series_column_verbose_names'];
            let seriesColNames = getTimeSeriesColumnNames(response);

            if (chartOptions.plot_total) {
                let results = $.slick_reporting.calculateTotalOnObjectArray(response.data, seriesColNames);
                for (let fieldIdx = 0; fieldIdx < seriesColNames.length; fieldIdx++) {
                    datasetData.push(results[seriesColNames[fieldIdx]])
                }
                datasets.push({
                    label: chartOptions.title,
                    data: datasetData,
                    backgroundColor: getBackgroundColors(1),
                    borderColor: getBackgroundColors(1),
                    fill: chartOptions.stacked === true,
                })


            } else {

                for (let i = 0; i < response.data.length; i++) {
                    let row = response.data[i];
                    let rowData = [];
                    for (let field = 0; field < seriesColNames.length; field++) {
                        rowData.push(response.data[i][seriesColNames[field]])
                    }
                    datasets.push({
                        label: $($.parseHTML(row[titleFieldName])).text(),
                        data: rowData,
                        backgroundColor: getBackgroundColors(i),
                        borderColor: getBackgroundColors(i),
                        fill: chartOptions.stacked === true,
                    })
                }
            }

            return {
                'labels': legendResults,
                'datasets': datasets,
            }
        }
        let results = getGroupByLabelAndSeries(response, chartOptions);
        datasets = [{
            data: results.series,
            backgroundColor: getBackgroundColors(),
            label: chartOptions.title
        }];
        return {
            'labels': results.labels,
            'datasets': datasets,
        }
    }

    function getBackgroundColors(i) {
        if (typeof (i) !== 'undefined') {
            return COLORS[i]
        }
        return COLORS
    }

    function displayChart(data, $elem, chartOptions) {
        // chart_id = chart_id || $elem.attr('data-report-default-chart') || '';
        if ($elem.find('canvas').length === 0) {
            $elem.append("<canvas width=\"400\" height=\"100\"></canvas>");
        }

        let cache_key = data.report_slug
        try {
            let existing_chart = _chart_cache[cache_key];
            if (typeof (existing_chart) !== 'undefined') {
                existing_chart.destroy();
            }
        } catch (e) {
            console.error(e)
        }

        let chartObject = $.slick_reporting.chartsjs.createChartObject(data, chartOptions);
        let $chart = $elem.find('canvas');
        try {
            _chart_cache[cache_key] = new Chart($chart, chartObject);
        } catch (e) {
            $elem.find('canvas').remove();
        }


    }


    if (typeof ($.slick_reporting) === 'undefined') {
        $.slick_reporting = {}
    }
    $.slick_reporting.chartsjs = {
        getGroupByLabelAndSeries: getGroupByLabelAndSeries,
        createChartObject: createChartObject,
        displayChart: displayChart,
        defaults: {
            // normalStackedTooltipFormatter: normalStackedTooltipFormatter,
            messages: {
                noData: 'No Data to display ... :-/',
                total: 'Total',
                percent: 'Percent',
            },
            credits: {
                // text: 'RaSystems.io',
                // href: 'https://rasystems.io'
            },
            notify_error: function () {
            },
            enable3d: false,

        }
    };

}(jQuery));