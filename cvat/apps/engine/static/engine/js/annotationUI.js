/*
 * Copyright (C) 2018 Intel Corporation
 *
 * SPDX-License-Identifier: MIT
 */

/* exported callAnnotationUI translateSVGPos blurAllElements drawBoxSize copyToClipboard */
"use strict";
var PROJECT = '';
var trainigsaveFlag = false;
var goNextRandom = false;
var goNext = false;
var saveByShift = false;
var setKeyFlag = false;
var isAdminFlag = false;
var passreload =false;
var loadJobEvent = null;
var LOCKALL = false;
function callAnnotationUI(jid,setKeyMode=false) {
    initLogger(jid);
    setKeyFlag = setKeyMode;
    loadJobEvent = Logger.addContinuedEvent(Logger.EventType.loadJob);
    serverRequest("get/job/" + jid, function(job) {
        serverRequest("get/annotation/job/" + jid, function(data) {
            // data = {'shapeData':annotation.to_client(),'frame':frame,'jid':new_jid,'frameInfo':frameInfo}
            if(data == "you need to get new work") {
                // $.confirm({
                //     title: '要領取工作了嗎？',
                //     content: '將會得到圖片或影片',
                //     boxWidth: '30%',
                //     useBootstrap: false,
                //     draggable: false,
                //     buttons: {
                //         是: {
                //             keys: ['enter'],
                //             action: function(){
                //                 console.log('confirm');
                //                 serverRequest('get/current/job/'+jid, function(test){
                //                     serverRequest("get/job/" + test.jid, function(job2) {
                //                         serverRequest("get/annotation/job/" + test.jid, function(data2) {
                //                             if (data2.jid == test.jid) {
                //                                 $('#loadingOverlay').remove();
                //                                 setTimeout(() => {
                //                                     buildAnnotationUI(job2, data2, loadJobEvent);
                //                                 }, 0);
                //                             }
                //                         });
                //                     });
                //                 });
                //             }
                //         },
                //         否: {
                //             keys: ['esc'],
                //             action: function(){
                //                 console.log("cancel,you need to get new work");
                //             }
                //         }
                //     }
                // });
            }
            else if (data.jid == jid) {
                $('#loadingOverlay').remove();
                setTimeout(() => {
                    buildAnnotationUI(job, data, loadJobEvent);
                }, 0);
            }
            else{
                console.log("some error");
            }
        });
    });
}

function callAnnotationUI_annotator(setKeyMode=false) {
    setKeyFlag = setKeyMode;
    function newWork() {
        serverRequest("get/currentJob", function(response) {
            console.log(response);
            if(response == "you need to get new work") {
                $.confirm({
                    title: '要領取工作了嗎？',
                    content: '將會得到圖片或影片',
                    boxWidth: '30%',
                    useBootstrap: false,
                    draggable: false,
                    buttons: {
                        是: {
                            keys: ['enter'],
                            action: function(){
                                console.log('confirm');
                                serverRequest('set/currentJob', function(msg){
                                    if(msg.status!=null){
                                        showOverlay(msg.text);
                                        $('#loadingOverlay_msg').text(msg.text);
                                    }
                                    else {
                                        console.log('set/currentJob', msg)
                                        newWork();
                                    }
                                });
                            }
                        },
                        否: {
                            keys: ['esc'],
                            action: function(){
                                console.log("cancel,u dont have current need set current");
                                $('#loadingOverlay_msg').text("你剛剛按了否, 想再領取工作, 請重新整理此網頁");
                            }
                        }
                    }
                });
            } else{
                initLogger(response.jid);
                loadJobEvent = Logger.addContinuedEvent(Logger.EventType.loadJob);
                $('#loadingOverlay').remove();
                setTimeout(() => {
                    buildAnnotationUI(response.job, response.data, loadJobEvent);
                }, 0);
            }
        });
    }
    newWork();
}

function initLogger(jobID) {
    if (!Logger.initializeLogger('CVAT', jobID))
    {
        let message = 'Could not initialize Logger. Please immediately report the problem to support team';
        console.error(message);
        showMessage(message);
        return;
    }

    Logger.setTimeThreshold(Logger.EventType.zoomImage);

    serverRequest('get/username', function(response) {
        Logger.setUsername(response.username);
    });
}

function buildAnnotationUI(job, shapeData, loadJobEvent) {
    // data = {'shapeData':annotation.to_client(),'frame':frame,'jid':new_jid,'frameInfo':frameInfo,'videoInfo':videoInfo}
    current_lang = 1;
    $.each(_LANG, function(index, value) {
        $(`#${index}`).text(value[current_lang]);
    }); 
    // Setup some API
    // shapeData = [data, frame], change by jeff
    console.log(job.start,job.stop);
    window.cvat = {
        frameInfo: shapeData.frameInfo,
        videoInfo: shapeData.videoInfo,
        labelsInfo: new LabelsInfo(job),
        player: {
            geometry: {
                scale: 1,
            },
            frames: {
                // change by jeff
                current: (shapeData.frame!= null)? shapeData.frame: job.start,
                start: (shapeData.frame!= null)? shapeData.frame: job.start,
                stop:  (shapeData.frame!= null)? shapeData.frame: job.stop,
            }
        },
        mode: null,
        job: {
            z_order: job.z_order,
            id: job.jobid
        },
        search: {
            value: window.location.search,

            set: function(name, value) {
                let searchParams = new URLSearchParams(this.value);

                if (typeof value === 'undefined' || value === null) {
                    if (searchParams.has(name)) {
                        searchParams.delete(name);
                    }
                }
                else searchParams.set(name, value);
                this.value = `${searchParams.toString()}`;
            },

            get: function(name) {
                try {
                    let decodedURI = decodeURIComponent(this.value);
                    let urlSearchParams = new URLSearchParams(decodedURI);
                    if (urlSearchParams.has(name)) {
                        return urlSearchParams.get(name);
                    }
                    else return null;
                }
                catch (error) {
                    showMessage('Bad URL has been found');
                    this.value = window.location.href;
                    return null;
                }
            },

            toString: function() {
                return `${window.location.origin}/?${this.value}`;
            }
        }
    };
    console.log("window.location",window.location);
    // Remove external search parameters from url

    // serverRequest('/get/isAdmin', function(response) {
    //     isAdminFlag = response.isAdmin;
        
    // });

    PROJECT = window.location.pathname.split('/')[1];
    if(PROJECT != 'fcw_training'){
        $('#isKeyFrame').prop('disabled',true);
    }
    
    if(isAdminFlag){
        window.history.replaceState(null, null, `${window.location.origin}${window.location.pathname}?id=${job.jobid}&setKey=${setKeyFlag}`);
        $('#task_name').text(job.slug);

        console.log(window.cvat.videoInfo);
        let framePackage = window.cvat.videoInfo.framePackage;
        let packages = Object.keys(window.cvat.videoInfo.framePackage);
        let allKeyframes = [];

        $("#select_keyframes").empty();
        $("#select_package").empty();

        $('#select_package').append($("<option></option>").attr("value",'all').text('all'));

        for(let key in framePackage){
            console.log('framePackage', key, framePackage[key]);
            allKeyframes.push(...framePackage[key]);
            $('#select_package').append($("<option></option>").attr("value",key).text(key));
        }
        allKeyframes.sort((a, b) => a - b);

        allKeyframes.forEach(function(value) {
            let txt = window.cvat.frameInfo[value].full_name;
            txt = txt.split('.')[0].slice(-4);
            $('#select_keyframes').append($("<option></option>").attr("value",value).text(txt));
        });

        $('#select_keyframes').on('change', (e) => {
            $('#select_keyframes').trigger('focusout');
            window.setTimeout(function() {
                let value = $('#select_keyframes').prop('value');
                let realframe = $('#select_keyframes option:selected').text();
                if (value != 'null') {
                    $('#realFrame').text(+realframe);
                    $('#frameNumber_show').val(+value+1);
                    $('#frameNumber_show').trigger('change');
                }
                else {
                    $('#select_keyframes').prop('value',$('#frameNumber').prop('value'));
                }
            }, 0);
        });

        $('#select_package').on('change', (e) => {
            console.log(e.target.value);

            $("#select_keyframes").empty();
            $('#select_keyframes').append($("<option></option>").attr("value","null").text("null"));

            if (e.target.value == 'all') {
                console.log('window.cvat.videoInfo.framePackage',framePackage);
                let keyframes = [];
                for(let key in framePackage){
                    console.log('framePackage', key, framePackage[key]);
                    keyframes.push(...framePackage[key]);
                }
                keyframes.sort((a, b) => a - b);
                keyframes.forEach(function(value) {
                    let txt = window.cvat.frameInfo[value].full_name;
                    txt = txt.split('.')[0].slice(-4);
                    $('#select_keyframes').append($("<option></option>").attr("value",value).text(txt));
                });
            }
            else {
                framePackage[e.target.value].forEach(function(value) {
                    let txt = window.cvat.frameInfo[value].full_name;
                    txt = txt.split('.')[0].slice(-4);
                    $('#select_keyframes').append($("<option></option>").attr("value",value).text(txt));
                });
            }
        });
    }
    else{
        window.history.replaceState(null, null, `${window.location.origin}${window.location.pathname}`);
        if(PROJECT=='fcw_training') {
            let full_name = shapeData.frameInfo[shapeData.frame].full_name;
            txt = (full_name)? full_name : job.slug + ', F' + String(+shapeData.frame+1).padStart(4, '0');
            $('#task_name').text(txt)
        }
        else {
            $('#task_name').text(job.slug);
        }

        let comment_list = window.cvat.frameInfo[shapeData.frame].comment.split(',');
        let comment_href = comment_list[0];
        if(!comment_href.includes('file:')){
            $('#redoComment_readonly').text(window.cvat.frameInfo[shapeData.frame].comment);

            $('#commentImgButton').addClass('hidden');
            console.log(' commentImgButton add hidden');
        }
        else {
            $('#commentImgButton').removeClass('hidden');
            let comment_str = comment_list.slice(1).join();
            $('#redoComment_readonly').text(comment_str);
            console.log(' commentImgButton remove hidden');
            $.alert({
                title: '特別需要注意！ 用下列網址開啟新分頁',
                content: '<label>' + comment_href + '<label>',
                boxWidth: '60%',
                useBootstrap: false,
                draggable: false,
                dragWindowBorder: false,
            });
            
        }
        $('#commentImgButton').click(function() {
            $.alert({
                title: '特別需要注意！ 用下列網址開啟新分頁',
                content: '<label>' + comment_href + '<label>',
                boxWidth: '60%',
                useBootstrap: false,
                draggable: false,
                dragWindowBorder: false,
            });
        });
    }

    

    window.cvat.config = new Config();

    // Setup components
    let annotationParser = new AnnotationParser(job, window.cvat.labelsInfo);

    let shapeCollectionModel = new ShapeCollectionModel().import(shapeData.shapeData).updateHash();
    let shapeCollectionController = new ShapeCollectionController(shapeCollectionModel);
    let shapeCollectionView = new ShapeCollectionView(shapeCollectionModel, shapeCollectionController);

    window.cvat.data = {
        get: () => shapeCollectionModel.export(),
        set: (data) => {
            shapeCollectionModel.empty();
            shapeCollectionModel.import(data);
            shapeCollectionModel.update();
        },
        clear: () => shapeCollectionModel.empty(),
        getCurrnetShapes: () => {return shapeCollectionModel._currentShapes;}
    };
    window.cvat.groupingData = {
        get: () => {
            
            let frame = window.cvat.player.frames.current;
            shapeCollectionModel._groupMap[frame] = shapeCollectionModel._groupMap[frame] || {};
            return shapeCollectionModel._groupMap[frame];
        },
        cleanCurrent: () => shapeCollectionModel._cleanCurrentGroup(),
    }

    let shapeBufferModel = new ShapeBufferModel(shapeCollectionModel);
    let shapeBufferController = new ShapeBufferController(shapeBufferModel);
    let shapeBufferView = new ShapeBufferView(shapeBufferModel, shapeBufferController);

    $('#shapeModeSelector').prop('value', job.mode);
    let shapeCreatorModel = new ShapeCreatorModel(shapeCollectionModel, job);
    let shapeCreatorController = new ShapeCreatorController(shapeCreatorModel);
    let shapeCreatorView = new ShapeCreatorView(shapeCreatorModel, shapeCreatorController);

    let polyshapeEditorModel = new PolyshapeEditorModel();
    let polyshapeEditorController = new PolyshapeEditorController(polyshapeEditorModel);
    let polyshapeEditorView = new PolyshapeEditorView(polyshapeEditorModel, polyshapeEditorController);

    // Add static member for class. It will be used by all polyshapes.
    PolyShapeView.editor = polyshapeEditorModel;

    let shapeMergerModel = new ShapeMergerModel(shapeCollectionModel);
    let shapeMergerController = new ShapeMergerController(shapeMergerModel);
    new ShapeMergerView(shapeMergerModel, shapeMergerController);

    let shapeGrouperModel = new ShapeGrouperModel(shapeCollectionModel);
    let shapeGrouperController = new ShapeGrouperController(shapeGrouperModel);
    let shapeGrouperView = new ShapeGrouperView(shapeGrouperModel, shapeGrouperController);

    let aamModel = new AAMModel(shapeCollectionModel, (xtl, xbr, ytl, ybr) => {
        playerModel.focus(xtl, xbr, ytl, ybr);
    });
    let aamController = new AAMController(aamModel);
    new AAMView(aamModel, aamController);

    shapeCreatorModel.subscribe(shapeCollectionModel);
    shapeGrouperModel.subscribe(shapeCollectionView);
    shapeCollectionModel.subscribe(shapeGrouperModel);

    $('#playerProgress').css('width', $('#player')["0"].clientWidth - 420);

    let playerGeometry = {
        width: $('#playerFrame').width(),
        height: $('#playerFrame').height(),
    };

    // add by jeff, set frame in playermodel
    let playerModel = new PlayerModel(job, playerGeometry,shapeData.frame);
    //let playerModel = new PlayerModel(job, playerGeometry);
    let playerController = new PlayerController(playerModel,
        () => shapeCollectionModel.activeShape,
        (direction) => shapeCollectionModel.find(direction),
        Object.assign({}, playerGeometry, {
            left: $('#playerFrame').offset().left,
            top: $('#playerFrame').offset().top,
        }), job);
    new PlayerView(playerModel, playerController, job);

    let historyModel = new HistoryModel(playerModel);
    let historyController = new HistoryController(historyModel);
    new HistoryView(historyController, historyModel);

    playerModel.subscribe(shapeCollectionModel);
    playerModel.subscribe(shapeCollectionView);
    playerModel.subscribe(shapeCreatorView);
    playerModel.subscribe(shapeBufferView);
    playerModel.subscribe(shapeGrouperView);
    playerModel.subscribe(polyshapeEditorView);
    playerModel.shift(window.cvat.search.get('frame') || 0, true);

    let shortkeys = window.cvat.config.shortkeys;

    setupHelpWindow(shortkeys);
    setupSettingsWindow();
    setupMenu(job, shapeCollectionModel, annotationParser, aamModel, playerModel, historyModel);
    setupFrameFilters();
    setupShortkeys(shortkeys, {
        aam: aamModel,
        shapeCreator: shapeCreatorModel,
        shapeMerger: shapeMergerModel,
        shapeGrouper: shapeGrouperModel,
        shapeBuffer: shapeBufferModel,
        shapeEditor: polyshapeEditorModel
    });

    $(window).on('click', function(event) {
        Logger.updateUserActivityTimer();
        if (['helpWindow', 'settingsWindow'].indexOf(event.target.id) != -1) {
            event.target.classList.add('hidden');
        }
    });

    let totalStat = shapeCollectionModel.collectStatistic()[1];
    loadJobEvent.addValues({
        'track count': totalStat.boxes.annotation + totalStat.boxes.interpolation +
            totalStat.polygons.annotation + totalStat.polygons.interpolation +
            totalStat.polylines.annotation + totalStat.polylines.interpolation +
            totalStat.points.annotation + totalStat.points.interpolation,
        'frame count': job.stop - job.start + 1,
        'object count': totalStat.total,
        'box count': totalStat.boxes.annotation + totalStat.boxes.interpolation,
        'polygon count': totalStat.polygons.annotation + totalStat.polygons.interpolation,
        'polyline count': totalStat.polylines.annotation + totalStat.polylines.interpolation,
        'points count': totalStat.points.annotation + totalStat.points.interpolation,
    });
    loadJobEvent.close();

    window.onbeforeunload = function(e) {
        if (passreload)return;
        if (shapeCollectionModel.hasUnsavedChanges()) {
            let message = "You have unsaved changes. Leave this page?";
            e.returnValue = message;
            return message;
        }
        return;
    };

    $('#player').on('click', (e) => {
        if (e.target.tagName.toLowerCase() != 'input') {
            blurAllElements();
        }
    });

    $("#group_status").mouseenter(function() {
        let frame = window.cvat.player.frames.current;
        if (shapeCollectionModel._groupMap[frame] == undefined){
            return;
        }

        let str = '';
        let groupInfo = []; //1-10
        let nogrouplist = [];
        let shapes = shapeCollectionModel._currentShapes;
        let groupIDS = Object.keys(shapeCollectionModel._groupMap[frame]);
        let groupInfoSize = parseInt(groupIDS[groupIDS.length-1]);
        while(groupInfoSize--){
            groupInfo.push({});
        }

        for (let shape of shapes) {
            if (shape.model.removed) continue;
            let gid_list =  shape.model._groupingID;
            let gorder_list =  shape.model._groupingOrder;
            if (gid_list.length) {
                for (let [index, gid] of gid_list.entries()){
                    groupInfo[gid-1][gorder_list[index]] = shape.model._obj_id;
                }
            }
            else {
                nogrouplist.push(shape.model._obj_id);
            }

        }
        console.log('HI',groupInfo);
        for (let [index, group] of groupInfo.entries()){
            if(Object.values(group).length>0){
                str += '群組' + (index+1).toString() + " : " + Object.values(group).toString() + '\n';
            }
        }
        if (nogrouplist.length) {
            str += '無群組 : ' + Object.values(nogrouplist).toString() + '\n';
        }
        
        console.log(str);
        $("#group_status_description").text(str);
        $("#group_status_description").show();
    }).mouseleave(function() {
        $("#group_status_description").hide();
    });
    
}


function copyToClipboard(text) {
    let tempInput = $("<input>");
    $("body").append(tempInput);
    tempInput.prop('value', text).select();
    document.execCommand("copy");
    tempInput.remove();
}


function setupFrameFilters() {
    let brightnessRange = $('#playerBrightnessRange');
    let contrastRange = $('#playerContrastRange');
    let saturationRange = $('#playerSaturationRange');
    let frameBackground = $('#frameBackground');
    let reset = $('#resetPlayerFilterButton');
    let brightness = 100;
    let contrast = 100;
    let saturation = 100;

    let shortkeys = window.cvat.config.shortkeys;
    brightnessRange.attr('title', `
        ${shortkeys['change_player_brightness'].view_value} - ${shortkeys['change_player_brightness'].description}`);
    contrastRange.attr('title', `
        ${shortkeys['change_player_contrast'].view_value} - ${shortkeys['change_player_contrast'].description}`);
    saturationRange.attr('title', `
        ${shortkeys['change_player_saturation'].view_value} - ${shortkeys['change_player_saturation'].description}`);

    let changeBrightnessHandler = Logger.shortkeyLogDecorator(function(e) {
        if(document.activeElement.tagName=='INPUT'){return;}
        if (e.shiftKey) brightnessRange.prop('value', brightness + 10).trigger('input');
        else brightnessRange.prop('value', brightness - 10).trigger('input');
    });

    let changeContrastHandler = Logger.shortkeyLogDecorator(function(e) {
        if(document.activeElement.tagName=='INPUT'){return;}
        if (e.shiftKey) contrastRange.prop('value', contrast + 10).trigger('input');
        else contrastRange.prop('value', contrast - 10).trigger('input');
    });

    let changeSaturationHandler = Logger.shortkeyLogDecorator(function(e) {
        if(document.activeElement.tagName=='INPUT'){return;}
        if (e.shiftKey) saturationRange.prop('value', saturation + 10).trigger('input');
        else saturationRange.prop('value', saturation - 10).trigger('input');
    });

    Mousetrap.bind(shortkeys["change_player_brightness"].value, changeBrightnessHandler, 'keydown');
    Mousetrap.bind(shortkeys["change_player_contrast"].value, changeContrastHandler, 'keydown');
    Mousetrap.bind(shortkeys["change_player_saturation"].value, changeSaturationHandler, 'keydown');

    reset.on('click', function() {
        brightness = 100;
        contrast = 100;
        saturation = 100;
        brightnessRange.prop('value', brightness);
        contrastRange.prop('value', contrast);
        saturationRange.prop('value', saturation);
        updateFilterParameters();
    });

    brightnessRange.on('input', function(e) {
        let value = Math.clamp(+e.target.value, +e.target.min, +e.target.max);
        brightness = e.target.value = value;
        updateFilterParameters();
    });

    contrastRange.on('input', function(e) {
        let value = Math.clamp(+e.target.value, +e.target.min, +e.target.max);
        contrast = e.target.value = value;
        updateFilterParameters();
    });

    saturationRange.on('input', function(e) {
        let value = Math.clamp(+e.target.value, +e.target.min, +e.target.max);
        saturation = e.target.value = value;
        updateFilterParameters();
    });

    function updateFilterParameters() {
        frameBackground.css('filter', `contrast(${contrast}%) brightness(${brightness}%) saturate(${saturation}%)`);
    }
}


function setupShortkeys(shortkeys, models) {
    let annotationMenu = $('#annotationMenu');
    let settingsWindow = $('#settingsWindow');
    let helpWindow = $('#helpWindow');

    Mousetrap.prototype.stopCallback = function() {
        return false;
    };

    let openHelpHandler = Logger.shortkeyLogDecorator(function() {
        let helpInvisible = helpWindow.hasClass('hidden');
        if (helpInvisible) {
            annotationMenu.addClass('hidden');
            settingsWindow.addClass('hidden');
            helpWindow.removeClass('hidden');
        }
        else {
            helpWindow.addClass('hidden');
        }
        return false;
    });

    let openSettingsHandler = Logger.shortkeyLogDecorator(function() {
        let settingsInvisible = settingsWindow.hasClass('hidden');
        if (settingsInvisible) {
            annotationMenu.addClass('hidden');
            helpWindow.addClass('hidden');
            settingsWindow.removeClass('hidden');
        }
        else {
            $('#settingsWindow').addClass('hidden');
        }
        return false;
    });

    let saveHandler = Logger.shortkeyLogDecorator(function() {
        let saveButtonLocked = $('#saveButton').prop('disabled');
        if (!saveButtonLocked) {
            $('#saveButton').click();
        }
        return false;
    });

    let cancelModeHandler = Logger.shortkeyLogDecorator(function() {
        switch (window.cvat.mode) {
        case 'aam':
            models.aam.switchAAMMode();
            break;
        case 'creation':
            models.shapeCreator.switchCreateMode(true);
            break;
        case 'merge':
            models.shapeMerger.cancel();
            break;
        case 'groupping':
            models.shapeGrouper.cancel();
            break;
        case 'paste':
            models.shapeBuffer.switchPaste();
            break;
        case 'poly_editing':f
            models.shapeEditor.finish();
            break;
        }

        // add by jef
        models.shapeGrouper.clearGrouping(true);

        return false;
    });

    // add by jeff
    let translateHandler = Logger.shortkeyLogDecorator(function(e) {
        e.preventDefault();
        if(current_lang == 0) current_lang = 1;
        else current_lang = 0;

        $.each(_LANG, function(index, value) {
            $(`#${index}`).text(value[current_lang]);
        }); 
    });

    Mousetrap.bind(shortkeys["open_help"].value, openHelpHandler, 'keydown');
    Mousetrap.bind(shortkeys["open_settings"].value, openSettingsHandler, 'keydown');
    Mousetrap.bind(shortkeys["save_work"].value, saveHandler, 'keydown');
    Mousetrap.bind(shortkeys["cancel_mode"].value, cancelModeHandler, 'keydown');
    Mousetrap.bind(shortkeys["translate"].value, translateHandler, 'keydown');
}


function setupHelpWindow(shortkeys) {
    let closeHelpButton = $('#closeHelpButton');
    let helpTable = $('#shortkeyHelpTable');

    closeHelpButton.on('click', function() {
        $('#helpWindow').addClass('hidden');
    });

    for (let key in shortkeys) {
        helpTable.append($(`<tr> <td> ${shortkeys[key].view_value} </td> <td> ${shortkeys[key].description} </td> </tr>`));
    }
}


function setupSettingsWindow() {
    let closeSettingsButton = $('#closeSettignsButton');
    let autoSaveBox = $('#autoSaveBox');
    let autoSaveTime = $('#autoSaveTime');

    closeSettingsButton.on('click', function() {
        $('#settingsWindow').addClass('hidden');
    });

    // modify by eric

    let saveInterval = null;
    if (document.getElementById("autoSaveBox").checked) {
        let time = +autoSaveTime.prop('value');
        saveInterval = setInterval(() => {
            let saveButton = $('#saveButton');
            if (!saveButton.prop('disabled')) {
                saveButton.click();
            }
        }, time * 1000 * 60);
    }

    autoSaveBox.on('change', function(e) {
        if (saveInterval) {
            clearInterval(saveInterval);
            saveInterval = null;
        }

        if (e.target.checked) {
            let time = +autoSaveTime.prop('value');
            saveInterval = setInterval(() => {
                let saveButton = $('#saveButton');
                if (!saveButton.prop('disabled')) {
                    saveButton.click();
                }
            }, time * 1000 * 60);
        }

        autoSaveTime.on('change', () => {
            let value = Math.clamp(+e.target.value, +e.target.min, +e.target.max);
            e.target.value = value;
            autoSaveBox.trigger('change');
        });
    });
}


function setupMenu(job, shapeCollectionModel, annotationParser, aamModel, playerModel, historyModel) {
    let annotationMenu = $('#annotationMenu');
    let menuButton = $('#menuButton');

    function hide() {
        annotationMenu.addClass('hidden');
    }

    (function setupVisibility() {
        let timer = null;
        menuButton.on('click', () => {
            let [byLabelsStat, totalStat] = shapeCollectionModel.collectStatistic();
            let table = $('#annotationStatisticTable');
            table.find('.temporaryStatisticRow').remove();

            for (let labelId in byLabelsStat) {
                $(`<tr>
                    <td class="semiBold"> ${window.cvat.labelsInfo.labels()[labelId].normalize()} </td>
                    <td> ${byLabelsStat[labelId].boxes.annotation} </td>
                    <td> ${byLabelsStat[labelId].boxes.interpolation} </td>
                    <td> ${byLabelsStat[labelId].polygons.annotation} </td>
                    <td> ${byLabelsStat[labelId].polygons.interpolation} </td>
                    <td> ${byLabelsStat[labelId].polylines.annotation} </td>
                    <td> ${byLabelsStat[labelId].polylines.interpolation} </td>
                    <td> ${byLabelsStat[labelId].points.annotation} </td>
                    <td> ${byLabelsStat[labelId].points.interpolation} </td>
                    <td> ${byLabelsStat[labelId].manually} </td>
                    <td> ${byLabelsStat[labelId].interpolated} </td>
                    <td class="semiBold"> ${byLabelsStat[labelId].total} </td>
                </tr>`).addClass('temporaryStatisticRow').appendTo(table);
            }

            $(`<tr class="semiBold">
                <td> Total: </td>
                <td> ${totalStat.boxes.annotation} </td>
                <td> ${totalStat.boxes.interpolation} </td>
                <td> ${totalStat.polygons.annotation} </td>
                <td> ${totalStat.polygons.interpolation} </td>
                <td> ${totalStat.polylines.annotation} </td>
                <td> ${totalStat.polylines.interpolation} </td>
                <td> ${totalStat.points.annotation} </td>
                <td> ${totalStat.points.interpolation} </td>
                <td> ${totalStat.manually} </td>
                <td> ${totalStat.interpolated} </td>
                <td> ${totalStat.total} </td>
            </tr>`).addClass('temporaryStatisticRow').appendTo(table);
        });

        menuButton.on('click', () => {
            annotationMenu.removeClass('hidden');
            annotationMenu.css('top', menuButton.offset().top - annotationMenu.height() - menuButton.height() + 'px');
            if (timer) {
                clearTimeout(timer);
                timer = null;
            }

            timer = setTimeout(hide, 1000);
        });

        annotationMenu.on('mouseout', () => {
            if (timer) {
                clearTimeout(timer);
                timer = null;
            }

            timer = setTimeout(hide, 500);
        });

        annotationMenu.on('mouseover', function() {
            if (timer) {
                clearTimeout(timer);
                timer = null;
            }
        });
    })();

    $('#statTaskName').text(job.slug);
    $('#statTaskStatus').text(job.status);
    $('#statFrames').text(`[${job.start}-${job.stop}]`);
    $('#statOverlap').text(job.overlap);
    $('#statZOrder').text(job.z_order);
    $('#statFlipped').text(job.flipped);


    let shortkeys = window.cvat.config.shortkeys;
    $('#helpButton').on('click', () => {
        hide();
        $('#helpWindow').removeClass('hidden');
    });
    $('#helpButton').attr('title', `
        ${shortkeys['open_help'].view_value} - ${shortkeys['open_help'].description}`);

    $('#settingsButton').on('click', () => {
        hide();
        $('#settingsWindow').removeClass('hidden');
    });
    $('#settingsButton').attr('title', `
        ${shortkeys['open_settings'].view_value} - ${shortkeys['open_settings'].description}`);

    $('#downloadAnnotationButton').on('click', (e) => {
        dumpAnnotationRequest(e.target, job.taskid, job.slug);
    });

    $('#uploadAnnotationButton').on('click', () => {
        hide();
        confirm('Current annotation will be removed from the client. Continue?',
            () => {
                uploadAnnotation(shapeCollectionModel, historyModel, annotationParser, $('#uploadAnnotationButton'));
            }
        );
    });

    $('#removeAnnotationButton').on('click', () => {
        if (!window.cvat.mode) {
            hide();
            confirm('Do you want to remove all annotations? The action cannot be undone!',
                () => {
                    historyModel.empty();
                    shapeCollectionModel.empty();
                }
            );
        }
    });

    $('#saveButton').on('click', () => {
        trainigsaveFlag = true;
        let saveFrame = null;
        if (saveByShift) saveFrame = playerModel._frame.previous
        else saveFrame = window.cvat.player.frames.current
        let StatusInfo = window.cvat.frameInfo[saveFrame];
        if(isAdminFlag){
            if(StatusInfo==null) {return; /* not keyframe */ }
            else if(StatusInfo.need_modify || StatusInfo.current || StatusInfo.user==''){
                if(saveByShift) {saveByShift = false;}
                else {
                    let annotator = '';
                    if (StatusInfo.userr=='')annotator="none"
                    else annotator = StatusInfo.user
                    if(annotator!="none") alert(`Hello! annotator is working !!! Current:${StatusInfo.current} Annotator:${annotator} Redo:${StatusInfo.need_modify}`);
                    else alert('no any annotator get this frame, u cannot save!!');
                }
            }
            else {
                console.log("frame",saveFrame,"to save");
                if(['fcw_testing','apacorner'].includes(PROJECT)){
                    if(window.cvat.videoInfo.video_submit) {
                        saveAnnotation(shapeCollectionModel, job);
                    }
                }
                else {
                    saveAnnotation(shapeCollectionModel, job);
                }
            }
        }
        else {
            if(StatusInfo==null || StatusInfo.checked ) {console.log('not keyframe or is checked'); return; }
            console.log("frame",saveFrame,"to save");
            saveAnnotation(shapeCollectionModel, job);
        }
    });
    $('#saveButton').attr('title', `
        ${shortkeys['save_work'].view_value} - ${shortkeys['save_work'].description}`);

    // JS function cancelFullScreen don't work after pressing
    // and it is famous problem.
    $('#fullScreenButton').on('click', () => {
        $('#playerFrame').toggleFullScreen();
    });

    $('#playerFrame').on('fullscreenchange webkitfullscreenchange mozfullscreenchange', () => {
        playerModel.updateGeometry({
            width: $('#playerFrame').width(),
            height: $('#playerFrame').height(),
        });
        playerModel.fit();
    });

    $('#switchAAMButton').on('click', () => {
        hide();
        aamModel.switchAAMMode();
    });

    $('#switchAAMButton').attr('title', `
        ${shortkeys['switch_aam_mode'].view_value} - ${shortkeys['switch_aam_mode'].description}`);
}


function drawBoxSize(scene, box) {
    let scale = window.cvat.player.geometry.scale;
    let width = +box.getAttribute('width');
    let height = +box.getAttribute('height');
    let text = `${width.toFixed(1)}x${height.toFixed(1)}`;
    let obj = this && this.textUI && this.rm ? this : {
        textUI: scene.text('').font({
            weight: 'bolder'
        }).fill('white'),

        rm: function() {
            if (this.textUI) {
                this.textUI.remove();
            }
        }
    };

    obj.textUI.clear().plain(text);

    obj.textUI.font({
        size: 20 / scale,
    }).style({
        stroke: 'black',
        'stroke-width': 1 / scale
    });

    obj.textUI.move(+box.getAttribute('x'), +box.getAttribute('y'));

    return obj;
}


function uploadAnnotation(shapeCollectionModel, historyModel, annotationParser, uploadAnnotationButton) {
    $('#annotationFileSelector').one('change', (e) => {
        let file = e.target.files['0'];
        e.target.value = "";
        if (!file || file.type != 'text/xml') return;
        uploadAnnotationButton.text('Preparing..');
        uploadAnnotationButton.prop('disabled', true);
        let overlay = showOverlay("File is being uploaded..");

        let fileReader = new FileReader();
        fileReader.onload = function(e) {
            let data = null;

            let asyncParse = function() {
                try {
                    data = annotationParser.parse(e.target.result);
                }
                catch (err) {
                    overlay.remove();
                    showMessage(err.message);
                    return;
                }
                finally {
                    uploadAnnotationButton.text('Upload Annotation');
                    uploadAnnotationButton.prop('disabled', false);
                }

                let asyncImport = function() {
                    try {
                        historyModel.empty();
                        shapeCollectionModel.empty();
                        shapeCollectionModel.import(data);
                        shapeCollectionModel.update();
                    }
                    finally {
                        overlay.remove();
                    }
                };

                overlay.setMessage('Data are being imported..');
                setTimeout(asyncImport);
            };

            overlay.setMessage('File is being parsed..');
            setTimeout(asyncParse);
        };
        fileReader.readAsText(file);
    }).click();
}


function saveAnnotation(shapeCollectionModel, job) {
    let saveButton = $('#saveButton');
    if (wasSend){console.log("was send, will not save"); return;}

    Logger.addEvent(Logger.EventType.saveJob);
    let totalStat = shapeCollectionModel.collectStatistic()[1];
    Logger.addEvent(Logger.EventType.sendTaskInfo, {
        'track count': totalStat.boxes.annotation + totalStat.boxes.interpolation +
            totalStat.polygons.annotation + totalStat.polygons.interpolation +
            totalStat.polylines.annotation + totalStat.polylines.interpolation +
            totalStat.points.annotation + totalStat.points.interpolation,
        'frame count': job.stop - job.start + 1,
        'object count': totalStat.total,
        'box count': totalStat.boxes.annotation + totalStat.boxes.interpolation,
        'polygon count': totalStat.polygons.annotation + totalStat.polygons.interpolation,
        'polyline count': totalStat.polylines.annotation + totalStat.polylines.interpolation,
        'points count': totalStat.points.annotation + totalStat.points.interpolation,
    });

    let exportedData = shapeCollectionModel.export();
    let annotationLogs = Logger.getLogs();

    const data = {
        current_frame: shapeCollectionModel._frame,
        annotation: exportedData,
        logs: JSON.stringify(annotationLogs.export()),
    };

    saveButton.prop('disabled', true);
    saveButton.text(_LANG_saveSaveing[current_lang]);
    console.log("this data is will save in db",data);
    saveJobRequest(job.jobid, data, (response) => {
        console.log("saveJobRequest is success",response);
        // success
        shapeCollectionModel.updateHash();
        saveButton.text(_LANG_saveSuccess[current_lang]);
        
        goNext = true;
        goNextRandom = true;
        setTimeout(() => {
            saveButton.prop('disabled', false);
            saveButton.text(_LANG_saveButton[current_lang]);
        }, 3000);
    }, (response) => {
        // error
        console.log("saveJobRequest is error",response);
        saveButton.prop('disabled', false);
        saveButton.text(_LANG_saveButton[current_lang]);
        let message = `Impossible to save job. Errors was occured. Status: ${response.status}`;
        showMessage(message + ' ' + 'Please immediately report the problem to support team');
        throw Error(message);
    });
}

function translateSVGPos(svgCanvas, clientX, clientY) {
    let pt = svgCanvas.createSVGPoint();
    pt.x = clientX;
    pt.y = clientY;
    pt = pt.matrixTransform(svgCanvas.getScreenCTM().inverse());

    let pos = {
        x: pt.x,
        y: pt.y
    };

    if (platform.name.toLowerCase() == 'firefox') {
        pos.x /= window.cvat.player.geometry.scale;
        pos.y /= window.cvat.player.geometry.scale;
    }

    return pos;
}


function blurAllElements() {
    document.activeElement.blur();
}