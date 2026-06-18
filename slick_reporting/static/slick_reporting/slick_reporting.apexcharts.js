(function ($) {

    let _chart_cache = {};

    function is_timeseries(response, chartOptions) {
        if (chartOptions.time_series_support === false) return false;
        return response.metadata.time_series_pattern || '';
    }

    function is_crosstab(response, chartOptions) {
        return response.metadata.crosstab_model || '';
    }

    function dataArrayToObject(data, key) {
        let output = {};
        for (let i = 0; i < data.length; i++) {
            output[data[i][key]] = data[i];
        }
        return output;
    }

    function stripHtml(txt) {
        try { return $($.parseHTML(txt)).text() || txt; } catch (e) { return txt; }
    }

    function resolveDataSourceCols(response, dataSource) {
        // Returns a map of { sourceField: [matching column names] }
        let sources = Array.isArray(dataSource) ? dataSource : [dataSource];
        let map = {};
        sources.forEach(function (src) {
            map[src] = [];
            response.columns.forEach(function (col) {
                if (col.computation_field === src) map[src].push(col.name);
            });
        });
        return map;
    }

    function get_normal_data(response, chartOptions) {
        let categories = [];
        let seriesData = [];
        let dataSource = Array.isArray(chartOptions.data_source) ? chartOptions.data_source[0] : chartOptions.data_source;
        response.data.forEach(function (row) {
            categories.push(stripHtml(row[chartOptions.title_source]));
            seriesData.push(parseFloat(row[dataSource]) || 0);
        });
        return {
            series: [{name: chartOptions.title, data: seriesData}],
            categories: categories,
        };
    }

    function get_time_series_data(response, chartOptions) {
        let categories = response.metadata.time_series_column_verbose_names;
        let apexSeries = [];
        let colMap = resolveDataSourceCols(response, chartOptions.data_source);
        let allCols = Object.values(colMap).reduce(function (a, b) { return a.concat(b); }, []);

        if (chartOptions.plot_total) {
            let totals = $.slick_reporting.calculateTotalOnObjectArray(response.data, allCols);
            apexSeries.push({
                name: chartOptions.title,
                data: allCols.map(function (col) { return parseFloat(totals[col]) || 0; }),
            });
        } else {
            response.data.forEach(function (row) {
                let data = [];
                allCols.forEach(function (col) { data.push(parseFloat(row[col]) || 0); });
                apexSeries.push({name: stripHtml(row[chartOptions.title_source]), data: data});
            });
        }
        return {series: apexSeries, categories: categories};
    }

    function get_crosstab_data(response, chartOptions) {
        let categories = response.metadata.crosstab_column_verbose_names;
        let apexSeries = [];
        let colMap = resolveDataSourceCols(response, chartOptions.data_source);
        let allCols = Object.values(colMap).reduce(function (a, b) { return a.concat(b); }, []);
        let colDict = dataArrayToObject(response.columns, 'name');

        if (chartOptions.plot_total) {
            let totals = $.slick_reporting.calculateTotalOnObjectArray(response.data, allCols);
            allCols.forEach(function (col) {
                apexSeries.push({name: colDict[col].verbose_name, data: [parseFloat(totals[col]) || 0]});
            });
        } else {
            response.data.forEach(function (row) {
                let data = [];
                allCols.forEach(function (col) { data.push(parseFloat(row[col]) || 0); });
                apexSeries.push({name: stripHtml(row[chartOptions.title_source]), data: data});
            });
        }
        return {series: apexSeries, categories: categories};
    }

    function createChartObject(response, chartOptions) {
        let chartType = chartOptions.type || 'bar';

        if (chartType === 'pie') {
            let pieData = is_timeseries(response, chartOptions)
                ? (function () {
                    let colMap = resolveDataSourceCols(response, chartOptions.data_source);
                    let allCols = Object.values(colMap).reduce(function (a, b) { return a.concat(b); }, []);
                    let totals = $.slick_reporting.calculateTotalOnObjectArray(response.data, allCols);
                    return {
                        series: allCols.map(function (col) { return parseFloat(totals[col]) || 0; }),
                        labels: response.metadata.time_series_column_verbose_names,
                    };
                })()
                : (function () {
                    let src = Array.isArray(chartOptions.data_source) ? chartOptions.data_source[0] : chartOptions.data_source;
                    let series = [], labels = [];
                    response.data.forEach(function (row) {
                        labels.push(stripHtml(row[chartOptions.title_source]));
                        series.push(parseFloat(row[src]) || 0);
                    });
                    return {series: series, labels: labels};
                })();

            return {
                chart: {type: 'pie', height: 400},
                series: pieData.series,
                labels: pieData.labels,
                title: {text: chartOptions.title},
                legend: {position: 'bottom'},
                responsive: [{breakpoint: 480, options: {legend: {position: 'bottom'}}}],
            };
        }

        let data = is_timeseries(response, chartOptions)
            ? get_time_series_data(response, chartOptions)
            : is_crosstab(response, chartOptions)
                ? get_crosstab_data(response, chartOptions)
                : get_normal_data(response, chartOptions);

        // ApexCharts uses 'bar' for both bar and column; horizontal flag distinguishes them
        let apexType = (chartType === 'column' || chartType === 'bar') ? 'bar' : chartType;

        let options = {
            chart: {
                type: apexType,
                height: 400,
                toolbar: {show: true},
                stacked: chartOptions.stacking ? true : false,
            },
            series: data.series,
            xaxis: {categories: data.categories},
            title: {text: chartOptions.title},
            dataLabels: {enabled: false},
            tooltip: {shared: true, intersect: false},
        };

        if (chartType === 'column') {
            options.plotOptions = {bar: {horizontal: false, borderRadius: 2}};
        } else if (chartType === 'bar') {
            options.plotOptions = {bar: {horizontal: true, borderRadius: 2}};
        } else if (chartType === 'area') {
            options.stroke = {curve: 'smooth', width: 2};
            options.fill = {type: 'gradient', gradient: {shadeIntensity: 1, opacityFrom: 0.5, opacityTo: 0.1}};
        } else if (chartType === 'line') {
            options.stroke = {curve: 'smooth', width: 2};
        }

        return options;
    }

    function displayChart(data, $elem, chartOptions) {
        if ($elem.find('[data-inner-chart-container]').length === 0) {
            $elem.append('<div data-inner-chart-container style="width:100%;min-height:400px;"></div>');
        }
        let container = $elem.find('[data-inner-chart-container]')[0];
        let cache_key = $.slick_reporting.get_xpath($elem) + ':' + data.report_slug + ':' + (chartOptions.id || '');

        try {
            let existing = _chart_cache[cache_key];
            if (typeof existing !== 'undefined') {
                existing.destroy();
                delete _chart_cache[cache_key];
            }
        } catch (e) { console.error(e); }

        let apexOptions = $.slick_reporting.apexcharts.createChartObject(data, chartOptions);
        try {
            let chart = new ApexCharts(container, apexOptions);
            chart.render();
            _chart_cache[cache_key] = chart;
        } catch (e) { console.error(e); }
    }

    if (typeof $.slick_reporting === 'undefined') { $.slick_reporting = {}; }
    $.slick_reporting.apexcharts = {
        createChartObject: createChartObject,
        displayChart: displayChart,
    };

}(jQuery));
