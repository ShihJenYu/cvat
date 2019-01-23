/*
 * Copyright (C) 2018 Intel Corporation
 *
 * SPDX-License-Identifier: MIT
 */

"use strict";

String.prototype.normalize = function() {
    let target = this;
    target = target.charAt(0).toUpperCase() + target.substr(1);
    return target;
};

window.onload = function() {
    window.onerror = function(errorMsg, url, lineNumber, colNumber, error) {
        Logger.sendException({
            message: errorMsg,
            filename: url,
            line: lineNumber,
            column: colNumber ? colNumber : '',
            stack: error && error.stack ? error.stack : '',
            browser: platform.name + ' ' + platform.version,
            os: platform.os.toString(),
        }).catch(() => { return; });
    };

    let id = null;
    let setKey = false;
    if (window.location.search.match(/setKey=true/gi)) {
        setKey = true;
    }

    let mysterious_key = null;
    $.getJSON("https://api.ipify.org?format=jsonp&callback=?",
      function(json) {
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
            success: function(respone) {
                console.log("/auth/mysteriousKey", respone);
                if(respone.auth=='error'){
                    window.location.href='/auth/logout';
                }
            },
            error: function(respone) {
                console.log("/auth/mysteriousKey is error", respone);
                window.location.href='/auth/logout';
            }
        });

        serverRequest('get/isAdmin', function(response) {
            isAdminFlag = response.isAdmin;
            if(isAdminFlag){
                setKeyFlag = true;
                console.log(window.location.search)
                id = window.location.search.match('id=[0-9]+')[0].slice(3);
                callAnnotationUI(id,setKeyMode=setKeyFlag);
            }
            else{
                setKeyFlag = false;
                callAnnotationUI_annotator(setKeyFlag);
            }
        });
      }
    );
};
