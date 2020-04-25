/**
 * Created by ramez on 2/5/15.
 * A wrapper around Datatables.net
 *
 */


(function ($) {
    var _cache = {};

    function provideGroupSupport(cols) {
        return cols.indexOf('_control_') != -1;
    }

    function isTotalField(field_name, total_fields) {
        // return false; //todo
        total_fields = total_fields || [];
        if (total_fields.indexOf(field_name) != -1) {
            return true;
        } else {
            return field_name.substring(0, 2) == '__';
        }
    }


    function constructTable(id, css_class, cols, cols_names, add_footer, total_verbose, total_fields) {
        // Construct an HTML table , header and footer , without a body as it is filled by th datatable.net plugin
        id = typeof id != 'undefined' ? id : 'mytable';
        cols = typeof cols != 'undefined' ? cols : false;
        cols_names = typeof cols_names != 'undefined' ? cols_names : cols;

        var return_val = '<table class="' + css_class + '"  width="98%" > <thead>' +
            '<tr>';

        var header_th = '';
        var footer_th = '';
        var footer_colspan = 0;
        var stop_colspan_detection = false;
        for (var i = 0; i < cols.length; i++) {
            header_th += '<th data-id="' + cols[i] + '">' + cols_names[i] + '</th>';
            if (isTotalField(cols[i], total_fields)) {
                stop_colspan_detection = true;
            }
            if (stop_colspan_detection == false) {
                footer_colspan += 1;
            } else {
                footer_th += '<th data-id="' + cols[i] + '"></th>';
            }
        }
        var footer = '';
        if (add_footer == true && stop_colspan_detection == true) {
            footer = '<tfoot><tr class="tr-totals active"><th colspan="' + footer_colspan + '" style="text-align:left">' + total_verbose + ':</th>' + footer_th + '</tr></tfoot>';
        }
        return_val = return_val + header_th +
            '</tr>' +
            '</thead>' + footer +
            '</table>';

        return return_val;
    }

    function _get_group_by(data, opts) {
        try {
            return data['form_settings'][opts.GROUP_BY_FIELD_NAME]
        } catch (err) {
            return 'group_by';
        }
    }

    function buildAndInitializeDataTable(data, $elem, extraOptions, successFunction) {
        let isGroup = true;
        var opts = $.extend({}, $.slick_reporting.datatable.defaults, extraOptions);
        opts['datatableContainer'] = $elem;

        var datatable_container = opts.datatableContainer;
        var datatableOptions = opts.datatableOptions;
        var form_settings = data['form_settings'] || {};
        var frontend_settings = form_settings['frontend_settings'] || {};
        var provide_total = frontend_settings.provide_total;
        provide_total = typeof provide_total == 'undefined' ? true : provide_total;
        var total_fields = frontend_settings.total_fields || [];
        var column_names = [];
        for (var i = 0; i < data['columns'].length; i++) {
            var col = data['columns'][i];
            column_names.push(col['verbose_name']);
            if (col['type'] === 'number') {
                total_fields.push(col['name'])
            }
        }
        if (data.data.length == 0) provide_total = false;

        _cache['groupData'] = data;
        var datatable_slug = _get_group_by(data, opts);
        datatable_container.html(constructTable(datatable_slug + 'groupTable', $.slick_reporting.datatable.defaults.tableCssClass, data['columns'], column_names, provide_total, opts.messages.total, total_fields));
        initializeReportDatatable(datatable_container.find('table'), data, isGroup, opts);

        // }

        if (typeof (successFunction) === 'function') {
            successFunction(data);
        }

    }


    function getDatatableColumns(isGroup, data) {
        // isGroup = data['columns'].indexOf('_control_') != -1;
        isGroup = false;
        var columns = [];
        if (isGroup === true) {
            columns = [
                {
                    "class": 'details-control',
                    "orderable": false,
                    "data": null,
                    "defaultContent": ''
                }
            ];
        }
        try {
            var hide_columns = data['form_settings']['hide_columns'] || [];
        } catch (exp) {
            hide_columns = [];
        }
        for (var i = 0; i < data['columns'].length; i++) {
            if ((isGroup && i > 0) || !isGroup) {
                var server_data = data['columns'][i];
                var col_data = {
                    "data": server_data['name'],
                    'visible': server_data['visible'],
                    'title': server_data['verbose_name']
                };
                // col_data['visible'] =
                // if (data['columns'][i].indexOf('_id') > -1) col_data['visible'] = false;
                // if (data['columns'][i].indexOf('doc_typeid') > -1) col_data['visible'] = false;
                // if (hide_columns.indexOf(data['columns'][i]) > -1) col_data['visible'] = false;
                columns.push(col_data);
            }
        }
        return columns;
    }

    function createChildTable(row, current_id, group_by, opts) {
        // Create s sub table inside the row

        var datatableOptions = {'container': row, current_id: current_id, group_by: group_by};
        var _para = {};
        _para[group_by] = current_id;
        var url = opts.ajax_url;
        url += '&' + $.param(_para);
        $.slick_reporting.report_loader.getDataFromServer(url, function (data) {
            var datatable_container = datatableOptions.container;
            var slug = datatableOptions.current_id;
            datatable_container.child('<div class="inner_table"> ' + constructTable(slug, $.slick_reporting.datatable.defaults.tableCssClass, data['columns'], column_names, true, opts.messages.total) + ' </div> ').show();
            initializeReportDatatable(datatable_container.child().find('table'), data, provideGroupSupport(data['columns']));
        });

        $(window).scroll();
    }

    function createTableInModal(row, current_id, group_by, opts) {
        var reportModal = $('#reportSub');
        var container = reportModal.find('.reportTableContainer');
        container.html('');
        reportModal.find('.reportChart').html('');
        var datatableOptions = {'container': container, current_id: current_id, group_by: group_by};
        var _para = {};
        _para[group_by] = current_id;
        var url = opts.ajax_url;
        url += '&' + $.param(_para);
        $.slick_reporting.report_loader.getDataFromServer(url, function (data) {
            var datatable_container = datatableOptions.container;
            var slug = datatableOptions.current_id;
            datatable_container.html('<div class="inner_table"> ' + constructTable(slug, $.slick_reporting.datatable.defaults.tableCssClass + ' display', data['columns'], column_names, true, opts.messages.total) + ' </div> ').show();
            initializeReportDatatable(datatable_container.find('table'), data, provideGroupSupport(data['columns']));
            reportModal.find('.chartContainer .controls').html($.slick_reporting.report_loader.createChartsUIfromResponse(data, 'inModalChart'));
            reportModal.attr('data-current-id', current_id);
            reportModal.attr('data-report-slug', data['report_slug']);
            reportModal.attr('data-report-url', url);

            $.slick_reporting.cache[data['report_slug'] + current_id] = data;
            reportModal.modal('show');
            setTimeout(function () {
                reportModal.find('.groupChartControllers').find('a:first').trigger('click');
            }, 200)

        });

    }


    function attachDetailsControlHandler($datatable, data, opts) {
        //    Provide the datatable grouping (expandable rows) #}
        //    Set the click event #}

        $datatable.find('tbody').on('click', 'td.details-control', function () {

            var table = $datatable.DataTable({retrieve: true});
            var tr = $(this).parents('tr');
            var row = table.row(tr);
            var group_by = _get_group_by(data, opts);
            if (!(group_by == 'slug' || group_by == 'doc_date' || group_by == 'doc_type')) {
                group_by = group_by + '_id'; //todo: Show be edited to _id
            }
            var current_id = row.data()[group_by];
            executeFunctionByName(opts.createChildTableFunctionName, window, row, current_id, group_by, opts);

        });

    }


    function apply_table_totals(all_data, opts, $datatable, total_fields) {
        var data = all_data.data;
        var total_fields_existing = [];
        var cols = all_data.columns;
        var INT_FIELDS = opts.intFields;

        //if (provide_total == false) {
        //    return
        //}
        if (data.length == 0) {
            $datatable.find('tfoot th:first').text('');
            return;
        }

        // Get existing total field on report
        for (var x = 0; x < cols.length; x++) {
            if (isTotalField(cols[x], total_fields)) {
                total_fields_existing.push(cols[x]);
            }
        }

        //calculate the total
        var total_container = calculateTotalOnObjectArray(data, total_fields_existing);

        //apply totals to datatable footer
        for (var f = 0; f < total_fields_existing.length; f++) {
            //console.log(total_fields_existing[f], total_container[total_fields_existing[f]]);
            var _total = total_container[total_fields_existing[f]];
            if (typeof _total != 'undefined') {
                if (INT_FIELDS.indexOf(total_fields_existing[f]) == -1)
                    _total = numberWithCommas(_total.toFixed(2));
                else
                    _total = numberWithCommas(_total);
            }
            $datatable.find('tfoot [data-id="' + total_fields_existing[f] + '"]').html(_total);
        }

    }

    function destroyAllFixedHeaders() {
        $('.fixedHeader').remove();
    }

    function initializeReportDatatable(tableSelector, data, isGroup, extraOptions) {
        tableSelector = typeof tableSelector != 'undefined' ? tableSelector : '.datatable';
        extraOptions = typeof extraOptions != 'undefined' ? extraOptions : {};

        var opts = $.extend({}, $.slick_reporting.datatable.defaults, extraOptions);

        var form_settings = data['form_settings'] || {};
        var frontend_settings = form_settings['frontend_settings'] || {};
        var provide_total = frontend_settings.provide_total;
        provide_total = typeof provide_total == 'undefined' ? true : provide_total;
        var total_fields = frontend_settings.total_fields || [];

        var dom = typeof (extraOptions.dom) == 'undefined' ? 'lfrtip' : extraOptions.dom;
        var paging = typeof (extraOptions.paging) == 'undefined' ? true : extraOptions.paging;
        var ordering = typeof (extraOptions.ordering) == 'undefined' ? true : extraOptions.ordering;
        var info = typeof (extraOptions.info) == 'undefined' ? true : extraOptions.info;
        if (data.data.length == 0) dom = '<"mb-20"t>';

        var datatableOptions = $.extend({}, extraOptions['datatableOptions']);

        datatableOptions.dom = dom;
        datatableOptions.ordering = ordering;
        datatableOptions.paging = paging;
        datatableOptions.info = info;

        datatableOptions.sorting = [];
        datatableOptions.processing = true;
        datatableOptions.data = data['data'];
        datatableOptions.columns = getDatatableColumns(isGroup, data);
        datatableOptions.initComplete = function (settings, json) {
            if (isGroup == true) {
                setTimeout(function () {
                    attachDetailsControlHandler(tableSelector, data, opts);
                    if (opts.enableFixedHeader) {
                        new $.fn.dataTable.FixedHeader(dt, {"zTop": "2001"});
                    }
                }, 100);
            }
            apply_table_totals(data, opts, tableSelector, total_fields);
        };
        dt = $(tableSelector).DataTable(datatableOptions);
//        dt = $(tableSelector).DataTable({
//            dom: dom,
//            ordering: ordering,
//            paging: paging,
//            info: info,
//
//            sorting: [],
//            processing: true,
//            //scrollX: true,
//            data: data['data'],
////            scrollX:Useless & aye harmful , no on top scroll bar
//            columns: getDatatableColumns(isGroup, data),
//
//            "initComplete": function (settings, json) {
//
//                if (isGroup == true) {
//                    setTimeout(function () {
//                        attachDetailsControlHandler(tableSelector, data, opts);
//                        if (opts.enableFixedHeader) {
//                            new $.fn.dataTable.FixedHeader(dt, {"zTop": "2001"});
//                        }
//                    }, 100);
//                }
//                apply_table_totals(data, opts, tableSelector, total_fields);
//            }
//        });
    }

    function calculateTotalOnObjectArray(data, columns) {
    // Compute totals in array of objects
    // example :
    // calculateTotalOnObjectArray ([{ value1:500, value2: 70} , {value:200, value2:15} ], ['value'])
    // return {'value1': 700, value2:85}

    var total_container = {};
    for (var r = 0; r < data.length; r++) {

        for (var i = 0; i < columns.length; i++) {

            if (typeof total_container[columns[i]] == 'undefined') {
                //console.log('columns i ', columns[i]);
                total_container[columns[i]] = 0;
            }
            var val = data[r][columns[i]];
            if (val == '-') val = 0;

            else if (typeof(val) == 'string') {
                try {
                    val = val.replace(/,/g, '');
                }
                catch (err) {
                    console.log(err, val, typeof(val));
                }
            }
            total_container[columns[i]] += parseFloat(val);
//            {#            console.log(val,parseFloat(val),total_container[columns[i]] )#}
        }
    }
    return total_container;
}


    $.slick_reporting.datatable = {
        initializeDataTable: initializeReportDatatable,
        _cache: _cache,
        buildAdnInitializeDatatable: buildAndInitializeDataTable,
        destroyAllFixedHeaders: destroyAllFixedHeaders,
        isTotalField: isTotalField,
        createChildTable: createChildTable,
        createTableInModal: createTableInModal,
        constructTable: constructTable,
        calculateTotalOnObjectArray:calculateTotalOnObjectArray
    }
}(jQuery));

$.slick_reporting.datatable.defaults = {
    isTotalField: $.slick_reporting.datatable.isTotalField,
    totalComputationFunction: $.slick_reporting.datatable.calculateTotalOnObjectArray,
    createChildTableFunctionName: '$.slick_reporting.datatable.createTableInModal',
    totalFields: ['__balance__', 'value', '__debit__', '__credit__', '__doc_count__', '__line_count__', '__total__', '__fb__',
        '__balance_quan__', 'quan', '__debit_quan__', '__credit_quan__', '__total_quantity__', '__fb_quan__', '__gross_value__', '__tax_addition__', '__tax_substract__', '__doc_value__'],
    intFields: ['__doc_count__'], //apply total to them & format them as int (ie no .00)
    ajax_url: '', // request_url
    GROUP_BY_FIELD_NAME: 'group_by',

    datatableSelector: '#group_report_datatable',
    detailsTableisChild: true,
    enableFixedHeader: false,
    fixedHeaderZindex: 2001,
    messages: {
        total: "Total",
    },
    tableCssClass: 'table table-xxs datatable-basic table-bordered table-striped table-hover ',

    datatableOptions: { // datatables options sent to its constructor.
        css_class: 'display'

    }
};