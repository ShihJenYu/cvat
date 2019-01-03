/*
 * Copyright (C) 2018 Intel Corporation
 *
 * SPDX-License-Identifier: MIT
 */

/* exported PlayerModel PlayerController PlayerView */
"use strict";
var keyframeStage = null;
var wasSend = false;
class FrameProvider extends Listener {
    constructor(stop, tid) {
        super('onFrameLoad', () => this._loaded);
        this._MAX_LOAD = 500;

        this._stack = [];
        this._loadInterval = null;
        this._required = null;
        this._loaded = null;
        this._loadAllowed = true;
        this._preloadRunned = false;
        this._loadCounter = this._MAX_LOAD;
        this._frameCollection = {};
        this._stop = stop;
        this._tid = tid;
    }
    get tid() {
        return this._tid;
    }

    require(frame) {
        if (frame in this._frameCollection) {
            this._preload(frame);
            return this._frameCollection[frame];
        }
        this._required = frame;
        this._loadCounter = this._MAX_LOAD;
        this._load();
        return null;
    }

    _onImageLoad(image, frame) {
        let next = frame + 1;
        if (next <= this._stop && this._loadCounter > 0) {
            this._stack.push(next);
        }
        this._loadCounter--;
        this._loaded = frame;
        this._frameCollection[frame] = image;
        this._loadAllowed = true;
        image.onload = null;
        image.onerror = null;
        this.notify();
    }

    _preload(frame) {
        if (this._preloadRunned) {
            return;
        }

        let last = Math.min(this._stop, frame + Math.ceil(this._MAX_LOAD / 2));
        if (!(last in this._frameCollection)) {
            // modify by Eric, original idx = frame + 1
            for (let idx = frame + 1; idx <= last; idx ++) {
                if (!(idx in this._frameCollection)) {
                    this._loadCounter = this._MAX_LOAD - (idx - frame);
                    this._stack.push(idx);
                    this._preloadRunned = true;
                    this._load();
                    return;
                }
            }
        }
    }

    _load() {
        if (!this._loadInterval) {
            this._loadInterval = setInterval(function() {
                if (!this._loadAllowed) {
                    return;
                }

                if (this._loadCounter <= 0) {
                    this._stack = [];
                }

                if (!this._stack.length && this._required == null) {
                    clearInterval(this._loadInterval);
                    this._preloadRunned = false;
                    this._loadInterval = null;
                    return;
                }

                if (this._required != null) {
                    this._stack.push(this._required);
                    this._required = null;
                }

                let frame = this._stack.pop();
                if (frame in this._frameCollection) {
                    this._loadCounter--;
                    let next = frame + 1;
                    if (next <= this._stop && this._loadCounter > 0) {
                        this._stack.push(frame + 1);
                    }
                    return;
                }

                // If load up to last frame, no need to load previous frames from stack
                if (frame === this._stop) {
                    this._stack = [];
                }

                this._loadAllowed = false;
                let image = new Image();
                image.onload = this._onImageLoad.bind(this, image, frame);
                image.onerror = () => {
                    this._loadAllowed = true;
                    image.onload = null;
                    image.onerror = null;
                };
                image.src = `get/task/${this._tid}/frame/${frame}`;
            }.bind(this), 25);
        }
    }
}


const MAX_PLAYER_SCALE = 10;
const MIN_PLAYER_SCALE = 0.1;

class PlayerModel extends Listener {
    // add by jeff, set frame in playermodel
    constructor(job, playerSize, myframe) {
        super('onPlayerUpdate', () => this);
        this._frame = {
            start: (myframe!= null)? myframe: job.start,
            stop: (myframe!= null)? myframe: job.stop,
            current: (myframe!= null)? myframe: job.start,
            previous: null
        };

        this._settings = {
            multipleStep: 10,
            fps: 15,
            resetZoom: job.mode === 'annotation'
        };

        this._playInterval = null;
        this._pauseFlag = null;
        this._frameProvider = new FrameProvider(this._frame.stop, job.taskid);
        this._continueAfterLoad = false;
        this._continueTimeout = null;

        this._rewinding = false;

        this._geometry = {
            scale: 1,
            left: 0,
            top: 0,
            width: playerSize.width,
            height: playerSize.height,
        };

        this._frameProvider.subscribe(this);

    }

    // add by jeff
    setframes(mframe) {
        this._frame.start = mframe;
        this._frame.stop = mframe;
        this._frame.current = mframe;
    }

    do(){
        console.log(this._frame.current);
    }

    get frames() {
        return {
            start: this._frame.start,
            stop: this._frame.stop,
            current: this._frame.current,
            previous: this._frame.previous
        };
    }

    get geometry() {
        return {
            scale: this._geometry.scale,
            top: this._geometry.top,
            left: this._geometry.left
        };
    }

    get playing() {
        return this._playInterval != null;
    }

    get image() {
        return this._frameProvider.require(this._frame.current);
    }

    get tid() {
        
        return this._frameProvider.tid;
    }

    get resetZoom() {
        return this._settings.resetZoom;
    }

    get multipleStep() {
        return this._settings.multipleStep;
    }

    set fps(value) {
        this._settings.fps = value;
    }

    set multipleStep(value) {
        this._settings.multipleStep = value;
    }

    set resetZoom(value) {
        this._settings.resetZoom = value;
    }

    ready() {
        return this._frame.previous === this._frame.current;
    }

    onFrameLoad(last) {  // callback for FrameProvider instance
        if (last === this._frame.current) {
            if (this._continueTimeout) {
                clearTimeout(this._continueTimeout);
                this._continueTimeout = null;
            }

            // If need continue playing after load, set timeout for additional frame download
            if (this._continueAfterLoad) {
                this._continueTimeout = setTimeout(function() {
                    // If you still need to play, start it
                    this._continueTimeout = null;
                    if (this._continueAfterLoad) {
                        this._continueAfterLoad = false;
                        this.play();
                    }   // Else update the frame
                    else {
                        this.shift(0);
                    }
                }.bind(this), 5000);
            }
            else {  // Just update frame if no need to play
                this.shift(0);
            }
        }
    }

    play() {
        this._pauseFlag = false;
        $('#saveButton').click();
        this._playInterval = setInterval(function() {
            if (this._pauseFlag) {      // pause method without notify (for frame downloading)
                if (this._playInterval) {
                    clearInterval(this._playInterval);
                    this._playInterval = null;
                }
                return;
            }
            
            let skip = Math.max( Math.floor(this._settings.fps / 25), 1 );
            if (!this.shift(skip)) this.pause();   // if not changed, pause
        }.bind(this), 1000 / this._settings.fps);
    }

    pause() {
        if (this._playInterval) {
            clearInterval(this._playInterval);
            this._playInterval = null;
            this._pauseFlag = true;
            this.notify();
        }
    }

    updateGeometry(geometry) {
        this._geometry.width = geometry.width;
        this._geometry.height = geometry.height;
    }

    shift(delta, absolute) {
        // Modify by ericlou.
        //console.log(delta);
        if(LOCKALL)return;

        if (['resize', 'drag'].indexOf(window.cvat.mode) != -1) {
            return false;
        }

        this._continueAfterLoad = false;  // default reset continue
        this._frame.current = Math.clamp(
            absolute ? delta : this._frame.current + delta,
            this._frame.start,
            this._frame.stop
        );
        let frame = this._frameProvider.require(this._frame.current);
        if (!frame) {
            this._continueAfterLoad = this.playing;
            this._pauseFlag = true;
            this.notify();
            return false;
        }

        window.cvat.player.frames.current = this._frame.current;
        window.cvat.player.geometry.frameWidth = frame.width;
        window.cvat.player.geometry.frameHeight = frame.height;

        Logger.addEvent(Logger.EventType.changeFrame, {
            from: this._frame.previous,
            to: this._frame.current,
        });

        let changed = this._frame.previous != this._frame.current;
        if (changed){
            // add by jeff
            window.cvat.groupingData.cleanCurrent();
            $('#group_current_label').text('無');
            
            $('.dontcare').remove();
            $('.detectpoint').remove();
            $('.detectpointAim').remove();
            saveByShift = true;
            
            if(this._frame.previous!=null && !this.playing && !this._rewinding) {
                $('#saveButton').click();
            }

        }
        if (this._settings.resetZoom || this._frame.previous === null) {  // fit in annotation mode or once in interpolation mode
            this._frame.previous = this._frame.current;
            this.fit();     // notify() inside the fit()
        }
        else {
            this._frame.previous = this._frame.current;
            this.notify();
        }

        return changed;
    }

    fit() {
        let img = this._frameProvider.require(this._frame.current);
        if (!img) return;
        this._geometry.scale = Math.min(this._geometry.width / img.width, this._geometry.height / img.height);
        this._geometry.top = (this._geometry.height - img.height * this._geometry.scale) / 2;
        this._geometry.left = (this._geometry.width - img.width * this._geometry.scale ) / 2;

        window.cvat.player.geometry.scale = this._geometry.scale;
        this.notify();
    }

    focus(xtl, xbr, ytl, ybr) {
        let img = this._frameProvider.require(this._frame.current);
        if (!img) return;
        let fittedScale = Math.min(this._geometry.width / img.width, this._geometry.height / img.height);

        let boxWidth = xbr - xtl;
        let boxHeight = ybr - ytl;
        let wScale = this._geometry.width / boxWidth;
        let hScale = this._geometry.height / boxHeight;
        this._geometry.scale = Math.min(wScale, hScale);
        this._geometry.scale = Math.min(this._geometry.scale, MAX_PLAYER_SCALE);
        this._geometry.scale = Math.max(this._geometry.scale, MIN_PLAYER_SCALE);

        if (this._geometry.scale < fittedScale) {
            this._geometry.scale = fittedScale;
            this._geometry.top = (this._geometry.height - img.height * this._geometry.scale) / 2;
            this._geometry.left = (this._geometry.width - img.width * this._geometry.scale ) / 2;
        }
        else {
            this._geometry.left = (this._geometry.width / this._geometry.scale - xtl * 2 - boxWidth) * this._geometry.scale / 2;
            this._geometry.top = (this._geometry.height / this._geometry.scale - ytl * 2 - boxHeight) * this._geometry.scale / 2;
        }
        window.cvat.player.geometry.scale = this._geometry.scale;
        this._frame.previous = this._frame.current;     // fix infinite loop via playerUpdate->collectionUpdate*->AAMUpdate->playerUpdate->...
        this.notify();

    }

    scale(x, y, value) {
        if (!this._frameProvider.require(this._frame.current)) return;

        let currentCenter = {
            x: (x - this._geometry.left) / this._geometry.scale,
            y: (y - this._geometry.top) / this._geometry.scale
        };

        this._geometry.scale = value > 0 ? this._geometry.scale * 6/5 : this._geometry.scale * 5/6;
        this._geometry.scale = Math.min(this._geometry.scale, MAX_PLAYER_SCALE);
        this._geometry.scale = Math.max(this._geometry.scale, MIN_PLAYER_SCALE);

        let newCenter = {
            x: (x - this._geometry.left) / this._geometry.scale,
            y: (y - this._geometry.top) / this._geometry.scale
        };

        this._geometry.left += (newCenter.x - currentCenter.x) * this._geometry.scale;
        this._geometry.top += (newCenter.y - currentCenter.y) * this._geometry.scale;

        window.cvat.player.geometry.scale = this._geometry.scale;
        this.notify();
    }

    move(topOffset, leftOffset) {
        this._geometry.top += topOffset;
        this._geometry.left += leftOffset;
        this.notify();
    }
}


class PlayerController {
    constructor(playerModel, activeTrack, find, playerOffset) {
        this._model = playerModel;
        this._find = find;
        this._rewinding = false;
        this._moving = false;
        //this._moving_key = false;
        this._leftOffset = playerOffset.left;
        this._topOffset = playerOffset.top;
        this._lastClickX = 0;
        this._lastClickY = 0;
        this._moveFrameEvent = null;
        this._events = {
            jump: null,
            move: null,
        };

        setupPlayerShortcuts.call(this, playerModel);

        function setupPlayerShortcuts(playerModel) {
            let nextHandler = Logger.shortkeyLogDecorator(function(e) {
                this.next();
                e.preventDefault();
            }.bind(this));

            let prevHandler = Logger.shortkeyLogDecorator(function(e) {
                this.previous();
                e.preventDefault();
            }.bind(this));

            let nextKeyFrameHandler = Logger.shortkeyLogDecorator(function() {
                let active = activeTrack();
                if (active && active.type.split('_')[0] === 'interpolation') {
                    let nextKeyFrame = active.nextKeyFrame();
                    if (nextKeyFrame != null) {
                        this._model.shift(nextKeyFrame, true);
                    }
                }
            }.bind(this));

            let prevKeyFrameHandler = Logger.shortkeyLogDecorator(function() {
                let active = activeTrack();
                if (active && active.type.split('_')[0] === 'interpolation') {
                    let prevKeyFrame = active.prevKeyFrame();
                    if (prevKeyFrame != null) {
                        this._model.shift(prevKeyFrame, true);
                    }
                }
            }.bind(this));


            let nextFilterFrameHandler = Logger.shortkeyLogDecorator(function(e) {
                if(isAdminFlag){
                    let frame = this._find(1);
                    if (frame != null) {
                        this._model.shift(frame, true);
                    }
                }
                e.preventDefault();
            }.bind(this));

            let prevFilterFrameHandler = Logger.shortkeyLogDecorator(function(e) {
                if(isAdminFlag){
                    let frame = this._find(-1);
                    if (frame != null) {
                        this._model.shift(frame, true);
                    }
                }
                e.preventDefault();
            }.bind(this));


            let forwardHandler = Logger.shortkeyLogDecorator(function() {
                this.forward();
            }.bind(this));

            let backwardHandler = Logger.shortkeyLogDecorator(function() {
                this.backward();
            }.bind(this));

            let playPauseHandler = Logger.shortkeyLogDecorator(function() {
                if (playerModel.playing) {
                    this.pause();
                }
                else {
                    this.play();
                }
                return false;
            }.bind(this));


            // let enableMovingKeyHandler = Logger.shortkeyLogDecorator(function() {
            //     this._moving_key = true;
            // }.bind(this));
            // let disableMovingKeyHandler = Logger.shortkeyLogDecorator(function() {
            //     this._moving_key = false;
            // }.bind(this));

            let shortkeys = window.cvat.config.shortkeys;

            Mousetrap.bind(shortkeys["next_frame"].value, nextHandler, 'keydown');
            Mousetrap.bind(shortkeys["prev_frame"].value, prevHandler, 'keydown');
            Mousetrap.bind(shortkeys["next_filter_frame"].value, nextFilterFrameHandler, 'keydown');
            Mousetrap.bind(shortkeys["prev_filter_frame"].value, prevFilterFrameHandler, 'keydown');
            Mousetrap.bind(shortkeys["next_key_frame"].value, nextKeyFrameHandler, 'keydown');
            Mousetrap.bind(shortkeys["prev_key_frame"].value, prevKeyFrameHandler, 'keydown');
            Mousetrap.bind(shortkeys["forward_frame"].value, forwardHandler, 'keydown');
            Mousetrap.bind(shortkeys["backward_frame"].value, backwardHandler, 'keydown');
            Mousetrap.bind(shortkeys["play_pause"].value, playPauseHandler, 'keydown');
            // Mousetrap.bind('alt', enableMovingKeyHandler, 'keydown');
            // Mousetrap.bind('alt', disableMovingKeyHandler, 'keyup');
        }
    }

    zoom(e) {
        let x = e.originalEvent.pageX - this._leftOffset;
        let y = e.originalEvent.pageY - this._topOffset;

        let zoomImageEvent = Logger.addContinuedEvent(Logger.EventType.zoomImage);
        if (e.originalEvent.deltaY < 0) {
            this._model.scale(x, y, 1);
        }
        else {
            this._model.scale(x, y, -1);
        }
        zoomImageEvent.close();
        e.preventDefault();
    }

    fit() {
        this._model.fit();
    }

    frameMouseDown(e) {
        if ((e.which === 1 && !window.cvat.mode) || (e.which === 2)) {
            this._moving = true;
            this._lastClickX = e.clientX;
            this._lastClickY = e.clientY;
            e.preventDefault();
        }
    }

    frameMouseUp() {
        this._moving = false;
        if (this._events.move) {
            this._events.move.close();
            this._events.move = null;
        }
    }

    frameMouseMove(e) {
        if (this._moving && move_background) {
            if (!this._events.move) {
                this._events.move = Logger.addContinuedEvent(Logger.EventType.moveImage);
            }

            let topOffset = e.clientY - this._lastClickY;
            let leftOffset = e.clientX - this._lastClickX;
            this._lastClickX = e.clientX;
            this._lastClickY = e.clientY;
            this._model.move(topOffset, leftOffset);
        }
    }

    progressMouseDown(e) {
        $('#saveButton').click();
        this._rewinding = true;
        this._model._rewinding = true;
        this._rewind(e);
    }

    progressMouseUp() {
        this._rewinding = false;
        this._model._rewinding = false;
        if (this._events.jump) {
            this._events.jump.close();
            this._events.jump = null;
        }
    }

    progressMouseMove(e) {
        this._rewind(e);
    }

    _rewind(e) {
        if (this._rewinding) {
            if (!this._events.jump) {
                this._events.jump = Logger.addContinuedEvent(Logger.EventType.jumpFrame);
            }

            let frames = this._model.frames;
            let progressWidth = e.target.clientWidth;
            let x = e.clientX + window.pageXOffset - e.target.offsetLeft;
            let percent = x / progressWidth;
            let targetFrame = Math.round((frames.stop - frames.start) * percent);
            this._model.pause();
            this._model.shift(targetFrame + frames.start, true);
        }
    }

    changeStep(e) {
        let value = Math.clamp(+e.target.value, +e.target.min, +e.target.max);
        e.target.value = value;
        this._model.multipleStep = value;
    }

    changeFPS(e) {
        let fpsMap = {
            1: 1,
            2: 5,
            3: 12,
            4: 25,
            5: 50,
            6: 100,
        };
        let value = Math.clamp(+e.target.value, 1, 6);
        this._model.fps = fpsMap[value];
    }

    changeResetZoom(e) {
        this._model.resetZoom = e.target.checked;
    }

    play() {
        this._model.play();
    }

    pause() {
        this._model.pause();
    }

    next() {
        this._model.shift(1);
        this._model.pause();
    }

    // add by Jeff
    next_random_frame() {
        // console.log("in next_random_frame");

        // modify by eric
        var all_dectect_points = window.document.querySelectorAll("*[class^=\"detect\"]");

        for (var i = 0; i < all_dectect_points.length; i++){
            let remove_detect_point = all_dectect_points[i].className.baseVal;
            $("."+remove_detect_point).remove();
        }

        let jid = this._model.tid;//window.location.href.match('id=[0-9]+')[0].slice(3);
        var data;
        $.ajax({
            url: "save/currentJob",
            dataType: "json",
            async: false,
            success: function(respone) {
                console.log("done save/currentJob", respone);
                data = respone;
                wasSend = true;
                $('#sendButton').prop('disabled',true);
                $('#sendButton').unbind('click');
            },
            error: serverError
        });
        window.cvat.data.clear();
        $('#frameContent').addClass('hidden');
        $('#frameBackground').addClass('hidden');
        //$('#frameLoadingAnim').removeClass('hidden');
        
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
                            }
                            else {
                                passreload = true;
                                window.location.replace(window.location.href);
                            }
                        });
                    }
                },
                否: {
                    keys: ['esc'],
                    action: function(){
                        LOCKALL = true;
                        console.log("cancel,you need to get new work");
                        $('#talkToUser').removeClass('hidden');
                        $('#talkToUser text').text("你剛剛按了否, 想再領取工作, 請重新整理此網頁");
                    }
                }
            }
        });
    }

    previous() {
        this._model.shift(-1);
        this._model.pause();
    }

    first() {
        this._model.shift(this._model.frames.start, true);
        this._model.pause();
    }

    last() {
        this._model.shift(this._model.frames.stop, true);
        this._model.pause();
    }

    forward() {
        this._model.shift(this._model.multipleStep);
        this._model.pause();
    }

    backward() {
        this._model.shift(-this._model.multipleStep);
        this._model.pause();
    }

    seek(frame) {
        this._model.shift(frame, true);
    }
}


class PlayerView {
    constructor(playerModel, playerController) {
        this._controller = playerController;
        this._playerUI = $('#playerFrame');
        this._playerBackgroundUI = $('#frameBackground');
        this._playerContentUI = $('#frameContent');
        this._playerGridUI = $('#frameGrid');
        this._progressUI = $('#playerProgress');
        this._loadingUI = $('#frameLoadingAnim');
        this._playButtonUI = $('#playButton');
        this._pauseButtonUI = $('#pauseButton');
        this._nextButtonUI = $('#nextButton');
        this._prevButtonUI = $('#prevButton');
        this._multipleNextButtonUI = $('#multipleNextButton');
        this._multiplePrevButtonUI = $('#multiplePrevButton');
        this._firstButtonUI = $('#firstButton');
        this._lastButtonUI = $('#lastButton');
        this._playerStepUI = $('#playerStep');
        this._playerSpeedUI = $('#speedSelect');
        this._resetZoomUI = $('#resetZoomBox');
        // add by eric
        this._frameNumber = $('#frameNumber'); 
        this._playerGridPattern = $('#playerGridPattern');
        this._playerGridPath = $('#playerGridPath');
        this._contextMenuUI = $('#playerContextMenu');
        // add by jeff
        this._isKeyFrame = $('#isKeyFrame');
        this._isComplete = $('#isComplete');
        this._isRedo = $('#isRedo');
        this._saveRedoComment = $('#saveRedoComment');
        this._redoComment = $('#redoComment');
        this._redoComment.on('keypress keydown keyup', (e) => e.stopPropagation());
        this._nextButtonFlag = $('#nextButtonFlag');
        this._sendButton = $('#sendButton');

        $('*').on('mouseup', () => this._controller.frameMouseUp());
        this._playerUI.on('wheel', (e) => this._controller.zoom(e));
        this._playerUI.on('dblclick', () => this._controller.fit());
        this._playerContentUI.on('mousedown', (e) => this._controller.frameMouseDown(e));
        this._playerUI.on('mousemove', (e) => this._controller.frameMouseMove(e));
        this._progressUI.on('mousedown', (e) => this._controller.progressMouseDown(e));
        this._progressUI.on('mouseup', () => this._controller.progressMouseUp());
        this._progressUI.on('mousemove', (e) => this._controller.progressMouseMove(e));
        this._playButtonUI.on('click', () => this._controller.play());
        this._pauseButtonUI.on('click', () => this._controller.pause());
        this._nextButtonUI.on('click', () => this._controller.next());
        this._prevButtonUI.on('click', () => this._controller.previous());
        this._multipleNextButtonUI.on('click', () => this._controller.forward());
        this._multiplePrevButtonUI.on('click', () => this._controller.backward());
        this._firstButtonUI.on('click', () => this._controller.first());
        this._lastButtonUI.on('click', () => this._controller.last());
        this._playerSpeedUI.on('change', (e) => this._controller.changeFPS(e));
        this._resetZoomUI.on('change', (e) => this._controller.changeResetZoom(e));
        this._playerStepUI.on('change', (e) => this._controller.changeStep(e));
        this._frameNumber.on('change', (e) =>
        {
            if (Number.isInteger(+e.target.value)) {
                this._controller.seek(+e.target.value);
                blurAllElements();
                $("#frameNumber_show").prop("value", parseInt($("#frameNumber").prop("value"))+1);
                console.log( $("#frameNumber_show").prop("value"));
            }
        });

        // add by eric
        // working
        let SubmitKeyframe = $('#Submit_Cato');
        SubmitKeyframe.on('click', function() {

            var BackLight_value = ""
            var Tunnel_value = ""
            var underbridge_value = ""
            var Time_value = $('#Select_VideoCatogory_Time').val();
            var Weather_value = $('#Select_VideoCatogory_Weather').val();
            var Way_value = $('#Select_VideoCatogory_Way').val();
         
            if ($("#Select_VideoCatogory_BackLight").is(":checked")){
                BackLight_value = "逆光"
            }
            if ($("#Select_VideoCatogory_Tunnel").is(":checked")){
                Tunnel_value = "隧道"
            }
            if ($("#Select_VideoCatogory_underbridge").is(":checked")){
                underbridge_value = "有經過(橋下、涵洞)"
            }
            
            var Catogory_out = Time_value + "," + Weather_value + "," + Way_value + "," + BackLight_value + "," + Tunnel_value + "," + underbridge_value

            $.ajax ({
                url: `set/task/${playerModel.tid}/catogory/${Catogory_out}`,
                success: function(response) {
                    console.log(Catogory_out);
                },
                error: function(response) {
                    let message = 'Abort. Reason: ' + response.responseText;
                    showMessage(message);
                }
            });  
        });

        $("#frameNumber_show").on('change', (e) => {
            $("#frameNumber").prop("value", +e.target.value - 1);
            this._controller.seek(parseInt($("#frameNumber").prop("value")));
            blurAllElements();
            console.log("asdasdasddasdsad");
            console.log( $("#frameNumber").prop("value"));
            //$('#select_keyframes').trigger('focusout');
            console.log("dsadsadsadsa");
        });

        // add by jeff
        this._isKeyFrame.unbind('click').on('click', () => {
            if(window.location.pathname.split('/')[1] != 'fcw_training'){
                $('#isKeyFrame').prop('checked',true);
                return;
            }
            console.log(window.cvat.frameInfo);
            $('#isKeyFrame').prop('disabled',true);
            let flag = $('#isKeyFrame').prop('checked');
            console.log(flag);
            if(flag) {
                serverRequest(`set/task/${playerModel.tid}/frame/${playerModel.frames.current}/isKeyFrame/${+flag}`, function(response){
                    console.log(response);
                    let keyframes = response.frames.sort((a, b) => a - b)
                    console.log("frames",keyframes);
                    $("#select_keyframes").empty();
                    $('#select_keyframes').append($("<option></option>").attr("value","null").text("null"));
                    keyframes.forEach(function(value) {
                        $('#select_keyframes').append($("<option></option>").attr("value",value+1).text(value+1));
                    });
                    $("#select_keyframes").prop("value",playerModel.frames.current+1);
                    let frame = playerModel.frames.current;
                    window.cvat.frameInfo[frame] = {'user':'',
                                                    'current':false,
                                                    'user_submit':false,
                                                    'need_modify':false,
                                                    'checked':false,
                                                    'comment':'',
                                                    'defaultCategory':'',
                                                    'extraCategory':''};
                    console.log(window.cvat.frameInfo);
                    resetStatusColumn(playerModel.tid, frame);
                    $('#isKeyFrame').prop('disabled',false);
                });
            }
            else {
                serverRequest(`get/task/${playerModel.tid}/frame/${playerModel.frames.current}/keyframeStage`, function(response) {
                    // console.log("in get keyframe stage",response);
                    if(response.current||response.need_modify||response.annotator!='')
                    {
                        $('#isKeyFrame').prop('checked',true);
                        $('#isKeyFrame').prop('disabled',false);
                        resetStatusColumn(playerModel.tid, playerModel.frames.current);
                        $.dialog({
                            title: 'You can not do it !',
                            content: '已有標記員使用過',
                            boxWidth: '30%',
                            useBootstrap: false,
                        });
                    }
                    else
                    {
                        serverRequest(`set/task/${playerModel.tid}/frame/${playerModel.frames.current}/isKeyFrame/${+flag}`, function(response) {
                            console.log(response);
                            let keyframes = response.frames.sort((a, b) => a - b)
                            console.log("frames",keyframes);
                            $("#select_keyframes").empty();
                            $('#select_keyframes').append($("<option></option>").attr("value","null").text("null"));
                            keyframes.forEach(function(value) {
                                $('#select_keyframes').append($("<option></option>").attr("value",value+1).text(value+1));
                            });
                            $("#select_keyframes").prop("value","null");

                            let frame = playerModel.frames.current;
                            delete window.cvat.frameInfo[frame];
                            console.log(window.cvat.frameInfo);

                            $('#isComplete').prop('disabled',false);
                            $('#isComplete_text').prop('disabled',false);
                            $('#isRedo').prop('disabled',false);
                            $('#isRedo_text').prop('disabled',false);
                            $('#redoComment').prop('disabled',false);
                            $('#saveRedoComment').prop('disabled',false);

                            $('#isKeyFrame').prop('disabled',false);
                        });
                    }
                });
            }
        });
        this._isComplete.unbind('click').on('click', () => {
            $('#isComplete').prop('disabled',true);
            let flag = $('#isComplete').prop('checked');
            console.log(flag);
            serverRequest(`set/task/${playerModel.tid}/frame/${playerModel.frames.current}/isComplete/${+flag}`, function(response) {
                console.log(response);
                let frame = playerModel.frames.current;
                window.cvat.frameInfo[frame].checked = flag;
                resetStatusColumn(playerModel.tid, frame);
                console.log(window.cvat.frameInfo);

                $('#isComplete').prop('disabled',false);
            });
        });
        this._saveRedoComment.unbind('click').on('click', () => {
            $('#saveRedoComment').prop('disabled',true);
            let comment = $('#redoComment').prop('value');
            if (comment==''){
                comment = 'ok';
            }
            serverRequest(`set/task/${playerModel.tid}/frame/${playerModel.frames.current}/redoComment/${comment}`, function(response) {
                console.log(response);
                let frame = playerModel.frames.current;
                window.cvat.frameInfo[frame].comment = comment;
                resetStatusColumn(playerModel.tid, frame);
                console.log(window.cvat.frameInfo);
                $('#saveRedoComment').prop('disabled',false);
            });
        });
        this._isRedo.unbind('click').on('click', () => {
            if($('#isRedo').prop('checked')!=false){
                $('#isRedo').prop('checked',false);
                $.confirm({
                    title: 'Comment!',
                    content: '' +
                    '<form action="" class="formComment">' +
                    '<div class="form-group">' +
                    '<label>Enter something here </label>' +
                    '<input type="text" placeholder="your comment ..." class="comment form-control" required />' +
                    '</div>' +
                    '</form>',
                    boxWidth: '30%',
                    useBootstrap: false,
                    draggable: false,
                    buttons: {
                        formSubmit: {
                            text: 'Submit',
                            btnClass: 'btn-blue',
                            action: function () {
                                let comment = this.$content.find('.comment').val();
                                if(!comment){
                                    $.alert('provide a valid comment');
                                    return false;
                                }
                                let frame = playerModel.frames.current;
                                serverRequest(`set/task/${playerModel.tid}/frame/${playerModel.frames.current}/isRedo/${+true}`, function(response) {
                                    console.log(response);
                                    window.cvat.frameInfo[frame].need_modify = true;
                                    serverRequest(`set/task/${playerModel.tid}/frame/${playerModel.frames.current}/redoComment/${comment}`, function(response) {
                                        console.log(response);
                                        window.cvat.frameInfo[frame].comment = comment;
                                        resetStatusColumn(playerModel.tid, frame);
                                        console.log(window.cvat.frameInfo);
                                    });
                                });
                            }
                        },
                        cancel: function () {
                            //close
                        },
                    },
                    onContentReady: function () {
                        // bind to events
                        var jc = this;
                        this.$content.find('.comment').on('keypress keydown keyup', (e) => e.stopPropagation());
                        this.$content.find('form').on('submit', function (e) {
                            // if the user submits the form by pressing enter in the field.
                            e.preventDefault();
                            jc.$$formSubmit.trigger('click'); // reference the button and click it
                        });
                    }
                });
            }
        });

        this._sendButton.unbind('click').on('click', () => {
            var me = $(this);
            $.confirm({
                title: '是否要送出？',
                content: '送出後將無法再次修改',
                boxWidth: '30%',
                useBootstrap: false,
                draggable: false,
                buttons: {
                    送出: {
                        keys: ['enter'],
                        action: function(){
                            console.log('confirm');
                            goNextRandom = false;
                            $('#saveButton').click();
                            function checkFlag() {
                                if(wasSend == false && goNextRandom == false) {
                                    console.log("QQ");
                                    window.setTimeout(checkFlag, 100); /* this checks the flag every 100 milliseconds*/
                                } else {
                                    goNextRandom = false;
                                    if(!wasSend)me[0]._controller.next_random_frame();
                                }
                            }
                            checkFlag();
                        }
                    },
                    取消: {
                        keys: ['esc'],
                        action: function(){
                            console.log('cancel');
                            goNextRandom = false;
                            $('#saveButton').click();
                            function checkFlag() {
                                if(wasSend == false && goNextRandom == false) {
                                    console.log("QQ");
                                    window.setTimeout(checkFlag, 100); /* this checks the flag every 100 milliseconds*/
                                } else {
                                    goNextRandom = false;
                                }
                            }
                            checkFlag();
                        }
                    }
                }
            });
            // if($('#nextButtonFlag').is(':checked')) {
            //     $('#nextButtonFlag').prop('checked',false);
            //     $('#nextButton_training')[0].setAttribute("class","playerButton_training disabledPlayerButton");
            //     this._controller.next_random_frame();
            //     trainigsaveFlag = false;
            // } else {
            //     assert("you can't do it before checkbox uncheck");
            // }
            
        });

        let shortkeys = window.cvat.config.shortkeys;
        let playerGridOpacityInput = $('#playerGridOpacityInput');
        playerGridOpacityInput.on('input', (e) => {
            let value = Math.clamp(+e.target.value, +e.target.min, +e.target.max);
            e.target.value = value;
            this._playerGridPath.attr({
                'opacity': value / +e.target.max,
            });
        });

        playerGridOpacityInput.attr('title', `
            ${shortkeys['change_grid_opacity'].view_value} - ${shortkeys['change_grid_opacity'].description}`);

        let playerGridStrokeInput = $('#playerGridStrokeInput');
        playerGridStrokeInput.on('change', (e) => {
            this._playerGridPath.attr({
                'stroke': e.target.value,
            });
        });

        playerGridStrokeInput.attr('title', `
            ${shortkeys['change_grid_color'].view_value} - ${shortkeys['change_grid_color'].description}`);

        $('#playerGridSizeInput').on('change', (e) => {
            let value = Math.clamp(+e.target.value, +e.target.min, +e.target.max);
            e.target.value = value;
            this._playerGridPattern.attr({
                width: value,
                height: value,
            });
        });

        Mousetrap.bind(shortkeys['focus_to_frame'].value, () => this._frameNumber.focus(), 'keydown');
        Mousetrap.bind(shortkeys["change_grid_opacity"].value,
            Logger.shortkeyLogDecorator(function(e) {
                let ui = playerGridOpacityInput;
                let value = +ui.prop('value');
                value += e.key === '=' ? 1 : -1;
                value = Math.clamp(value, 0, 5);
                ui.prop('value', value);
                this._playerGridPath.attr({
                    'opacity': value / +ui.prop('max'),
                });
            }.bind(this)),
            'keydown');

        Mousetrap.bind(shortkeys["change_grid_color"].value,
            Logger.shortkeyLogDecorator(function() {
                let ui = playerGridStrokeInput;
                let colors = [];
                for (let opt of ui.find('option')) {
                    colors.push(opt.value);
                }
                let idx = colors.indexOf(this._playerGridPath.attr('stroke')) + 1;
                let value = colors[idx] || colors[0];
                this._playerGridPath.attr('stroke', value);
                ui.prop('value', value);
            }.bind(this)),
            'keydown');

        this._progressUI['0'].max = playerModel.frames.stop - playerModel.frames.start;
        this._progressUI['0'].value = 0;

        this._resetZoomUI.prop('checked', playerModel.resetZoom);
        this._playerStepUI.prop('value', playerModel.multipleStep);
        this._playerSpeedUI.prop('value', '4');

        this._frameNumber.attr('title', `
            ${shortkeys['focus_to_frame'].view_value} - ${shortkeys['focus_to_frame'].description}`);

        this._nextButtonUI.find('polygon').append($(document.createElementNS('http://www.w3.org/2000/svg', 'title'))
            .html(`${shortkeys['next_frame'].view_value} - ${shortkeys['next_frame'].description}`));

        this._prevButtonUI.find('polygon').append($(document.createElementNS('http://www.w3.org/2000/svg', 'title'))
            .html(`${shortkeys['prev_frame'].view_value} - ${shortkeys['prev_frame'].description}`));

        this._playButtonUI.find('polygon').append($(document.createElementNS('http://www.w3.org/2000/svg', 'title'))
            .html(`${shortkeys['play_pause'].view_value} - ${shortkeys['play_pause'].description}`));

        this._pauseButtonUI.find('polygon').append($(document.createElementNS('http://www.w3.org/2000/svg', 'title'))
            .html(`${shortkeys['play_pause'].view_value} - ${shortkeys['play_pause'].description}`));

        this._multipleNextButtonUI.find('polygon').append($(document.createElementNS('http://www.w3.org/2000/svg', 'title'))
            .html(`${shortkeys['forward_frame'].view_value} - ${shortkeys['forward_frame'].description}`));

        this._multiplePrevButtonUI.find('polygon').append($(document.createElementNS('http://www.w3.org/2000/svg', 'title'))
            .html(`${shortkeys['backward_frame'].view_value} - ${shortkeys['backward_frame'].description}`));


        this._contextMenuUI.click((e) => {
            $('.custom-menu').hide(100);
            switch($(e.target).attr("action")) {
            case "job_url": {
                window.cvat.search.set('frame', null);
                window.cvat.search.set('filter', null);
                copyToClipboard(window.cvat.search.toString());
                break;
            }
            case "frame_url":
                window.cvat.search.set('frame', window.cvat.player.frames.current);
                window.cvat.search.set('filter', null);
                copyToClipboard(window.cvat.search.toString());
                window.cvat.search.set('frame', null);
                break;
            }
        });

        this._playerUI.on('contextmenu.playerContextMenu', (e) => {
            if (!window.cvat.mode) {
                $('.custom-menu').hide(100);
                this._contextMenuUI.finish().show(100).offset({
                    top: e.pageY - 10,
                    left: e.pageX - 10,
                });
                e.preventDefault();
            }
        });

        this._playerContentUI.on('mousedown.playerContextMenu', () => {
            $('.custom-menu').hide(100);
        });

        playerModel.subscribe(this);
    }

    onPlayerUpdate(model) {
        let image = model.image;
        let frames = model.frames;
        let geometry = model.geometry;

        if (!image) {
            this._loadingUI.removeClass('hidden');
            this._playerBackgroundUI.css('background-image', '');
            return;
        }

        this._loadingUI.addClass('hidden');
        if (this._playerBackgroundUI.css('background-image').slice(5,-2) != image.src) {
            this._playerBackgroundUI.css('background-image', 'url(' + '"' + image.src + '"' + ')');
        }

        if (model.playing) {
            this._playButtonUI.addClass('hidden');
            this._pauseButtonUI.removeClass('hidden');
        }
        else {
            this._pauseButtonUI.addClass('hidden');
            this._playButtonUI.removeClass('hidden');
        }

        if (frames.current === frames.start) {
            this._firstButtonUI.addClass('disabledPlayerButton');
            this._prevButtonUI.addClass('disabledPlayerButton');
            this._multiplePrevButtonUI.addClass('disabledPlayerButton');
        }
        else {
            this._firstButtonUI.removeClass('disabledPlayerButton');
            this._prevButtonUI.removeClass('disabledPlayerButton');
            this._multiplePrevButtonUI.removeClass('disabledPlayerButton');
        }

        if (frames.current === frames.stop) {
            this._lastButtonUI.addClass('disabledPlayerButton');
            this._nextButtonUI.addClass('disabledPlayerButton');
            this._playButtonUI.addClass('disabledPlayerButton');
            this._multipleNextButtonUI.addClass('disabledPlayerButton');
        }
        else {
            this._lastButtonUI.removeClass('disabledPlayerButton');
            this._nextButtonUI.removeClass('disabledPlayerButton');
            this._playButtonUI.removeClass('disabledPlayerButton');
            this._multipleNextButtonUI.removeClass('disabledPlayerButton');
        }

        this._progressUI['0'].value = frames.current - frames.start;

        for (let obj of [this._playerBackgroundUI, this._playerContentUI, this._playerGridUI]) {
            obj.css('width', image.width);
            obj.css('height', image.height);
            obj.css('top', geometry.top);
            obj.css('left', geometry.left);
            obj.css('transform', 'scale(' + geometry.scale + ')');
        }

        // Modify by jeff/ericlou.
        this._playerGridPath.attr('stroke-width', 2 / geometry.scale);
        this._frameNumber.prop('value', frames.current);
        $("#frameNumber_show").prop("value", (frames.current+1));

        let isKeyFrame = window.cvat.frameInfo.hasOwnProperty(frames.current);
        $('#isKeyFrame').prop('checked',isKeyFrame);
        if(isKeyFrame) {
            $('#select_keyframes').prop("value", (frames.current+1));
            if(isAdminFlag) {
                resetStatusColumn(model.tid, frames.current);
            }
            else {
                $('#redoComment_readonly').text(window.cvat.frameInfo[frames.current].comment);
            }
        }
        else {
            $('#select_keyframes').prop("value", "null");
            $('#isKeyFrame').prop('disabled',false);
            $('#isComplete').prop('disabled',true);
            $('#isComplete_text').prop('disabled',true);
            $('#isRedo').prop('disabled',true);
            $('#isRedo_text').prop('disabled',true);
            $('#redoComment').prop('disabled',true);
            $('#saveRedoComment').prop('disabled',true);
            let keyframeStage_str = "annotator: None";
            $('#beAnnotatorUsing_text').text(keyframeStage_str);
        }
    }
}

function resetStatusColumn(tid,frame){

    let StatusInfo = window.cvat.frameInfo[frame];
    let annotator_name = (StatusInfo.user!='')? StatusInfo.user : "None";
    let current_str = (StatusInfo.current==true)? "標記中" : "未檢查";
    if (StatusInfo.checked)
        current_str = "已檢查"

    let keyframeStage_str = "annotator: " + annotator_name + ', ' + current_str;
    $('#beAnnotatorUsing_text').text(keyframeStage_str);

    $('#isComplete').prop('checked',StatusInfo.checked);
    $('#isRedo').prop('checked',StatusInfo.need_modify);
    $('#redoComment').prop('value',StatusInfo.comment);

    if(StatusInfo.user == '') {
        // console.log("keyframeStage.annotator == ''");
        $('#isKeyFrame').prop('disabled',false);
        $('#isComplete').prop('disabled',true);
        $('#isComplete_text').prop('disabled',true);
        $('#isRedo').prop('disabled',true);
        $('#isRedo_text').prop('disabled',true);
        $('#redoComment').prop('disabled',true);
        $('#saveRedoComment').prop('disabled',true);
    }
    else if(StatusInfo.current || StatusInfo.need_modify) {
        // console.log("keyframeStage.current || keyframeStage.need_modify");
        $('#isKeyFrame').prop('disabled',true);
        $('#isComplete').prop('disabled',true);
        $('#isComplete_text').prop('disabled',true);
        $('#isRedo').prop('disabled',true);
        $('#isRedo_text').prop('disabled',true);
        $('#redoComment').prop('disabled',false);
        $('#saveRedoComment').prop('disabled',false);
    }
    else if(StatusInfo.checked) {
        // console.log("keyframeStage.checked");
        $('#isKeyFrame').prop('disabled',false);
        $('#isComplete').prop('disabled',false);
        $('#isComplete_text').prop('disabled',false);
        $('#isRedo').prop('disabled',true);
        $('#isRedo_text').prop('disabled',true);
        $('#redoComment').prop('disabled',true);
        $('#saveRedoComment').prop('disabled',true);
    }
    else if(StatusInfo.user_submit) {
        // console.log("keyframeStage.user_submit");
        $('#isKeyFrame').prop('disabled',false);
        $('#isComplete').prop('disabled',false);
        $('#isComplete_text').prop('disabled',false);
        $('#isRedo').prop('disabled',false);
        $('#isRedo_text').prop('disabled',false);
        $('#redoComment').prop('disabled',false);
        $('#saveRedoComment').prop('disabled',false);
    }
    else if(!StatusInfo.current && !StatusInfo.need_modify) {
        // console.log("!keyframeStage.current && !keyframeStage.need_modify");
        $('#isKeyFrame').prop('disabled',false);
        $('#isComplete').prop('disabled',false);
        $('#isComplete_text').prop('disabled',false);
        $('#isRedo').prop('disabled',false);
        $('#isRedo_text').prop('disabled',false);
        $('#redoComment').prop('disabled',false);
        $('#saveRedoComment').prop('disabled',false);
    }
}
// not use
function resetAdminCheckBox(tid,frame){
    serverRequest(`get/task/${tid}/frame/${frame}/keyframeStage`, function(response) {
        // console.log("in get keyframe stage",response);
        keyframeStage = response;

        let annotator_name = (keyframeStage.annotator!='')? keyframeStage.annotator : "None";
        let current_str = (keyframeStage.current!='')? "標記中" : "未檢查";
        if (keyframeStage.checked)
            current_str = "已檢查"

        let keyframeStage_str = "annotator: " + annotator_name + ', ' + current_str;
        $('#beAnnotatorUsing_text').text(keyframeStage_str);

        $('#isComplete').prop('checked',keyframeStage.checked);
        $('#isRedo').prop('checked',keyframeStage.need_modify);
        $('#redoComment').prop('value',keyframeStage.comment);

        if(keyframeStage.annotator == '') {
            // console.log("keyframeStage.annotator == ''");
            $('#isKeyFrame').prop('disabled',false);
            $('#isComplete').prop('disabled',true);
            $('#isComplete_text').prop('disabled',true);
            $('#isRedo').prop('disabled',true);
            $('#isRedo_text').prop('disabled',true);
            $('#redoComment').prop('disabled',true);
            $('#saveRedoComment').prop('disabled',true);
        }
        else if(keyframeStage.current || keyframeStage.need_modify) {
            // console.log("keyframeStage.current || keyframeStage.need_modify");
            $('#isKeyFrame').prop('disabled',true);
            $('#isComplete').prop('disabled',true);
            $('#isComplete_text').prop('disabled',true);
            $('#isRedo').prop('disabled',true);
            $('#isRedo_text').prop('disabled',true);
            $('#redoComment').prop('disabled',false);
            $('#saveRedoComment').prop('disabled',false);
        }
        else if(keyframeStage.checked) {
            // console.log("keyframeStage.checked");
            $('#isKeyFrame').prop('disabled',false);
            $('#isComplete').prop('disabled',false);
            $('#isComplete_text').prop('disabled',false);
            $('#isRedo').prop('disabled',true);
            $('#isRedo_text').prop('disabled',true);
            $('#redoComment').prop('disabled',true);
            $('#saveRedoComment').prop('disabled',true);
        }
        else if(keyframeStage.user_submit) {
            // console.log("keyframeStage.user_submit");
            $('#isKeyFrame').prop('disabled',false);
            $('#isComplete').prop('disabled',false);
            $('#isComplete_text').prop('disabled',false);
            $('#isRedo').prop('disabled',false);
            $('#isRedo_text').prop('disabled',false);
            $('#redoComment').prop('disabled',false);
            $('#saveRedoComment').prop('disabled',false);
        }
        else if(!keyframeStage.current && !keyframeStage.need_modify) {
            // console.log("!keyframeStage.current && !keyframeStage.need_modify");
            $('#isKeyFrame').prop('disabled',false);
            $('#isComplete').prop('disabled',false);
            $('#isComplete_text').prop('disabled',false);
            $('#isRedo').prop('disabled',false);
            $('#isRedo_text').prop('disabled',false);
            $('#redoComment').prop('disabled',false);
            $('#saveRedoComment').prop('disabled',false);
        }
    });
}
