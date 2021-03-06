/*
 * Copyright (C) 2018 Intel Corporation
 *
 * SPDX-License-Identifier: MIT
 */

/* exported PolyShapeModel buildShapeModel buildShapeController buildShapeView */
"use strict";

const STROKE_WIDTH = 2.5;
const SELECT_POINT_STROKE_WIDTH = 2.5;
const POINT_RADIUS = 5;
const AREA_TRESHOLD = 9;
const TEXT_MARGIN = 10;

var menuScroll = false;
// add by eric
var previous_type = null;
// var previous_rotation = null;
var previous_Light = null;
var previous_cant_see = null;

function mapColor_Corner(type_value){
    let value = type_value.toLowerCase();
    if(value == ("corner_perpendicular")){
        return {shape: "#0b8043",ui: "#0b8043"};
    }
    else if(value == ("corner_parallel")){
        return {shape: "#ff00ff",ui: "#ff00ff"};
    }
    else if(value == ("corner_slanted")){
        return {shape: "#3d85c6",ui: "#3d85c6"};
    }
    else if(value == ("corner")){
        return {shape: "#ffff00",ui: "#ffff00"};
    }
    else if(value == ("corner_far")){
        return {shape: "#d4b639",ui: "#d4b639"};
    }
    else if(value == ("corner_aux")){
        return {shape: "#ff0000",ui: "#ff0000"};
    }
    else if(value == ("corner_noncar")){
        return {shape: "#dd42cd",ui: "#dd42cd"};
    }
    else if(value == ("corner_far_noncar")){
        return {shape: "#ff9900",ui: "#ff9900"};
    }
    else if(value == ("endpoint_perpendicular")){
        return {shape: "#00ffff",ui: "#00ffff"};
    }
    else if(value == ("endpoint_parallel")){
        return {shape: "#f4cccc",ui: "#f4cccc"};
    }
    else if(value == ("endpoint_slanted")){
        return {shape: "#9900ff",ui: "#9900ff"};
    }
    else if(value == ("endpoint")){
        return {shape: "#84c44f",ui: "#84c44f"};
    }
    else if(value == ("endpoint_far")){
        return {shape: "#1155cc",ui: "#1155cc"};
    }
    else if(value == ("endpoint_aux")){
        return {shape: "#ffd966",ui: "#ffd966"};
    }
    else if(value == ("endpoint_noncar")){
        return {shape: "#ea9999",ui: "#ea9999"};
    }
    else if(value == ("endpoint_far_noncar")){
        return {shape: "#ff9900",ui: "#ff9900"};
    }
    else if(value == ("angcorner_slanted")){
        return {shape: "#00ff00",ui: "#00ff00"};
    }
    else if(value == ("angcorner")){
        return {shape: "#ff0000",ui: "#ff0000"};
    }
    else if(value == ("angcorner_far")){
        return {shape: "#fff100",ui: "#fff100"};
    }
    else if(value == ("angcorner_aux")){
        return {shape: "#0000ff",ui: "#0000ff"};
    }
    else if(value == ("angcorner_noncar")){
        return {shape: "#4a86e8",ui: "#4a86e8"};
    }
    else if(value == ("angcorner_far_noncar")){
        return {shape: "#ff9900",ui: "#ff9900"};
    }
    else if(value == ("double_perpendicular")){
        return {shape: "#0fb860",ui: "#0fb860"};
    }
    else if(value == ("double_parallel")){
        return {shape: "#f2a0ff",ui: "#f2a0ff"};
    }
    else if(value == ("double_slanted")){
        return {shape: "#4eabff",ui: "#4eabff"};
    }
    else if(value == ("double")){
        return {shape: "#faff83",ui: "#faff83"};
    }
    else if(value == ("double_far")){
        return {shape: "#d4b639",ui: "#d4b639"};
    }
    else if(value == ("double_aux")){
        return {shape: "#ff0000",ui: "#ff0000"};
    }
    else if(value == ("double_noncar")){
        return {shape: "#dd42cd",ui: "#dd42cd"};
    }
    else if(value == ("double_far_noncar")){
        return {shape: "#ff9900",ui: "#ff9900"};
    }
    else {
        console.log("error but set default with corner_perpendicular");
        return {shape: "#0b8043",ui: "#0b8043"};
    }
}

function mapColor_DMS(type_value){
    let value = type_value.toLowerCase();
    if(value == ("臉")){
        return {shape: "#6b79ba",ui: "#6b79ba"};
    }
    else if(value == ("臉頰")){
        return {shape: "#7ab567",ui: "#7ab567"};
    }
    else if(value == ("鼻子")){
        return {shape: "#ffe059",ui: "#ffe059"};
    }
    else if(value == ("左眉毛")){
        return {shape: "#d88498",ui: "#d88498"};
    }
    else if(value == ("右眉毛")){
        return {shape: "#84a8d8",ui: "#84a8d8"};
    }
    else if(value == ("左眼睛")){
        return {shape: "#a33413",ui: "#a33413"};
    }
    else if(value == ("右眼睛")){
        return {shape: "#84cad8",ui: "#84cad8"};
    }
    else if(value == ("嘴巴")){
        return {shape: "#f7ad67",ui: "#f7ad67"};
    }
    else {
        console.log("error but set default with face");
        return {shape: "#2a30ea",ui: "#2a30ea"};
    }
}

/******************************** SHAPE MODELS  ********************************/
class ShapeModel extends Listener {
    constructor(data, positions, type, id, color) {
        super('onShapeUpdate', () => this );
        this._id = id;
        this._groupId = data.group_id;
        this._type = type;
        this._color = color;
        this._label = data.label_id;
        this._frame = type.split('_')[0] === 'annotation' ? data.frame :
            positions.filter((pos) => pos.frame < window.cvat.player.frames.start).length ?
                window.cvat.player.frames.start : Math.min(...positions.map((pos) => pos.frame));
        this._removed = false;
        this._locked = false;
        this._merging = false;
        this._active = false;
        this._selected = false;
        this._activeAAM = false;
        this._activeAAMAttributeId = null;
        this._merge = false;
        this._hiddenShape = false;
        // add by eric, obj_id
        this._obj_id = data.obj_id;
        this._grouping = data.grouping;

        this._groupingID = [];
        this._groupingOrder = [];
        this._importGrouping(data.grouping);
        // modify by eric, to change hiddentext state
        this._hiddenText = true;
        this._updateReason = null;

        this._importAttributes(data.attributes, positions);
        
    }
    //add by jeff
    mapColor(type_value){
        let value = type_value.toLowerCase();
        if(value.includes("car")){
            this._color = {shape: "#255f9d",ui: "#255f9d"};
        }
        else if(value.includes("van")){
            this._color = {shape: "#14ad78",ui: "#14ad78"};
        }
        else if(value.includes("motorbike")){
            this._color = {shape: "#a41ea4",ui: "#a41ea4"};
        }
        else if(value.includes("bike")){
            this._color = {shape: "#e77408",ui: "#e77408"};
        }
        else if(value.includes("truck")){
            this._color = {shape: "#209211",ui: "#209211"};
        }
        else if(value.includes("bus")){
            this._color = {shape: "#926511",ui: "#926511"};
        }
        else if(value.includes("代步車")){
            this._color = {shape: "#7f0fff",ui: "#7f0fff"};
        }
        else if(value.includes("工程車")){
            this._color = {shape: "#009ff5",ui: "#009ff5"};
        }
        else if(value.includes("無殼三輪車")){
            this._color = {shape: "#e713d5",ui: "#e713d5"};
        }
        else if(value.includes("有殼三輪車")){
            this._color = {shape: "#8ab427",ui: "#8ab427"};
        }
        else if(value.includes("無人機車群")){
            this._color = {shape: "#a0a800",ui: "#a0a800"};
        }
        else if(value.includes("無人腳踏車群")){
            this._color = {shape: "#00d676",ui: "#00d676"};
        }
        else if(value.includes("misc")){
            this._color = {shape: "#ff38ca",ui: "#ff38ca"};
        }
        else if(value.includes("background")){
            this._color = {shape: "#fbddac",ui: "#fbddac"};
        }
        else if(value.includes("tram")){
            this._color = {shape: "#c1fbac",ui: "#c1fbac"};
        }
        else if(value.includes("crowd")){
            this._color = {shape: "#f9c8c8",ui: "#f9c8c8"};
        }
        else if(["pedestrian_行人(直立)","personsitting_行人(非直立)"].includes(value)){
            this._color = {shape: "#a01313",ui: "#a01313"};
        }
        else if(value.includes("動物")){
            this._color = {shape: "#efe1b3",ui: "#efe1b3"};
        }
        else {
            console.log("error but set default with car");
            this._color = {shape: "#255f9d",ui: "#255f9d"};
        }
    }

    _importGrouping(grouping) {
        if(grouping!=null && grouping.length) {
            let groupingList = grouping.split(/(?:,|-| )+/);
            for (let [index, value] of groupingList.entries()) {
                if (index % 2 == 0) {
                    this._groupingID.push(parseInt(value));
                }
                else {
                    this._groupingOrder.push(parseInt(value));
                }
            }
        }
    }
    _exportGrouping(groupingID,groupingOrder) {
        this._grouping = '';
        for (let [index, id] of groupingID.entries()) {
            this._grouping += id.toString() + '-' + groupingOrder[index].toString();
            if(index+1<groupingID.length) {
                this._grouping += ',';
            }
        }
    }

    _importAttributes(attributes, positions) {
        let converted = {};
        let labelsInfo = window.cvat.labelsInfo;
        for (let attr of attributes) {
            // modify by jeff
            let attrInfo = labelsInfo.attrInfo(attr.id);
            if(attrInfo.type=="multiselect"){
                let value = attr.value;
                if (!Array.isArray(value))
                    if (value.match(/\'(.*?)\'/g))
                        converted[attr.id] = value.match(/\'(.*?)\'/g).map(value => value.substr(1, value.length-2));
                    else
                        converted[attr.id] = [];
                else
                    converted[attr.id] = value;
            }
            else converted[attr.id] = attr.value;
        }
        attributes = converted;

        this._attributes = {
            immutable: {},
            mutable: {},
        };

        if (PROJECT == 'dms_training') {
            this._color = mapColor_DMS(labelsInfo._labels[this._label].name);
        }

        let labelAttributes = labelsInfo.labelAttributes(this._label);
        let Type_value = '';
        for (let attrId in labelAttributes) {
            let attrInfo = labelsInfo.attrInfo(attrId);
            if (attrInfo.mutable) {
                this._attributes.mutable[this._frame] = this._attributes.mutable[this._frame] || {};
                this._attributes.mutable[this._frame][attrId] = attrInfo.values[0];
                // add by jeff
                if (attrInfo.type=="multiselect") {
                    this._attributes.mutable[this._frame][attrId] = [];

                    if(attrInfo.name=="小標"){
                        let corner_att =  $('#default_corner_att').val();
                        if (corner_att==null)corner_att=[];
                        this._attributes.mutable[this._frame][attrId] = corner_att;
                    }
                }
                if (attrInfo.type=="singleselect" && attrInfo.name=="大標") {
                    let corner_type =  $('#default_corner_type').prop('value');
                    if (attrInfo.values.includes(corner_type)) {
                        this._attributes.mutable[this._frame][attrId] = corner_type;
                    }
                    this._color = mapColor_Corner(this._attributes.mutable[this._frame][attrId]);
                }

                // add by eric
                if (attrInfo.name=="Type"){
                    if (previous_type===null){
                        this._attributes.mutable[this._frame][attrId] = attrInfo.values[0];
                        // console.log(attrInfo.values[0], attrInfo.values[1], "mutable");
                    } else {
                        this._attributes.mutable[this._frame][attrId] = previous_type;
                        // console.log(previous_type, "mutable");
                    }
                    Type_value = this._attributes.mutable[this._frame][attrId].toLowerCase();
                    this.mapColor(this._attributes.mutable[this._frame][attrId]);
                }

                // if (attrInfo.name=="Rotation"){
                //     if (previous_rotation===null){
                //         this._attributes.mutable[this._frame][attrId] = attrInfo.values[0];
                //     } else {
                //         this._attributes.mutable[this._frame][attrId] = previous_rotation;
                //     }
                // }

                if (attrInfo.name=="有開燈"){
                    if (previous_Light===null){
                        this._attributes.mutable[this._frame][attrId] = attrInfo.values[0];
                        // console.log(attrInfo.values[0], attrInfo.values[1], "mutable");
                    } else {
                        this._attributes.mutable[this._frame][attrId] = previous_Light;
                        // console.log(previous_Light, "mutable");
                    }
                }

                if (attrInfo.name=="障礙物"){
                    if (previous_cant_see===null){
                        this._attributes.mutable[this._frame][attrId] = attrInfo.values[0];
                        // console.log(attrInfo.values[0], attrInfo.values[1], "mutable");
                    } else {
                        this._attributes.mutable[this._frame][attrId] = previous_cant_see;
                        // console.log(previous_cant_see, "mutable");
                    }
                }
                if(attrInfo.name == "DetectPoints") {
                    var dectpoint_id = attrId;
                }
            }
            else {
                this._attributes.immutable[attrId] = attrInfo.values[0];
            }
        }

        // add by eric
        if (Type_value.includes("car") || Type_value.includes("van") || Type_value.includes("truck") || Type_value.includes("bus") ||
            Type_value.includes("代步車") || Type_value.includes("工程車") || Type_value.includes("tram") || Type_value=="無殼三輪車" || Type_value=="有殼三輪車"){
            this._attributes.mutable[this._frame][dectpoint_id] = "\"0.1,-1,0.9,-1\"";
        }

        if (Type_value=="bike" || Type_value=="motorbike" || Type_value=="動物"){
            this._attributes.mutable[this._frame][dectpoint_id] = "\"0,-1,0.5,-1\"";
        }

        for (let attrId in attributes) {
            let attrInfo = labelsInfo.attrInfo(attrId);
            if(attrInfo.name=="Type") {
                this.mapColor(attributes[attrId]);
            }
            if (attrInfo.type=="singleselect" && attrInfo.name=="大標") {
                this._color = mapColor_Corner(attributes[attrId]);
            }
            if (attrInfo.mutable) {
                if(attrInfo.name == "DetectPoints"){
                    let detectpoints = attributes[attrId].replace(/"/g, "").split(/[\s,]+/);
                    this._attributes.mutable[this._frame][attrId] = "\"" + detectpoints[0] + ",-1," + detectpoints[2] + ",-1\"";
                }
                else this._attributes.mutable[this._frame][attrId] = labelsInfo.strToValues(attrInfo.type, attributes[attrId])[0];
            }
            else {
                this._attributes.immutable[attrId] = labelsInfo.strToValues(attrInfo.type, attributes[attrId])[0];
            }
        }

        for (let pos of positions) {
            let frame = pos.frame;
            let attributes = pos.attributes;
            for (let attr of attributes) {
                let attrInfo = labelsInfo.attrInfo(attr.id);
                if (attrInfo.mutable) {
                    this._attributes.mutable[frame] = this._attributes.mutable[frame] || {};
                    this._attributes.mutable[frame][attr.id] = labelsInfo.strToValues(attrInfo.type, attr.value)[0];
                }
            }
        }
    }

    _interpolateAttributes(frame) {
        let labelsInfo = window.cvat.labelsInfo;
        let interpolated = {};
        for (let attrId in this._attributes.immutable) {
            let attrInfo = labelsInfo.attrInfo(attrId);
            interpolated[attrId] = {
                name: attrInfo.name,
                value: this._attributes.immutable[attrId],
            };
        }

        if (!Object.keys(this._attributes.mutable).length) {
            return interpolated;
        }

        let mutableAttributes = {};
        for (let attrId in window.cvat.labelsInfo.labelAttributes(this._label)) {
            let attrInfo = window.cvat.labelsInfo.attrInfo(attrId);
            if (attrInfo.mutable) {
                mutableAttributes[attrId] = attrInfo.name;
            }
        }

        for (let attrId in mutableAttributes) {
            for (let frameKey in this._attributes.mutable) {
                frameKey = +frameKey;
                if (attrId in this._attributes.mutable[frameKey] &&
                    (frameKey <= frame || !(attrId in interpolated))) {
                    interpolated[attrId] = {
                        name: mutableAttributes[attrId],
                        value: this._attributes.mutable[frameKey][attrId],
                    };
                }
            }

            if (!(attrId != interpolated)) {
                throw Error(`Keyframe for mutable attribute not found. Frame: ${frame}, attributeId: ${attrId}`);
            }
        }

        return interpolated;
    }

    _neighboringFrames(frame) {
        if (!Number.isInteger(frame) || frame < 0) {
            throw Error(`Got invalid frame: ${frame}`);
        }

        let leftFrame = null;
        let rightFrame = null;

        for (let frameKey in this._positions) {
            frameKey = +frameKey;
            if (frameKey < frame && (frameKey > leftFrame || leftFrame === null)) {
                leftFrame = frameKey;
            }

            if (frameKey > frame && (frameKey < rightFrame || rightFrame === null)) {
                rightFrame = frameKey;
            }
        }

        return [leftFrame, rightFrame];
    }

    // Function mark frames which contain attribute updates as key frames
    _setupKeyFrames() {
        for (let frame in this._attributes.mutable) {
            if (!(frame in this._positions)) {
                let position = this._interpolatePosition(+frame);
                this.updatePosition(+frame, position, true);
            }
        }
    }

    _computeFrameCount() {
        if (this._type.split('_')[0] === 'annotation') {
            return 1;
        }

        let counter = 0;
        let visibleFrame = null;
        let hiddenFrame = null;
        let last = 0;
        for (let frame in this._positions) {
            if (visibleFrame === null && !this._positions[frame].outside) {
                visibleFrame = +frame;
            }
            else if (visibleFrame != null && this._positions[frame].outside) {
                hiddenFrame = +frame;
                counter += hiddenFrame - visibleFrame;
                visibleFrame = null;
                hiddenFrame = null;
            }
            last = +frame;
        }

        if (visibleFrame != null) {
            if (this._type === 'interpolation_box') {
                counter += window.cvat.player.frames.stop - visibleFrame + 1;
            }
            else {
                counter += last - visibleFrame + 1;
            }
        }
        return counter;
    }

    collectStatistic() {
        let collectObj = {};
        collectObj.type = this._type.split('_')[1];
        collectObj.mode = this._type.split('_')[0];
        collectObj.labelId = this._label;
        collectObj.manually = Object.keys(this._positions).length;
        for (let frame in this._positions) {
            if (this._positions[frame].outside) {
                collectObj.manually --;
            }
        }
        collectObj.total = this._computeFrameCount();
        collectObj.interpolated = collectObj.total - collectObj.manually;

        return collectObj;
    }

    updateAttribute(frame, attrId, value) {
        let labelsInfo = window.cvat.labelsInfo;
        let attrInfo = labelsInfo.attrInfo(attrId);

        Logger.addEvent(Logger.EventType.changeAttribute, {
            attrId: attrId,
            value: value,
            attrName: attrInfo.name
        });

        // Undo/redo code
        let oldAttr = attrInfo.mutable ? this._attributes.mutable[frame] ? this._attributes.mutable[frame][attrId] : undefined :
            this._attributes.immutable[attrId];

        window.cvat.addAction('Change Attribute', () => {
            if (typeof(oldAttr) === 'undefined') {
                delete this._attributes.mutable[frame][attrId];
                this._updateReason = 'attributes';
                this.notify();
            }
            else {
                this.updateAttribute(frame, attrId, oldAttr);
            }
        }, () => {
            this.updateAttribute(frame, attrId, value);
        }, frame);
        // End of undo/redo code

        if (attrInfo.mutable) {
            this._attributes.mutable[frame] = this._attributes.mutable[frame]|| {};
            this._attributes.mutable[frame][attrId] = labelsInfo.strToValues(attrInfo.type, value)[0];
            this._setupKeyFrames();
        }
        else {
            this._attributes.immutable[attrId] = labelsInfo.strToValues(attrInfo.type, value)[0];
        }

        this._updateReason = 'attributes';
        this.notify();
    }

    changeLabel(labelId) {
        Logger.addEvent(Logger.EventType.changeLabel, {
            from: this._label,
            to: labelId,
        });

        if (labelId in window.cvat.labelsInfo.labels()) {
            this._label = +labelId;
            this._importAttributes([], []);
            this._setupKeyFrames();
            this._updateReason = 'changelabel';
            this.notify();
        }
        else {
            throw Error(`Unknown label id value found: ${labelId}`);
        }
    }

    changeColor(color) {
        this._color = color;
        this._updateReason = 'color';
        this.notify();
    }

    interpolate(frame) {
        return {
            attributes: this._interpolateAttributes(frame),
            position: this._interpolatePosition(frame)
        };
    }

    switchOccluded(frame) {
        let position = this._interpolatePosition(frame);
        position.occluded = !position.occluded;

        // Undo/redo code
        window.cvat.addAction('Change Occluded', () => {
            this.switchOccluded(frame);
        }, () => {
            this.switchOccluded(frame);
        }, frame);
        // End of undo/redo code

        this.updatePosition(frame, position, true);
        this._updateReason = 'occluded';
        this.notify();
    }

    switchLock() {
        this._locked = !this._locked;
        this._updateReason = 'lock';
        this.notify();
    }

    // modify by eric
    switchHide() {
        // if (!this._hiddenText) {
        //     this._hiddenText = true;
        //     this._hiddenShape = false;
        // }
        // else if (this._hiddenText && !this._hiddenShape) {
        //     this._hiddenShape = true;
        //     this._hiddenText = true;
        // }
        // else if (this._hiddenText && this._hiddenShape) {
        //     this._hiddenShape = false;
        //     this._hiddenText = false;
        // }

        if (!this._hiddenShape) {
            this._hiddenShape = true;
        } else if (this._hiddenShape) {
            this._hiddenShape = false;
        }

        console.log("HIDDEN")

        this._updateReason = 'hidden';
        this.notify();
    }

    switchOutside(frame) {
        // Only for interpolation boxes
        if (this._type != 'interpolation_box') {
            return;
        }

        // Undo/redo code
        let oldPos = Object.assign({}, this._positions[frame]);
        window.cvat.addAction('Change Outside', () => {
            if (!Object.keys(oldPos).length) {
                // Frame hasn't been a keyframe, remove it from position and redestribute attributes
                delete this._positions[frame];
                this._frame = Math.min(...Object.keys(this._positions).map((el) => +el));
                if (frame < this._frame && frame in this._attributes.mutable) {
                    this._attributes.mutable[this._frame] = this._attributes.mutable[frame];
                }

                if (frame in this._attributes.mutable) {
                    delete this._attributes.mutable[frame];
                }

                this._updateReason = 'outside';
                this.notify();
            }
            else {
                this.switchOutside(frame);
            }
        }, () => {
            this.switchOutside(frame);
        }, frame);
        // End of undo/redo code

        let position = this._interpolatePosition(frame);
        position.outside = !position.outside;
        this.updatePosition(frame, position, true);

        // Update the start frame if need and redestribute attributes
        if (frame < this._frame) {
            if (this._frame in this._attributes.mutable) {
                this._attributes.mutable[frame] = this._attributes.mutable[this._frame];
                delete(this._attributes.mutable[this._frame]);
            }
            this._frame = frame;
        }

        this._updateReason = 'outside';
        this.notify();
    }

    switchKeyFrame(frame) {
        // Only for interpolation boxes
        if (this._type != 'interpolation_box') {
            return;
        }

        // Undo/redo code
        window.cvat.addAction('Change Keyframe', () => {
            this.switchKeyFrame(frame);
        }, () => {
            this.switchKeyFrame(frame);
        }, frame);
        // End of undo/redo code

        if (frame in this._positions && Object.keys(this._positions).length > 1) {
            // If frame is first object frame, need redestribute attributes
            if (frame === this._frame) {
                this._frame = Object.keys(this._positions).map((el) => +el).sort((a,b) => a - b)[1];
                if (frame in this._attributes.mutable) {
                    this._attributes.mutable[this._frame] = this._attributes.mutable[frame];
                    delete(this._attributes.mutable[frame]);
                }
            }
            delete(this._positions[frame]);
        }
        else {
            let position = this._interpolatePosition(frame);
            this.updatePosition(frame, position, true);

            if (frame < this._frame) {
                if (this._frame in this._attributes.mutable) {
                    this._attributes.mutable[frame] = this._attributes.mutable[this._frame];
                    delete(this._attributes.mutable[this._frame]);
                }
                this._frame = frame;
            }
        }
        this._updateReason = 'keyframe';
        this.notify();
    }

    click() {
        this._updateReason = 'click';
        this.notify();
    }

    prevKeyFrame() {
        return this._neighboringFrames(window.cvat.player.frames.current)[0];
    }

    nextKeyFrame() {
        return this._neighboringFrames(window.cvat.player.frames.current)[1];
    }

    initKeyFrame() {
        return this._frame;
    }

    isKeyFrame(frame) {
        return frame in this._positions;
    }

    aamAttributeFocus() {
        this._updateReason = 'attributeFocus';
        this.notify();
    }

    select() {
        if (!this._selected) {
            this._selected = true;
            this._updateReason = 'selection';
            this.notify();
        }
    }

    deselect() {
        if (this._selected) {
            this._selected = false;
            this._updateReason = 'selection';
            this.notify();
        }
    }

    // Explicit remove by user
    remove() {
        // modify by eric
        trainigsaveFlag = false;
        $('#nextButtonFlag').prop('checked',false);
        //$('#nextButton_training')[0].setAttribute("class","playerButton_training");
        
        Logger.addEvent(Logger.EventType.deleteObject, {
            count: 1,
        });

        this.removed = true;

        let rm_dontcare = "dontcare_";
        $("#"+rm_dontcare.concat(this._id,"_L")).remove();
        $("#"+rm_dontcare.concat(this._id,"_R")).remove();

        let rm_point = "detectpoint_";
        $("#"+rm_point.concat(this._id,"_L")).remove();
        $("#"+rm_point.concat(this._id,"_R")).remove();

        let rm_pointAim = "detectpointAim_";
        $("#"+rm_pointAim.concat(this._id,"_L")).remove();
        $("#"+rm_pointAim.concat(this._id,"_R")).remove();

        // Undo/redo code
        window.cvat.addAction('Remove Object', () => {
            this.removed = false;
        }, () => {
            this.removed = true;
        }, window.cvat.player.frames.current);
        // End of undo/redo code
    }

    set z_order(value) {
        if (!this._locked) {
            let frame = window.cvat.player.frames.current;
            let position = this._interpolatePosition(frame);
            position.z_order = value;
            this.updatePosition(frame, position, true);
            this._updateReason = 'z_order';
            this.notify();
        }
    }

    set removed(value) {
        if (value) {
            this._active = false;
        }
        this._removed = value;
        this._updateReason = 'remove';
        this.notify();
    }

    get removed() {
        return this._removed;
    }

    get lock() {
        return this._locked;
    }

    get hiddenShape() {
        return this._hiddenShape;
    }

    get hiddenText() {
        return this._hiddenText;
    }

    set active(value) {
        this._active = value;

        // add by eric
        let labelsInfo = window.cvat.labelsInfo;
        let labelAttributes = labelsInfo.labelAttributes(this._label);

        for (let attrId in labelAttributes) {
            let attrInfo = labelsInfo.attrInfo(attrId);
                // add by eric
                if (attrInfo.name=="Type"){
                    // console.log(this._attributes.mutable[this._frame][attrId], "Type");
                    previous_type = this._attributes.mutable[this._frame][attrId];
                }
                // if (attrInfo.name=="Rotation"){
                //     console.log(this._attributes.mutable[this._frame][attrId], "Rotation");
                //     previous_rotation = this._attributes.mutable[this._frame][attrId];
                // } 
                if (attrInfo.name=="有開燈"){
                    // console.log(this._attributes.mutable[this._frame][attrId], "有開燈");
                    previous_Light = this._attributes.mutable[this._frame][attrId];
                } 
                if (attrInfo.name=="障礙物"){
                    // console.log(this._attributes.mutable[this._frame][attrId], "障礙物");
                    previous_cant_see = this._attributes.mutable[this._frame][attrId];
                } 
        }

        if (!this._removed) {
            this._updateReason = 'activation';
            this.notify();
        }
        // add by jeff
        let content = $('#frameContent');
        let shapes = $(content.find('.detectpointAim')).toArray();
        for (let shape of shapes) {
            content.append(shape);
        }
        shapes = $(content.find('.detectpoint')).toArray();
        for (let shape of shapes) {
            content.append(shape);
        }
    }

    get active() {
        return this._active;
    }

    set activeAAM(active) {
        this._activeAAM = active.shape;
        this._activeAAMAttributeId = active.attribute;
        this._updateReason = 'activeAAM';
        this.notify();
    }

    get activeAAM() {
        return {
            shape: this._activeAAM,
            attributeId: this._activeAAMAttributeId
        };
    }

    set merge(value) {
        this._merge = value;
        this._updateReason = 'merge';
        this.notify();
    }

    get merge() {
        return this._merge;
    }

    set groupping(value) {
        this._groupping = value;
        this._updateReason = 'groupping';
        this.notify();
    }

    get groupping() {
        return this._groupping;
    }

    set groupId(value) {
        this._groupId = value;
    }

    get groupId() {
        return this._groupId;
    }

    get type() {
        return this._type;
    }

    get id() {
        return this._id;
    }

    get frame() {
        return this._frame;
    }

    get color() {
        return this._color;
    }

    get updateReason() {
        return this._updateReason;
    }

    get label() {
        return this._label;
    }

    get keyframes() {
        return Object.keys(this._positions);
    }

    get selected() {
        return this._selected;
    }
}


class BoxModel extends ShapeModel {
    constructor(data, type, id, color) {
        super(data, data.shapes || [], type, id, color);
        this._positions = BoxModel.importPositions.call(this, data.shapes || data);
        this._setupKeyFrames();
    }

    _interpolatePosition(frame) {
        if (this._type.startsWith('annotation')) {
            return Object.assign({},
                this._positions[this._frame],
                {
                    outside: false
                }
            );
        }

        let [leftFrame, rightFrame] = this._neighboringFrames(frame);
        if (frame in this._positions) {
            leftFrame = frame;
        }

        let leftPos = null;
        let rightPos = null;

        if (leftFrame != null) leftPos = this._positions[leftFrame];
        if (rightFrame != null) rightPos = this._positions[rightFrame];

        if (!leftPos) {
            if (rightPos) {
                return Object.assign({}, rightPos, {
                    outside: true,
                });
            }
            else {
                return {
                    outside: true
                };
            }
        }

        if (frame === leftFrame || leftPos.outside || !rightPos || rightPos.outside) {
            return Object.assign({}, leftPos);
        }

        let moveCoeff = (frame - leftFrame) / (rightFrame - leftFrame);

        return {
            xtl: leftPos.xtl + (rightPos.xtl - leftPos.xtl) * moveCoeff,
            ytl: leftPos.ytl + (rightPos.ytl - leftPos.ytl) * moveCoeff,
            xbr: leftPos.xbr + (rightPos.xbr - leftPos.xbr) * moveCoeff,
            ybr: leftPos.ybr + (rightPos.ybr - leftPos.ybr) * moveCoeff,
            occluded: leftPos.occluded,
            outside: leftPos.outside,
            z_order: leftPos.z_order,
        };
    }

    _verifyArea(box) {
        return ((box.xbr - box.xtl) * (box.ybr - box.ytl) >= AREA_TRESHOLD);
    }

    updatePosition(frame, position, silent) {
        let pos = {
            xtl: Math.clamp(position.xtl, 0, window.cvat.player.geometry.frameWidth),
            ytl: Math.clamp(position.ytl, 0, window.cvat.player.geometry.frameHeight),
            xbr: Math.clamp(position.xbr, 0, window.cvat.player.geometry.frameWidth),
            ybr: Math.clamp(position.ybr, 0, window.cvat.player.geometry.frameHeight),
            occluded: position.occluded,
            z_order: position.z_order,
        }; 

        if (this._verifyArea(pos)) {
            if (this._type === 'annotation_box') {
                if (this._frame != frame) {
                    throw Error(`Got bad frame for annotation box during update position: ${frame}. Own frame is ${this._frame}`);
                }
            }

            if (!silent) {
                // Undo/redo code
                let oldPos = Object.assign({}, this._positions[frame]);
                window.cvat.addAction('Change Position', () => {
                    if (!Object.keys(oldPos).length) {
                        delete this._positions[frame];
                        this._updateReason = 'position';
                        this.notify();
                    }
                    else {
                        this.updatePosition(frame, oldPos, false);
                    }
                }, () => {
                    this.updatePosition(frame, pos, false);
                }, frame);
                // End of undo/redo code
            }

            if (this._type === 'annotation_box') {
                this._positions[frame] = pos;
            }
            else {
                this._positions[frame] = Object.assign(pos, {
                    outside: position.outside,
                });
            }
        }

        // add by Jeff
        // modify by ericlou
        // only update positsion
        //working
        
        let xdl, ydl, xdr, ydr;
        for (let attrId in this._attributes.mutable[frame]) {
            let attrInfo = window.cvat.labelsInfo.attrInfo(attrId);
            if(attrInfo.name == "DetectPoints") {
                let detectpoints = this._attributes.mutable[frame][attrId].replace(/"/g, "").split(/[\s,]+/);
                xdl = detectpoints[0];
                ydl = detectpoints[1];
                xdr = detectpoints[2];
                ydr = detectpoints[3];

                if (ydl != "-1" && ydr != "-1") {
                    if(xdl == "-1")xdl=+parseFloat(1/10).toFixed(6);
                    if(xdr == "-1")xdr=+parseFloat(9/10).toFixed(6);
                    
                    let new_y = +parseFloat(pos.ytl + (pos.ybr - pos.ytl) * 2/3).toFixed(6);

                    this.updateAttribute(frame, attrId, "\"" + xdl + "," + new_y + "," + xdr + "," + new_y + "\"");
                }

                break;
            }
        }

        if (!silent) {
            this._updateReason = 'position';
            this.notify();
        }
    }

    contain(mousePos, frame) {
        let pos = this._interpolatePosition(frame);
        if (pos.outside) return false;
        let x = mousePos.x;
        let y = mousePos.y;
        return (x >= pos.xtl && x <= pos.xbr && y >= pos.ytl && y <= pos.ybr);
    }

    distance(mousePos, frame) {
        let pos = this._interpolatePosition(frame);
        if (pos.outside) return Number.MAX_SAFE_INTEGER;
        let points = [{x: pos.xtl, y: pos.ytl,}, {x: pos.xbr, y: pos.ytl,}, {x: pos.xbr, y: pos.ybr,}, {x: pos.xtl, y: pos.ybr,}];
        let minDistance = Number.MAX_SAFE_INTEGER;
        for (let i = 0; i < points.length; i ++) {
            let p1 = points[i];
            let p2 = points[i+1] || points[0];

            // perpendicular from point to straight length
            let distance = (Math.abs((p2.y - p1.y) * mousePos.x - (p2.x - p1.x) * mousePos.y + p2.x * p1.y - p2.y * p1.x)) /
                Math.sqrt(Math.pow(p2.y - p1.y, 2) + Math.pow(p2.x - p1.x, 2));

            // check if perpendicular belongs to the straight segment
            let a = Math.pow(p1.x - mousePos.x, 2) + Math.pow(p1.y - mousePos.y, 2);
            let b = Math.pow(p2.x - p1.x, 2) + Math.pow(p2.y - p1.y, 2);
            let c = Math.pow(p2.x - mousePos.x, 2) + Math.pow(p2.y - mousePos.y, 2);
            if (distance < minDistance && (a + b - c) >= 0 && (c + b - a) >= 0) {
                minDistance = distance;
            }
        }
        return minDistance;
    }

    export() {
        let immutableAttributes = [];
        for (let attrId in this._attributes.immutable) {
            immutableAttributes.push({
                id: +attrId,
                value: this._attributes.immutable[attrId],
            });
        }
        
        //add by jeff
        this._exportGrouping(this._groupingID, this._groupingOrder); 

        if (this._type === 'annotation_box') {
            if (this._frame in this._attributes.mutable) {
                for (let attrId in this._attributes.mutable[this._frame]) {
                    immutableAttributes.push({
                        id: +attrId,
                        value: this._attributes.mutable[this._frame][attrId],
                    });
                }
            }

            // add by ericlou, obj_id
            return Object.assign({}, this._positions[this._frame], {
                attributes: immutableAttributes,
                label_id: this._label,
                group_id: this._groupId,
                frame: this._frame,
                obj_id: this._obj_id,
                grouping: this._grouping,
            });
        }
        else {
            let boxPath = {
                label_id: this._label,
                group_id: this._groupId,
                grouping: this._grouping,
                frame: this._frame,
                attributes: immutableAttributes,
                shapes: [],
            };

            for (let frame in this._positions) {
                let mutableAttributes = [];
                if (frame in this._attributes.mutable) {
                    for (let attrId in this._attributes.mutable[frame]) {
                        mutableAttributes.push({
                            id: +attrId,
                            value: this._attributes.mutable[frame][attrId],
                        });
                    }
                }

                let position = Object.assign({}, this._positions[frame], {
                    attributes: mutableAttributes,
                    frame: +frame,
                });
                boxPath.shapes.push(position);
            }

            return boxPath;
        }
    }

    removePoint() {
        // nothing do
    }

    static importPositions(positions) {
        let imported = {};
        if (this._type === 'interpolation_box') {
            let last_key_in_prev_segm = null;
            let segm_start = window.cvat.player.frames.start;
            let segm_stop = window.cvat.player.frames.stop;

            for (let pos of positions) {
                let frame = pos.frame;

                if (frame >= segm_start && frame <= segm_stop) {
                    imported[frame] = {
                        xtl: pos.xtl,
                        ytl: pos.ytl,
                        xbr: pos.xbr,
                        ybr: pos.ybr,
                        occluded: pos.occluded,
                        outside: pos.outside,
                        z_order: pos.z_order,
                    };
                }
                else {
                    console.log(`Frame ${frame} has been found in segment [${segm_start}-${segm_stop}]. It have been ignored.`);
                    if (!last_key_in_prev_segm || frame > last_key_in_prev_segm.frame) {
                        last_key_in_prev_segm = pos;
                    }
                }
            }

            if (last_key_in_prev_segm && !(segm_start in imported)) {
                imported[segm_start] = {
                    xtl: last_key_in_prev_segm.xtl,
                    ytl: last_key_in_prev_segm.ytl,
                    xbr: last_key_in_prev_segm.xbr,
                    ybr: last_key_in_prev_segm.ybr,
                    occluded: last_key_in_prev_segm.occluded,
                    outside: last_key_in_prev_segm.outside,
                    z_order: last_key_in_prev_segm.z_order,
                };
            }

            return imported;
        }

        imported[this._frame] = {
            xtl: positions.xtl,
            ytl: positions.ytl,
            xbr: positions.xbr,
            ybr: positions.ybr,
            occluded: positions.occluded,
            z_order: positions.z_order,
        };

        return imported;
    }
}

class PolyShapeModel extends ShapeModel {
    constructor(data, type, id, color) {
        super(data, data.shapes || [], type, id, color);
        this._positions = PolyShapeModel.importPositions.call(this, data.shapes || data);
        this._setupKeyFrames();
    }


    _interpolatePosition(frame) {
        if (frame in this._positions) {
            return Object.assign({}, this._positions[frame], {
                outside: false
            });
        }
        else {
            return {
                outside: true
            };
        }
    }

    updatePosition(frame, position, silent) {
        let box = {
            xtl: Number.MAX_SAFE_INTEGER,
            ytl: Number.MAX_SAFE_INTEGER,
            xbr: Number.MIN_SAFE_INTEGER,
            ybr: Number.MIN_SAFE_INTEGER,
        };

        let points = PolyShapeModel.convertStringToNumberArray(position.points);
        for (let point of points) {
            point.x = Math.clamp(point.x, 0, window.cvat.player.geometry.frameWidth);
            point.y = Math.clamp(point.y, 0, window.cvat.player.geometry.frameHeight);
            box.xtl = Math.min(box.xtl, point.x);
            box.ytl = Math.min(box.ytl, point.y);
            box.xbr = Math.max(box.xbr, point.x);
            box.ybr = Math.max(box.ybr, point.y);
        }
        position.points = PolyShapeModel.convertNumberArrayToString(points);

        let pos = {
            occluded: position.occluded,
            points: position.points,
            z_order: position.z_order,
        };

        if (this._verifyArea(box)) {
            if (!silent) {
                // Undo/redo code
                let oldPos = Object.assign({}, this._positions[frame]);
                window.cvat.addAction('Change Position', () => {
                    this.updatePosition(frame, oldPos, false);
                }, () => {
                    this.updatePosition(frame, pos, false);
                }, frame);
                // End of undo/redo code
            }

            if (this._type.startsWith('annotation')) {
                if (this._frame != frame) {
                    throw Error(`Got bad frame for annotation poly shape during update position: ${frame}. Own frame is ${this._frame}`);
                }
                this._positions[frame] = pos;
            }
            else {
                this._positions[frame] = Object.assign(pos, {
                    outside: position.outside,
                });
            }
        }

        if (!silent) {
            this._updateReason = 'position';
            this.notify();
        }
    }

    export() {
        let immutableAttributes = [];
        for (let attrId in this._attributes.immutable) {
            immutableAttributes.push({
                id: +attrId,
                value: this._attributes.immutable[attrId],
            });
        }

        //add by jeff
        this._exportGrouping(this._groupingID, this._groupingOrder); 
        
        if (this._type.startsWith('annotation')) {
            if (this._frame in this._attributes.mutable) {
                for (let attrId in this._attributes.mutable[this._frame]) {
                    immutableAttributes.push({
                        id: +attrId,
                        value: this._attributes.mutable[this._frame][attrId],
                    });
                }
            }

            return Object.assign({}, this._positions[this._frame], {
                attributes: immutableAttributes,
                label_id: this._label,
                group_id: this._groupId,
                grouping: this._grouping,
                frame: this._frame,
                obj_id: this._obj_id,
            });
        }
        else {
            let polyPath = {
                label_id: this._label,
                group_id: this._groupId,
                grouping: this._grouping,
                frame: this._frame,
                attributes: immutableAttributes,
                shapes: [],
            };

            for (let frame in this._positions) {
                let mutableAttributes = [];
                if (frame in this._attributes.mutable) {
                    for (let attrId in this._attributes.mutable[frame]) {
                        mutableAttributes.push({
                            id: +attrId,
                            value: this._attributes.mutable[frame][attrId],
                        });
                    }
                }

                let position = Object.assign({}, this._positions[frame], {
                    attributes: mutableAttributes,
                    frame: +frame,
                });

                polyPath.shapes.push(position);
            }

            return polyPath;
        }
    }

    removePoint(idx) {
        let frame = window.cvat.player.frames.current;
        let position = this._interpolatePosition(frame);
        let points = PolyShapeModel.convertStringToNumberArray(position.points);
        if (points.length > this._minPoints) {
            points.splice(idx, 1);
            position.points = PolyShapeModel.convertNumberArrayToString(points);
            this.updatePosition(frame, position);
            
        }
    }

    static convertStringToNumberArray(serializedPoints) {
        let pointArray = [];
        for (let pair of serializedPoints.split(' ')) {
            pointArray.push({
                x: +pair.split(',')[0],
                y: +pair.split(',')[1],
            });
        }
        return pointArray;
    }

    static convertNumberArrayToString(arrayPoints) {
        let serializedPoints = '';
        for (let point of arrayPoints) {
            serializedPoints += `${point.x},${point.y} `;
        }
        let len = serializedPoints.length;
        if (len) {
            serializedPoints = serializedPoints.substring(0, len - 1);
        }

        return serializedPoints;
    }

    static importPositions(positions) {
        let imported = {};
        if (this._type.startsWith('interpolation')) {
            let last_key_in_prev_segm = null;
            let segm_start = window.cvat.player.frames.start;
            let segm_stop = window.cvat.player.frames.stop;

            for (let pos of positions) {
                let frame = pos.frame;
                if (frame >= segm_start && frame <= segm_stop) {
                    imported[pos.frame] = {
                        points: pos.points,
                        occluded: pos.occluded,
                        outside: pos.outside,
                        z_order: pos.z_order,
                    };
                }
                else {
                    console.log(`Frame ${frame} has been found in segment [${segm_start}-${segm_stop}]. It have been ignored.`);
                    if (!last_key_in_prev_segm || frame > last_key_in_prev_segm.frame) {
                        last_key_in_prev_segm = pos;
                    }
                }
            }

            if (last_key_in_prev_segm && !(segm_start in imported)) {
                imported[segm_start] = {
                    points: last_key_in_prev_segm.points,
                    occluded: last_key_in_prev_segm.occluded,
                    outside: last_key_in_prev_segm.outside,
                    z_order: last_key_in_prev_segm.z_order,
                };
            }

            return imported;
        }

        imported[this._frame] = {
            points: positions.points,
            occluded: positions.occluded,
            z_order: positions.z_order,
        };

        return imported;
    }
}

class PointsModel extends PolyShapeModel {
    constructor(data, type, id, color) {
        super(data, type, id, color);
        this._minPoints = 1;
    }

    distance(mousePos, frame) {
        let pos = this._interpolatePosition(frame);
        if (pos.outside) return Number.MAX_SAFE_INTEGER;
        let points = PolyShapeModel.convertStringToNumberArray(pos.points);
        let minDistance = Number.MAX_SAFE_INTEGER;
        for (let point of points) {
            let distance = Math.sqrt(Math.pow(point.x - mousePos.x, 2) + Math.pow(point.y - mousePos.y, 2));
            if (distance < minDistance) {
                minDistance = distance;
            }
        }
        return minDistance;
    }

    _verifyArea() {
        return true;
    }
}


class PolylineModel extends PolyShapeModel {
    constructor(data, type, id, color) {
        super(data, type, id, color);
        this._minPoints = 2;
    }

    _verifyArea(box) {
        return ((box.xbr - box.xtl) >= AREA_TRESHOLD || (box.ybr - box.ytl) >= AREA_TRESHOLD);
    }

    distance(mousePos, frame) {
        let pos = this._interpolatePosition(frame);
        if (pos.outside) return Number.MAX_SAFE_INTEGER;
        let points = PolyShapeModel.convertStringToNumberArray(pos.points);
        let minDistance = Number.MAX_SAFE_INTEGER;
        for (let i = 0; i < points.length - 1; i ++) {
            let p1 = points[i];
            let p2 = points[i+1];

            // perpendicular from point to straight length
            let distance = (Math.abs((p2.y - p1.y) * mousePos.x - (p2.x - p1.x) * mousePos.y + p2.x * p1.y - p2.y * p1.x)) /
                Math.sqrt(Math.pow(p2.y - p1.y, 2) + Math.pow(p2.x - p1.x, 2));

            // check if perpendicular belongs to the straight segment
            let a = Math.pow(p1.x - mousePos.x, 2) + Math.pow(p1.y - mousePos.y, 2);
            let b = Math.pow(p2.x - p1.x, 2) + Math.pow(p2.y - p1.y, 2);
            let c = Math.pow(p2.x - mousePos.x, 2) + Math.pow(p2.y - mousePos.y, 2);
            if (distance < minDistance && (a + b - c) >= 0 && (c + b - a) >= 0) {
                minDistance = distance;
            }
        }
        return minDistance;
    }
}


class PolygonModel extends PolyShapeModel {
    constructor(data, type, id, color) {
        super(data, type, id, color);
        this._minPoints = 3;
        this._draggable = false;
    }

    _verifyArea(box) {
        return ((box.xbr - box.xtl) * (box.ybr - box.ytl) >= AREA_TRESHOLD);
    }

    contain(mousePos, frame) {
        let pos = this._interpolatePosition(frame);
        if (pos.outside) return false;
        let points = PolyShapeModel.convertStringToNumberArray(pos.points);
        let wn = 0;
        for (let i = 0; i < points.length; i ++) {
            let p1 = points[i];
            let p2 = points[i + 1] || points[0];

            if (p1.y <= mousePos.y) {
                if (p2.y > mousePos.y) {
                    if (isLeft(p1, p2, mousePos) > 0) {
                        wn ++;
                    }
                }
            }
            else {
                if (p2.y < mousePos.y) {
                    if (isLeft(p1, p2, mousePos) < 0) {
                        wn --;
                    }
                }
            }
        }

        return wn != 0;

        function isLeft(P0, P1, P2) {
            return ( (P1.x - P0.x) * (P2.y - P0.y) - (P2.x -  P0.x) * (P1.y - P0.y) );
        }
    }

    distance(mousePos, frame) {
        let pos = this._interpolatePosition(frame);
        if (pos.outside) return Number.MAX_SAFE_INTEGER;
        let points = PolyShapeModel.convertStringToNumberArray(pos.points);
        let minDistance = Number.MAX_SAFE_INTEGER;
        for (let i = 0; i < points.length; i ++) {
            let p1 = points[i];
            let p2 = points[i+1] || points[0];

            // perpendicular from point to straight length
            let distance = (Math.abs((p2.y - p1.y) * mousePos.x - (p2.x - p1.x) * mousePos.y + p2.x * p1.y - p2.y * p1.x)) /
                Math.sqrt(Math.pow(p2.y - p1.y, 2) + Math.pow(p2.x - p1.x, 2));

            // check if perpendicular belongs to the straight segment
            let a = Math.pow(p1.x - mousePos.x, 2) + Math.pow(p1.y - mousePos.y, 2);
            let b = Math.pow(p2.x - p1.x, 2) + Math.pow(p2.y - p1.y, 2);
            let c = Math.pow(p2.x - mousePos.x, 2) + Math.pow(p2.y - mousePos.y, 2);
            if (distance < minDistance && (a + b - c) >= 0 && (c + b - a) >= 0) {
                minDistance = distance;
            }
        }
        return minDistance;
    }

    set draggable(value) {
        this._draggable = value;
        this._updateReason = 'draggable';
        this.notify();
    }

    get draggable() {
        return this._draggable;
    }
}


/******************************** SHAPE CONTROLLERS  ********************************/

class ShapeController {
    constructor(shapeModel) {
        this._model = shapeModel;
    }
    
    // modify by Eric
    updatePosition(frame, position) {
        trainigsaveFlag = false;
        if($('#nextButtonFlag').length) $('#nextButtonFlag').prop('checked',false);
       // if($('#nextButton_training').length) $('#nextButton_training')[0].setAttribute("class","playerButton_training");
        this._model.updatePosition(frame, position);

        // add by jeff woeking
        if (position.xtl>0 && position.xbr<=window.cvat.player.geometry.frameWidth-1) {
            let flag = false, detectPoints_id = null, type_value = '';
            for (let attrId in this._model._attributes.mutable[frame]) {
                let attrInfo = window.cvat.labelsInfo.attrInfo(attrId);
                if(attrInfo.name == "看不見車頭車尾") {
                    if(this._model._attributes.mutable[frame][attrId] == true) {
                        flag = true;
                        this.updateAttribute(frame, attrId, false);
                    }
                    else return;
                }
                if(attrInfo.name == "DetectPoints") {
                    detectPoints_id = attrId;
                }
                if(attrInfo.name == "Type") type_value = this._model._attributes.mutable[frame][attrId].toLowerCase();
            }
            if(flag) {
                if (type_value.includes("car") || type_value.includes("van") || type_value.includes("truck") || type_value.includes("bus") || type_value.includes("代步車")
                || type_value.includes("工程車") || type_value.includes("tram") || type_value=="無殼三輪車" || type_value=="有殼三輪車"){
                    this.updateAttribute(window.cvat.player.frames.current, detectPoints_id, "\"0.1,-1,0.9,-1\"");
                } else if (type_value=="bike" || type_value=="motorbike" || type_value=="動物"){
                    this.updateAttribute(window.cvat.player.frames.current, detectPoints_id, "\"0,-1,0.5,-1\"");
                } else this.updateAttribute(window.cvat.player.frames.current, detectPoints_id, "\"-1,-1,-1,-1\"");
            }
        }
    }

    updateAttribute(frame, attrId, value) {
        trainigsaveFlag = false;
        if($('#nextButtonFlag').length) $('#nextButtonFlag').prop('checked',false);
        //if($('#nextButton_training').length) $('#nextButton_training')[0].setAttribute("class","playerButton_training");
        this._model.updateAttribute(frame, attrId, value);
        
    }
    //add by jeff change color
    changeColor(color){
        trainigsaveFlag = false;
        this._model.changeColor(color);
    }

    interpolate(frame) {
        return this._model.interpolate(frame);
    }

    changeLabel(labelId) {
        trainigsaveFlag = false;
        if($('#nextButtonFlag').length) $('#nextButtonFlag').prop('checked',false);
        //if($('#nextButton_training').length) $('#nextButton_training')[0].setAttribute("class","playerButton_training");
        this._model.changeLabel(labelId);
    }

    remove(e) {
        if($('#nextButtonFlag').length) $('#nextButtonFlag').prop('checked',false);
        if (!window.cvat.mode) {
            if (!this._model.lock || e.shiftKey) {
                this._model.remove();
            }
        }
    }

    isKeyFrame(frame) {
        return this._model.isKeyFrame(frame);
    }

    switchOccluded() {
        this._model.switchOccluded(window.cvat.player.frames.current);
    }

    switchOutside() {
        this._model.switchOutside(window.cvat.player.frames.current);
    }

    switchKeyFrame() {
        this._model.switchKeyFrame(window.cvat.player.frames.current);
    }

    prevKeyFrame() {
        let frame = this._model.prevKeyFrame();
        if (Number.isInteger(frame)) {
            $('#frameNumber').prop('value', frame).trigger('change');
        }
    }

    nextKeyFrame() {
        let frame = this._model.nextKeyFrame();
        if (Number.isInteger(frame)) {
            $('#frameNumber').prop('value', frame).trigger('change');
        }
    }

    initKeyFrame() {
        let frame = this._model.initKeyFrame();
        $('#frameNumber').prop('value', frame).trigger('change');
    }

    switchLock() {
        this._model.switchLock();
    }

    switchHide() {
        this._model.switchHide();
    }

    click() {
        this._model.click();
    }

    model() {
        return this._model;
    }

    get id() {
        return this._model.id;
    }

    get label() {
        return this._model.label;
    }

    get type() {
        return this._model.type;
    }

    get lock() {
        return this._model.lock;
    }

    get merge() {
        return this._model.merge;
    }

    get hiddenShape() {
        return this._model.hiddenShape;
    }

    get hiddenText() {
        return this._model.hiddenText;
    }

    get color() {
        return this._model.color;
    }

    set active(value) {
        this._model.active = value;
    }
}


class BoxController extends ShapeController {
    constructor(boxModel) {
        super(boxModel);
    }
}

class PolyShapeController extends ShapeController {
    constructor(polyShapeModel) {
        super(polyShapeModel);
    }
}

class PointsController extends PolyShapeController {
    constructor(pointsModel) {
        super(pointsModel);
    }
}


class PolylineController extends PolyShapeController {
    constructor(polylineModel) {
        super(polylineModel);
    }
}

class PolygonController extends PolyShapeController {
    constructor(polygonModel) {
        super(polygonModel);
    }

    set draggable(value) {
        this._model.draggable = value;
    }

    get draggable() {
        return this._model.draggable;
    }
}


/******************************** SHAPE VIEWS  ********************************/
class ShapeView extends Listener {
    constructor(shapeModel, shapeController, svgScene, menusScene, menusObj) {
        super('onShapeViewUpdate', () => this);
        this._uis = {
            menu: null,
            attributes: {},
            buttons: {},
            changelabel: null,
            shape: null,
            text: [],
        };

        this._scenes = {
            svg: svgScene,
            menus: menusScene,
            //add by jeff
            menusObj: menusObj
        };

        this._appearance = {
            colors: shapeModel.color,
            fillOpacity: 0,
            selectedFillOpacity: 0.2,
        };

        this._flags = {
            editable: false,
            selected: false,
            dragging: false,
            resizing: false
        };

        this._controller = shapeController;

        this._shapeContextMenu = $('#shapeContextMenu');
        this._pointContextMenu = $('#pointContextMenu');

        shapeModel.subscribe(this);
    }


    _makeEditable() {
        if (this._uis.shape && this._uis.shape.node.parentElement && !this._flags.editable) {
            let events = {
                drag: null,
                resize: null
            };

            this._uis.shape.front();
            if (!this._controller.lock) {
                // Setup drag events
                this._uis.shape.draggable().on('dragstart', () => {
                    events.drag = Logger.addContinuedEvent(Logger.EventType.dragObject);
                    this._flags.dragging = true;
                    blurAllElements();
                    this._hideShapeText();
                    this.notify();
                }).on('dragend', (e) => {
                    let p1 = e.detail.handler.startPoints.point;
                    let p2 = e.detail.p;
                    if (Math.sqrt(Math.pow(p1.x - p2.x, 2) + Math.pow(p1.y - p2.y, 2)) > 1) {
                        let frame = window.cvat.player.frames.current;
                        this._controller.updatePosition(frame, this._buildPosition());
                    }
                    events.drag.close();
                    events.drag = null;
                    this._flags.dragging = false;
                    // modify by Eric
                    // this._removeShapeText();
                    this._showShapeText();
                    // console.log("no show text");
                    this.notify();
                }).on('mousedown', () => {
                    mousedown_in_shape = true;
                }).on('mouseup', () => {
                    mousedown_in_shape = false;
                });

                // Setup resize events
                let objWasResized = false;
                this._uis.shape.selectize({
                    classRect: 'shapeSelect',
                    rotationPoint: false,
                    pointSize: POINT_RADIUS * 2 / window.cvat.player.geometry.scale,
                    deepSelect: true,
                }).resize({
                    snapToGrid: 0.1,
                }).on('resizestart', () => {
                    objWasResized = false;
                    this._flags.resizing = true;
                    events.resize = Logger.addContinuedEvent(Logger.EventType.resizeObject);
                    blurAllElements();
                    this._hideShapeText();
                    this.notify();
                }).on('resizing', () => {
                    objWasResized = true;
                }).on('resizedone', () => {
                    if (objWasResized) {
                        let frame = window.cvat.player.frames.current;
                        this._controller.updatePosition(frame, this._buildPosition());
                        objWasResized = false;
                    }
                    events.resize.close();
                    events.resize = null;
                    this._flags.resizing = false;
                    // modify by Eric
                    // this._removeShapeText();
                    this._showShapeText();
                    // console.log("no show text");
                    this.notify();
                });


                this._updateColorForDots();
                let self = this;

                // JEFF WILL DO
                $('.svg_select_points').each(function() {
                    $(this).on('mouseover', () => {
                        this.instance.attr('stroke-width', STROKE_WIDTH * 2 / window.cvat.player.geometry.scale);
                    }).on('mouseout', () => {
                        this.instance.attr('stroke-width', STROKE_WIDTH / window.cvat.player.geometry.scale);
                    }).on('mousedown', () => {
                        self._positionateMenus();
                        mousedown_in_shape = true;
                        // $('.svg_select_points').removeAttr('lockedPoint');
                        // this.instance.attr('willlockedPoint','true');
                    }).on('mouseup', () => {
                        mousedown_in_shape = false;
                        //$('.svg_select_points').removeAttr('willlockedPoint');
                    });
                });

                this._flags.editable = true;
            }


            // Setup context menu
            this._uis.shape.on('mousedown.contextMenu', (e) => {
                if (e.which === 1) {
                    this._shapeContextMenu.hide(100);
                    this._pointContextMenu.hide(100);
                }
                if (e.which === 3) {
                    e.stopPropagation();
                }
            });

            this._uis.shape.on('contextmenu.contextMenu', (e) => {
                this._pointContextMenu.hide(100);
                let type = this._controller.type.split('_');
                if (type[0] === 'interpolation') {
                    this._shapeContextMenu.find('.interpolationItem').removeClass('hidden');
                }
                else {
                    this._shapeContextMenu.find('.interpolationItem').addClass('hidden');
                }

                let dragPolyItem =  this._shapeContextMenu.find('.polygonItem[action="drag_polygon"]');
                let draggable = this._controller.draggable;
                if (type[1] === 'polygon') {
                    dragPolyItem.removeClass('hidden');
                    if (draggable) {
                        dragPolyItem.text('Disable Dragging');
                    }
                    else {
                        dragPolyItem.text('Enable Dragging');
                    }
                }
                else {
                    dragPolyItem.addClass('hidden');
                }

                if(!passNoShow) {
                    this._shapeContextMenu.finish().show(100).offset({
                        top: e.pageY - 10,
                        left: e.pageX - 10,
                    });
                }
                else passNoShow = false;
                

                e.preventDefault();
                e.stopPropagation();
            });
        }
    }


    _makeNotEditable() {
        if (this._uis.shape && this._flags.editable) {
            this._uis.shape.draggable(false).selectize(false, {
                deepSelect: true,
            }).resize(false);

            this._uis.shape.off('dragstart')
                .off('dragend')
                .off('resizestart')
                .off('resizing')
                .off('resizedone')
                .off('contextmenu.contextMenu')
                .off('mousedown.contextMenu');
            this._flags.editable = false;
        }

        this._pointContextMenu.hide(100);
        this._shapeContextMenu.hide(100);
    }


    _select() {
        if (this._uis.shape && this._uis.shape.node.parentElement) {
            this._uis.shape.addClass('selectedShape');
            this._uis.shape.attr({
                'fill-opacity': this._appearance.selectedFillOpacity
            });
        }

        if (this._uis.menu) {
            this._uis.menu.addClass('highlightedUI');
            //add by jeff
            if(menuScroll){
                menuScroll = false;
                this._positionateMenus();
            }
            
        }
    }


    _deselect() {
        if (this._uis.shape) {
            this._uis.shape.removeClass('selectedShape');

            if (this._appearance.whiteOpacity) {
                this._uis.shape.attr({
                    'stroke-opacity': this._appearance.fillOpacity,
                    'stroke-width': 1 / window.cvat.player.geometry.scale,
                    'fill-opacity': this._appearance.fillOpacity
                });
            }
            else {
                this._uis.shape.attr({
                    'stroke-opacity': 1,
                    'stroke-width': STROKE_WIDTH / window.cvat.player.geometry.scale,
                    'fill-opacity': this._appearance.fillOpacity
                });
            }
        }

        if (this._uis.menu) {
            this._uis.menu.removeClass('highlightedUI');
        }
    }


    _removeShapeUI() {
        if (this._uis.shape) {
            this._uis.shape.remove();
            SVG.off(this._uis.shape.node);
            this._uis.shape = null;
        }
    }


    _removeShapeText() {
        // if (this._uis.text) {
        //     this._uis.text.remove();
        //     SVG.off(this._uis.text.node);
        //     this._uis.text = null;
        // }
        if(Array.isArray(this._uis.text)) {
            for(let a_text of this._uis.text) {
                a_text.remove();
                SVG.off(a_text.node);
            }
            this._uis.text = [];
        }
    }


    _removeMenu() {
        if (this._uis.menu) {
            this._uis.menu.remove();
            this._uis.menu = null;
        }
    }


    _hideShapeText() {
        for(let a_text of this._uis.text) {
            if (a_text && a_text.node.parentElement) {
                this._scenes.svg.node.removeChild(a_text.node);
            }
        }
        // if (this._uis.text && this._uis.text.node.parentElement) {
        //     this._scenes.svg.node.removeChild(this._uis.text.node);
        // }
    }


    _showShapeText() {
        if (!this._uis.text || this._uis.text.length == 0) {
            let frame = window.cvat.player.frames.current;
            this._drawShapeText(this._controller.interpolate(frame).attributes);
        }
        // else if (!this._uis.text.node.parentElement) {
        //     this._scenes.svg.node.appendChild(this._uis.text.node);
        // }
        else {
            for(let a_text of this._uis.text) {
                if (!a_text.node.parentElement) {
                    this._scenes.svg.node.appendChild(a_text.node);
                }
            }
        }

        this.updateShapeTextPosition();
    }


    _drawShapeText() {

        // modify by eric

        // this._removeShapeText();
        if (this._uis.shape) {
            // modify by ericlou, obj_id
            let id = this._controller._model._obj_id;//this._controller.id;
            let grouping = this._controller._model._grouping;
            let groupingID = this._controller._model._groupingID;
            let groupingOrder = this._controller._model._groupingOrder;
            let label = ShapeView.labels()[this._controller.label];
            let bbox = this._uis.shape.node.getBBox();
            
            let x = bbox.x + bbox.width + TEXT_MARGIN;
            let y = bbox.y;

            if (PROJECT != 'dms_training' && this._uis.shape.type=='polyline'){
                x = this._uis.shape.node.points[0].x + TEXT_MARGIN;
                y = this._uis.shape.node.points[0].y;
            }
            
            let gruopText = '';
            if (PROJECT=='apacorner') {
                for (let i = 0; i < groupingID.length; i++) {
                    if(i==0)
                        gruopText = groupingID[i];
                    else
                        gruopText += ',' + groupingID[i];
                }
            }
            else {
                for (let i = 0; i < groupingID.length; i++) {
                    if(i==0)
                        gruopText = groupingID[i] + '-' + groupingOrder[i];
                    else
                        gruopText += ',' + groupingID[i] + '-' + groupingOrder[i];
                }
            }

            if (PROJECT == 'dms_training' && this._uis.shape.type=='polyline') {
                this._uis.text = [];
                let labels = window.cvat.labelsInfo.labels();
                let labelId = this._controller._model._label;
                let label_str = labels[labelId];
                for (let i = 0; i < this._uis.shape.node.points.length; i++) {
                    let offset = TEXT_MARGIN * (1/window.cvat.player.geometry.scale);
                    if ((label_str.includes("眼睛") && i==1) || (label_str.includes("嘴巴") && i==2)){
                        offset = -TEXT_MARGIN * (1/window.cvat.player.geometry.scale);
                    }

                    x = this._uis.shape.node.points[i].x;
                    y = this._uis.shape.node.points[i].y + offset;
                    this._uis.text.push(this._scenes.svg.text((add) => {
                        // add.tspan(`${label.normalize()} ${id}`).addClass('bold');
                        add.tspan(`${id}-${i+1}`).addClass('bold');
                        add.tspan(`${gruopText}`).attr({ dy: '1em', x: x});
                        // for (let attrId in attributes) {
                        //     let value = attributes[attrId].value != AAMUndefinedKeyword ?
                        //         attributes[attrId].value : '';
                        //     let name = attributes[attrId].name;
                        //     add.tspan(`${name}: ${value}`).attr({ dy: '1em', x: x, attrId: attrId});
                        // }
                    }).move(x, y).addClass('shapeText regular'));
                }
            }
            else {
                this._uis.text = [];
                this._uis.text.push(this._scenes.svg.text((add) => {
                    // add.tspan(`${label.normalize()} ${id}`).addClass('bold');
                    add.tspan(`${id}`).addClass('bold');
                    add.tspan(`${gruopText}`).attr({ dy: '1em', x: x});
                    // for (let attrId in attributes) {
                    //     let value = attributes[attrId].value != AAMUndefinedKeyword ?
                    //         attributes[attrId].value : '';
                    //     let name = attributes[attrId].name;
                    //     add.tspan(`${name}: ${value}`).attr({ dy: '1em', x: x, attrId: attrId});
                    // }
                }).move(x, y).addClass('shapeText regular'));
            }
        }
    }


    _highlightAttribute(attrId) {

        for(let a_text of this._uis.text) {
            if (a_text) {
                for (let tspan of a_text.lines().members) {
                    if (+tspan.attr('attrId') == +attrId) {
                        tspan.fill('red');
                    }
                    else tspan.fill('white');
                }
            }
        }

        // if (this._uis.text) {
        //     for (let tspan of this._uis.text.lines().members) {
        //         if (+tspan.attr('attrId') == +attrId) {
        //             tspan.fill('red');
        //         }
        //         else tspan.fill('white');
        //     }
        // }
    }


    _setupOccludedUI(occluded) {
        if (this._uis.shape) {
            if (occluded) {
                this._uis.shape.node.classList.add('occludedShape');
            }
            else {
                this._uis.shape.node.classList.remove('occludedShape');
            }
        }
    }


    _setupLockedUI(locked) {
        if (this._uis.changelabel) {
            if (PROJECT != 'dms_training') {
                this._uis.changelabel.disabled = locked;
            }
        }

        if ('occlude' in this._uis.buttons) {
            this._uis.buttons.occlude.disabled = locked;
        }

        if ('keyframe' in this._uis.buttons) {
            this._uis.buttons.keyframe.disabled = locked;
        }

        if ('outside' in this._uis.buttons) {
            this._uis.buttons.outside.disabled = locked;
        }

        for (let attrId in this._uis.attributes) {
            let attrInfo = window.cvat.labelsInfo.attrInfo(attrId);
            let attribute = this._uis.attributes[attrId];
            if (attrInfo.type === 'radio') {
                for (let attrPart of attribute) {
                    attrPart.disabled = locked;
                }
            }
            else {
                attribute.disabled = locked;
            }
        }
        for (let attrId in this._uis.attributes) {
            let attrInfo = window.cvat.labelsInfo.attrInfo(attrId);
            if (attrInfo.name == "Type"){
                let value = this._uis.attributes[attrId].value.toLowerCase();
                if(value.includes("動物") || value.includes("行人") || value.includes("群") || value.includes("background")) {
                    for (let tmpId in this._uis.attributes) {
                        let tmpInfo = window.cvat.labelsInfo.attrInfo(tmpId);
                        if(!value.includes("動物") && tmpInfo.name=="Rotation") {
                            this._uis.attributes[tmpId].setAttribute('disabled', true);
                            this._uis.attributes[tmpId].value = "-90";
                        }
                        if(tmpInfo.name=="有開燈") {
                            this._uis.attributes[tmpId].setAttribute('disabled', true);
                            this._uis.attributes[tmpId].checked = false;
                        }
                        else if(tmpInfo.name=="障礙物") {
                            this._uis.attributes[tmpId].setAttribute('disabled', true);
                            this._uis.attributes[tmpId].checked = false;
                        }
                    }
                }
                if (value.includes("無人") || value.includes("人") || value.includes("background")) {
                    for (let tmpId in this._uis.attributes) {
                        let tmpInfo = window.cvat.labelsInfo.attrInfo(tmpId);
                        if(tmpInfo.name=="DetectPoints") {
                            this._uis.attributes[tmpId].value = "\"-1,-1,-1,-1\"";
                        }
                        if(tmpInfo.name=="看不見車頭車尾") {
                            this._uis.attributes[tmpId].setAttribute('disabled', true);
                            this._uis.attributes[tmpId].checked = false;
                        }
                    }
                }
            }
            if (attrInfo.name == "Dont_Care") {
                let value = this._uis.attributes[attrId].checked;
                if (value){
                    for (let tmpId in this._uis.attributes) {
                        let tmpInfo = window.cvat.labelsInfo.attrInfo(tmpId);
                        if(tmpInfo.name=="DetectPoints") {
                            this._uis.attributes[tmpId].value = "\"-1,-1,-1,-1\"";
                        }
                        if(tmpInfo.name=="看不見車頭車尾") {
                            this._uis.attributes[tmpId].setAttribute('disabled', true);
                            this._uis.attributes[tmpId].checked = false;
                        }
                    }
                }
            }
            if (attrInfo.name == "看不見車頭車尾") {
                let value = this._uis.attributes[attrId].checked;
                if (value){
                    for (let tmpId in this._uis.attributes) {
                        let tmpInfo = window.cvat.labelsInfo.attrInfo(tmpId);
                        if(tmpInfo.name=="DetectPoints") {
                            this._uis.attributes[tmpId].value = "\"-1,-1,-1,-1\"";
                            break;
                        }
                    }
                }
            }
        }
    }


    _setupMergeView(merge) {
        if (this._uis.shape) {
            if (merge) {
                this._uis.shape.addClass('mergeShape');
            }
            else {
                this._uis.shape.removeClass('mergeShape');
            }
        }
    }


    _setupGroupView(group) {
        if (this._uis.shape) {
            if (group) {
                this._uis.shape.addClass('groupShape');
            }
            else {
                this._uis.shape.removeClass('groupShape');
            }
        }
    }


    _positionateMenus() {
        if (this._uis.menu) {
            this._scenes.menus.scrollTop(0);
            this._scenes.menus.scrollTop(this._uis.menu.offset().top - this._scenes.menus.offset().top);
        }
    }


    _drawMenu(outside) {
        let id = this._controller.id;
        // add by Ericlou
        let obj_id = this._controller._model._obj_id;

        let label = ShapeView.labels()[this._controller.label];
        let type = this._controller.type;
        let shortkeys = ShapeView.shortkeys();

        // Use native java script code because draw UI is performance bottleneck
        let UI = document.createElement('div');
        let titleBlock = makeTitleBlock.call(this, obj_id, label, type, shortkeys);

        let buttonBlock = makeButtonBlock.call(this, type, outside, shortkeys);
        UI.appendChild(titleBlock);
        UI.appendChild(buttonBlock);

        if (!outside) {
            let changeLabelBlock = makeChangeLabelBlock.call(this, shortkeys);
            let attributesBlock = makeAttributesBlock.call(this, id);
            if (changeLabelBlock) {
                UI.appendChild(changeLabelBlock);
            }

            if (attributesBlock) {
                UI.appendChild(attributesBlock);
            }
        }
        UI.id = `menu_obj_${obj_id}`
        UI.classList.add('uiElement', 'regular');
        UI.style.backgroundColor = this._controller.color.ui;

        this._uis.menu = $(UI);

        let index = this._scenes.menusObj.findIndex(x => x.obj_id==obj_id);
        if (index==-1)
            this._scenes.menusObj.push({'obj_id':obj_id, 'menu':this._uis.menu});
        else
            this._scenes.menusObj[index] = {'obj_id':obj_id, 'menu':this._uis.menu};

        this._scenes.menusObj = this._scenes.menusObj.sort(function (a, b) {
                                    return a.obj_id > b.obj_id ? 1 : -1;
                                });
        
        //for (let member in this._scenes.menus) delete this._scenes.menus[member];

        // while (this._scenes.menus.firstChild) {
        //     this._scenes.menus.removeChild(this._scenes.menus.firstChild);
        // }
        //this._scenes.menus.empty();

        for (let member in this._scenes.menusObj) this._scenes.menus.append(this._scenes.menusObj[member].menu);

        $(`#menu_obj_${obj_id} .selectpicker`).selectpicker('refresh');
        //this._scenes.menus.append(this._uis.menu);
        
        // add by ericlou, for Rotation Unknown
        $("option[value='Unknown']").attr("disabled", "disabled");
        $("input[type='radio'][value='Unknow']").attr("disabled", "disabled");

        function makeTitleBlock(id, label, type, shortkeys) {
            let title = document.createElement('div');

            let titleText = document.createElement('label');
            titleText.innerText = `${label} ${id} ` +
                `[${type.split('_')[1]}, ${type.split('_')[0]}]`;
            title.appendChild(titleText);
            title.classList.add('bold');
            title.style.marginRight = '32px';

            let deleteButton = document.createElement('a');
            deleteButton.classList.add('close');
            this._uis.buttons['delete'] = deleteButton;
            deleteButton.setAttribute('title', `
                ${shortkeys['delete_shape'].view_value} - ${shortkeys['delete_shape'].description}`);

            title.appendChild(titleText);
            title.appendChild(deleteButton);

            return title;
        }

        function makeButtonBlock(type, outside, shortkeys) {
            let buttonBlock = document.createElement('div');
            buttonBlock.appendChild(document.createElement('hr'));

            if (!outside) {
                let annotationCenter = document.createElement('center');

                let lockButton = document.createElement('button');
                lockButton.classList.add('graphicButton', 'lockButton');
                lockButton.setAttribute('title', `
                    ${shortkeys['switch_lock_property'].view_value} - ${shortkeys['switch_lock_property'].description}` + `\n` +
                    `${shortkeys['switch_all_lock_property'].view_value} - ${shortkeys['switch_all_lock_property'].description}`);

                let occludedButton = document.createElement('button');
                occludedButton.classList.add('graphicButton', 'hidden', 'occludedButton');
                occludedButton.setAttribute('title', `
                    ${shortkeys['switch_occluded_property'].view_value} - ${shortkeys['switch_occluded_property'].description}`);

                let copyButton = document.createElement('button');
                copyButton.classList.add('graphicButton', 'hidden', 'copyButton');
                copyButton.setAttribute('title', `
                    ${shortkeys['copy_shape'].view_value} - ${shortkeys['copy_shape'].description}` + `\n` +
                    `${shortkeys['switch_paste'].view_value} - ${shortkeys['switch_paste'].description}`);

                let propagateButton = document.createElement('button');
                propagateButton.classList.add('graphicButton', 'propagateButton');
                propagateButton.setAttribute('title', `
                    ${shortkeys['propagate_shape'].view_value} - ${shortkeys['propagate_shape'].description}`);

                let hiddenButton = document.createElement('button');
                hiddenButton.classList.add('graphicButton', 'hiddenButton');
                hiddenButton.setAttribute('title', `
                    ${shortkeys['switch_hide_mode'].view_value} - ${shortkeys['switch_hide_mode'].description}` + `\n` +
                    `${shortkeys['switch_all_hide_mode'].view_value} - ${shortkeys['switch_all_hide_mode'].description}`);

                annotationCenter.appendChild(lockButton);
                annotationCenter.appendChild(occludedButton);
                annotationCenter.appendChild(copyButton);
                annotationCenter.appendChild(propagateButton);
                annotationCenter.appendChild(hiddenButton);
                buttonBlock.appendChild(annotationCenter);

                this._uis.buttons['lock'] = lockButton;
                this._uis.buttons['occlude'] = occludedButton;
                this._uis.buttons['hide'] = hiddenButton;
                this._uis.buttons['copy'] = copyButton;
                this._uis.buttons['propagate'] = propagateButton;
            }

            if (type.split('_')[0] == 'interpolation') {
                let interpolationCenter = document.createElement('center');

                if (type.split('_')[1] == 'box') {
                    let outsideButton = document.createElement('button');
                    outsideButton.classList.add('graphicButton', 'outsideButton');

                    let keyframeButton = document.createElement('button');
                    keyframeButton.classList.add('graphicButton', 'keyFrameButton');

                    interpolationCenter.appendChild(outsideButton);
                    interpolationCenter.appendChild(keyframeButton);

                    this._uis.buttons['outside'] = outsideButton;
                    this._uis.buttons['keyframe'] = keyframeButton;
                }

                let prevKeyFrameButton = document.createElement('button');
                prevKeyFrameButton.classList.add('graphicButton', 'prevKeyFrameButton');
                prevKeyFrameButton.setAttribute('title', `
                    ${shortkeys['prev_key_frame'].view_value} - ${shortkeys['prev_key_frame'].description}`);

                let initKeyFrameButton = document.createElement('button');
                initKeyFrameButton.classList.add('graphicButton', 'initKeyFrameButton');

                let nextKeyFrameButton = document.createElement('button');
                nextKeyFrameButton.classList.add('graphicButton', 'nextKeyFrameButton');
                nextKeyFrameButton.setAttribute('title', `
                    ${shortkeys['next_key_frame'].view_value} - ${shortkeys['next_key_frame'].description}`);

                interpolationCenter.appendChild(prevKeyFrameButton);
                interpolationCenter.appendChild(initKeyFrameButton);
                interpolationCenter.appendChild(nextKeyFrameButton);
                buttonBlock.appendChild(interpolationCenter);

                this._uis.buttons['prevKeyFrame'] = prevKeyFrameButton;
                this._uis.buttons['initKeyFrame'] = initKeyFrameButton;
                this._uis.buttons['nextKeyFrame'] = nextKeyFrameButton;
            }

            return buttonBlock;
        }

        function makeChangeLabelBlock(shortkeys) {
            let labels = ShapeView.labels();
            if (Object.keys(labels).length > 1) {
                let block = document.createElement('div');

                let htmlLabel = document.createElement('label');
                htmlLabel.classList.add('semiBold');
                htmlLabel.innerText = 'Label: ';

                let select = document.createElement('select');
                if (PROJECT == 'dms_training') select.setAttribute('disabled', true);
                select.classList.add('regular');
                for (let labelId in labels) {
                    let option = document.createElement('option');
                    option.setAttribute('value', labelId);
                    option.innerText = `${labels[labelId].normalize()}`;
                    select.add(option);
                }

                select.setAttribute('title', `
                    ${shortkeys['change_shape_label'].view_value} - ${shortkeys['change_shape_label'].description}`);

                block.appendChild(htmlLabel);
                block.appendChild(select);

                this._uis.changelabel = select;
                return block;
            }

            return null;
        }

        function makeAttributesBlock(objectId) {
            let attributes = window.cvat.labelsInfo.labelAttributes(this._controller.label);

            if (Object.keys(attributes).length) {
                let block = document.createElement('div');
                let htmlLabel = document.createElement('label');
                htmlLabel.classList.add('semiBold');
                htmlLabel.innerHTML = 'Attributes <br>';

                block.appendChild(htmlLabel);

                // Make it beaturiful. Group attributes by type:
                // modify by jeff
                let attrByType = [];
                let attrTmp = {};

                let attrIndexTmp = 13;
                for (let attrId in attributes) {
                    let attrInfo = window.cvat.labelsInfo.attrInfo(attrId);
                    attrByType[attrInfo.type] = attrByType[attrInfo.type] || [];
                    attrByType[attrInfo.type].push(attrId);
                    
                    // sort, show att order  
                    if(attrInfo.name == "Type"){
                        attrTmp[0]=attrId;
                    }else if(attrInfo.name == "有開燈"){
                        attrTmp[1]=attrId;
                    }else if(attrInfo.name == "障礙物"){
                        attrTmp[2]=attrId;
                    }else if(attrInfo.name == "Rotation"){
                        attrTmp[3]=attrId;
                    }else if(attrInfo.name == "Truncated"){
                        attrTmp[4]=attrId;
                    }else if(attrInfo.name == "Occluded"){
                        attrTmp[5]=attrId;
                    }else if(attrInfo.name == "看不見車頭車尾"){
                        attrTmp[6]=attrId;
                    }else if(attrInfo.name == "Dont_Care"){
                        attrTmp[7]=attrId;
                    }else if(attrInfo.name == "DetectPoints"){
                        attrTmp[8]=attrId;
                    }// use labelme version
                    else if(attrInfo.name == "大標"){
                        attrTmp[9]=attrId;
                    }else if(attrInfo.name == "小標"){
                        attrTmp[10]=attrId;
                    }// use dms version
                    else if(attrInfo.name == "Pitch"){
                        attrTmp[11]=attrId;
                    }else if(attrInfo.name == "Key_Face"){
                        attrTmp[12]=attrId;
                    }
                    else{
                        attrIndexTmp += 1;
                        attrTmp[attrIndexTmp]=attrId;
                    }
                }

                let radios = attrByType['radio'] || [];
                let selects = attrByType['select'] || [];
                let texts = attrByType['text'] || [];
                let numbers = attrByType['number'] || [];
                let checkboxes = attrByType['checkbox'] || [];
                let multiselects = attrByType['multiselect'] || [];
                let singleselects = attrByType['singleselect'] || [];

                selects.sort((attrId_1, attrId_2) =>
                    attributes[attrId_1].normalize().length - attributes[attrId_2].normalize().length
                );
                texts.sort((attrId_1, attrId_2) =>
                    attributes[attrId_1].normalize().length - attributes[attrId_2].normalize().length
                );
                numbers.sort((attrId_1, attrId_2) =>
                    attributes[attrId_1].normalize().length - attributes[attrId_2].normalize().length
                );
                checkboxes.sort((attrId_1, attrId_2) =>
                    attributes[attrId_1].normalize().length - attributes[attrId_2].normalize().length
                );

                //for (let attrId of [...radios, ...selects, ...texts, ...numbers, ...checkboxes]) {
                for (let index in attrTmp) {
                    let attrInfo = window.cvat.labelsInfo.attrInfo(attrTmp[index]);
                    let htmlAttribute = makeAttribute.call(this, attrInfo, attrTmp[index], objectId);
                    htmlAttribute.classList.add('uiAttr');

                    block.appendChild(htmlAttribute);
                }

                return block;
            }

            return null;
        }

        function makeAttribute(attrInfo, attrId, objectId) {
            switch (attrInfo.type) {
            case 'checkbox':
                return makeCheckboxAttr.call(this, attrInfo, attrId, objectId);
            case 'select':
                return makeSelectAttr.call(this, attrInfo, attrId, objectId);
            case 'radio':
                return makeRadioAttr.call(this, attrInfo, attrId, objectId);
            case 'number':
                return makeNumberAttr.call(this, attrInfo, attrId, objectId);
            case 'text':
                return makeTextAttr.call(this, attrInfo, attrId, objectId);
            case 'multiselect':
                return makeMultiselectAttr.call(this, attrInfo, attrId, objectId);
            case 'singleselect':
                return makeSingleselectAttr.call(this, attrInfo, attrId, objectId);
            default:
                throw Error(`Unknown attribute type found: ${attrInfo.type}`);
            }
        }

        function makeCheckboxAttr(attrInfo, attrId, objectId) {
            let block = document.createElement('div');

            let checkbox = document.createElement('input');
            checkbox.setAttribute('type', 'checkbox');
            checkbox.setAttribute('id', `attr_${attrId}_of_${objectId}`);
            checkbox.setAttribute('attrId', attrId);

            let label = document.createElement('label');
            label.setAttribute('for', `attr_${attrId}_of_${objectId}`);
            label.innerText = `${attrInfo.name.normalize()}`;

            block.appendChild(checkbox);
            block.appendChild(label);

            this._uis.attributes[attrId] = checkbox;
            return block;
        }

        function makeSelectAttr(attrInfo, attrId) {
            let block = document.createElement('div');

            let select = document.createElement('select');
            select.setAttribute('attrId', attrId);
            select.classList.add('regular', 'selectAttr');
            for (let value of attrInfo.values) {
                let option = document.createElement('option');
                option.setAttribute('value', value);
                if (value === AAMUndefinedKeyword) {
                    option.innerText = '';
                }
                else {
                    option.innerText = value.normalize();
                }

                select.add(option);
            }

            let label = document.createElement('label');
            label.innerText = `${attrInfo.name.normalize()}: `;

            block.appendChild(label);
            block.appendChild(select);

            this._uis.attributes[attrId] = select;
            return block;
        }

        function makeSingleselectAttr(attrInfo, attrId) {
            let block = document.createElement('div');

            let select = document.createElement('select');
            select.setAttribute('data-live-search', true);
            select.setAttribute('attrId', attrId);
            select.classList.add('selectpicker','regular', 'selectAttr');
            for (let value of attrInfo.values) {
                let option = document.createElement('option');
                option.setAttribute('value', value);
                if (value === AAMUndefinedKeyword) {
                    option.innerText = '';
                }
                else {
                    option.innerText = value.normalize();
                }

                select.add(option);
            }

            let label = document.createElement('label');
            label.innerText = `${attrInfo.name.normalize()}: `;

            block.appendChild(label);
            block.appendChild(select);

            this._uis.attributes[attrId] = select;
            return block;
        }

        // add by jeff
        function makeMultiselectAttr(attrInfo, attrId) {
            let block = document.createElement('div');

            let select = document.createElement('select');
            select.setAttribute('multiple', '');
            select.setAttribute('data-live-search', true);
            select.setAttribute('attrId', attrId);
            select.classList.add('selectpicker','regular', 'selectAttr');
            let flag_for_disabled = false;
            for (let values of attrInfo.values) {
                let optgroup = document.createElement('optgroup');
                // disable next group
                if (flag_for_disabled) optgroup.setAttribute('disabled', true);

                for (let value of values) {
                    if (PROJECT == 'apacorner' && value == 'obstructed') { flag_for_disabled = true; }

                    let option = document.createElement('option');
                    option.setAttribute('value', value);
                    if (value === AAMUndefinedKeyword) {
                        option.innerText = '';
                    }
                    else {
                        option.innerText = value.normalize();
                    }
                    optgroup.appendChild(option);
                }
                select.add(optgroup);
            }

            let label = document.createElement('label');
            label.innerText = `${attrInfo.name.normalize()}: `;

            block.appendChild(label);
            block.appendChild(select);

            this._uis.attributes[attrId] = select;

            //$(`select[attrid=${attrId}]`).selectpicker('refresh');
            
            return block;
        }

        function makeRadioAttr(attrInfo, attrId, objectId) {
            let block = document.createElement('fieldset');

            let legend = document.createElement('legend');
            legend.innerText = `${attrInfo.name.normalize()}`;
            block.appendChild(legend);

            this._uis.attributes[attrId] = [];
            for (let idx = 0; idx < attrInfo.values.length; idx ++) {
                let value = attrInfo.values[idx];
                let wrapper = document.createElement('div');

                let label = document.createElement('label');
                label.setAttribute('for', `attr_${attrId}_of_${objectId}_${idx}`);

                if (value === AAMUndefinedKeyword) {
                    label.innerText = '';
                }
                else {
                    label.innerText = value.normalize();
                }

                let radio = document.createElement('input');
                radio.setAttribute('type', 'radio');
                radio.setAttribute('name', `attr_${attrId}_of_${objectId}`);
                radio.setAttribute('attrId', attrId);
                radio.setAttribute('value', value);
                radio.setAttribute('id', `attr_${attrId}_of_${objectId}_${idx}`);

                wrapper.appendChild(radio);
                wrapper.appendChild(label);
                block.appendChild(wrapper);

                this._uis.attributes[attrId].push(radio);
            }

            return block;
        }

        function makeNumberAttr(attrInfo, attrId) {
            let [min, max, step] = attrInfo.values;
            let block = document.createElement('div');

            let label = document.createElement('label');
            label.innerText = `${attrInfo.name.normalize()}: `;

            let number = document.createElement('input');
            number.setAttribute('type', 'number');
            number.setAttribute('step', `${step}`);
            number.setAttribute('min', `${min}`);
            number.setAttribute('max', `${max}`);
            number.classList.add('regular', 'numberAttr');

            let stopProp = function(e) {
                let key = e.keyCode;
                let serviceKeys = [37, 38, 39, 40, 13, 16, 9, 109];
                if (serviceKeys.includes(key)) {
                    e.preventDefault();
                    return;
                }
                e.stopPropagation();
            };
            number.onkeydown = stopProp;

            block.appendChild(label);
            block.appendChild(number);

            this._uis.attributes[attrId] = number;
            return block;
        }

        function makeTextAttr(attrInfo, attrId, objectId) {
            let block = document.createElement('div');

            let label = document.createElement('label');
            label.innerText = `${attrInfo.name.normalize()}: `;

            let text = document.createElement('input');
            // add by jeff
            // modify by eric
            text.setAttribute('attrId', attrId);
            text.setAttribute('caside_id', objectId)
            text.setAttribute('type', 'text');
            if(attrInfo.name.normalize()=='DetectPoints'){
                text.readOnly = true;
            }
            text.classList.add('regular', 'textAttr');

            let stopProp = function(e) {
                let key = e.keyCode;
                let serviceKeys = [37, 38, 39, 40, 13, 16, 9, 109];
                if (serviceKeys.includes(key)) {
                    e.preventDefault();
                    return;
                }
                e.stopPropagation();
            };
            text.onkeydown = stopProp;

            block.appendChild(label);
            block.appendChild(text);

            this._uis.attributes[attrId] = text;
            return block;
        }
    }

    _drawShapeUI() {
        this._uis.shape.on('click', function() {
            this._positionateMenus();
            menuScroll = true;
            this._controller.click();
        }.bind(this));

        // Save view in order to have access to view in shapeGrouper (no such other methods to get it)
        this._uis.shape.node.cvatView = this;
    }


    _updateButtonsBlock(position) {
        let occluded = position.occluded;
        let outside = position.outside;
        let lock = this._controller.lock;
        let hiddenShape = this._controller.hiddenShape;
        let hiddenText = this._controller.hiddenText;
        let keyFrame = this._controller.isKeyFrame(window.cvat.player.frames.current);

        if ('occlude' in this._uis.buttons) {
            if (occluded) {
                this._uis.buttons.occlude.classList.add('occluded');
            }
            else {
                this._uis.buttons.occlude.classList.remove('occluded');
            }
            this._uis.buttons.occlude.disabled = lock;
        }

        if ('lock' in this._uis.buttons) {
            if (lock) {
                this._uis.buttons.lock.classList.add('locked');
            }
            else {
                this._uis.buttons.lock.classList.remove('locked');
            }
        }

        if ('hide' in this._uis.buttons) {
            if (hiddenShape) {
                this._uis.buttons.hide.classList.remove('hiddenText');
                this._uis.buttons.hide.classList.add('hiddenShape');
            }
            else if (hiddenText) {
                this._uis.buttons.hide.classList.add('hiddenText');
                this._uis.buttons.hide.classList.remove('hiddenShape');
            }
            else {
                this._uis.buttons.hide.classList.remove('hiddenText', 'hiddenShape');
            }
        }

        if ('outside' in this._uis.buttons) {
            if (outside) {
                this._uis.buttons.outside.classList.add('outside');
            }
            else {
                this._uis.buttons.outside.classList.remove('outside');
            }
        }

        if ('keyframe' in this._uis.buttons) {
            if (keyFrame) {
                this._uis.buttons.keyframe.classList.add('keyFrame');
            }
            else {
                this._uis.buttons.keyframe.classList.remove('keyFrame');
            }
        }
    }


    _updateMenuContent(interpolation) {
        let attributes = interpolation.attributes;
        for (let attrId in attributes) {
            if (attrId in this._uis.attributes) {
                let attrInfo = window.cvat.labelsInfo.attrInfo(attrId);
                if (attrInfo.type === 'radio') {
                    let idx = attrInfo.values.indexOf(attributes[attrId].value);
                    this._uis.attributes[attrId][idx].checked = true;
                }
                else if (attrInfo.type === 'checkbox') {
                    this._uis.attributes[attrId].checked = attributes[attrId].value;
                }
                else if (attrInfo.type === 'multiselect') {

                    if(attributes[attrId].value.includes('obstructed')) {
                        $(this._uis.attributes[attrId]).children()[1].removeAttribute('disabled');
                    }
                    else {
                        $(this._uis.attributes[attrId]).children()[1].setAttribute('disabled', true);
                    }

                    $(this._uis.attributes[attrId]).val(attributes[attrId].value);
                    $(this._uis.attributes[attrId]).selectpicker('render');
                    // this._uis.attributes[attrId].value = attributes[attrId].value;
                    // $(this._uis.attributes[attrId]).selectpicker('refresh');
                    console.log('_updateMenuContent multiselect',attributes[attrId].value);
                }
                else if (attrInfo.type === 'singleselect') {
                    $(this._uis.attributes[attrId]).val(attributes[attrId].value);
                    $(this._uis.attributes[attrId]).selectpicker('render');
                }
                else {
                    this._uis.attributes[attrId].value = attributes[attrId].value;
                }
            }
        }

        if (this._uis.changelabel) {
            this._uis.changelabel.value = this._controller.label;
        }

        this._updateButtonsBlock(interpolation.position);
    }


    _activateMenu() {
        if ('occlude' in this._uis.buttons) {
            this._uis.buttons.occlude.onclick = () => {
                this._controller.switchOccluded();
            };
        }

        if ('lock' in this._uis.buttons) {
            this._uis.buttons.lock.onclick = () => {
                this._controller.switchLock();
            };
        }

        if ('hide' in this._uis.buttons) {
            this._uis.buttons.hide.onclick = () => {
                this._controller.switchHide();
            };
        }

        if ('copy' in this._uis.buttons) {
            this._uis.buttons.copy.onclick = () => {
                Mousetrap.trigger(window.cvat.config.shortkeys['copy_shape'].value, 'keydown');
            };
        }

        if ('propagate' in this._uis.buttons) {
            this._uis.buttons.propagate.onclick = () => {
                Mousetrap.trigger(window.cvat.config.shortkeys['propagate_shape'].value, 'keydown');
            };
        }

        if ('delete' in this._uis.buttons) {
            
            this._uis.buttons.delete.onclick = (e) => {
                let index = this._scenes.menusObj.findIndex(x => x.obj_id==this._controller._model._obj_id);
                
                //清除當前shape值
                let activeShape = this._controller._model;
                let needDelgroupingID = [... activeShape._groupingID];
                let needDelgroupingOrder = [... activeShape._groupingOrder];
                let groupMap = window.cvat.groupingData.get();
                if (PROJECT=='apacorner') {
                    //清除map中有關的group
                    for (let i = 0; i < needDelgroupingID.length; i++) {
                        if(!(groupMap[needDelgroupingID[i]] === undefined)) {
                            delete groupMap[needDelgroupingID[i]];
                        }
                    }
                    //清除shape中有關的group
                    let currentShapes = window.cvat.data.getCurrnetShapes();
                    currentShapes.forEach(function(shape) {
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
                        if(!(groupMap[needDelgroupingID[i]] === undefined)) {
                            let index = groupMap[needDelgroupingID[i]].indexOf([needDelgroupingOrder[i]]);
                            if(index!=-1) {
                                groupMap[needDelgroupingID[i]].splice(index, 1);
                            }
                            // if [] will delete
                            if(groupMap[needDelgroupingID[i]].length == 0) {
                                delete groupMap[needDelgroupingID[i]];
                            }
                        }
                    }
                }
                activeShape._grouping = '';
                activeShape._groupingID = [];
                activeShape._groupingOrder = [];
                
                if (index > -1) {
                    this._scenes.menusObj.splice(index, 1);
                }
                this._controller.remove(e)
            };
        }

        if ('outside' in this._uis.buttons) {
            this._uis.buttons.outside.onclick = () => {
                this._controller.switchOutside();
            };
        }

        if ('keyframe' in this._uis.buttons) {
            this._uis.buttons.keyframe.onclick = () => {
                this._controller.switchKeyFrame();
            };
        }

        if ('prevKeyFrame' in this._uis.buttons) {
            this._uis.buttons.prevKeyFrame.onclick = () => this._controller.prevKeyFrame();
        }

        if ('nextKeyFrame' in this._uis.buttons) {
            this._uis.buttons.nextKeyFrame.onclick = () => this._controller.nextKeyFrame();
        }

        if ('initKeyFrame' in this._uis.buttons) {
            this._uis.buttons.initKeyFrame.onclick = () => this._controller.initKeyFrame();
        }

        if (this._uis.changelabel) {
            this._uis.changelabel.onchange = (e) => this._controller.changeLabel(e.target.value);
        }

        this._uis.menu.on('mousedown', (e) => {
            if (!window.cvat.mode && !e.ctrlKey) {
                this._controller.active = true;
            }
        });

        // add by jeff
        function setLightFix (attributes,controller) {
            for (let tmpId in attributes) {
                let tmpInfo = window.cvat.labelsInfo.attrInfo(tmpId);
                if(tmpInfo.name=="有開燈"){
                    attributes[tmpId].setAttribute('disabled', true);
                    controller.updateAttribute(window.cvat.player.frames.current, tmpId, false);
                    break;
                }
            }
        }
        function setLightRelease (attributes,controller) {
            for (let tmpId in attributes) {
                let tmpInfo = window.cvat.labelsInfo.attrInfo(tmpId);
                if(tmpInfo.name=="有開燈"){
                    attributes[tmpId].removeAttribute('disabled');
                    break;
                }
            }
        }

        function setObstacleFix (attributes,controller) {
            for (let tmpId in attributes) {
                let tmpInfo = window.cvat.labelsInfo.attrInfo(tmpId);
                if(tmpInfo.name=="障礙物"){
                    attributes[tmpId].setAttribute('disabled', true);
                    controller.updateAttribute(window.cvat.player.frames.current, tmpId, false);
                    break;
                }
            }
        }
        function setObstacleRelease (attributes,controller) {
            for (let tmpId in attributes) {
                let tmpInfo = window.cvat.labelsInfo.attrInfo(tmpId);
                if(tmpInfo.name=="障礙物"){
                    attributes[tmpId].removeAttribute('disabled');
                    break;
                }
            }
        }

        function setRotationFix (attributes,controller) {
            for (let tmpId in attributes) {
                let tmpInfo = window.cvat.labelsInfo.attrInfo(tmpId);
                if(tmpInfo.name=="Rotation"){
                    attributes[tmpId].setAttribute('disabled', true);
                    controller.updateAttribute(window.cvat.player.frames.current, tmpId, "-90");
                    break;
                }
            }
        }
        function setRotationRelease (attributes,controller) {
            for (let tmpId in attributes) {
                let tmpInfo = window.cvat.labelsInfo.attrInfo(tmpId);
                if(tmpInfo.name=="Rotation"){
                    attributes[tmpId].removeAttribute('disabled');
                    break;
                }
            }
        }

        function setHeadTailFix (attributes,controller) {
            for (let tmpId in attributes) {
                let tmpInfo = window.cvat.labelsInfo.attrInfo(tmpId);
                if(tmpInfo.name == "看不見車頭車尾"){
                    attributes[tmpId].setAttribute('disabled', true);
                    controller.updateAttribute(window.cvat.player.frames.current, tmpId, false);
                    break;
                }
            }
        }
        function setHeadTailRelease (attributes,controller) {
            let flag = true;
            for (let tmpId in attributes) {
                let tmpInfo = window.cvat.labelsInfo.attrInfo(tmpId);
                if (tmpInfo.name == "Type"){
                    let value = attributes[tmpId].value.toLowerCase();
                    if (value.includes("無人") || value.includes("人") || value.includes("background")){
                        flag = false;
                        break;
                    }
                }
                if (tmpInfo.name == "Dont_Care"){
                    if (attributes[tmpId].checked){
                        flag = false;
                        break;
                    }
                    
                }
            }
            if(flag) {
                for (let tmpId in attributes) {
                    let tmpInfo = window.cvat.labelsInfo.attrInfo(tmpId);
                    if(tmpInfo.name == "看不見車頭車尾"){
                        attributes[tmpId].removeAttribute('disabled');
                        break;
                    }
                }
            }
        }
        function setDetectPointToEdge (attributes,controller) {
            let flag = false;
            for (let tmpId in attributes) {
                let tmpInfo = window.cvat.labelsInfo.attrInfo(tmpId);
                if(tmpInfo.name=="DetectPoints"){
                    let xtl = controller._model._positions[controller._model._frame].xtl;
                    let xbr = controller._model._positions[controller._model._frame].xbr;
                    let y = controller._model._positions[controller._model._frame].ybr;
                    
                    if (xtl==0 || xbr>=window.cvat.player.geometry.frameWidth-1) {
                        controller.updateAttribute(window.cvat.player.frames.current, tmpId, "\"-1,-1,-1,-1\"");
                        let rm_point = "detectpoint_";
                        $("#"+rm_point.concat(controller._model._id,"_L")).remove();
                        $("#"+rm_point.concat(controller._model._id,"_R")).remove();

                        let rm_pointAim = "detectpointAim_";
                        $("#"+rm_pointAim.concat(controller._model._id,"_L")).remove();
                        $("#"+rm_pointAim.concat(controller._model._id,"_R")).remove();

                        let rm_dontcare = "dontcare_";
                        $("#"+rm_dontcare.concat(controller._model._id,"_L")).remove();
                        $("#"+rm_dontcare.concat(controller._model._id,"_R")).remove();
                    }
                    else {
                        flag = true;
                    }                    
                    break;
                }
            }
            if (flag) {
                for (let tmpId in attributes) {
                    let tmpInfo = window.cvat.labelsInfo.attrInfo(tmpId);
                    if(tmpInfo.name=="看不見車頭車尾"){
                        controller.updateAttribute(window.cvat.player.frames.current, tmpId, false);
                        break;
                    }
                }
            }
        }
        function setDetectPointDefault (attributes,controller,preValue) {
            let value = null, detectpoints = null, att_id = null;
            for (let tmpId in attributes) {
                let tmpInfo = window.cvat.labelsInfo.attrInfo(tmpId);
                if(tmpInfo.name=="Type") value = attributes[tmpId].value.toLowerCase();
                if(tmpInfo.name=="DetectPoints"){
                    detectpoints = attributes[tmpId].value.replace(/"/g, "").split(/[\s,]+/);
                    att_id = tmpId;
                }
            }
            if (value.includes("car") || value.includes("van") || value.includes("truck") || value.includes("bus") || value.includes("代步車")
                || value.includes("工程車") || value.includes("tram") || value=="無殼三輪車" || value=="有殼三輪車"){
                value = 2;
            } else if (value=="bike" || value=="motorbike" || value=="動物"){
                value = 1;
            } else value = 0;

            if (preValue == null) {
                switch(value) {
                    case 0 : controller.updateAttribute(window.cvat.player.frames.current, att_id, "\"-1,-1,-1,-1\""); break;
                    case 1 : controller.updateAttribute(window.cvat.player.frames.current, att_id, "\"0,-1,0.5,-1\""); break;
                    case 2 : controller.updateAttribute(window.cvat.player.frames.current, att_id, "\"0.1,-1,0.9,-1\""); break;
                }
                return;
            } else if (preValue.includes("car") || preValue.includes("van") || preValue.includes("truck") || preValue.includes("bus") || preValue.includes("代步車")
                || preValue.includes("工程車") || preValue.includes("tram") || preValue=="無殼三輪車" || preValue=="有殼三輪車"){
                preValue = 2;
            } else if (preValue=="bike" || preValue=="motorbike" || preValue=="動物"){
                preValue = 1;
            } else preValue = 0;

            if (preValue != value) {
                switch(value) {
                    case 0 : controller.updateAttribute(window.cvat.player.frames.current, att_id, "\"-1,-1,-1,-1\""); break;
                    case 1 : controller.updateAttribute(window.cvat.player.frames.current, att_id, "\"0,-1,0.5,-1\""); break;
                    case 2 : controller.updateAttribute(window.cvat.player.frames.current, att_id, "\"0.1,-1,0.9,-1\""); break;
                }
            } else {
                // car to van , don't change detectpoints
                // if (detectpoints.includes("-1")){
                //     switch(value) {
                //         case 0 : controller.updateAttribute(window.cvat.player.frames.current, att_id, "\"-1,-1,-1,-1\""); break;
                //         case 1 : controller.updateAttribute(window.cvat.player.frames.current, att_id, "\"0,-1,0.5,-1\""); break;
                //         case 2 : controller.updateAttribute(window.cvat.player.frames.current, att_id, "\"0.1,-1,0.9,-1\""); break;
                //     }
                // }
            }
        }

        function rmDetectPointValue (attributes,controller) {
            for (let tmpId in attributes) {
                let tmpInfo = window.cvat.labelsInfo.attrInfo(tmpId);
                if(tmpInfo.name=="DetectPoints"){
                    controller.updateAttribute(window.cvat.player.frames.current, tmpId, "\"-1,-1,-1,-1\"");
                    let rm_point = "detectpoint_";
                    $("#"+rm_point.concat(controller._model._id,"_L")).remove();
                    $("#"+rm_point.concat(controller._model._id,"_R")).remove();
                    
                    let rm_dontcare = "dontcare_";
                    $("#"+rm_dontcare.concat(controller._model._id,"_L")).remove();
                    $("#"+rm_dontcare.concat(controller._model._id,"_R")).remove();

                    let rm_pointAim = "detectpointAim_";
                    $("#"+rm_pointAim.concat(controller._model._id,"_L")).remove();
                    $("#"+rm_pointAim.concat(controller._model._id,"_R")).remove();
                    break;
                }
            }
        }

        for (let attrId in this._uis.attributes) {
            let attrInfo = window.cvat.labelsInfo.attrInfo(attrId);
            switch (attrInfo.type) {
            case 'radio':
                for (let idx = 0; idx < this._uis.attributes[attrId].length; idx++) {
                    this._uis.attributes[attrId][idx].onchange = function(e) {
                        this._controller.updateAttribute(window.cvat.player.frames.current, attrId, e.target.value);
                    }.bind(this);
                }
                break;
            case 'checkbox':
                this._uis.attributes[attrId].onchange = function(e) {
                    this._controller.updateAttribute(window.cvat.player.frames.current, attrId, e.target.checked);
                    if(attrInfo.name == "Dont_Care") {
                        if(e.target.checked) {
                            rmDetectPointValue(this._uis.attributes,this._controller);
                            setHeadTailFix(this._uis.attributes,this._controller);
                        }
                        else {
                            setHeadTailRelease(this._uis.attributes,this._controller);
                            setDetectPointDefault(this._uis.attributes,this._controller,null);
                        }
                    }
                    if(attrInfo.name == "看不見車頭車尾") {
                        if(e.target.checked) {
                            setDetectPointToEdge(this._uis.attributes,this._controller);
                        }
                        else {
                            setDetectPointDefault(this._uis.attributes,this._controller,null);
                        }
                    }

                }.bind(this);
                break;
            case 'number':
                this._uis.attributes[attrId].onchange = function(e) {
                    let value = Math.clamp(+e.target.value, +e.target.min, +e.target.max);
                    e.target.value = value;
                    this._controller.updateAttribute(window.cvat.player.frames.current, attrId, value);
                }.bind(this);
                break;
            case 'multiselect':
                this._uis.attributes[attrId].onchange = function(e) {
                    console.log('in onchange multiselect');
                    let values = $(e.target).val();
                    if(PROJECT == 'apacorner') {
                        if($(e.target).val().includes('obstructed')) {
                            $(e.target).children()[1].removeAttribute('disabled');
                        }
                        else {
                            $(e.target).children()[1].setAttribute('disabled', true);
                            values = values.filter(function(value, index, arr){ return ['stopper','unarmed_lock'].includes(value); });
                            $(e.target).val(values);
                        }
                        $(e.target).selectpicker('refresh');
                    }
                    this._controller.updateAttribute(window.cvat.player.frames.current, attrId, values);
                }.bind(this);
                break;
            case 'singleselect':
                this._uis.attributes[attrId].onchange = function(e) {
                    console.log('in onchange singleselect');
                    let value = $(e.target).val();
                    this._controller.updateAttribute(window.cvat.player.frames.current, attrId, value);
                    value = value.toLowerCase();
                    this._controller.changeColor(mapColor_Corner(value));
                }.bind(this);
                break;
            default:
                this._uis.attributes[attrId].onchange = function(e) {
                    //add by jeff
                    let preValue = this._controller._model._attributes.mutable[window.cvat.player.frames.current][attrId].toLowerCase();
                    this._controller.updateAttribute(window.cvat.player.frames.current, attrId, e.target.value);
                    if(attrInfo.name == "Type") {
                        let value = e.target.value.toLowerCase();
                        setRotationRelease(this._uis.attributes,this._controller);
                        setHeadTailRelease(this._uis.attributes,this._controller);
                        setLightRelease(this._uis.attributes,this._controller);
                        setObstacleRelease(this._uis.attributes,this._controller);
                        
                        if(value.includes("car")){
                            this._controller.changeColor({shape: "#255f9d",ui: "#255f9d"});
                        }
                        else if(value.includes("van")){
                            this._controller.changeColor({shape: "#14ad78",ui: "#14ad78"});
                        }
                        else if(value.includes("motorbike")){
                            this._controller.changeColor({shape: "#a41ea4",ui: "#a41ea4"});
                        }
                        else if(value.includes("bike")){
                            this._controller.changeColor({shape: "#e77408",ui: "#e77408"});
                        }
                        else if(value.includes("truck")){
                            this._controller.changeColor({shape: "#209211",ui: "#209211"});
                        }
                        else if(value.includes("bus")){
                            this._controller.changeColor({shape: "#926511",ui: "#926511"});
                        }
                        else if(value.includes("代步車")){
                            this._controller.changeColor({shape: "#7f0fff",ui: "#7f0fff"});
                        }
                        else if(value.includes("工程車")){
                            this._controller.changeColor({shape: "#009ff5",ui: "#009ff5"});
                        }
                        else if(value.includes("無殼三輪車")){
                            this._controller.changeColor({shape: "#e713d5",ui: "#e713d5"});
                        }
                        else if(value.includes("有殼三輪車")){
                            this._controller.changeColor({shape: "#8ab427",ui: "#8ab427"});
                        }
                        else if(value.includes("無人機車群")){
                            this._controller.changeColor({shape: "#a0a800",ui: "#a0a800"});
                            setRotationFix(this._uis.attributes,this._controller);
                        }
                        else if(value.includes("無人腳踏車群")){
                            this._controller.changeColor({shape: "#00d676",ui: "#00d676"});
                            setRotationFix(this._uis.attributes,this._controller);
                        }
                        else if(value.includes("misc")){
                            this._controller.changeColor({shape: "#ff38ca",ui: "#ff38ca"});
                        }
                        else if(value.includes("background")){
                            this._controller.changeColor({shape: "#fbddac",ui: "#fbddac"});
                        }
                        else if(value.includes("tram")){
                            this._controller.changeColor({shape: "#c1fbac",ui: "#c1fbac"});
                        }
                        else if(value.includes("crowd")){
                            this._controller.changeColor({shape: "#f9c8c8",ui: "#f9c8c8"});
                            setRotationFix(this._uis.attributes,this._controller);
                        }
                        else if(["pedestrian_行人(直立)","personsitting_行人(非直立)"].includes(value)){
                            this._controller.changeColor({shape: "#a01313",ui: "#a01313"});
                            setRotationFix(this._uis.attributes,this._controller);
                        }
                        else if(value.includes("動物")){
                            this._controller.changeColor({shape: "#efe1b3",ui: "#efe1b3"});
                        }
                        else {
                            console.log("error but set default with car");
                            this._controller.changeColor({shape: "#255f9d",ui: "#255f9d"});
                        }

                        // add by jeff
                        if (value.includes("無人") || value.includes("人") || value.includes("background")) {
                            rmDetectPointValue(this._uis.attributes,this._controller);
                            setHeadTailFix(this._uis.attributes,this._controller);
                        }
                        else {
                            setDetectPointDefault(this._uis.attributes,this._controller,preValue);
                        }
                        
                        if(value.includes("動物") || value.includes("行人") || value.includes("群") || value.includes("background")) {
                            setLightFix(this._uis.attributes,this._controller);
                            setObstacleFix(this._uis.attributes,this._controller);
                        }
                    }
                }.bind(this);
            }
        }
    }


    _updateColorForDots() {
        let color = this._appearance.fill || this._appearance.colors.shape;
        let scaledStroke = SELECT_POINT_STROKE_WIDTH / window.cvat.player.geometry.scale;
        $('.svg_select_points').each(function() {
            this.instance.fill(color);
            this.instance.stroke('black');
            this.instance.attr('stroke-width', scaledStroke);
        });
        $(".svg_select_points[is_selected='true']").attr('stroke', 'violet');
    }


    // Inteface methods
    // Modify by Ericlou
    draw(interpolation, id = null) {
        let outside = interpolation.position.outside;

        if (!outside) {
            if (!this._controller.hiddenShape) {
                // Add by eric
                // draw carside once load UI.
                console.log("in draw");
                this._drawShapeUI(interpolation, id);
                // this._setupOccludedUI(interpolation.position.occluded);
                this._setupMergeView(this._controller.merge);
                if (!this._controller.hiddenText) {
                    // modify by Eric
                    // this._removeShapeText();
                    this._showShapeText();
                    // console.log("no show text");
                }
            }
        }

        this._drawMenu(outside);
        this._updateMenuContent(interpolation);
        this._activateMenu();
        this._setupLockedUI(this._controller.lock);
    }


    erase() {
        this._removeShapeUI();
        this._removeShapeText();
        this._removeMenu();
        this._uis.attributes = {};
        this._uis.buttons = {};
        this._uis.changelabel = null;
    }

    updateShapeTextPosition() {
        if (this._uis.shape && this._uis.shape.node.parentElement) {
            let scale = window.cvat.player.geometry.scale;
            if (this._appearance.whiteOpacity) {
                this._uis.shape.attr('stroke-width', 1 / scale);
            }
            else {
                this._uis.shape.attr('stroke-width', STROKE_WIDTH / scale);
            }

            let index = -1;
            let labels = window.cvat.labelsInfo.labels();
            let labelId = this._controller._model._label;
            let label_str = labels[labelId];
            for(let a_text of this._uis.text) {
                if (a_text && a_text.node.parentElement) {
                    index++;
                    let revscale = 1 / scale;
                    let shapeBBox = this._uis.shape.node.getBBox();
                    let textBBox = a_text.node.getBBox();
    
                    let x = 0;
                    let y = 0;
    
                    if (this._uis.shape.type=='polyline') {
                        if (PROJECT == 'dms_training') {
                            let offset = TEXT_MARGIN*revscale;
                            if ((label_str.includes("眼睛") && index==1) || (label_str.includes("嘴巴") && index==2)){
                                offset = -TEXT_MARGIN*revscale - textBBox.width * revscale;
                            }

                            x = this._uis.shape.node.points[index].x;
                            y = this._uis.shape.node.points[index].y + offset;
                            if (x + textBBox.width * revscale > window.cvat.player.geometry.frameWidth) {
                                // x = shapeBBox.x - TEXT_MARGIN - textBBox.width * revscale;
                                x = this._uis.shape.node.points[index].x - TEXT_MARGIN - textBBox.width * revscale;
                                if (x < 0) {
                                    x = this._uis.shape.node.points[index].x + TEXT_MARGIN;
                                }
                            }
                        }
                        else{
                            x = this._uis.shape.node.points[0].x + TEXT_MARGIN;
                            y = this._uis.shape.node.points[0].y;
                            if (x + textBBox.width * revscale > window.cvat.player.geometry.frameWidth) {
                                // x = shapeBBox.x - TEXT_MARGIN - textBBox.width * revscale;
                                x = this._uis.shape.node.points[0].x - TEXT_MARGIN - textBBox.width * revscale;
                                if (x < 0) {
                                    x = this._uis.shape.node.points[0].x + TEXT_MARGIN;
                                }
                            }
                        }
                    }
                    else {
                        x = shapeBBox.x + shapeBBox.width + TEXT_MARGIN;
                        y = shapeBBox.y;
    
                        if (x + textBBox.width * revscale > window.cvat.player.geometry.frameWidth) {
                            x = shapeBBox.x - TEXT_MARGIN - textBBox.width * revscale;
                            if (x < 0) {
                                x = shapeBBox.x + TEXT_MARGIN;
                            }
                        }
                    }
    
                    if (y + textBBox.height * revscale > window.cvat.player.geometry.frameHeight) {
                        y = Math.max(0, window.cvat.player.geometry.frameHeight - textBBox.height * revscale);
                    }
    
                    a_text.move(x / revscale, y / revscale);
                    a_text.attr('transform', `scale(${revscale})`);
    
                    for (let tspan of a_text.lines().members) {
                        tspan.attr('x', a_text.attr('x'));
                    }
                }
            }
        }
    }

    onShapeUpdate(model) {

        let interpolation = model.interpolate(window.cvat.player.frames.current);
        let hiddenText = model.hiddenText;
        let hiddenShape = model.hiddenShape;
        let activeAAM = model.activeAAM;

        this._makeNotEditable();
        this._deselect();
        if (hiddenText && !activeAAM.shape) {
            this._hideShapeText();
        }

        switch (model.updateReason) {
        case 'activation':
            if (!model.active) {
                ShapeCollectionView.sortByZOrder();
            }
            break;
        case 'attributes':
            this._updateMenuContent(interpolation);
            setupHidden.call(this, hiddenShape, hiddenText, activeAAM, model.active, interpolation, model._id);
            break;
        case 'merge':
            this._setupMergeView(model.merge);
            break;
        case 'groupping':
            this._setupGroupView(model.groupping);
            break;
        case 'lock': {
            let locked = model.lock;
            if (locked) {
                ShapeCollectionView.sortByZOrder();
            }
            this._setupLockedUI(locked);
            this._updateButtonsBlock(interpolation.position);
            break;
        }
        case 'occluded':
            this._setupOccludedUI(interpolation.position.occluded);
            this._updateButtonsBlock(interpolation.position);
            break;
        case 'hidden':
            setupHidden.call(this, hiddenShape, hiddenText, activeAAM, model.active, interpolation, model._id);
            this._updateButtonsBlock(interpolation.position);
            break;
        case 'remove':
            if (model.removed) {
                this.erase();
            }
            break;
        case 'position':
        case 'changelabel': {
            // add by jeff
            menuScroll = true;

            let idx = this._uis.menu.index();
            this._controller.model().unsubscribe(this);
            this.erase();

            this.draw(interpolation, model._id);
            this._controller.model().subscribe(this);
            this._uis.menu.detach();
            if (!idx) {
                this._uis.menu.prependTo(this._scenes.menus);
            }
            else {
                this._uis.menu.insertAfter(this._scenes.menus.find(`.uiElement:nth-child(${idx})`));
            }

            let colorByLabel = $('#colorByLabelRadio');
            if (colorByLabel.prop('checked')) {
                colorByLabel.trigger('change');
            }
            break;
        }
        case 'attributeFocus': {
            let attrId = model.activeAAM.attributeId;
            this._uis.attributes[attrId].focus();
            this._uis.attributes[attrId].select();
            break;
        }
        case 'activeAAM':
            this._setupAAMView(activeAAM.shape, interpolation.position);
            setupHidden.call(this, hiddenShape, hiddenText, activeAAM, model.active, interpolation);

            if (activeAAM.shape && this._uis.shape) {
                this._uis.shape.node.dispatchEvent(new Event('click'));
                this._highlightAttribute(activeAAM.attributeId);
            }
            else {
                this._highlightAttribute(null);
            }
            break;
        case 'color': {
            this._appearance.colors = model.color;
            this._applyColorSettings();
            this._updateColorForDots();
            break;
        }
        case 'z_order': {
            if (this._uis.shape) {
                this._uis.shape.attr('z_order', interpolation.position.z_order);
                ShapeCollectionView.sortByZOrder();
                return;
            }
            break;
        }
        case 'selection': {
            if (model.selected) {
                this._select();
            }
            else {
                this._deselect();
            }
            break;
        }
        case 'grouping': {
            this._drawShapeText();
            if(!model.active) {
                this._removeShapeText();
            }
            break;
        }
        }

        if (model.active || activeAAM.shape) {
            this._select();
            if (!activeAAM.shape) {
                this._makeEditable();
                let content = $('#frameContent');
                let shapes = $(content.find('.detectpointAim')).toArray();
                for (let shape of shapes) {
                    content.append(shape);
                }
                shapes = $(content.find('.detectpoint')).toArray();
                for (let shape of shapes) {
                    content.append(shape);
                }
            }
        }

        if (model.active || !hiddenText) {
            // modify by Eric
            // this._removeShapeText();
            this._showShapeText();
            // console.log("no show text");
        }

        function setupHidden(hiddenShape, hiddenText, activeAAM, active, interpolation, id) {
            this._makeNotEditable();
            this._removeShapeUI();
            this._removeShapeText();
            
            console.log("setuphidden");

            // modify by Eric

            let rm_dontcare = "dontcare_";
            $("#"+rm_dontcare.concat(id,"_L")).remove();
            $("#"+rm_dontcare.concat(id,"_R")).remove();

            let rm_point = "detectpoint_";
            $("#"+rm_point.concat(id,"_L")).remove();
            $("#"+rm_point.concat(id,"_R")).remove();

            let rm_pointAim = "detectpointAim_";
            $("#"+rm_pointAim.concat(id,"_L")).remove();
            $("#"+rm_pointAim.concat(id,"_R")).remove();

            console.log(hiddenShape, hiddenText, active)

            // if (!hiddenShape || !hiddenText || activeAAM.shape) {
            if (!hiddenShape || activeAAM.shape) {
                console.log("in set hidden");
                this._drawShapeUI(interpolation, id);
                // this._setupOccludedUI(interpolation.position.occluded);
                if (!hiddenText || active || activeAAM.shape) {
                    // modify by Eric
                    // this._removeShapeText();
                    this._showShapeText();
                    console.log("no show text");
                }

                if (model.active || activeAAM.shape) {
                    this._select();
                    if (!activeAAM.shape) {
                        this._makeEditable();
                        let content = $('#frameContent');
                        let shapes = $(content.find('.detectpointAim')).toArray();
                        for (let shape of shapes) {
                            content.append(shape);
                        }
                        shapes = $(content.find('.detectpoint')).toArray();
                        for (let shape of shapes) {
                            content.append(shape);
                        }
                    }
                    else {
                        this._highlightAttribute(activeAAM.attributeId);
                    }
                }
            }
        }
    }

    _applyColorSettings() {
        if (this._uis.shape) {
            if (!this._uis.shape.hasClass('selectedShape')) {
                if (this._appearance.whiteOpacity) {
                    this._uis.shape.attr({
                        'stroke-opacity': this._appearance.fillOpacity,
                        'stroke-width': 1 / window.cvat.player.geometry.scale,
                        'fill-opacity': this._appearance.fillOpacity,
                    });
                }
                else {
                    this._uis.shape.attr({
                        'stroke-opacity': 1,
                        'stroke-width': STROKE_WIDTH / window.cvat.player.geometry.scale,
                        'fill-opacity': this._appearance.fillOpacity,
                    });
                }
            }

            this._uis.shape.attr({
                'stroke': this._appearance.stroke || this._appearance.colors.shape,
                'fill': this._appearance.fill || this._appearance.colors.shape,
            });
        }

        if (this._uis.menu) {
            this._uis.menu.css({
                'background-color': this._appearance.fill ? this._appearance.fill : this._appearance.colors.ui,
            });
        }
    }


    updateColorSettings(settings) {
        if ('white-opacity' in settings) {
            this._appearance.whiteOpacity = true;
            this._appearance.fillOpacity = settings['white-opacity'];
            this._appearance.fill = '#ffffff';
            this._appearance.stroke = '#ffffff';
        } else {
            this._appearance.whiteOpacity = false;
            delete this._appearance.stroke;
            delete this._appearance.fill;

            if ('fill-opacity' in settings) {
                this._appearance.fillOpacity = settings['fill-opacity'];
            }

            if (settings['color-by-group']) {
                let color = settings['colors-by-group'](this._controller.model().groupId);
                this._appearance.stroke = color;
                this._appearance.fill = color;
            }
            else if (settings['color-by-label']) {
                let color = settings['colors-by-label'](window.cvat.labelsInfo.labelColorIdx(this._controller.label));
                this._appearance.stroke = color;
                this._appearance.fill = color;
            }
        }

        if ('selected-fill-opacity' in settings) {
            this._appearance.selectedFillOpacity = settings['selected-fill-opacity'];
        }

        if (settings['black-stroke']) {
            this._appearance['stroke'] = 'black';
        }
        else if (!(settings['color-by-group'] || settings['color-by-label'] || settings['white-opacity'])) {
            delete this._appearance['stroke'];
        }

        this._applyColorSettings();
        if (this._flags.editable) {
            this._updateColorForDots();
        }
    }


    // Used by shapeCollectionView for select management
    get dragging() {
        return this._flags.dragging;
    }

    // Used by shapeCollectionView for resize management
    get resize() {
        return this._flags.resizing;
    }

    // Used in shapeGrouper in order to get model via controller and set group id
    controller() {
        return this._controller;
    }
}

ShapeView.shortkeys = function() {
    if (!ShapeView._shortkeys) {
        ShapeView._shortkeys = window.cvat.config.shortkeys;
    }
    return ShapeView._shortkeys;
};

ShapeView.labels = function() {
    if (!ShapeView._labels) {
        ShapeView._labels = window.cvat.labelsInfo.labels();
    }
    return ShapeView._labels;
};


class BoxView extends ShapeView {
    constructor(boxModel, boxController, svgScene, menusScene, menusObj) {
        super(boxModel, boxController, svgScene, menusScene, menusObj);
    }

    _makeEditable() {
        if (this._uis.shape && this._uis.shape.node.parentElement && !this._flags.editable) {
            if (!this._controller.lock) {
                let sizeObject = null;
                this._uis.shape.on('resizestart', (e) => {
                    sizeObject = drawBoxSize(this._scenes.svg, e.target);
                }).on('resizing', (e) => {
                    sizeObject = drawBoxSize.call(sizeObject, this._scenes.svg, e.target);
                }).on('resizedone', () => {
                    sizeObject.rm();
                });
            }
            ShapeView.prototype._makeEditable.call(this);
        }
    }


    _buildPosition() {
        let shape = this._uis.shape.node;
        return {
            xtl: +shape.getAttribute('x'),
            ytl: +shape.getAttribute('y'),
            xbr: +shape.getAttribute('x') + +shape.getAttribute('width'),
            ybr: +shape.getAttribute('y') + +shape.getAttribute('height'),
            occluded: this._uis.shape.hasClass('occludedShape'),
            outside: false,    // if drag or resize possible, track is not outside
            z_order: +shape.getAttribute('z_order'),
        };
    }

    // modify by eric.
    // draw carside once load UI.

    _drawShapeUI(interpolation, id_) {

        var position = interpolation.position;
        var attributes = interpolation.attributes;
        let xtl = position.xtl;
        let ytl = position.ytl;
        let xbr = position.xbr;
        let ybr = position.ybr;
        let width = position.xbr - position.xtl;
        let height = position.ybr - position.ytl;

        let dont_care_value = null;
        let type_value = '';
        let Occlude_value = ''

        for (let attrId in attributes) {
            var get_name = String(attributes[attrId]['name']) ;
            if (get_name === "DetectPoints"){
                var dectectpoin_value = attributes[attrId]['value'];
            }
            if (get_name === "Dont_Care"){
                dont_care_value = attributes[attrId]['value'];
            }
            if (get_name === "Type"){
                type_value = attributes[attrId]['value'];
            }
            if (get_name === "Occluded"){
                Occlude_value = attributes[attrId]['value'];
            }
        }

        let DONT_CARE = "dontcare";
        $("#"+DONT_CARE + "_" + id_ + "_L").remove();
        $("#"+DONT_CARE + "_" + id_ + "_R").remove();

        let value = type_value.toLowerCase();
        let dont_care_color = "";
        if(value.includes("car")){
            dont_care_color = "#255f9d";
        }
        else if(value.includes("van")){
            dont_care_color = "#14ad78";
        }
        else if(value.includes("motorbike")){
            dont_care_color = "#a41ea4";
        }
        else if(value.includes("bike")){
            dont_care_color = "#e77408";
        }
        else if(value.includes("truck")){
            dont_care_color = "#209211";
        }
        else if(value.includes("bus")){
            dont_care_color = "#926511";
        }
        else if(value.includes("代步車")){
            dont_care_color = "#7f0fff";
        }
        else if(value.includes("工程車")){
            dont_care_color = "#009ff5";
        }
        else if(value.includes("無殼三輪車")){
            dont_care_color = "#e713d5";
        }
        else if(value.includes("有殼三輪車")){
            dont_care_color = "#8ab427";
        }
        else if(value.includes("無人機車群")){
            dont_care_color = "#a0a800";
        }
        else if(value.includes("無人腳踏車群")){
            dont_care_color = "#00d676";
        }
        else if(value.includes("misc")){
            dont_care_color = "#ff38ca";
        }
        else if(value.includes("background")){
            dont_care_color = "#fbddac";
        }
        else if(value.includes("tram")){
            dont_care_color = "#c1fbac";
        }
        else if(value.includes("crowd")){
            dont_care_color = "#f9c8c8";
        }
        else if(["pedestrian_行人(直立)","personsitting_行人(非直立)"].includes(value)){
            dont_care_color = "#a01313";
        }
        else if(value.includes("動物")){
            dont_care_color = "#efe1b3";
        }
        else {
            console.log("error but set default with car");
            dont_care_color = "#255f9d";
        }

        if (dont_care_value) {
            // dont care line 
            this._uis.shape = this._scenes.svg.line(xtl,ytl,xbr,ybr).attr(
                {
                    'stroke-width': STROKE_WIDTH / 2 / window.cvat.player.geometry.scale ,'stroke': dont_care_color,
                    'id': DONT_CARE + "_" + id_ + "_L"
                }
            ).addClass(DONT_CARE);
    
            this._uis.shape = this._scenes.svg.line(xbr,ytl,xtl,ybr).attr(
                {
                    'stroke-width': STROKE_WIDTH / 2 / window.cvat.player.geometry.scale ,'stroke': dont_care_color,
                    'id': DONT_CARE + "_" + id_ + "_R"
                }
            ).addClass(DONT_CARE);        
        } else {
            let rm_point = "detectpoint_";
            $("#"+rm_point.concat(id_,"_L")).remove();
            $("#"+rm_point.concat(id_,"_R")).remove();
    
            let rm_pointAim = "detectpointAim_";
            $("#"+rm_pointAim.concat(id_,"_L")).remove();
            $("#"+rm_pointAim.concat(id_,"_R")).remove();
        }

        this._uis.shape = this._scenes.svg.rect().size(width, height).attr({
            'fill': this._appearance.fill || this._appearance.colors.shape,
            'stroke': this._appearance.stroke || this._appearance.colors.shape,
            'stroke-width': STROKE_WIDTH /  window.cvat.player.geometry.scale,
            'z_order': position.z_order,
            'fill-opacity': this._appearance.fillOpacity
        }).move(xtl, ytl).addClass('shape');

        if (Occlude_value === "Largely_Occluded"){
            this._uis.shape.node.classList.add('occludedShape'); 
        } else {
            this._uis.shape.node.classList.remove('occludedShape');
        }

        ShapeView.prototype._drawShapeUI.call(this);
        // console.log("_drawShapeUI(interpolation, id_)");
        setDetectPoint(this._controller._model);
    }

    _setupAAMView(active, pos) {
        let oldRect = $('#outsideRect');
        let oldMask = $('#outsideMask');

        if (active) {
            if (oldRect.length) {
                oldRect.remove();
                oldMask.remove();
            }

            let size = {
                x: 0,
                y: 0,
                width: window.cvat.player.geometry.frameWidth,
                height: window.cvat.player.geometry.frameHeight
            };

            let excludeField = this._scenes.svg.rect(size.width, size.height).move(size.x, size.y).fill('#666');
            let includeField = this._scenes.svg.rect(pos.xbr - pos.xtl, pos.ybr - pos.ytl).move(pos.xtl, pos.ytl);
            this._scenes.svg.mask().add(excludeField).add(includeField).fill('black').attr('id', 'outsideMask');
            this._scenes.svg.rect(size.width, size.height).move(size.x, size.y).attr({
                mask: 'url(#outsideMask)',
                id: 'outsideRect'
            });
        }
        else {
            oldRect.remove();
            oldMask.remove();
        }
    }
}


class PolyShapeView extends ShapeView {
    constructor(polyShapeModel, polyShapeController, svgScene, menusScene, menusObj) {
        super(polyShapeModel, polyShapeController, svgScene, menusScene, menusObj);
    }


    _buildPosition() {
        return {
            points: this._uis.shape.node.getAttribute('points'),
            occluded: this._uis.shape.hasClass('occludedShape'),
            outside: false,
            z_order: +this._uis.shape.node.getAttribute('z_order'),
        };
    }


    _setupAAMView(active, pos) {
        let oldRect = $('#outsideRect');
        let oldMask = $('#outsideMask');

        if (active) {
            if (oldRect.length) {
                oldRect.remove();
                oldMask.remove();
            }

            let size = {
                x: 0,
                y: 0,
                width: window.cvat.player.geometry.frameWidth,
                height: window.cvat.player.geometry.frameHeight
            };

            let excludeField = this._scenes.svg.rect(size.width, size.height).move(size.x, size.y).fill('#666');
            let includeField = this._scenes.svg.polygon(pos.points);
            this._scenes.svg.mask().add(excludeField).add(includeField).fill('black').attr('id', 'outsideMask');
            this._scenes.svg.rect(size.width, size.height).move(size.x, size.y).attr({
                mask: 'url(#outsideMask)',
                id: 'outsideRect'
            });
        }
        else {
            oldRect.remove();
            oldMask.remove();
        }
    }


    _makeEditable() {
        ShapeView.prototype._makeEditable.call(this);
        if (this._flags.editable) {
            for (let point of $('.svg_select_points')) {
                point = $(point);

                point.on('contextmenu.contextMenu', (e) => {
                    this._shapeContextMenu.hide(100);
                    this._pointContextMenu.attr('point_idx', point.index());
                    this._pointContextMenu.attr('dom_point_id', point.attr('id'));

                    if(!passNoShow){
                        this._pointContextMenu.finish().show(100).offset({
                            top: e.pageY - 20,
                            left: e.pageX - 20,
                        });
                    }
                    else passNoShow = false;
                    

                    e.preventDefault();
                });

                point.on('dblclick.polyshapeEditor', (e) => {
                    if (e.shiftKey) {
                        if (!window.cvat.mode) {
                            // Get index before detach shape from DOM
                            let index = point.index();

                            // Make non active view and detach shape from DOM
                            this._makeNotEditable();
                            this._deselect();
                            if (this._controller.hiddenText) {
                                this._hideShapeText();
                            }
                            this._uis.shape.addClass('hidden');
                            if (this._uis.points) {
                                this._uis.points.addClass('hidden');
                            }

                            // Run edit mode
                            PolyShapeView.editor.edit(this._controller.type.split('_')[1],
                                this._uis.shape.attr('points'), this._color, index, e,
                                (points) => {
                                    this._uis.shape.removeClass('hidden');
                                    if (this._uis.points) {
                                        this._uis.points.removeClass('hidden');
                                    }
                                    if (points) {
                                        this._uis.shape.attr('points', points);
                                        this._controller.updatePosition(window.cvat.player.frames.current, this._buildPosition());
                                    }
                                }
                            );
                        }
                    }
                    else {
                        this._controller.model().removePoint(point.index());
                    }
                    e.stopPropagation();
                });
            }
        }
    }


    _makeNotEditable() {
        for (let point of $('.svg_select_points')) {
            $(point).off('contextmenu.contextMenu');
            $(point).off('dblclick.polyshapeEditor');
        }
        ShapeView.prototype._makeNotEditable.call(this);
    }
}


class PolygonView extends PolyShapeView {
    constructor(polygonModel, polygonController, svgContent, UIContent, menusObj) {
        super(polygonModel, polygonController, svgContent, UIContent, menusObj);
    }
    _drawShapeUI(interpolation, id_) {
        this._uis.shape = this._scenes.svg.polygon(interpolation.position.points).fill(this._appearance.colors.shape).attr({
            'fill': this._appearance.fill || this._appearance.colors.shape,
            'stroke': this._appearance.stroke || this._appearance.colors.shape,
            'stroke-width': STROKE_WIDTH / window.cvat.player.geometry.scale,
            'z_order': interpolation.position.z_order,
            'fill-opacity': this._appearance.fillOpacity
        }).addClass('shape');

        ShapeView.prototype._drawShapeUI.call(this);
    }

    _makeEditable() {
        PolyShapeView.prototype._makeEditable.call(this);
        if (this._flags.editable && !this._controller.draggable) {
            this._uis.shape.draggable(false);
            this._uis.shape.style('cursor', 'default');
        }
    }

    onShapeUpdate(model) {


        ShapeView.prototype.onShapeUpdate.call(this, model);
        if (model.updateReason === 'draggable' && this._flags.editable) {
            if (model.draggable) {
                this._uis.shape.draggable();
            }
            else {
                this._uis.shape.draggable(false);
            }
        }
    }
}


class PolylineView extends PolyShapeView {
    constructor(polylineModel, polylineController, svgScene, menusScene, menusObj) {
        super(polylineModel, polylineController, svgScene, menusScene, menusObj);
    }
    _drawShapeUI(interpolation, id_) {
        this._uis.shape = this._scenes.svg.polyline(interpolation.position.points).fill(this._appearance.colors.shape).attr({
            'stroke': this._appearance.stroke || this._appearance.colors.shape,
            'stroke-width': STROKE_WIDTH / window.cvat.player.geometry.scale,
            'z_order': interpolation.position.z_order,
        }).addClass('shape polyline');

        ShapeView.prototype._drawShapeUI.call(this);
    }

    _setupMergeView(merge) {
        if (this._uis.shape) {
            if (merge) {
                this._uis.shape.addClass('mergeLine');
            }
            else {
                this._uis.shape.removeClass('mergeLine');
            }
        }
    }


    _setupGroupView(group) {
        if (this._uis.shape) {
            if (group) {
                this._uis.shape.addClass('groupLine');
            }
            else {
                this._uis.shape.removeClass('groupLine');
            }
        }
    }


    _deselect() {
        ShapeView.prototype._deselect.call(this);

        if (this._appearance.whiteOpacity) {
            if (this._uis.shape) {
                this._uis.shape.attr({
                    'visibility': 'hidden'
                });
            }
        }
    }

    _applyColorSettings() {
        ShapeView.prototype._applyColorSettings.call(this);
        if (this._appearance.whiteOpacity) {
            if (this._uis.shape) {
                this._uis.shape.attr({
                    'visibility': 'hidden'
                });
            }
        }
        else {
            if (this._uis.shape) {
                this._uis.shape.attr({
                    'visibility': 'visible'
                });
            }
        }
    }
}


class PointsView extends PolyShapeView {
    constructor(pointsModel, pointsController, svgScene, menusScene, menusObj) {
        super(pointsModel, pointsController, svgScene, menusScene, menusObj);
        this._uis.points = null;
    }


    _setupMergeView(merge) {
        if (this._uis.points) {
            if (merge) {
                this._uis.points.addClass('mergePoints');
            }
            else {
                this._uis.points.removeClass('mergePoints');
            }
        }
    }


    _setupGroupView(group) {
        if (this._uis.points) {
            if (group) {
                this._uis.points.addClass('groupPoints');
            }
            else {
                this._uis.points.removeClass('groupPoints');
            }
        }
    }


    _drawPointMarkers(position) {
        if (this._uis.points) {
            return;
        }

        this._uis.points = this._scenes.svg.group().fill(this._appearance.fill || this._appearance.colors.shape)
            .on('click', () => {
                this._positionateMenus();
                this._controller.click();
            }).attr({
                'z_order': position.z_order
            }).addClass('pointTempGroup');

        let points = PolyShapeModel.convertStringToNumberArray(position.points);
        for (let point of points) {
            let radius = POINT_RADIUS * 2 / window.cvat.player.geometry.scale;
            let scaledStroke = STROKE_WIDTH / window.cvat.player.geometry.scale;
            this._uis.points.circle(radius).move(point.x - radius / 2, point.y - radius / 2)
                .fill('inherit').stroke('black').attr('stroke-width', scaledStroke).addClass('tempMarker');
        }
    }


    _removePointMarkers() {
        if (this._uis.points) {
            this._uis.points.off('click');
            this._uis.points.remove();
            this._uis.points = null;
        }
    }


    _makeEditable() {
        PolyShapeView.prototype._makeEditable.call(this);
        if (!this._controller.lock) {
            $('.svg_select_points').on('click', () => this._positionateMenus());
            this._removePointMarkers();
        }
    }


    _makeNotEditable() {
        PolyShapeView.prototype._makeNotEditable.call(this);
        if (!this._controller.hiddenShape) {
            let interpolation = this._controller.interpolate(window.cvat.player.frames.current);
            if (interpolation.position.points) {
                this._drawPointMarkers(interpolation.position);
            }
        }
    }


    _drawShapeUI(interpolation, id_) {
        this._uis.shape = this._scenes.svg.polyline(interpolation.position.points).addClass('shape points').attr({
            'z_order': interpolation.position.z_order,
        });
        this._drawPointMarkers(interpolation.position);
        ShapeView.prototype._drawShapeUI.call(this);
    }


    _removeShapeUI() {
        ShapeView.prototype._removeShapeUI.call(this);
        this._removePointMarkers();
    }


    _deselect() {
        ShapeView.prototype._deselect.call(this);

        if (this._appearance.whiteOpacity) {
            if (this._uis.points) {
                this._uis.points.attr({
                    'visibility': 'hidden'
                });
            }

            if (this._uis.shape) {
                this._uis.shape.attr({
                    'visibility': 'hidden'
                });
            }
        }
    }

    _applyColorSettings() {
        ShapeView.prototype._applyColorSettings.call(this);

        if (this._appearance.whiteOpacity) {
            if (this._uis.points) {
                this._uis.points.attr({
                    'visibility': 'hidden'
                });
            }

            if (this._uis.shape) {
                this._uis.shape.attr({
                    'visibility': 'hidden'
                });
            }
        }
        else {
            if (this._uis.points) {
                this._uis.points.attr({
                    'visibility': 'visible',
                    'fill': this._appearance.fill || this._appearance.colors.shape,
                });
            }

            if (this._uis.shape) {
                this._uis.shape.attr({
                    'visibility': 'visible',
                });
            }
        }
    }
}



function buildShapeModel(data, type, idx, color) {
    switch (type) {
    case 'interpolation_box':
    case 'annotation_box':
        return new BoxModel(data, type, idx, color);
    case 'interpolation_points':
    case 'annotation_points':
        return new PointsModel(data, type, idx, color);
    case 'interpolation_polyline':
    case 'annotation_polyline':
        return new PolylineModel(data, type, idx, color);
    case 'interpolation_polygon':
    case 'annotation_polygon':
        return new PolygonModel(data, type, idx, color);
    }
    throw Error('Unreacheable code was reached.');
}


function buildShapeController(shapeModel) {
    switch (shapeModel.type) {
    case 'interpolation_box':
    case 'annotation_box':
        return new BoxController(shapeModel);
    case 'interpolation_points':
    case 'annotation_points':
        return new PointsController(shapeModel);
    case 'interpolation_polyline':
    case 'annotation_polyline':
        return new PolylineController(shapeModel);
    case 'interpolation_polygon':
    case 'annotation_polygon':
        return new PolygonController(shapeModel);
    }
    throw Error('Unreacheable code was reached.');
}


function buildShapeView(shapeModel, shapeController, svgContent, UIContent, menusObj) {
    switch (shapeModel.type) {
    case 'interpolation_box':
    case 'annotation_box':
        return new BoxView(shapeModel, shapeController, svgContent, UIContent, menusObj);
    case 'interpolation_points':
    case 'annotation_points':
        return new PointsView(shapeModel, shapeController, svgContent, UIContent, menusObj);
    case 'interpolation_polyline':
    case 'annotation_polyline':
        return new PolylineView(shapeModel, shapeController, svgContent, UIContent, menusObj);
    case 'interpolation_polygon':
    case 'annotation_polygon':
        return new PolygonView(shapeModel, shapeController, svgContent, UIContent, menusObj);
    }
    throw Error('Unreacheable code was reached.');
}
