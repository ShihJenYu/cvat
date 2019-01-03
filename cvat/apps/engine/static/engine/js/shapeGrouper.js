/*
 * Copyright (C) 2018 Intel Corporation
 *
 * SPDX-License-Identifier: MIT
 */

/* exported ShapeGrouperModel ShapeGrouperController ShapeGrouperView*/
"use strict";

class ShapeGrouperModel extends Listener {
    constructor(shapeCollection) {
        super('onGrouperUpdate', () => this);

        this._shapeCollection = shapeCollection;
        this._active = false;
        this._selectedObjects = [];

        this.keyinGroupID = null;
        this.keyinGroupOrder = null;
        // add by jeff
        // this._preShapeId = shapeCollection._preShapeId;
        // this._currentGroupID = shapeCollection._currentGroupID;
        // this._currentGroupOrder = shapeCollection._currentGroupOrder;
        // this._groupMap = shapeCollection._groupMap;
    }

    _unselectObjects() {
        for (let obj of this._selectedObjects) {
            obj.groupping = false;
        }
        this._selectedObjects = [];
    }

    apply() {
        if (this._selectedObjects.length) {
            this._shapeCollection.joinToGroup(this._selectedObjects);
        }
    }

    reset() {
        if (this._selectedObjects.length) {
            this._shapeCollection.resetGroupFor(this._selectedObjects);
        }
    }

    cancel() {
        if (this._active) {
            this._unselectObjects();

            this._active = false;
            if (window.cvat.mode === 'groupping') {
                window.cvat.mode = null;
            }
            this.notify();
        }
    }

    switch() {
        if (this._active) {
            this.apply();
            this.cancel();
        }
        else if (window.cvat.mode === null) {
            window.cvat.mode = 'groupping';
            this._active = true;
            this._shapeCollection.resetActive();
            this.notify();
        }
    }

    add(model) {
        let idx = this._selectedObjects.indexOf(model);
        if (idx === -1) {
            this._selectedObjects.push(model);
            model.groupping = true;
        }
    }

    click() {
        if (this._active) {
            let active = this._shapeCollection.selectShape(this._shapeCollection.lastPosition, true);
            if (active) {
                let idx = this._selectedObjects.indexOf(active);
                if (idx != -1) {
                    this._selectedObjects.splice(idx, 1);
                    active.groupping = false;
                }
                else {
                    this._selectedObjects.push(active);
                    active.groupping = true;
                }
            }
        }
    }

    // add by jeff
    clearGrouping(withAlt) {
        if (withAlt) {
            //清除預設值
            this._shapeCollection._currentGroupID = 0;
            this._shapeCollection._currentGroupOrder = 0;
            this._shapeCollection._preShape = null;

            $('#group_current_label').text("無");
        }
        else {
            //清除當前shape值
            if(this._shapeCollection._activeShape==null){return};
            let activeShape = this._shapeCollection._activeShape;
            let needDelgroupingID = [... activeShape._groupingID];
            let needDelgroupingOrder = [... activeShape._groupingOrder];

            let frame = window.cvat.player.frames.current;
            this._shapeCollection._groupMap[frame] = this._shapeCollection._groupMap[frame] || {};
            if (PROJECT=='fcw_testing') {
                //清除map中有關的group
                for (let i = 0; i < needDelgroupingID.length; i++) {
                    if(!(this._shapeCollection._groupMap[activeShape.frame][needDelgroupingID[i]] === undefined)) {
                        delete this._shapeCollection._groupMap[activeShape.frame][needDelgroupingID[i]];
                    }
                }
                //清除shape中有關的group
                this._shapeCollection._currentShapes.forEach(function(shape) {
                    for (let i = 0; i < needDelgroupingID.length; i++) {
                        let index = shape.model._groupingID.indexOf(needDelgroupingID[i]);
                        if(index != -1){
                            shape.model._groupingID.splice(index, 1);
                            shape.model._groupingOrder.splice(index, 1);
                            shape.model._updateReason = 'grouping';
                            shape.model.notify();
                        }
                    }
                });
            }
            else {
                //清除map中有關的group
                for (let i = 0; i < needDelgroupingID.length; i++) {
                    if(!(this._shapeCollection._groupMap[activeShape.frame][needDelgroupingID[i]] === undefined)) {
                        let index = this._shapeCollection._groupMap[activeShape.frame][needDelgroupingID[i]].indexOf([needDelgroupingOrder[i]]);
                        if(index!=-1) {
                            this._shapeCollection._groupMap[activeShape.frame][needDelgroupingID[i]].splice(index, 1);
                        }
                        // if [] will delete
                        if(this._shapeCollection._groupMap[activeShape.frame][needDelgroupingID[i]].length == 0) {
                            delete this._shapeCollection._groupMap[activeShape.frame][needDelgroupingID[i]];
                        }
                    }
                }
            }
            activeShape._grouping = '';
            activeShape._groupingID = [];
            activeShape._groupingOrder = [];
            activeShape._updateReason = 'grouping';
            activeShape.notify();
        }
        console.log(this._shapeCollection._groupMap,this._shapeCollection._currentGroupID,
            this._shapeCollection._currentGroupOrder,this._shapeCollection._preShape);
    }
    setNextGroup(withAlt,groupId) {
        this._shapeCollection._currentGroupID = 0;
        this._shapeCollection._currentGroupOrder = 0;
        this._shapeCollection._preShape = null;
        let frame = window.cvat.player.frames.current;
        $('#group_current_label').text("無");
        let flag = true;
        this._shapeCollection._groupMap[frame] = this._shapeCollection._groupMap[frame] || {};
            
        if (withAlt) {
            //設定預設值
            if (PROJECT=='fcw_testing') {
                if (this._shapeCollection._groupMap[frame].hasOwnProperty(groupId)) {
                    //group [] >=2 will error
                    if (this._shapeCollection._groupMap[frame][groupId].length >= 2) {
                        flag = false;
                        alert("[order,...] >=2 will error");
                    }
                    else if (this._shapeCollection._groupMap[frame][groupId].length == 0) {
                        this._shapeCollection._currentGroupID = groupId;
                        this._shapeCollection._currentGroupOrder = 1;
                    }
                    else {
                        this._shapeCollection._currentGroupID = groupId;
                        this._shapeCollection._currentGroupOrder = this._shapeCollection._groupMap[frame][groupId][this._shapeCollection._groupMap[frame][groupId].length-1] + 1;
                    }
                }
                else {
                    this._shapeCollection._currentGroupID = groupId;
                    this._shapeCollection._currentGroupOrder = 1;
                }
            }
            else {
                if (this._shapeCollection._groupMap[frame].hasOwnProperty(groupId)) {
                    if (this._shapeCollection._groupMap[frame][groupId].length == 0) {
                        this._shapeCollection._currentGroupID = groupId;
                        this._shapeCollection._currentGroupOrder = 1;
                    }
                    else {
                        this._shapeCollection._currentGroupID = groupId;
                        this._shapeCollection._currentGroupOrder = this._shapeCollection._groupMap[frame][groupId][this._shapeCollection._groupMap[frame][groupId].length-1] + 1;
                    }
                }
                else {
                    this._shapeCollection._currentGroupID = groupId;
                    this._shapeCollection._currentGroupOrder = 1;
                }
            }
            if(flag) {
                $('#group_current_label').text((this._shapeCollection._currentGroupID).toString());
            }
        }
        else {
            //設定當前shape值
            if(this._shapeCollection._activeShape==null){return};
            let groupingID = this._shapeCollection._activeShape._groupingID;
            let groupingOrder = this._shapeCollection._activeShape._groupingOrder;
            let groupMap = this._shapeCollection._groupMap[frame];
            
            if (PROJECT=='fcw_testing') {
                if(groupMap.hasOwnProperty(groupId))
                {
                    //group [] >=2 will error
                    if (groupMap[groupId].length >= 2) {
                        alert("ERROR this key is has 2 order");
                    }
                    else if (groupMap[groupId].length == 0) {
                        groupingID.push(groupId);
                        groupingOrder.push(1);
                        groupMap[groupId] = [1];
                    }
                    else {
                        //自己已經有相同group
                        if (groupingID.includes(groupId)){
                            alert("ERROR 已經有相同group");
                        }
                        else {
                            groupingID.push(groupId);
                            let value = groupMap[groupId][groupMap[groupId].length-1]+1
                            groupingOrder.push(value);
                            groupMap[groupId].push(value);
                        }
                    }
                }
                else
                {
                    groupingID.push(groupId);
                    groupingOrder.push(1);
                    groupMap[groupId] = [1];
                }
            }
            else {
                if (groupingID.length == groupingOrder.length) {
                    let id = (groupingID.length == 0)? 0: groupingID[0];
                    let order = (groupingOrder.length == 0)? 0: groupingOrder[0];
                    groupingID = [];
                    groupingOrder = [];
                    if(groupMap.hasOwnProperty(groupId))
                    {
                        if (groupMap[groupId].length == 0) {
                            groupingID.push(groupId);
                            groupingOrder.push(1);
                            groupMap[groupId] = [1];
                        }
                        else {
                            //自己已經有相同group
                            if (id == groupId){
                                groupingID.push(id);
                                groupingOrder.push(order);
                            }
                            else {
                                //先刪除map
                                if(groupMap.hasOwnProperty(id)) {
                                    let index = groupMap[id].indexOf(order);
                                    if(index != -1)
                                        groupMap[id].splice(index, 1);
                                    if(groupMap[id].length == 0)
                                        delete groupMap[id];
                                }
                                
                                    
                                groupingID.push(groupId);
                                let value = groupMap[groupId][groupMap[groupId].length-1]+1
                                groupingOrder.push(value);
                                groupMap[groupId].push(value);
                            }
                        }
                    }
                    else
                    {
                        groupingID.push(groupId);
                        groupingOrder.push(1);
                        groupMap[groupId] = [1];
                    }
                }
                else {
                    console.log("ERROR oupingID.length != groupingOrder.lengt");
                }
            }

            this._shapeCollection._activeShape._groupingID = groupingID;
            this._shapeCollection._activeShape._groupingOrder = groupingOrder;
            
            this._shapeCollection._activeShape._updateReason = 'grouping';
            this._shapeCollection._activeShape.notify();
        }

        console.log(this._shapeCollection._groupMap,this._shapeCollection._currentGroupID,
            this._shapeCollection._currentGroupOrder,this._shapeCollection._preShape);
    }

    onCollectionUpdate() {
        if (this._active) {
            this._unselectObjects();
        }
    }

    get active() {
        return this._active;
    }
}


class ShapeGrouperController {
    constructor(grouperModel) {
        this._model = grouperModel;

        setupGrouperShortkeys.call(this);
        function setupGrouperShortkeys() {
            let shortkeys = window.cvat.config.shortkeys;

            let switchGrouperHandler = Logger.shortkeyLogDecorator(function() {
                this.switch();
            }.bind(this));

            let cancelGrouperHandler = Logger.shortkeyLogDecorator(function() {
                if (this._model.active) {
                    this._model.cancel();
                }
            }.bind(this));

            let resetGroupHandler = Logger.shortkeyLogDecorator(function() {
                if (this._model.active) {
                    this._model.reset();
                    this._model.cancel();
                    this._model.notify();
                }
            }.bind(this));

            Mousetrap.bind(shortkeys["switch_group_mode"].value, switchGrouperHandler.bind(this), 'keydown');
            Mousetrap.bind(shortkeys["cancel_group_mode"].value, cancelGrouperHandler.bind(this), 'keydown');
            Mousetrap.bind(shortkeys["reset_group"].value, resetGroupHandler.bind(this), 'keydown');

            // add by jeff
            let nextshapeGrouperHandler = Logger.shortkeyLogDecorator(function(e) {
                e.preventDefault();
                console.log(1,'keycode',e.keyCode);
                console.log(1,'withalt',e.altKey);
                let key = e.keyCode;
                if (key >= 48 && key <= 57) {
                    key -= 48;  // 0 and 9
                }
                else if (key >= 96 && key <= 105) {
                    key -= 96; // num 0 and 9
                }
                else {
                    return;
                }
                let groupId = (key == 0)? 10 : key;
                
                this.setNextGroup(true,groupId);
            }.bind(this));

            let currentshapeGrouperHandler = Logger.shortkeyLogDecorator(function(e) {
                // this.switch();
                e.preventDefault();
                console.log(1,'keycode',e.keyCode);
                console.log(1,'withalt',e.altKey);
                let key = e.keyCode;
                if (key >= 48 && key <= 57) {
                    key -= 48;  // 0 and 9
                }
                else if (key >= 96 && key <= 105) {
                    key -= 96; // num 0 and 9
                }
                else {
                    return;
                }
                let groupId = (key == 0)? 10 : key;
                
                this.setNextGroup(false,groupId);
            }.bind(this));

            let cancelNextShapeGrouperHandler = Logger.shortkeyLogDecorator(function(e) {
                e.preventDefault();
                this.clearGrouping(true);
            }.bind(this));

            let cancelCurrentShapeGrouperHandler = Logger.shortkeyLogDecorator(function(e) {
                e.preventDefault();
                this.clearGrouping(false);
            }.bind(this));

            Mousetrap.bind(shortkeys["set_nextshape_groupID"].value, nextshapeGrouperHandler.bind(this), 'keydown');
            Mousetrap.bind(shortkeys["set_currentshape_groupID"].value, currentshapeGrouperHandler.bind(this), 'keydown');
            Mousetrap.bind(shortkeys["cancel_nextshape_groupID"].value, cancelNextShapeGrouperHandler.bind(this), 'keydown');
            Mousetrap.bind(shortkeys["cancel_currentshape_groupID"].value, cancelCurrentShapeGrouperHandler.bind(this), 'keydown');
        }
    }

    switch() {
        this._model.switch();
    }

    add(model) {
        this._model.add(model);
    }

    click() {
        this._model.click();
    }

    // add by jeff
    clearGrouping(withAlt) {
        this._model.clearGrouping(withAlt);
    }
    setNextGroup(withAlt,groupId){
        this._model.setNextGroup(withAlt,groupId);
    }
}


class ShapeGrouperView {
    constructor(grouperModel, grouperController) {
        this._controller = grouperController;
        this._frameContent = $('#frameContent');
        this._groupShapesButton = $('#groupShapesButton');
        this._rectSelector = null;
        this._initPoint = null;
        this._scale = 1;

        this._groupShapesButton.on('click', () => {
            this._controller.switch();
        });

        let shortkeys = window.cvat.config.shortkeys;

        this._groupShapesButton.attr('title', `
            ${shortkeys['switch_group_mode'].view_value} - ${shortkeys['switch_group_mode'].description}` + `\n` +
            `${shortkeys['cancel_group_mode'].view_value} - ${shortkeys['cancel_group_mode'].description}` + `\n` +
            `${shortkeys['reset_group'].view_value} - ${shortkeys['reset_group'].description}`);

        grouperModel.subscribe(this);
    }

    _select() {
        if (this._rectSelector) {
            let rect1 = this._rectSelector[0].getBBox();
            for (let shape of this._frameContent.find('.shape')) {
                let rect2 = shape.getBBox();

                if (rect1.x < rect2.x && rect1.y < rect2.y &&
                    rect1.x + rect1.width > rect2.x + rect2.width &&
                    rect1.y + rect1.height > rect2.y + rect2.height) {
                    this._controller.add(shape.cvatView.controller().model());
                }
            }
        }
    }

    _reset() {
        if (this._rectSelector) {
            this._rectSelector.remove();
            this._rectSelector = null;
        }

        if (this._initPoint) {
            this._initPoint = null;
        }
    }

    _enableEvents() {
        this._frameContent.on('mousedown.grouper', (e) => {
            this._initPoint = translateSVGPos(this._frameContent[0], e.clientX, e.clientY);
        });

        this._frameContent.on('mousemove.grouper', (e) => {
            let currentPoint = translateSVGPos(this._frameContent[0], e.clientX, e.clientY);
            if (this._initPoint) {
                if (!this._rectSelector) {
                    this._rectSelector = $(document.createElementNS('http://www.w3.org/2000/svg', 'rect'));
                    this._rectSelector.appendTo(this._frameContent);
                    this._rectSelector.attr({
                        'stroke-width': (STROKE_WIDTH / 3) / this._scale,
                        'stroke': 'darkmagenta',
                        'fill': 'darkmagenta',
                        'fill-opacity': 0.5,
                        'stroke-dasharray': 5,
                    });
                }

                this._rectSelector.attr({
                    'x': Math.min(this._initPoint.x, currentPoint.x),
                    'y': Math.min(this._initPoint.y, currentPoint.y),
                    'width': Math.max(this._initPoint.x, currentPoint.x) - Math.min(this._initPoint.x, currentPoint.x),
                    'height': Math.max(this._initPoint.y, currentPoint.y) - Math.min(this._initPoint.y, currentPoint.y),
                });
            }
        });

        this._frameContent.on('mouseup.grouper', () => {
            this._select();
            this._reset();
        });

        this._frameContent.on('mouseleave.grouper', () => {
            this._select();
            this._reset();
        });

        this._frameContent.on('click.grouper', () => {
            this._controller.click();
        });
    }

    _disableEvents() {
        this._frameContent.off('mousedown.grouper');
        this._frameContent.off('mousemove.grouper');
        this._frameContent.off('mouseup.grouper');
        this._frameContent.off('mouseleave.grouper');
        this._frameContent.off('click.grouper');
    }

    onGrouperUpdate(grouper) {
        if (grouper.active) {
            this._enableEvents();
            this._groupShapesButton.text('Apply Group');
        }
        else {
            this._reset();
            this._disableEvents();
            this._groupShapesButton.text('Group Shapes');
            if (this._rectSelector) {
                this._rectSelector.remove();
                this._rectSelector = null;
            }
        }
    }

    onPlayerUpdate(player) {
        if (this._scale != player.geometry.scale) {
            this._scale = player.geometry.scale;
            if (this._rectSelector) {
                this._rectSelector.attr({
                    'stroke-width': STROKE_WIDTH / this._scale,
                });
            }
        }
    }
}