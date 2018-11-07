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
    if (window.location.href.match(/setKey=true/gi)) {
        setKey = true;
    }

    serverRequest('/get/isAdmin', function(response) {
        isAdminFlag = response.isAdmin;
        if(isAdminFlag){
            setKeyFlag = true;
            id = window.location.href.match('id=[0-9]+')[0].slice(3);
            callAnnotationUI(id,setKeyMode=setKeyFlag);
        }
        else{
            setKeyFlag = false;
            serverRequest("/get/fcw/job", function(response) {
                console.log("setKey",setKey);
                callAnnotationUI(response.jid,setKeyMode=setKey);
            });
        }
    });


    // serverRequest("/get/fcw/job", function(response) {
    //     console.log("setKey",setKey);
    //     callAnnotationUI(response.jid,setKeyMode=setKey);
    // });
    
};
