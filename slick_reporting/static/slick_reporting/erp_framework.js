/**
 * Created by ramez on 1/5/15.
 */



function parseArabicNumbers(str) {
    str = typeof str == 'undefined' ? '0' : str;
    return Number(str.replace(/[٠١٢٣٤٥٦٧٨٩]/g, function (d) {
        return d.charCodeAt(0) - 1632;
    }).replace(/[۰۱۲۳۴۵۶۷۸۹]/g, function (d) {
        return d.charCodeAt(0) - 1776;
    }));
}


function calculateTotalOnObjectArray(data, columns) {
    // Compute totals in array of objects
    // example :
    // calculateTotalOnObjectArray ([{ value1:500, value2: 70} , {value1:200, value2:15} ], ['value'])
    // return {'value1': 700, value2:85}

    let total_container = {};
    for (let r = 0; r < data.length; r++) {

        for (let i = 0; i < columns.length; i++) {
            if (typeof total_container[columns[i]] == 'undefined') {
                total_container[columns[i]] = 0;
            }
            let val = data[r][columns[i]];
            if (val === '-') val = 0;

            else if (typeof (val) == 'string') {
                try {
                    val = val.replace(/,/g, '');
                } catch (err) {
                    console.log(err, val, typeof (val));
                }
            }
            total_container[columns[i]] += parseFloat(val);
        }
    }
    return total_container;
}

function executeFunctionByName(functionName, context /*, args */) {
    let args = Array.prototype.slice.call(arguments, 2);
    let namespaces = functionName.split(".");
    let func = namespaces.pop();
    for (let i = 0; i < namespaces.length; i++) {
        context = context[namespaces[i]];
    }
    try {
        func = context[func];
        if (typeof func == 'undefined') {
            throw 'Function {0} is not found the context {1}'.format(functionName, context);
        }

    } catch (err) {
        console.error('Function {0} is not found the context {1}'.format(functionName, context), err)
    }
    return func.apply(context, args);
}


(function ($) {


    // let opts = $.extend({}, $.erp_framework.defaults, options);

    function enable_tab_support() {
        //support for enter key as a navigation
        let focusables = $(':focusable');
        $('input').not('[ra_autocomplete_bind="true"]').not('[type="search"]').not('#top_search_box')
            .on("keydown", function (event) {
                if (event.keyCode === 13) {
                    let current = focusables.index(this);
                    let check = false;
                    while (!check) {
                        let next = getNext(current);
                        let readOnly = $(next).attr('readonly');

                        if (typeof readOnly == 'undefined') {
                            check = true;
                        }
                        if ($(next).hasClass('delete-row')) {
                            check = false;
                        }
                        current++;
                    }
                    next.focus();
                    next.select();
                    event.preventDefault();
                }

                function getNext(current) {
                    return focusables.eq(current + 1).length ? focusables.eq(current + 1) : focusables.eq(0);
                }
            });
    }

    function smartParseFloat(number, to_fixed) {
        // Wrapper around parseFloat aimed to deliver only numbers

        let val = parseFloat(number);
        if (isNaN(val)) return 0;
        else {
            if (to_fixed > 0 && to_fixed <= 20) return val.toFixed(to_fixed);
            else return val
        }

    }

    function focus_first($div) {
        $div = $div || $('body');
        $div.find('input:visible').not(':disabled').not('.hasDatepicker').not('.timeinput').first().select().focus();
    }

    function adjustNumberWidget() {
        $('input[type=number]').on('focus', function (e) {
            $(this).on('mousewheel.disableScroll', function (e) {
                e.preventDefault();
                var scrollTo = (e.originalEvent.wheelDelta * -1) + $(document.documentElement).scrollTop();
                $(document.documentElement).scrollTop(scrollTo);
            })
        }).on('blur', function (e) {
            $(this).off('mousewheel.disableScroll')
        });
    }

    $.erp_framework = {
        enterTabSupport: enable_tab_support,
        smartParseFloat: smartParseFloat,
        focus_first: focus_first,

    } ;
    // };

    $.erp_framework.defaults = {
        debug: true,

        messages: {

            DoneMessage: "Done...",
            SuccessMessage: "<i class='icon-checkmark-circle'></i> Done...",
            ErrorMessage: "An error happened :( ",
            WaitMessage: 'Just a moment...',
            LoadingMessage: 'loading...',
            total: 'Total',

        },
        urls: {

        },
    };

    $.erp_framework.cache = {};
    $.erp_framework.rtl = false;

    $.erp_framework.debug = false; // turned on only on dev ;
}(jQuery));

        
