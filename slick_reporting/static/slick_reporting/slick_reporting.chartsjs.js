// type / title_source / data_source,
// title

(function ($) {


    var COLORS = ['#7cb5ec', '#f7a35c', '#90ee7e', '#7798BF', '#aaeeee', '#ff0066', '#eeaaee', '#55BF3B', '#DF5353', '#7798BF', '#aaeeee'];

    let _chart_cache = {};

    function is_time_series(response, chartOptions) {
        if (chartOptions.time_series_support === false) return false;
        return response['metadata']['time_series_pattern'] !== "";
    }

    function is_crosstab(response, chartOptions) {
        return response['metadata']['crosstab_model'] || '';
    }

    function getTimeSeriesColumnNames(response) {
        return response['metadata']['time_series_column_names'];
    }

    function createChartObject(response, chartOptions, extraOptions) {
        let extractedData = extractDataFromResponse(response, chartOptions);

        // Chart.js has no 'area' type; use 'line' with fill
        let chartType = chartOptions.type;
        let fillArea = false;
        if (chartType === 'area') {
            chartType = 'line';
            fillArea = true;
        }

        let chartObject = {
            type: chartType,
            'data': {
                labels: extractedData.labels,
                datasets: extractedData.datasets,
            },
            'options': {
                'responsive': true,
                plugins: {
                    title: {
                        display: true,
                        text: chartOptions.title,
                    },
                    tooltip: {
                        mode: 'index',
                    },
                },
            }
        };

        if (chartOptions.type === 'pie') {
            chartObject['options'] = {
                responsive: true,
                maintainAspectRatio: true,
                aspectRatio: 2,
                plugins: {
                    title: {
                        display: true,
                        text: chartOptions.title,
                    },
                },
            }
        }
        if (chartOptions.stacking === true) {
            chartObject['options']['scales'] = {
                y: {stacked: true},
                x: {stacked: true},
            }
        }
        if (fillArea) {
            chartObject.data.datasets.forEach(function (ds) {
                ds.fill = true;
            });
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
                txt = $(txt).text() || txt; // the title is an <a tag , we want the text only
                legendResults.push(txt)
            }
            datasetData.push(parseFloat(row[dataFieldName]))
        }
        return {
            'labels': legendResults,
            "series": datasetData,
        }
    }

    function getCrosstabColumnNames(response, chartOptions) {
        let colNames = [];
        let dataFieldName = chartOptions['data_source'];
        if (typeof dataFieldName === 'string') dataFieldName = [dataFieldName];
        dataFieldName.forEach(function (source) {
            response.columns.forEach(function (col) {
                if (col.computation_field === source) {
                    colNames.push(col.name);
                }
            });
        });
        return colNames;
    }

    function extractDataFromResponse(response, chartOptions) {
        let dataFieldName = chartOptions['data_source'];
        let titleFieldName = chartOptions['title_source'];
        let isTimeSeries = is_time_series(response, chartOptions);
        let isCrosstab = is_crosstab(response, chartOptions);
        let datasets = [];
        let legendResults = [];
        let datasetData = [];

        if (isTimeSeries) {
            legendResults = response.metadata['time_series_column_verbose_names'];
            let seriesColNames = getTimeSeriesColumnNames(response);

            // Pie charts on time series should always show totals
            if (chartOptions.type === 'pie') {
                chartOptions.plot_total = true;
            }

            if (chartOptions.plot_total) {
                let results = $.slick_reporting.calculateTotalOnObjectArray(response.data, seriesColNames);
                for (let fieldIdx = 0; fieldIdx < seriesColNames.length; fieldIdx++) {
                    datasetData.push(results[seriesColNames[fieldIdx]])
                }
                datasets.push({
                    label: chartOptions.title,
                    data: datasetData,
                    backgroundColor: getBackgroundColors(),
                    borderColor: getBackgroundColors(),
                    fill: chartOptions.stacking === true,
                })


            } else {

                for (let i = 0; i < response.data.length; i++) {
                    let row = response.data[i];
                    let rowData = [];
                    for (let field = 0; field < seriesColNames.length; field++) {
                        rowData.push(response.data[i][seriesColNames[field]])
                    }
                    let txt = row[titleFieldName];
                    try {
                        txt = $($.parseHTML(txt)).text() || txt;
                    } catch (e) {
                        // title is not HTML, use as-is
                    }
                    datasets.push({
                        label: txt,
                        data: rowData,
                        backgroundColor: getBackgroundColors(i),
                        borderColor: getBackgroundColors(i),
                        fill: chartOptions.stacking === true,
                    })
                }
            }

            return {
                'labels': legendResults,
                'datasets': datasets,
            }
        }

        if (isCrosstab) {
            legendResults = response.metadata['crosstab_column_verbose_names'];
            let crosstabColNames = getCrosstabColumnNames(response, chartOptions);

            if (chartOptions.plot_total) {
                let results = $.slick_reporting.calculateTotalOnObjectArray(response.data, crosstabColNames);
                for (let fieldIdx = 0; fieldIdx < crosstabColNames.length; fieldIdx++) {
                    datasetData.push(results[crosstabColNames[fieldIdx]])
                }
                datasets.push({
                    label: chartOptions.title,
                    data: datasetData,
                    backgroundColor: getBackgroundColors(),
                    borderColor: getBackgroundColors(),
                })
            } else {
                for (let i = 0; i < response.data.length; i++) {
                    let row = response.data[i];
                    let rowData = [];
                    for (let field = 0; field < crosstabColNames.length; field++) {
                        rowData.push(row[crosstabColNames[field]])
                    }
                    let txt = row[titleFieldName];
                    try {
                        txt = $($.parseHTML(txt)).text() || txt;
                    } catch (e) {}
                    datasets.push({
                        label: txt,
                        data: rowData,
                        backgroundColor: getBackgroundColors(i),
                        borderColor: getBackgroundColors(i),
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

        let cache_key = $.slick_reporting.get_xpath($elem) + ":" + data.report_slug + ':' + chartOptions.id;
        try {
            let existing_chart = _chart_cache[cache_key];
            if (typeof (existing_chart) !== 'undefined') {
                existing_chart.destroy();
            }
        } catch (e) {
            console.error(e)
        }

        let chartObject = $.slick_reporting.chartsjs.createChartObject(data, chartOptions);
        let canvas = $elem.find('canvas')[0];
        try {
            _chart_cache[cache_key] = new Chart(canvas, chartObject);
        } catch (e) {
            console.error(e);
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
