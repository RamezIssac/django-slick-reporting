/**
 * Created by ramez on 2/5/15.
 * A wrapper around Datatables.net
 *
 */


(function ($) {
    let _cache = {};
    let _instances = {}


    function constructTable(css_class, cols, cols_names, add_footer, total_verbose, total_fields, data) {
        // Construct an HTML table , header and footer , without a body as it is filled by th datatable.net plugin
        cols = typeof cols != 'undefined' ? cols : false;
        cols_names = typeof cols_names != 'undefined' ? cols_names : cols;

        let return_val = `<table class="${css_class}"> <thead><tr>`;
        let header_th = '';
        let footer_th = '';
        let footer_colspan = 0;
        let stop_colspan_detection = false;
        let totals_container = $.slick_reporting.calculateTotalOnObjectArray(data, total_fields);
        if (data.length <= 1) {
            add_footer = false;
        }

        for (let i = 0; i < cols.length; i++) {
            let col_name = cols[i].name;
            header_th += `<th data-id="${col_name}">${cols_names[i]}</th>`;
            if (total_fields.indexOf(col_name) !== -1) {
                stop_colspan_detection = true;
            }
            if (!stop_colspan_detection) {
                footer_colspan += 1;
            } else {
                let column_total = totals_container[col_name]
                if (!(column_total || column_total === 0)) {
                    column_total = ''
                }
                footer_th += `<th data-id=${col_name}">${column_total}</th>`;
            }
        }
        let footer = '';
        if (add_footer && stop_colspan_detection) {
            footer = '<tfoot><tr class="tr-totals active"><th colspan="' + footer_colspan + '" style="text-align:left">' + total_verbose + '</th>' + footer_th + '</tr></tfoot>';
        }
        return_val = return_val + header_th + `</tr> </thead>${footer}</table>`;
        return return_val;
    }


    function buildAndInitializeDataTable(data, $elem, extraOptions, successFunction) {
        // Responsible for turning a ReportView Response into a datatable.

        let opts = $.extend({}, $.slick_reporting.datatable.defaults, extraOptions);
        opts['datatableContainer'] = $elem;

        let datatable_container = opts.datatableContainer;

        let provide_total = true; // typeof provide_total == 'undefined' ? true : provide_total;
        let total_fields = []; //# frontend_settings.total_fields || [];
        let column_names = [];
        for (let i = 0; i < data['columns'].length; i++) {
            let col = data['columns'][i];
            column_names.push(col['verbose_name']);
            if (col['is_summable'] === true) {
                total_fields.push(col['name'])
            }
        }

        if (total_fields.length === 0) provide_total = false;

        datatable_container.html(constructTable(
            $.slick_reporting.datatable.defaults.tableCssClass, data['columns'], column_names,
            provide_total, opts.messages.total, total_fields, data.data));
        initializeReportDatatable(datatable_container.find('table'), data, opts);

        if (typeof (successFunction) === 'function') {
            successFunction(data);
        }

    }


    function getDatatableColumns(data) {
        let columns = [];
        for (let i = 0; i < data['columns'].length; i++) {

            let server_data = data['columns'][i];
            let col_data = {
                "data": server_data['name'],
                'visible': server_data['visible'],
                'title': server_data['verbose_name']
            };
            columns.push(col_data);

        }
        return columns;
    }


    function initializeReportDatatable(tableSelector, data, extraOptions) {
        tableSelector = typeof tableSelector != 'undefined' ? tableSelector : '.datatable';
        extraOptions = typeof extraOptions != 'undefined' ? extraOptions : {};

        let opts = $.extend({}, $.slick_reporting.datatable.defaults, extraOptions);


        let dom = typeof (extraOptions.dom) == 'undefined' ? 'lfrtip' : extraOptions.dom;
        let paging = typeof (extraOptions.paging) == 'undefined' ? true : extraOptions.paging;
        let ordering = typeof (extraOptions.ordering) == 'undefined' ? true : extraOptions.ordering;
        let info = typeof (extraOptions.info) == 'undefined' ? true : extraOptions.info;
        let searching = typeof (extraOptions.searching) == 'undefined' ? true : extraOptions.searching;
        if (data.data.length === 0) dom = '<"mb-20"t>';

        let datatableOptions = $.extend({}, extraOptions['datatableOptions']);

        datatableOptions.dom = dom;
        datatableOptions.ordering = ordering;
        datatableOptions.paging = paging;
        datatableOptions.info = info;
        datatableOptions.searching = searching;

        datatableOptions.sorting = [];
        datatableOptions.processing = true;
        datatableOptions.data = data['data'];
        datatableOptions.columns = getDatatableColumns(data);
        datatableOptions.initComplete = function (settings, json) {
            setTimeout(function () {
                if (opts.enableFixedHeader) {
                    new $.fn.dataTable.FixedHeader(dt, {"zTop": "2001"});
                }
            }, 100);

        };
        _instances[data.report_slug] = $(tableSelector).DataTable(datatableOptions);
    }


    $.slick_reporting.datatable = {
        initializeDataTable: initializeReportDatatable,
        _cache: _cache,
        buildAdnInitializeDatatable: buildAndInitializeDataTable,
        constructTable: constructTable,
        instances: _instances
    }
}(jQuery));

$.slick_reporting.datatable.defaults = {

    enableFixedHeader: false,
    fixedHeaderZindex: 2001,
    messages: {
        total: $.slick_reporting.defaults.total_label,
    },
    tableCssClass: 'table table-xxs datatable-basic table-bordered table-striped table-hover ',

    datatableOptions: { // datatables options sent to its constructor.
        css_class: 'display'

    }
};