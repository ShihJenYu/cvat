"use strict";


window.onload = function() {
    
    $.getJSON("https://api.ipify.org?format=jsonp&callback=?",
      function(json) {

        let mysterious_key = null;
        mysterious_key = json.ip;
        mysterious_key = md5(mysterious_key);

        let mysteriousData = new FormData();
        console.log('mysterious_key',mysterious_key);
        mysteriousData.append('mysteriousKey', mysterious_key);
        $.ajax({
            url: '/auth/mysteriousKey',
            type: 'POST',
            async: false,
            data: mysteriousData,
            contentType: false,
            processData: false,
            success: function(response) {
                console.log("/auth/mysteriousKey", response);
                if(response.auth=='error'){
                    window.location.href='/auth/logout';
                }
            },
            error: function(response) {
                console.log("/auth/mysteriousKey is error", response);
                window.location.href='/auth/logout';
            }
        });
      }
    );


    $('#search_user_btn').on('click', () => {
        let project = $('#userProject').prop('value')
        let user = $('#inpustUser').prop('value')
        $('#userWorkSpace').text('');
        $.ajax({
            url: `get/${user}/${project}/workSpace`,
            dataType: "json",
            success: function(response){
                console.log('success',response);
                $('#userWorkSpace').text(response.packagename);
            },
            error: function(response){
                console.log('error',response);
            },
        });
    });

    
    $('#workspace_project_btn').on('click', () => {
        $("#workspace_package").empty();
        let project = $('#workspace_project').prop('value');
        $('#selected_project').text(project);
        $.ajax({
            url: `get/${project}/packagename`,
            dataType: "json",
            success: function(response){
                console.log('success',response);
                for(let name of response.packagenames) {
                    $('#workspace_package').append($("<option></option>").attr("value",name).text(name));
                }
            },
            error: function(response){
                console.log('error',response);
            },
        });
    });

    $('#workspace_package_btn').on('click', () => {

        $('#WorkSpaceUser optgroup').empty()
        $('#WorkSpaceUser_to optgroup').empty()

        if ($('.inWorkSpaceUser optgroup[label="SOHO"]').length == 0)
            $('.inWorkSpaceUser').append($("<optgroup></optgroup>").attr("label","SOHO"));
        if ($('.outWorkSpaceUser optgroup[label="SOHO"]').length == 0)
            $('.outWorkSpaceUser').append($("<optgroup></optgroup>").attr("label","SOHO"));
        
        if ($('.inWorkSpaceUser optgroup[label="Company"]').length == 0)
            $('.inWorkSpaceUser').append($("<optgroup></optgroup>").attr("label","Company"));
        if ($('.outWorkSpaceUser optgroup[label="Company"]').length == 0)
            $('.outWorkSpaceUser').append($("<optgroup></optgroup>").attr("label","Company"));

        let project = $('#selected_project').text();
        let package = $('#workspace_package').prop('value');
        $('#selected_package').text(package);
        $.ajax({
            url: `get/${project}/${package}/workSpaceUsers`,
            dataType: "json",
            success: function(response){
                console.log('success',response);
                let inWorkSpaceUsers = response.inWorkSpaceUsers;
                let outWorkSpaceUsers = response.outWorkSpaceUsers;

                for (let user of inWorkSpaceUsers) {
                    if(user.toLowerCase().startsWith("oto")) {
                        $('.inWorkSpaceUser optgroup[label="Company"]').append($("<option></option>").attr("value",user).text(user));
                    }
                    else {
                        $('.inWorkSpaceUser optgroup[label="SOHO"]').append($("<option></option>").attr("value",user).text(user));
                    }
                }
                for (let user of outWorkSpaceUsers) {
                    if(user.toLowerCase().startsWith("oto")) {
                        $('.outWorkSpaceUser optgroup[label="Company"]').append($("<option></option>").attr("value",user).text(user));
                    }
                    else {
                        $('.outWorkSpaceUser optgroup[label="SOHO"]').append($("<option></option>").attr("value",user).text(user));
                    }
                }
            },
            error: function(response){
                console.log('error',response);
            },
        });
    });

    $('#workspace_save_btn').on('click', () => {
        
        let inUsers = $.map($('.inWorkSpaceUser option') ,function(option) {
            return option.value;
        });
        let outUsers = $.map($('.outWorkSpaceUser option') ,function(option) {
            return option.value;
        });

        let project = $('#selected_project').text();
        let package = $('#selected_package').text();

        let workSpaceData = new FormData();
        workSpaceData.append('project', project);
        workSpaceData.append('package', package);
        workSpaceData.append('inUsers', inUsers);
        workSpaceData.append('outUsers', outUsers);
        $.ajax({
            url: 'set/workSpaceUsers',
            type: 'POST',
            data: workSpaceData,
            contentType: false,
            processData: false,
            success: function(response) {
                console.log(response);
            },
            error: function(response) {
                console.log(response);
            }
        });
    });


    $('#search_efficiencyTable').on('click', () => {

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
                    let checked_objs = row.checked_objs;
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
                    // <td> 目標[4000] /已正確圖片量的物件量 </td>
                    // <td> 待修改圖片量 </td>
                    // <td> 未檢查圖片量 </td>
                    // <td> 錯誤圖片量 </td>
                    // <td> 正確圖片量 </td>
                    // <td> 正確物件量 </td>
                    // <td> 查詢時間 </td>

                    let perfection_color = (checked_objs >= 4000)?"background-color: greenyellow;":"background-color: lightcoral;";
                    $('#efficiencyTable > tbody:last-child').append(
                        `<tr class='per_data'><td>${user}</td>` + 
                        `<td>${search_targets} / ${row.search_targets_objs}</td>` + 
                        `<td style="${perfection_color}">${row.checked} / ${row.checked_objs}</td>` + 
                        `<td>${need_modify} / ${row.need_modify_objs}</td>` + 
                        `<td>${uncheck} / ${row.uncheck_objs}</td>` + 
                        `<td>${terrible} / ${row.terrible}</td>` + 
                        `<td>${excellent} / ${row.excellent_objs}</td>` + 
                        `<td>${date_str}</td></tr>`
                    );
                }
            },
        });
    });
};

$(document).ready(function($) {
    $('#WorkSpaceUser').multiselect({
        right: '#js_multiselect_to_1',
        rightAll: '#js_right_All_1',
        rightSelected: '#js_right_Selected_1',
        leftSelected: '#js_left_Selected_1',
        leftAll: '#js_left_All_1',
        search: {
            left: '<input type="text" name="q" class="form-control" placeholder="Search..." />',
            right: '<input type="text" name="q" class="form-control" placeholder="Search..." />',
        },
        fireSearch: function(value) {
            return value.length > 0;
        },
        keepRenderingSort: true,

    });
});