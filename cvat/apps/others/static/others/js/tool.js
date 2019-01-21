"use strict";


window.onload = function() {

    $('#search_efficiencyTable').on('click', () => {
        console.log('hello world');

        function formatDate(date_str) {
            let utcDate_strs = new Date(date_str).toUTCString().split(' ',5);
            let utcDate = new Date(utcDate_strs.slice(0,4).join(' '));

            let month = '' + (utcDate.getMonth() + 1);
            let day = '' + utcDate.getDate();
            let year = '' + utcDate.getFullYear();

            if (month.length < 2) month = '0' + month;
            if (day.length < 2) day = '0' + day;

            return [year, month, day].join('-') + ' ' + utcDate_strs[4];
        }
        
        let search_project = $('#search_project').prop('value');
        let office = $('#office').prop('value');

        let startDate_str = $('#startDate').prop('value') + ' 00:00:00';
        let endDate_str = $('#endDate').prop('value') + ' 23:59:59';
        startDate_str = formatDate(startDate_str) + '.00';
        endDate_str = formatDate(endDate_str) + '.99';

        console.log(startDate_str,'to',endDate_str);
        
        let searchParam = new FormData();
        searchParam.append('search_project', search_project);
        searchParam.append('office', office);
        searchParam.append('startDate', startDate_str);
        searchParam.append('endDate', endDate_str);

        $.ajax({
            url: 'efficiencyTable',
            type: 'POST',
            data: searchParam,
            contentType: false,
            processData: false,
            success: function(response){
                console.log(response);

                $('.per_data').remove();
                for(let row of response.efficiencyTable) {
                    let user = row.user;
                    let search_targets = row.search_targets;
                    let checked = row.checked;
                    let need_modify = row.need_modify;
                    let uncheck = row.uncheck;
                    let terrible = row.terrible;
                    let excellent = row.excellent;
                    let excellent_objs = row.excellent_objs;

                    let date = new Date();
                    let year = '' + date.getFullYear();
                    let month = '' + (date.getMonth() + 1);
                    let day = '' + date.getDate();
                    let hours = '' + date.getHours();
                    let minutes = '' + date.getMinutes();
                    let seconds = '' + date.getSeconds();

                    if (month.length < 2) month = '0' + month;
                    if (day.length < 2) day = '0' + day;
                    if (hours.length < 2) hours = '0' + hours;
                    if (minutes.length < 2) minutes = '0' + minutes;
                    if (seconds.length < 2) seconds = '0' + seconds;

                    let date_str = [year, month, day].join('-') + ' ' + [hours, minutes, seconds].join(':');
                    // <td> 用戶 </td>
                    // <td> 標記圖片量 </td>
                    // <td> 已正確圖片量 </td>
                    // <td> 待修改圖片量 </td>
                    // <td> 未檢查圖片量 </td>
                    // <td> 錯誤圖片量 </td>
                    // <td> 正確圖片量 </td>
                    // <td> 正確物件量 </td>
                    // <td> 查詢時間 </td>
                    $('#efficiencyTable > tbody:last-child').append(
                        `<tr class='per_data'><td>${user}</td>` + 
                        `<td>${search_targets}</td>` + 
                        `<td>${checked}</td>` + 
                        `<td>${need_modify}</td>` + 
                        `<td>${uncheck}</td>` + 
                        `<td>${terrible}</td>` + 
                        `<td>${excellent}</td>` + 
                        `<td>${excellent_objs}</td>` + 
                        `<td>${date_str}</td></tr>`
                    );
                }
            },
        });
    });
};