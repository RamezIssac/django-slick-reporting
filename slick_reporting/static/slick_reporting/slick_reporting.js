(function ($) {

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
                throw `Function ${functionName} is not found in the context ${context}`
            }

        } catch (err) {
            console.error(`Function ${functionName} is not found in the context ${context}`, err)
        }
        return func.apply(context, args);
    }

    function getObjFromArray(objList, obj_key, key_value, failToFirst) {
        failToFirst = typeof (failToFirst) !== 'undefined';
        if (key_value !== '') {
            for (let i = 0; i < objList.length; i++) {
                if (objList[i][obj_key] === key_value) {
                    return objList[i];
                }
            }
        }
        if (failToFirst && objList.length > 0) {
            return objList[0]
        }

        return false;
    }

    function calculateTotalOnObjectArray(data, columns) {
        // Compute totals in array of objects
        // example :
        // calculateTotalOnObjectArray ([{ value1:500, value2: 70} , {value:200, value2:15} ], ['value'])
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

    function get_xpath($element, forceTree) {
        if ($element.length === 0) {
            return null;
        }

        let element = $element[0];

        if ($element.attr('id') && ((forceTree === undefined) || !forceTree)) {
            return '//*[@id="' + $element.attr('id') + '"]';
        } else {
            let paths = [];
            for (; element && element.nodeType === Node.ELEMENT_NODE; element = element.parentNode) {
                let index = 0;
                for (let sibling = element.previousSibling; sibling; sibling = sibling.previousSibling) {
                    if (sibling.nodeType === Node.DOCUMENT_TYPE_NODE)
                        continue;
                    if (sibling.nodeName === element.nodeName)
                        ++index;
                }

                var tagName = element.nodeName.toLowerCase();
                var pathIndex = (index ? '[' + (index + 1) + ']' : '');
                paths.splice(0, 0, tagName + pathIndex);
            }

            return paths.length ? '/' + paths.join('/') : null;
        }
    }


    let _numberFormatCache = {};

    function formatNumber(value, fmt) {
        if (value === null || value === undefined || value === '') return '';
        let num = parseFloat(value);
        if (isNaN(num)) return value;
        let cacheKey = JSON.stringify(fmt);
        if (!_numberFormatCache[cacheKey]) {
            _numberFormatCache[cacheKey] = fmt.use_locale
                ? new Intl.NumberFormat(undefined, {
                    minimumFractionDigits: fmt.decimal_places,
                    maximumFractionDigits: fmt.decimal_places,
                })
                : '__manual__';
        }
        if (fmt.use_locale) {
            return _numberFormatCache[cacheKey].format(num);
        }
        let fixed = num.toFixed(fmt.decimal_places);
        let parts = fixed.split('.');
        parts[0] = parts[0].replace(/\B(?=(\d{3})+(?!\d))/g, fmt.thousands_separator);
        return parts.join('.');
    }

    $.slick_reporting = {
        'getObjFromArray': getObjFromArray,
        'calculateTotalOnObjectArray': calculateTotalOnObjectArray,
        "executeFunctionByName": executeFunctionByName,
        "get_xpath": get_xpath,
        "formatNumber": formatNumber,
        defaults: {
            total_label: 'Total',
            number_format: null,
        }

    }
    $.slick_reporting.cache = {}

}(jQuery));