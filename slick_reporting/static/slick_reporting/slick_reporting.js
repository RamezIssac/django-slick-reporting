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

    function calculateTotalOnColumnArray(data, columns) {
        // Compute totals on columnar data (one values array per column)
        // example :
        // calculateTotalOnColumnArray ({value1: [500, 200], value2: [70, 15]}, ['value1'])
        // return {'value1': 700}

        let total_container = {};
        for (let i = 0; i < columns.length; i++) {
            let values = data[columns[i]] || [];
            total_container[columns[i]] = 0;
            for (let r = 0; r < values.length; r++) {
                let val = values[r];
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

    function getReportRowCount(response) {
        // The number of rows in a columnar report response: the length of any column values array
        let data = response.data || {};
        if (response.columns && response.columns.length > 0) {
            let values = data[response.columns[0].name];
            return values ? values.length : 0;
        }
        let keys = Object.keys(data);
        if (keys.length > 0 && data[keys[0]]) {
            return data[keys[0]].length;
        }
        return 0;
    }

    function dataToRows(response) {
        // Convert the columnar response data ({colName: [value per row, ...]})
        // into an array of row objects ([{colName: value, ...}, ...])
        let data = response.data || {};
        let keys = Object.keys(data);
        let rowCount = getReportRowCount(response);
        let rows = [];
        for (let r = 0; r < rowCount; r++) {
            let row = {};
            for (let k = 0; k < keys.length; k++) {
                let values = data[keys[k]];
                row[keys[k]] = values ? values[r] : undefined;
            }
            rows.push(row);
        }
        return rows;
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


    $.slick_reporting = {
        'getObjFromArray': getObjFromArray,
        'calculateTotalOnObjectArray': calculateTotalOnObjectArray,
        'calculateTotalOnColumnArray': calculateTotalOnColumnArray,
        'getReportRowCount': getReportRowCount,
        'dataToRows': dataToRows,
        "executeFunctionByName": executeFunctionByName,
        "get_xpath": get_xpath,
        defaults: {
            total_label: 'Total',
        }

    }
    $.slick_reporting.cache = {}

}(jQuery));