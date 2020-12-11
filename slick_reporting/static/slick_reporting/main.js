(function ($) {

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


    $.slick_reporting = {
        'getObjFromArray': getObjFromArray,
        'calculateTotalOnObjectArray': calculateTotalOnObjectArray,

    }

}(jQuery));