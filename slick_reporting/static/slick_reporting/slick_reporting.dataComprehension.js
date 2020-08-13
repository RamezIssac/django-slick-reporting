/**
 * Created by ramez on 8/22/16.
 */
(function ($) {

    function dataArrayToObject(data, key) {
        // Turn a data array to an object
        // Example:
        // in: [
        // {'key': key , 'value': 0},
        // {'key': key , 'value': 1},
        // {'key': key , 'value': 2},
        // ]
        // out: {'key':key , 'value':[0,1,2]}
        var output = {};
        for (var r = 0; r < data.length; r++) {
            output[data[r][key]] = data[r];
        }
        return output
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

    function removeObjFromArray(objList, obj_key, key_value) {
        for (let i = 0; i < objList.length; i++) {
            if (objList[i][obj_key] == key_value) {
                objList.splice(i, 1);
            }
        }
        return false;
    }

    function getPercentToTotal(objList, obj_key, key_value, computation_field) {
        // Get the percentage of an obj computation_field (obj in the list is identified by obj_key and key_value)
        // to the total of this computation field in the list
        // example:
        //          objList = [{expense_id:1, value:20} , {expense_id: 2 value: 80}]
        //          obj_key = 'expense_id'
        //          key_value = '1'
        //          computation_field='value'
        //  return
        //      { percentToTotal: 20, total:100, obj:{expense_id:1, value:20} }


        var total = 0, percent_to_total = 0;
        var obj_of_intrest = false;
        for (var i = 0; i < objList.length; i++) {
            total = total + objList[i][computation_field];
            if (objList[i][obj_key] === key_value) {
                obj_of_intrest = objList[i];
            }
        }
        if (obj_of_intrest !== false) {
            percent_to_total = (obj_of_intrest[computation_field] / total) * 100;
            if (isNaN(percent_to_total)) {
                percent_to_total = 0
            }
            return {
                'obj': obj_of_intrest,
                'total': total,
                'percentToTotal': percent_to_total
            }
        }

        return false;
    }

    $.slick_reporting.dataComprehension = {
        dataArrayToObject: dataArrayToObject,
        getObjFromArray: getObjFromArray,
        // removeObjFromArray: removeObjFromArray,
        // getPercentToTotal: getPercentToTotal,
    }
})(jQuery);
