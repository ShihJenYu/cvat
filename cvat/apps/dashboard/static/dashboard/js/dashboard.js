/*
 * Copyright (C) 2018 Intel Corporation
 *
 * SPDX-License-Identifier: MIT
 */

"use strict";

/* Dashboard entrypoint */
window.cvat = window.cvat || {};
window.cvat.dashboard = window.cvat.dashboard || {};
window.cvat.dashboard.uiCallbacks = window.cvat.dashboard.uiCallbacks || [];
window.cvat.config = new Config();

window.cvat.dashboard.uiCallbacks.push(function(elements) {
    elements.each(function(idx) {
        let elem = $(elements[idx]);
        let taskID = +elem.attr('id').split('_')[1];
        let taskName = $.trim($( elem.find('label.dashboardTaskNameLabel')[0] ).text());
        let buttonsUI = elem.find('div.dashboardButtonsUI')[0];

        let dumpButton = $( $(buttonsUI).find('button.dashboardDumpAnnotation')[0] );
        let uploadButton = $( $(buttonsUI).find('button.dashboardUploadAnnotation')[0] );
        let updateButton = $( $(buttonsUI).find('button.dashboardUpdateTask')[0] );
        let deleteButton = $( $(buttonsUI).find('button.dashboardDeleteTask')[0] );

        let bugTrackerButton =  $(buttonsUI).find('.dashboardOpenTrackerButton');
        if (bugTrackerButton.length) {
            bugTrackerButton = $(bugTrackerButton[0]);
            bugTrackerButton.on('click', function() {
                window.open($(buttonsUI).find('a.dashboardBugTrackerLink').attr('href'));
            });
        }

        dumpButton.on('click', function() {
            window.cvat.dashboard.taskID = taskID;
            window.cvat.dashboard.taskName = taskName;
            dumpAnnotationRequest(dumpButton, taskID, taskName);
        });

        uploadButton.on('click', function() {
            window.cvat.dashboard.taskID = taskID;
            window.cvat.dashboard.taskName = taskName;
            confirm('The current annotation will be lost. Are you sure?', uploadAnnotationRequest);
        });

        updateButton.on('click', function() {
            window.cvat.dashboard.taskID = taskID;
            window.cvat.dashboard.taskName = taskName;
            $('#dashboardUpdateModal').removeClass('hidden');
            $('#dashboardUpdateModal')[0].loadCurrentLabels();
        });

        deleteButton.on('click', function() {
            window.cvat.dashboard.taskID = taskID;
            window.cvat.dashboard.taskName = taskName;
            RemoveTaskRequest();
        });
    });
});

document.addEventListener("DOMContentLoaded", buildDashboard);


function buildDashboard() {
    /* Setup static content */
    setupTaskCreator();
    setupTaskUpdater();
    setupSearch();

    $(window).on('click', function(e) {
        let target = $(e.target);
        if ( target.hasClass('modal') ) {
            target.addClass('hidden');
        }
    });

    /* Setup task UIs */
    for (let callback of window.cvat.dashboard.uiCallbacks) {
        callback( $('.dashboardTaskUI') );
    }

    $('#loadingOverlay').remove();
}


function setupTaskCreator() {
    let dashboardCreateTaskButton = $('#dashboardCreateTaskButton');
    // add by ericlou
    let dashboardUploadKeyframeButton = $('#dashboardUploadKeyframeButton');
    //
    let createModal = $('#dashboardCreateModal');
    let nameInput = $('#dashboardNameInput');
    let packageInput = $('#dashboardPackageInput');
    let labelsInput = $('#dashboardLabelsInput');
    let bugTrackerInput = $('#dashboardBugTrackerInput');
    let localSourceRadio = $('#dashboardLocalSource');
    let shareSourceRadio = $('#dashboardShareSource');
    let selectFiles = $('#dashboardSelectFiles');
    let filesLabel = $('#dashboardFilesLabel');
    let localFileSelector = $('#dashboardLocalFileSelector');
    // add by ericlou
    let localKeyframeUploader = $('#dashboardlocalKeyframeUploader');
    let KeyframeUploaderLabel = $('#dashboardKeyframeUploaderLabel');
    //
    let shareFileSelector = $('#dashboardShareBrowseModal');
    let shareBrowseTree = $('#dashboardShareBrowser');
    let cancelBrowseServer = $('#dashboardCancelBrowseServer');
    let submitBrowseServer = $('#dashboardSubmitBrowseServer');
    let flipImagesBox = $('#dashboardFlipImages');
    let zOrderBox = $('#dashboardZOrder');
    let segmentSizeInput = $('#dashboardSegmentSize');
    let customSegmentSize = $('#dashboardCustomSegment');
    let overlapSizeInput = $('#dashboardOverlap');
    let customOverlapSize = $('#dashboardCustomOverlap');
    let imageQualityInput = $('#dashboardImageQuality');
    let customCompressQuality = $('#dashboardCustomQuality');

    let taskMessage = $('#dashboardCreateTaskMessage');
    // add by ericlou
    let CSVMessage = $('#dashboardUploadCSVMessage');
    let KeyframeMessage = $('#dashboardInsertKeyframeMessage');
    
    let submitCreate = $('#dashboardSubmitTask');
    let cancelCreate = $('#dashboardCancelTask');

    // add by ericlou
    let SubmitKeyframe = $('#dashboardSubmitKeyframe');
    

    // add by ericlou, CSV upload
    let selectCSV = $('#dashboardSelectCSV');
    let CSVfilesLabel = $('#dashboardCSVFilesLabel');
    let submitCSVServer = $('#dashboardSubmitCSVBrowseServer');
    let submitCSVCreate = $('#dashboardSubmitCSV');
    //
    // add by jeff, insert keyframes
    let selectKeyframe = $('#dashboardInsertKeyframe');
    let keyframesfilesLabel = $('#dashboardKeyframesLabel');
    let submitKeyframesServer = $('#dashboardSubmitKeyframesBrowseServer');
    let submitKeyframesCreate = $('#dashboardSubmitKeyframe_insert');
    //

    //add by jeff
    let seletcAllTask = $('#seletcAllTask');
    let cancelAllTask = $('#cancelAllTask');
    let setVideoPriority = $('#setVideoPriority');
    let setVideoPriority_OUT = $('#setVideoPriority_OUT');

    let name = nameInput.prop('value');
    let packagename = packageInput.prop('value');
    let labels = labelsInput.prop('value');
    let bugTrackerLink = bugTrackerInput.prop('value');
    let source = 'local';
    let flipImages = false;
    let zOrder = false;
    let segmentSize = 5000;
    let overlapSize = 0;
    let compressQuality = 50;
    let files = [];
    // add by eric
    let keyframefiles = [];

    dashboardCreateTaskButton.on('click', function() {
        $('#dashboardCreateModal').removeClass('hidden');
    });

    seletcAllTask.on('click', function() {
        $(".selectTask[id]").prop("checked",true);

    });
    cancelAllTask.on('click', function() {
        $(".selectTask[id]").prop("checked",false);
    });
    
    $('.dashboardNickName[id]').on('focusout', (e) => {
        let tid = parseInt(e.target.id.split('_')[1]);
        let nickname = (e.target.value=='')? 'default': e.target.value;
        // console.log(tid, nickname);
        $.ajax ({
            url: `set/task/${tid}/nickname/${nickname}`,
            success: function(response) {
                // console.log(response);
            },
            error: function(response) {
                let message = 'Abort. Reason: ' + response.responseText;
                showMessage(message);
            }
        });
    });

    $('.dashboardNickName[id]').on('keypress',(e) => {
        if (e.keyCode != 13) return;
        let tid = parseInt(e.target.id.split('_')[1]);
        let nickname = (e.target.value=='')? 'default': e.target.value;
        // console.log(tid, nickname);
        $.ajax ({
            url: `set/task/${tid}/nickname/${nickname}`,
            success: function(response) {
                // console.log(response);
            },
            error: function(response) {
                let message = 'Abort. Reason: ' + response.responseText;
                showMessage(message);
            }
        });
    });

    setVideoPriority.on('click', function() {
        let priority = $('#priority').val();
        if (priority == '' || priority < 0) priority = 0;
        if (priority > 50) priority = 50;
        
        var IDs = $(".selectTask[id]")         // find spans with ID attribute
                    .map(function() { if($(this).prop("checked")) return this.id.split('_')[1]; }) // convert to set of IDs
                    .get(); // convert to instance of Array (optional)
        setPriorityRequest(IDs, true, priority, function(response) {
            $('#setVideoPriority').prop('disabled',false);
            IDs.forEach(element => {
                $(`#detailPriority_${element}`).html(parseInt(priority));
            });
        });
    });

    setVideoPriority_OUT.on('click', function() {
        let priority = $('#priority_out').val();
        if (priority == '' || priority < 0) priority = 0;
        if (priority > 50) priority = 50;
        
        var IDs = $(".selectTask[id]")         // find spans with ID attribute
                    .map(function() { if($(this).prop("checked")) return this.id.split('_')[1]; }) // convert to set of IDs
                    .get(); // convert to instance of Array (optional)
        setPriorityRequest(IDs, false, priority, function(response) {
            $('#setVideoPriority').prop('disabled',false);
            IDs.forEach(element => {
                $(`#detailPriorityOUT_${element}`).html(parseInt(priority));
            });
        });
    });

    nameInput.on('change', (e) => {name = e.target.value;});
    packageInput.on('change', (e) => {packagename = e.target.value;});
    bugTrackerInput.on('change', (e) => {bugTrackerLink = e.target.value;});
    labelsInput.on('change', (e) => {labels = e.target.value;});

    localSourceRadio.on('click', function() {
        if (source == 'local') return;
        source = 'local';
        files = [];
        updateSelectedFiles();
    });

    shareSourceRadio.on('click', function() {
        if (source == 'share') return;
        source = 'share';
        files = [];
        updateSelectedFiles();
    });

    selectFiles.on('click', function() {
        submitBrowseServer.removeClass('hidden');
        submitCSVServer.addClass('hidden');
        submitKeyframesServer.addClass('hidden');
        if (source == 'local') {
            localFileSelector.click();
        }
        else {
            shareBrowseTree.jstree("refresh");
            shareFileSelector.removeClass('hidden');
            shareBrowseTree.jstree({
                core: {
                    data: {
                        url: 'get_share_nodes',
                        data: (node) => { return {'project':window.location.pathname.split('/')[2],'id' : node.id}; }
                    }
                },
                plugins: ['checkbox', 'sort'],
            });
        }
    });

    localFileSelector.on('change', function(e) {
        files = e.target.files;
        updateSelectedFiles();
    });


    cancelBrowseServer.on('click', () => shareFileSelector.addClass('hidden'));
    submitBrowseServer.on('click', function() {
        files = shareBrowseTree.jstree(true).get_selected();
        cancelBrowseServer.click();
        updateSelectedFiles();
    });

    // upload_CSV, add by ericlou
    selectCSV.on('click', function() {
        submitCSVServer.removeClass('hidden');
        submitBrowseServer.addClass('hidden');
        submitKeyframesServer.addClass('hidden');

        shareBrowseTree.jstree("refresh");
        shareFileSelector.removeClass('hidden');
        shareBrowseTree.jstree({
            core: {
                data: {
                    url: 'get_share_nodes',
                    data: (node) => { return {'project':window.location.pathname.split('/')[2],'id' : node.id}; }
                }
            },
            plugins: ['checkbox', 'sort'],
        });
    });

    submitCSVServer.on('click', function() {
        files = shareBrowseTree.jstree(true).get_selected();
        cancelBrowseServer.click();
        updateSelectedCSVFiles();
        // console.log(files, "456");
    });

    // insert Keyframes, add by jeff
    selectKeyframe.on('click', function() {
        submitCSVServer.addClass('hidden');
        submitBrowseServer.addClass('hidden');
        submitKeyframesServer.removeClass('hidden');

        shareBrowseTree.jstree("refresh");
        shareFileSelector.removeClass('hidden');
        shareBrowseTree.jstree({
            core: {
                data: {
                    url: 'get_share_nodes',
                    data: (node) => { return {'project':window.location.pathname.split('/')[2],'id' : node.id}; }
                }
            },
            plugins: ['checkbox', 'sort'],
        });
    });

    submitKeyframesServer.on('click', function() {
        files = shareBrowseTree.jstree(true).get_selected();
        cancelBrowseServer.click();
        updateSelectedKeyframeFiles();
        // console.log(files, "456");
    });

    flipImagesBox.on('click', (e) => {
        flipImages = e.target.checked;
    });

    zOrderBox.on('click', (e) => {
        zOrder = e.target.checked;
    });
    customSegmentSize.on('change', (e) => segmentSizeInput.prop('disabled', !e.target.checked));
    customOverlapSize.on('change', (e) => overlapSizeInput.prop('disabled', !e.target.checked));
    customCompressQuality.on('change', (e) => imageQualityInput.prop('disabled', !e.target.checked));

    segmentSizeInput.on('change', function() {
        let value = Math.clamp(
            +segmentSizeInput.prop('value'),
            +segmentSizeInput.prop('min'),
            +segmentSizeInput.prop('max')
        );

        segmentSizeInput.prop('value', value);
        segmentSize = value;
    });

    overlapSizeInput.on('change', function() {
        let value = Math.clamp(
            +overlapSizeInput.prop('value'),
            +overlapSizeInput.prop('min'),
            +overlapSizeInput.prop('max')
        );

        overlapSizeInput.prop('value', value);
        overlapSize = value;
    });

    imageQualityInput.on('change', function() {
        let value = Math.clamp(
            +imageQualityInput.prop('value'),
            +imageQualityInput.prop('min'),
            +imageQualityInput.prop('max')
        );

        imageQualityInput.prop('value', value);
        compressQuality = value;
    });

    // working
    submitCSVCreate.on('click', function(){
        
        if (files.length <= 0) {
            CSVMessage.css('color', 'red');
            CSVMessage.text('Need specify files for task');
            return;
        }

        let CSVkData = new FormData();
        CSVkData.append('project', window.location.pathname.split('/')[2]);

        for (let file of files) {
            CSVkData.append('data', file);
        }        
        // console.log(CSVkData, "submitCSVCreate");
        submitCSVCreate.prop('disabled', true);

        UploadCSVRequest(CSVkData, 
            () => submitCSVCreate.prop('disabled', false),
            () => {
                CSVMessage.css('color', 'red');
                CSVMessage.text("Please contact enginer");
            });
    });

    // add by jeff
    submitKeyframesCreate.on('click', function(){
        
        if (files.length <= 0) {
            KeyframeMessage.css('color', 'red');
            KeyframeMessage.text('Need specify files for task');
            return;
        }

        let KeyframesData = new FormData();
        KeyframesData.append('project', window.location.pathname.split('/')[2]);
        for (let file of files) {
            KeyframesData.append('data', file);
        }        
        // console.log(CSVkData, "submitCSVCreate");
        submitKeyframesCreate.prop('disabled', true);

        InsertImagesRequest(KeyframesData, 
            () => submitKeyframesCreate.prop('disabled', false),
            () => {
                KeyframeMessage.css('color', 'red');
                KeyframeMessage.text("Please contact enginer");
            });
    });




    submitCreate.on('click', function() {
        if (!validateName(name)) {
            taskMessage.css('color', 'red');
            taskMessage.text('Invalid task name');
            return;
        }

        if (!validateName(packagename)) {
            taskMessage.css('color', 'red');
            taskMessage.text('Invalid task packagename');
            return;
        }

        if (!validateLabels(labels)) {
            taskMessage.css('color', 'red');
            taskMessage.text('Invalid task labels');
            return;
        }

        if (!validateSegmentSize(segmentSize)) {
            taskMessage.css('color', 'red');
            taskMessage.text('Segment size out of range');
            return;
        }

        if (!validateOverlapSize(overlapSize, segmentSize)) {
            taskMessage.css('color', 'red');
            taskMessage.text('Overlap size must be positive and not more then segment size');
            return;
        }

        if (files.length <= 0) {
            taskMessage.css('color', 'red');
            taskMessage.text('Need specify files for task');
            return;
        }
        else if (files.length > maxUploadCount && source == 'local') {
            taskMessage.css('color', 'red');
            taskMessage.text('Too many files. Please use share functionality');
            return;
        }
        else if (source == 'local') {
            let commonSize = 0;
            for (let file of files) {
                commonSize += file.size;
            }
            if (commonSize > maxUploadSize) {
                taskMessage.css('color', 'red');
                taskMessage.text('Too big size. Please use share functionality');
                return;
            }
        }

        let taskData = new FormData();
        taskData.append('task_name', name);
        taskData.append('task_packagename', packagename);
        taskData.append('project', window.location.pathname.split('/')[2]);
        taskData.append('bug_tracker_link', bugTrackerLink);
        taskData.append('labels', labels);
        taskData.append('flip_flag', flipImages);
        taskData.append('z_order', zOrder);
        taskData.append('storage', source);

        if (customSegmentSize.prop('checked')) {
            taskData.append('segment_size', segmentSize);
        }
        if (customOverlapSize.prop('checked')) {
            taskData.append('overlap_size', overlapSize);
        }
        if (customCompressQuality.prop('checked')) {
            taskData.append('compress_quality', compressQuality);
        }

        for (let file of files) {
            taskData.append('data', file);
        }
        
        submitCreate.prop('disabled', true);
        createTaskRequest(taskData,
            () => {
                taskMessage.css('color', 'green');
                taskMessage.text('Successful request! Creating..');
            },
            () => window.location.reload(),
            (response) => {
                taskMessage.css('color', 'red');
                taskMessage.text(response);
            },
            () => submitCreate.prop('disabled', false),
            (status) => {
                taskMessage.css('color', 'blue');
                taskMessage.text(status);
            });
    });

    function updateSelectedFiles() {
        switch (files.length) {
        case 0:
            filesLabel.text('No Files');
            break;
        case 1:
            filesLabel.text(typeof(files[0]) == 'string' ? files[0] : files[0].name);
            break;
        default:
            filesLabel.text(files.length + ' files');
        }
    }

    // add by ericlou
    function updateSelectedCSVFiles() {
        switch (files.length) {
        case 0:
            CSVfilesLabel.text('No Files');
            break;
        case 1:
            CSVfilesLabel.text(typeof(files[0]) == 'string' ? files[0] : files[0].name);
            break;
        default:
            CSVfilesLabel.text(files.length + ' files');
        }
    }
    // add by jeff
    function updateSelectedKeyframeFiles() {
        switch (files.length) {
        case 0:
            keyframesfilesLabel.text('No Files');
            break;
        case 1:
            keyframesfilesLabel.text(typeof(files[0]) == 'string' ? files[0] : files[0].name);
            break;
        default:
            keyframesfilesLabel.text(files.length + ' files');
        }
    }

    function validateName(name) {
        let math = name.match('[a-zA-Z0-9()_ ]+');
        return math != null;
    }

    function validateLabels(labels) {
        let tmp = labels.replace(/\s/g,'');
        return tmp.length > 0;
        // to do good validator
    }

    function validateSegmentSize(segmentSize) {
        return (segmentSize >= 100 && segmentSize <= 50000);
    }

    function validateOverlapSize(overlapSize, segmentSize) {
        return (overlapSize >= 0 && overlapSize <= segmentSize - 1);
    }

    cancelCreate.on('click', () => createModal.addClass('hidden'));

    // add by eric
    dashboardUploadKeyframeButton.on('click', function() {
        localKeyframeUploader.click();
    });

    localKeyframeUploader.on('change', function(e) {
        keyframefiles = e.target.files;
        updateKeyframeFiles();
    });

    function updateKeyframeFiles() {
        switch (keyframefiles.length) {
        case 0:
            KeyframeUploaderLabel.text('No Files').css('color', 'black');
            $('#dashboardSubmitKeyframe').removeClass('hidden');
            break;
        case 1:
            KeyframeUploaderLabel.text(typeof(keyframefiles[0]) == 'string' ? keyframefiles[0] : keyframefiles[0].name).css('color', 'black');
            $('#dashboardSubmitKeyframe').removeClass('hidden');
            break;
        default:
            KeyframeUploaderLabel.text("cannot upload more than one keyframe list.").css('color', 'black');
            $('#dashboardSubmitKeyframe').addClass('hidden');
        }
    };

    SubmitKeyframe.on('click', function() {

        let keyframeData = new FormData();
        keyframeData.append('data', keyframefiles[0]);
        keyframeData.append('project', window.location.pathname.split('/')[2]);
        $.ajax({
            url: '/dashboard/update_keyframe',
            type: 'POST',
            data: keyframeData,
            contentType: false,
            processData: false,
            success: function(response) {

                if (response.data=='Success update frames'){
                    let message = 'Keyframe files successfully inserted';
                    KeyframeUploaderLabel.css('color', 'green');
                    KeyframeUploaderLabel.text("Upload Success.");
                    console.log(message);
                }
                else{
                    let message = 'Error';
                    showMessage(response);
                    onError();
                    console.log("error list",response.data);
                }

            },
            error: function(response) {
                KeyframeUploaderLabel.css('color', 'red');
                let message = 'Bad task request: ' + response.responseText;
                KeyframeUploaderLabel.text(message);
                throw Error(message);
            }
        });
    });

}


function setupTaskUpdater() {
    let updateModal = $('#dashboardUpdateModal');
    let oldLabels = $('#dashboardOldLabels');
    let newLabels = $('#dashboardNewLabels');
    let submitUpdate = $('#dashboardSubmitUpdate');
    let cancelUpdate = $('#dashboardCancelUpdate');

    updateModal[0].loadCurrentLabels = function() {
        $.ajax({
            url: 'get/task/' + window.cvat.dashboard.taskID,
            success: function(data) {
                let labels = new LabelsInfo(data.spec);
                oldLabels.attr('value', labels.normalize());
            },
            error: function(response) {
                oldLabels.attr('value', 'Bad request');
                let message = 'Bad task request: ' + response.responseText;
                throw Error(message);
            }
        });
    };

    cancelUpdate.on('click', function() {
        $('#dashboardNewLabels').prop('value', '');
        updateModal.addClass('hidden');
    });

    submitUpdate.on('click', () => UpdateTaskRequest(newLabels.prop('value')));
}


function setupSearch() {
    let searchInput_name = $("#dashboardSearchInput");
    let searchInput_packagename = $("#dashboardSearchInput_packagename");
    let searchInput_nickname = $("#dashboardSearchInput_nickname");
    let searchInput_createdate = $("#dashboardSearchInput_createdate");
    let searchSubmit = $("#dashboardSearchSubmit");

    let name = getUrlParameter('name') || "";
    searchInput_name.val(name);
    let packagename = getUrlParameter('packagename') || "";
    searchInput_packagename.val(packagename);
    let nickname = getUrlParameter('nickname') || "";
    searchInput_nickname.val(nickname);
    let createdate = getUrlParameter('createdate') || "";
    searchInput_createdate.val(createdate);

    searchSubmit.on('click', function() {
        let e = $.Event('keypress');
        e.keyCode = 13;
        searchInput_name.trigger(e);
    });

    $( "input[name*='search']" ).on('keypress', function(e) {
        if (e.keyCode != 13) return;
        let filter_name = searchInput_name.val();
        let filter_packagename = searchInput_packagename.val();
        let filter_nickname = searchInput_nickname.val();
        let filter_createdate = searchInput_createdate.val();
        if (!filter_name && !filter_packagename && !filter_nickname && !filter_createdate) window.location.search = "";
        else window.location.search = `name=${filter_name}&packagename=${filter_packagename}&nickname=${filter_nickname}&createdate=${filter_createdate}`;
    });

    function getUrlParameter(name) {
        let regex = new RegExp('[\\?&]' + name + '=([^&#]*)');
        let results = regex.exec(window.location.search);
        return results === null ? '' : decodeURIComponent(results[1].replace(/\+/g, ' '));
    }
}


/* Server requests */

function setPriorityRequest(selectTasks, inCompany , priority, successCallback)
{
    let priorityData = new FormData();
    priorityData.append('selectTasks', selectTasks);
    priorityData.append('inCompany', inCompany);
    priorityData.append('priority', priority);
    priorityData.append('project', window.location.pathname.split('/')[2]);
    $.ajax({
        url: 'set/tasks/priority',
        type: 'POST',
        data: priorityData,
        contentType: false,
        processData: false,
        success: successCallback,
    });
}

function createTaskRequest(oData, onSuccessRequest, onSuccessCreate, onError, onComplete, onUpdateStatus) {
    $.ajax({
        url: 'create/task',
        type: 'POST',
        data: oData,
        contentType: false,
        processData: false,
        success: function(data) {
            onSuccessRequest();
            requestCreatingStatus(data);
        },
        error: function(data) {
            onComplete();
            onError(data.responseText);
        }
    });

    function requestCreatingStatus(data) {
        let tid = data.tid;
        let request_frequency_ms = 1000;
        let done = false;

        let requestInterval = setInterval(function() {
            $.ajax({
                url: 'check/task/' + tid,
                success: receiveStatus,
                error: function(data) {
                    clearInterval(requestInterval);
                    onComplete();
                    onError(data.responseText);
                }
            });
        }, request_frequency_ms);

        function receiveStatus(data) {
            if (done) return;
            if (data['state'] == 'created') {
                done = true;
                clearInterval(requestInterval);
                onComplete();
                onSuccessCreate();
            }
            else if (data['state'] == 'error') {
                done = true;
                clearInterval(requestInterval);
                onComplete();
                onError(data.stderr);
            }
            else if (data['state'] == 'started' && 'status' in data) {
                onUpdateStatus(data['status']);
            }
        }
    }
}

function UpdateTaskRequest(labels) {
    let oData = new FormData();
    oData.append('labels', labels);

    $.ajax({
        url: 'update/task/' + window.cvat.dashboard.taskID,
        type: 'POST',
        data: oData,
        contentType: false,
        processData: false,
        success: function() {
            $('#dashboardNewLabels').prop('value', '');
            showMessage('Task successfully updated.');
        },
        error: function(data) {
            showMessage('Task update error. ' + data.responseText);
        },
        complete: () => $('#dashboardUpdateModal').addClass('hidden')
    });
}


function RemoveTaskRequest() {
    confirm('The action can not be undone. Are you sure?', confirmCallback);

    function confirmCallback() {
        $.ajax ({
            url: 'delete/task/' + window.cvat.dashboard.taskID,
            success: function() {
                $(`#dashboardTask_${window.cvat.dashboard.taskID}`).remove();
                showMessage('Task removed.');
            },
            error: function(response) {
                let message = 'Abort. Reason: ' + response.responseText;
                showMessage(message);
                throw Error(message);
            }
        });
    }
}


function uploadAnnotationRequest() {
    let input = $('<input>').attr({
        type: 'file',
        accept: 'text/xml'
    }).on('change', loadXML).click();

    function loadXML(e) {
        input.remove();
        let overlay = showOverlay("File is being uploaded..");
        let file = e.target.files[0];
        let fileReader = new FileReader();
        fileReader.onload = (e) => parseFile(e, overlay);
        fileReader.readAsText(file);
    }

    function parseFile(e, overlay) {
        let xmlText = e.target.result;
        overlay.setMessage('Request task data from server..');
        $.ajax({
            url: 'get/task/' + window.cvat.dashboard.taskID,
            success: function(data) {
                let annotationParser = new AnnotationParser({
                    start: 0,
                    stop: data.size,
                    image_meta_data: data.image_meta_data,
                    flipped: data.flipped
                }, new LabelsInfo(data.spec));

                let asyncParse = function() {
                    let parsed = null;
                    try {
                        parsed = annotationParser.parse(xmlText);
                    }
                    catch(error) {
                        overlay.remove();
                        showMessage("Parsing errors was occured. " + error);
                        return;
                    }

                    let asyncSave = function() {
                        $.ajax({
                            url: 'save/annotation/task/' + window.cvat.dashboard.taskID,
                            type: 'POST',
                            data: JSON.stringify(parsed),
                            contentType: 'application/json',
                            success: function() {
                                let message = 'Annotation successfully uploaded';
                                showMessage(message);
                            },
                            error: function(response) {
                                let message = 'Annotation uploading errors was occured. ' + response.responseText;
                                showMessage(message);
                            },
                            complete: () => overlay.remove()
                        });
                    };

                    overlay.setMessage('Annotation is being saved..');
                    setTimeout(asyncSave);
                };

                overlay.setMessage('File is being parsed..');
                setTimeout(asyncParse);
            },
            error: function(response) {
                overlay.remove();
                let message = 'Bad task request: ' + response.responseText;
                showMessage(message);
                throw Error(message);
            }
        });
    }
}

// add by eric
function UploadCSVRequest(oData, onSuccessRequest, onError) {
    $.ajax({
        url: '/dashboard/upload_XML',
        type: 'POST',
        data: oData,
        contentType: false,
        processData: false,
        success: function(response) {
            if (response){
                let message = 'CSV files successfully uploaded';
                showMessage(message);
                onSuccessRequest();
            }
        },
        error: function() {
            let message = 'Error';
            showMessage(message);
            onError();
        }
    });
}

// add by jeff
function InsertImagesRequest(oData, onSuccessRequest, onError) {
    $.ajax({
        url: '/dashboard/insert_images',
        type: 'POST',
        data: oData,
        contentType: false,
        processData: false,
        success: function(response) {
            if (response.data=='Success insert_frames'){
                let message = 'Keyframe files successfully inserted';
                showMessage(message);
                onSuccessRequest();
            }
            else{
                let message = 'Error';
                showMessage(response);
                onError();
                console.log("error list",response.data);
            }
        },
        error: function(response) {
            let message = 'Error';
            showMessage(response);
            onError();
        }
    });
}
