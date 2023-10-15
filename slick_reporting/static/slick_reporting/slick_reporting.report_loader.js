/*jshint esversion: 6 */

/**
 * Created by ramezashraf on 13/08/16.
 */

(function ($) {
    let settings = {};

    function failFunction(data, $elem) {
        if (data.status === 403) {
            $elem.hide()
        } else {
            console.log(data, $elem)
        }
    }

    function loadComponents(data, $elem) {
        let chartElem = $elem.find('[data-report-chart]');
        let chart_id = $elem.attr('data-chart-id');
        let display_chart_selector = $elem.attr('data-display-chart-selector');
        if (chartElem.length !== 0 && data.chart_settings.length !== 0) {

            $.slick_reporting.report_loader.displayChart(data, chartElem, chart_id);
        }

        if (display_chart_selector !== "False" && data.chart_settings.length > 1) {
            $.slick_reporting.report_loader.createChartsUIfromResponse(data, $elem);
        }

        let tableElem = $elem.find('[data-report-table]');
        if (tableElem.length !== 0) {
            $.slick_reporting.datatable.buildAdnInitializeDatatable(data, tableElem);
        }

    }

    function displayChart(data, $elem, chart_id) {
        let engine = "highcharts";
        let chartOptions = $.slick_reporting.getObjFromArray(data.chart_settings, 'id', chart_id, true);
        let entryPoint = chartOptions.entryPoint || $.slick_reporting.report_loader.chart_engines[engine];
        $.slick_reporting.executeFunctionByName(entryPoint, window, data, $elem, chartOptions);
    }


    function refreshReportWidget($elem, extra_params) {
        let successFunctionName = $elem.attr('data-success-callback');
        successFunctionName = successFunctionName || "$.slick_reporting.report_loader.successCallback";
        let failFunctionName = $elem.attr('data-fail-callback');
        failFunctionName = failFunctionName || "$.slick_reporting.report_loader.failFunction";

        let data = {};

        let url = $elem.attr('data-report-url');
        extra_params = extra_params || ''
        let extraParams = extra_params + ($elem.attr('data-extra-params') || '');

        let formSelector = $elem.attr('data-form-selector');
        if (formSelector) {
            data = $(formSelector).serialize();
        } else {
            if (url === '#') return; // there is no actual url, probably not enough permissions

            if (extraParams !== '') {
                url = url + "?" + extraParams;
            }

        }

        $.get(url, data, function (data) {
            $.slick_reporting.cache[data['report_slug']] = jQuery.extend(true, {}, data);
            $.slick_reporting.executeFunctionByName(successFunctionName, window, data, $elem);
        }).fail(function (data) {
            $.slick_reporting.executeFunctionByName(failFunctionName, window, data, $elem);
        });

    }


    function initialize() {
        settings = JSON.parse(document.getElementById('slick_reporting_settings').textContent);
        let chartSettings = {};
        $('[data-report-widget]').not('[data-no-auto-load]').each(function (i, elem) {
            refreshReportWidget($(elem));
        });

        Object.keys(settings["CHARTS"]).forEach(function (key) {
            chartSettings[key] = settings.CHARTS[key].entryPoint;
        })
        $.slick_reporting.report_loader.chart_engines = chartSettings;
        try {
            $("select").select2();
        } catch (e) {
            console.error(e);
        }
        $.slick_reporting.defaults.total_label = settings["MESSAGES"]["TOTAL_LABEL"];
    }

    function _get_chart_icon(chart_type) {
        try {
            return "<i class='" + settings.FONT_AWESOME.ICONS[chart_type] + "'></i>";
        } catch (e) {
            console.error(e);
        }
        return '';
    }

    function createChartsUIfromResponse(data, $elem, a_class) {
        a_class = typeof a_class == 'undefined' ? 'groupChartController' : a_class;
        let $container = $('<div></div>');

        let chartList = data['chart_settings'];
        let report_slug = data['report_slug'];
        $elem.find('.groupChartControllers').remove();
        if (chartList.length !== 0) {
            $container.append('<div class="groupChartControllers">' +
                '<ul class="nav nav-charts"></ul></div>');
        }
        var ul = $container.find('ul');
        for (var i = 0; i < chartList.length; i++) {
            var icon;
            var chart = chartList[i];
            if (chart.disabled) continue;

            let chart_type = chart.type;
            icon = _get_chart_icon(chart_type);

            ul.append('<li class="nav-link"><a href class="' + a_class + '" data-chart-id="' + chart.id + '" ' +
                'data-report-slug="' + report_slug + '">' + icon + ' ' + chart.title + '</a></li>')
        }
        $elem.prepend($container)
        return $container
    }


    jQuery(document).ready(function () {
        $.slick_reporting.report_loader.initialize();
        $('body').on('click', 'a[data-chart-id]', function (e) {
            e.preventDefault();
            let $this = $(this);
            let data = $.slick_reporting.cache[$this.attr('data-report-slug')]
            let chart_id = $this.attr('data-chart-id')
            $.slick_reporting.report_loader.displayChart(data, $this.parents('[data-report-widget]').find('[data-report-chart]'), chart_id)

        });

        $('[data-export-btn]').on('click', function (e) {
            let $elem = $(this);
            e.preventDefault()
            let form = $($elem.attr('data-form-selector'));
            window.location = '?' + form.serialize() + '&_export=' + $elem.attr('data-export-parameter');
        });
        $('[data-get-results-button]').not(".vanilla-btn-flag").on('click', function (event) {
            event.preventDefault();
            let $elem = $('[data-report-widget]')
            $.slick_reporting.report_loader.refreshReportWidget($elem)
        });

    });


    $.slick_reporting.report_loader = {
        cache: $.slick_reporting.cache,
        // "extractDataFromResponse": extractDataFromResponse,
        initialize: initialize,
        refreshReportWidget: refreshReportWidget,
        failFunction: failFunction,
        displayChart: displayChart,
        createChartsUIfromResponse: createChartsUIfromResponse,
        successCallback: loadComponents,

    }
})(jQuery);