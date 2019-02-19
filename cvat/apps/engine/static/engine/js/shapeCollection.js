/*
 * Copyright (C) 2018 Intel Corporation
 *
 * SPDX-License-Identifier: MIT
 */

/* exported ShapeCollectionModel ShapeCollectionController ShapeCollectionView */
"use strict";

var mousedownAtDetectPoint = false;
var is_one_frame_mode = false;
var one_frame_data = null;
var mousedown_in_shape = false;
var move_background = false;

var passNoShow = false;
class ShapeCollectionModel extends Listener {
    constructor() {
        super('onCollectionUpdate', () => this);
        this._annotationShapes = {};
        this._groups = {};
        this._interpolationShapes = [];
        this._shapes = [];
        this._showAllInterpolation = false;
        this._hash = null;
        this._currentShapes = [];
        this._idx = 0;
        this._groupIdx = 0;
        this._frame = null;
        this._activeShape = null;
        this._activeShape_before_Create = null;
        this._idx_before_Create = null;
        this._activeAAMShape = null;
        this._lastPos = {
            x: 0,
            y: 0,
        };
        this._z_order =  {
            max: 0,
            min: 0,
        };
        this._colors = [
            "#0066FF", "#AF593E", "#01A368", "#FF861F", "#ED0A3F", "#FF3F34", "#76D7EA",
            "#8359A3", "#FBE870", "#C5E17A", "#03BB85", "#FFDF00", "#8B8680", "#0A6B0D",
            "#8FD8D8", "#A36F40", "#F653A6", "#CA3435", "#FFCBA4", "#FF99CC", "#FA9D5A",
            "#FFAE42", "#A78B00", "#788193", "#514E49", "#1164B4", "#F4FA9F", "#FED8B1",
            "#C32148", "#01796F", "#E90067", "#FF91A4", "#404E5A", "#6CDAE7", "#FFC1CC",
            "#006A93", "#867200", "#E2B631", "#6EEB6E", "#FFC800", "#CC99BA", "#FF007C",
            "#BC6CAC", "#DCCCD7", "#EBE1C2", "#A6AAAE", "#B99685", "#0086A7", "#5E4330",
            "#C8A2C8", "#708EB3", "#BC8777", "#B2592D", "#497E48", "#6A2963", "#E6335F",
            "#00755E", "#B5A895", "#0048ba", "#EED9C4", "#C88A65", "#FF6E4A", "#87421F",
            "#B2BEB5", "#926F5B", "#00B9FB", "#6456B7", "#DB5079", "#C62D42", "#FA9C44",
            "#DA8A67", "#FD7C6E", "#93CCEA", "#FCF686", "#503E32", "#FF5470", "#9DE093",
            "#FF7A00", "#4F69C6", "#A50B5E", "#F0E68C", "#FDFF00", "#F091A9", "#FFFF66",
            "#6F9940", "#FC74FD", "#652DC1", "#D6AEDD", "#EE34D2", "#BB3385", "#6B3FA0",
            "#33CC99", "#FFDB00", "#87FF2A", "#6EEB6E", "#FFC800", "#CC99BA", "#7A89B8",
            "#006A93", "#867200", "#E2B631", "#D9D6CF"
        ];

        this._colorIdx = 0;
        this._filter = new FilterModel(() => this.update());
        this._splitter = new ShapeSplitter();

        //add by jeff
        this._preShape = null;
        this._currentGroupID = 0;
        this._currentGroupOrder = 0;
        this._groupMap = {};

        this._isImported = false;

    }

    _cleanCurrentGroup() {
        this._preShape = null;
        this._currentGroupID = 0;
        this._currentGroupOrder = 0;
    }

    _nextIdx() {
        return this._idx++;
    }

    _nextGroupIdx() {
        return ++this._groupIdx;
    }

    nextColor() {
        // Step used for more color variability
        let idx = ++this._colorIdx % this._colors.length;
        let color = this._colors[idx];

        return {
            shape: color,
            ui: color,
        };
    }

    _computeInterpolation(frame) {
        let interpolated = [];
        for (let shape of (this._annotationShapes[frame] || []).concat(this._interpolationShapes) ) {
            if (!shape.removed) {
                let interpolation = shape.interpolate(frame);
                if (!interpolation.position.outside || shape.isKeyFrame(frame) ||
                    (shape.type.split('_')[0] === 'interpolation' && this._showAllInterpolation)) {
                    interpolated.push({
                        model: shape,
                        interpolation: shape.interpolate(frame),
                    });
                }
            }
        }

        return interpolated;
    }

    _clear() {
        this._z_order.max = 0;
        this._z_order.min = 0;

        if (this._activeShape) {
            this._activeShape.active = false;
        }

        if (this._activeAAMShape) {
            this._activeAAMShape.activeAAM = {
                shape: false,
                attribute: null
            };
        }

        this._currentShapes = [];
    }

    _interpolate() {
        this._clear();
        this._currentShapes = this._computeInterpolation(this._frame);
        for (let shape of this._currentShapes) {
            let z_order = shape.interpolation.position.z_order;
            if (z_order > this._z_order.max) {
                this._z_order.max = z_order;
            }
            if (z_order < this._z_order.min) {
                this._z_order.min = z_order;
            }
        }

        this._currentShapes = this._filter.filter(this._currentShapes);
        this.notify();
    }

    _removeFromGroup(elem) {
        let groupId = elem.groupId;

        // Check if elem in group
        if (groupId) {
            if (groupId in this._groups) {
                // Remove from group
                let idx = this._groups[groupId].indexOf(elem);
                if (idx != -1) {
                    this._groups[groupId].splice(idx, 1);
                }

                // Now remove group if it empty
                if (!this._groups[groupId].length) {
                    delete this._groups[groupId];
                }
            }
            elem.groupId = 0;
        }
    }

    // Common code for switchActiveOccluded(), switchActiveKeyframe(), switchActiveLock() and switchActiveOutside()
    _selectActive() {
        let shape = null;
        if (this._activeAAMShape) {
            shape = this._activeAAMShape;
        }
        else {
            this.selectShape(this._lastPos, false);
            if (this._activeShape) {
                shape = this._activeShape;
            }
        }

        return shape;
    }

    colorsByGroup(groupId) {
        // If group id of shape is 0 (default value), then shape not contained in a group
        if (!groupId) {
            return '#ffffff';
        }

        return this._colors[groupId % this._colors.length];
    }

    joinToGroup(elements) {
        let groupIdx = this._nextGroupIdx();
        this._groups[groupIdx] = [];

        for (let elem of elements) {
            // Clear old group
            this._removeFromGroup(elem);
            this._groups[groupIdx].push(elem);
            elem.groupId = groupIdx;
        }
    }

    resetGroupFor(elements) {
        for (let elem of elements) {
            this._removeFromGroup(elem);
        }
    }

    updateGroupIdx(groupId) {
        if (groupId in this._groups) {
            let newGroupId = this._nextGroupIdx();
            this._groups[newGroupId] = this._groups[groupId];
            delete this._groups[groupId];
            for (let elem of this._groups[newGroupId]) {
                elem.groupId = newGroupId;
            }
        }
    }

    import(data) {
        for (let box of data.boxes) {
            this.add(box, 'annotation_box');
        }

        for (let box_path of data.box_paths) {
            this.add(box_path, 'interpolation_box');
        }

        for (let points of data.points) {
            this.add(points, 'annotation_points');
        }

        for (let points_path of data.points_paths) {
            this.add(points_path, 'interpolation_points');
        }

        for (let polygon of data.polygons) {
            this.add(polygon, 'annotation_polygon');
        }

        for (let polygon_path of data.polygon_paths) {
            this.add(polygon_path, 'interpolation_polygon');
        }

        for (let polyline of data.polylines) {
            this.add(polyline, 'annotation_polyline');
        }

        for (let polyline_path of data.polyline_paths) {
            this.add(polyline_path, 'interpolation_polyline');
        }
        //add by jeff
        this._isImported = true;
        this._preShape = null;

        this.notify();
        return this;
    }


    export() {
        let response = {
            "boxes": [],
            "box_paths": [],
            "points": [],
            "points_paths": [],
            "polygons": [],
            "polygon_paths": [],
            "polylines": [],
            "polyline_paths": [],
        };

        for (let shape of this._shapes) {
            if (shape.removed || shape._frame!=this._frame) continue;
            
            switch (shape.type) {
            case 'annotation_box':
                response.boxes.push(shape.export());
                break;
            case 'interpolation_box':
                response.box_paths.push(shape.export());
                break;
            case 'annotation_points':
                response.points.push(shape.export());
                break;
            case 'interpolation_points':
                response.points_paths.push(shape.export());
                break;
            case 'annotation_polygon':
                response.polygons.push(shape.export());
                break;
            case 'interpolation_polygon':
                response.polygon_paths.push(shape.export());
                break;
            case 'annotation_polyline':
                response.polylines.push(shape.export());
                break;
            case 'interpolation_polyline':
                response.polyline_paths.push(shape.export());
            }
        }

        return JSON.stringify(response);
    }

    find(direction) {
        let max = $('#select_keyframes > option').length-1;
        if (!max && !direction) return null;

        let index = $('#select_keyframes').prop('selectedIndex');

        if (Math.sign(direction) > 0) {
            if(index >= max) index = 0;
            $('#select_keyframes option').eq(index+1).prop('selected', true);
        }
        else {
            if(index <= 1) index = max+1;
            $('#select_keyframes option').eq(index-1).prop('selected', true);
        }
        return $('#select_keyframes').prop('value');
    }

    zOrder(frame) {
        if (frame === this._frame) {
            this._z_order.max ++;
            this._z_order.min --;
            return {
                max: this._z_order.max,
                min: this._z_order.min,
            };
        }
        else {
            let interpolation = this._computeInterpolation(frame);
            let max = 0;
            let min = 0;
            for (let shape of interpolation) {
                let z_order = shape.interpolation.position.z_order;
                if (z_order > max) {
                    max = z_order;
                }
                if (z_order < min) {
                    min = z_order;
                }
            }
            return {
                max: max + 1,
                min: min - 1,
            };
        }
    }

    hasUnsavedChanges() {
        return md5(this.export()) !== this._hash;
    }

    updateHash() {
        this._hash = md5(this.export());
        return this;
    }

    empty() {
        this._annotationShapes = {};
        this._interpolationShapes = [];
        this._shapes = [];
        this._idx = 0;
        this._colorIdx = 0;
        this._interpolate();
    }

    add(data, type) {
        menuScroll = true;
        let default_color = {shape: "#ffffff",ui: "#ffffff"};

        if(PROJECT=='apacorner'){
            default_color = {shape: "#0b8043",ui: "#0b8043"};
        }
        else {
            default_color = {shape: "#255f9d",ui: "#255f9d"};
        }

        let model = buildShapeModel(data, type, this._nextIdx(), default_color); // default car color
        //let model = buildShapeModel(data, type, this._nextIdx(), this.nextColor());
        if (type.startsWith('interpolation')) {
            this._interpolationShapes.push(model);
        }
        else {
            this._annotationShapes[model.frame] = this._annotationShapes[model.frame] || [];
            this._annotationShapes[model.frame].push(model);
        }
        this._shapes.push(model);
        model.subscribe(this);

        // Update collection groups & group index
        let groupIdx = model.groupId;
        this._groupIdx = Math.max(this._groupIdx, groupIdx);
        if (groupIdx) {
            this._groups[groupIdx] = this._groups[groupIdx] || [];
            this._groups[groupIdx].push(model);
        }

        this._groupMap[model.frame] = this._groupMap[model.frame] || {};

        for (let [index, id] of model._groupingID.entries()){
            if (!this._groupMap[model.frame].hasOwnProperty(id)) {
                this._groupMap[model.frame][id] = [];
            }
            if(this._groupMap[model.frame][id].indexOf(model._groupingOrder[index]) == -1) {
                this._groupMap[model.frame][id].push(model._groupingOrder[index]);
            }
        }

        // add by jeff
        if(this._isImported && this._currentGroupID > 0) {
            // find preshape then add group
            // currentshape add group
            if(this._groupMap[model.frame].hasOwnProperty(this._currentGroupID) && this._groupMap[model.frame][this._currentGroupID].length > 0) {
                this._currentGroupOrder = Math.max.apply(null, this._groupMap[model.frame][this._currentGroupID]) + 1
            }
            else{
                this._currentGroupOrder = 1;
            }

            if (PROJECT=='apacorner') {
                this.addGrouping(0,this._preShape, this._currentGroupID, this._currentGroupOrder);
            }
            this.addGrouping(1,model, this._currentGroupID, this._currentGroupOrder);
            this._preShape = model;

            if (PROJECT=='apacorner' && this._groupMap[model.frame].hasOwnProperty(this._currentGroupID) && this._groupMap[model.frame][this._currentGroupID].length>=2) {
                this._currentGroupID += 1;
                this._currentGroupOrder = 1;
                if(!(this._groupMap[model.frame][this._currentGroupID] === undefined) && this._groupMap[model.frame][this._currentGroupID].length >= 2){
                    this._currentGroupID = 0;
                    this._currentGroupOrder = 0;
                    $('#group_current_label').text("無");
                }
                else
                {
                    $('#group_current_label').text((this._currentGroupID).toString());
                }
            }
        }
    }

    addGrouping(flag,model, currentGroupID, currentGroupOrder) {
        if(model==null){return;}
        
        if (PROJECT=='apacorner'){
            if(!(this._groupMap[model.frame][this._currentGroupID] === undefined) && this._groupMap[model.frame][this._currentGroupID].length >= 2){
                flag = 0;
                this._currentGroupID = 0;
                this._currentGroupOrder = 0;
                $('#group_current_label').text("無");
            }
        }
        else{
            flag=1;
        }
        
        if (this._currentGroupID != null && this._currentGroupID > 0){
            if (!this._groupMap[model.frame].hasOwnProperty(this._currentGroupID))
                {this._groupMap[model.frame][this._currentGroupID] = [];flag=1;}

            if(flag&&this._groupMap[model.frame][this._currentGroupID].indexOf(this._currentGroupOrder) == -1) 
            {
                this._groupMap[model.frame][this._currentGroupID].push(this._currentGroupOrder);
                
                model._groupingID.push( currentGroupID);
                model._groupingOrder.push( currentGroupOrder);
                this._currentGroupOrder += 1;
                model._updateReason = 'grouping';
                model.notify();
            }
        }
    }

    selectShape(pos, noActivation) {
        let closedShape = {
            minDistance: Number.MAX_SAFE_INTEGER,
            shape: null,
        };

        let openShape = {
            minDistance: 5 / window.cvat.player.geometry.scale,
            shape: null,
        };

        for (let shape of this._currentShapes) {
            if (shape.model.hiddenShape) continue;
            if (shape.model.removed) continue;
            switch (shape.model.type.split('_')[1]) {
            case 'box':
            case 'polygon':
                if (shape.model.contain(pos, this._frame)) {
                    let distance = shape.model.distance(pos, this._frame);
                    if (distance < closedShape.minDistance) {
                        closedShape.minDistance = distance;
                        closedShape.shape = shape.model;
                    }
                }
                break;
            case 'polyline':
            case 'points': {
                let distance = shape.model.distance(pos, this._frame);
                if (distance < openShape.minDistance) {
                    openShape.minDistance = distance;
                    openShape.shape = shape.model;
                }
                break;
            }
            }
        }

        let active = closedShape.shape;
        if (openShape.shape) {
            active = openShape.shape;
        }

        if (noActivation) {
            return active;
        }

        if (active && active != this._activeShape) {
            if (this._activeShape) {
                this._activeShape.active = false;
                this._activeShape = null;
            }
            this._activeShape = active;
            this._activeShape.active = true;
        }
        
    }

    update() {
        this._interpolate();
    }

    resetActive() {
        if (this._activeShape) {
            this._activeShape.active = false;
            this._activeShape = null;
        }
    }

    onPlayerUpdate(player) {
        if (player.ready()) {
            let frame = player.frames.current;

            // If frame was not changed and collection already interpolated (for example after pause() call)
            if (frame === this._frame && this._currentShapes.length) return;
            if (this._activeShape) {
                this._activeShape.active = false;
                this._activeShape = null;
            }
            if (this._activeAAMShape) {
                this._activeAAMShape.activeAAM = {
                    shape: false,
                    attribute: null,
                };
            }
            this._frame = frame;
            this._interpolate();
        }
        else {
            this._clear();
            this.notify();
        }
    }

    onShapeUpdate(model) {
        switch (model.updateReason) {
        case 'activeAAM':
            if (model.activeAAM.shape) {
                this._activeAAMShape = model;
            }
            else if (this._activeAAMShape === model) {
                this._activeAAMShape = null;
            }
            break;
        case 'activation': {
            let active = model.active;
            if (active) {
                if (this._activeShape != model) {
                    if (this._activeShape) {
                        this._activeShape.active = false;
                        $(".detectpoint").remove();
                        // Now loop occure -> active(false) -> notify -> onShapeUpdate
                        // But it will go on 'else' branch and this._activeShape will set to null
                    }
                    this._activeShape = model;
                    // console.log("Now loop occure -> active(false) -> notify -> onShapeUpdate");
                    //setDetectPoint(this._activeShape);
                }
                if (this._activeShape === model) {
                    // console.log("But it will go on 'else' branch and this._activeShape will set to null");
                    setDetectPoint(this._activeShape);
                }
            }
            else {
                if (this._activeShape === model) {
                    this._activeShape = null;
                }

                $(".detectpoint").remove();
            }
            break;
        }
        case 'remove':
            if (model.removed) {
                if (this._activeShape === model) {
                    this._activeShape = null;
                }
                break;
            }
            this.update();
            break;
        case 'keyframe':
        case 'outside':
            this.update();
            break;
        }
    }

    onShapeCreatorUpdate(shapeCreator) {
        if (shapeCreator.createMode) {
            this._activeShape_before_Create = this._activeShape;
            this._idx_before_Create = this._idx;
            this.resetActive();
            //hide all shape
            this.switchObjectsHide();
        }
        else {
            //show all shape
            for (let shape of this._shapes) {
                if (shape.removed) continue;
                while (shape.hiddenShape) {
                    shape.switchHide();
                }
                console.log("visible");
            }
            $('.detectpoint').remove();
            //set newShape / preShape to active 
            menuScroll = true;
            if(this._idx_before_Create != this._idx) {
                this._currentShapes[this._currentShapes.length-1].model.active = true;
            }
            else if(this._activeShape_before_Create){
                this._activeShape_before_Create.active = true;
            }
        }
    }

    collectStatistic() {
        let statistic = {};
        let labels = window.cvat.labelsInfo.labels();
        for (let labelId in labels) {
            statistic[labelId] = {
                boxes: {
                    annotation: 0,
                    interpolation: 0,
                },
                polygons: {
                    annotation: 0,
                    interpolation: 0,
                },
                polylines: {
                    annotation: 0,
                    interpolation: 0,
                },
                points: {
                    annotation: 0,
                    interpolation: 0,
                },
                manually: 0,
                interpolated: 0,
                total: 0,
            };
        }

        let totalForLabels = {
            boxes: {
                annotation: 0,
                interpolation: 0,
            },
            polygons: {
                annotation: 0,
                interpolation: 0,
            },
            polylines: {
                annotation: 0,
                interpolation: 0,
            },
            points: {
                annotation: 0,
                interpolation: 0,
            },
            manually: 0,
            interpolated: 0,
            total: 0,
        };

        for (let shape of this._shapes) {
            if (shape.removed) continue;
            let statShape = shape.collectStatistic();
            statistic[statShape.labelId].manually += statShape.manually;
            statistic[statShape.labelId].interpolated += statShape.interpolated;
            statistic[statShape.labelId].total += statShape.total;
            switch (statShape.type) {
            case 'box':
                statistic[statShape.labelId].boxes[statShape.mode] ++;
                break;
            case 'polygon':
                statistic[statShape.labelId].polygons[statShape.mode] ++;
                break;
            case 'polyline':
                statistic[statShape.labelId].polylines[statShape.mode] ++;
                break;
            case 'points':
                statistic[statShape.labelId].points[statShape.mode] ++;
                break;
            default:
                throw Error(`Unknown shape type found: ${statShape.type}`);
            }
        }

        for (let labelId in labels) {
            totalForLabels.boxes.annotation += statistic[labelId].boxes.annotation;
            totalForLabels.boxes.interpolation += statistic[labelId].boxes.interpolation;
            totalForLabels.polygons.annotation += statistic[labelId].polygons.annotation;
            totalForLabels.polygons.interpolation += statistic[labelId].polygons.interpolation;
            totalForLabels.polylines.annotation += statistic[labelId].polylines.annotation;
            totalForLabels.polylines.interpolation += statistic[labelId].polylines.interpolation;
            totalForLabels.points.annotation += statistic[labelId].points.annotation;
            totalForLabels.points.interpolation += statistic[labelId].points.interpolation;
            totalForLabels.manually += statistic[labelId].manually;
            totalForLabels.interpolated += statistic[labelId].interpolated;
            totalForLabels.total += statistic[labelId].total;
        }

        return [statistic, totalForLabels];
    }

    switchActiveLock() {
        let shape = this._selectActive();

        if (shape) {
            shape.switchLock();
            Logger.addEvent(Logger.EventType.lockObject, {
                count: 1,
                value: !shape.lock
            });
        }
    }

    switchObjectsLock(labelId) {
        this.resetActive();
        let value = true;

        let shapes = Number.isInteger(labelId) ? this._currentShapes.filter((el) => el.model.label === labelId) : this._currentShapes;
        for (let shape of shapes) {
            if (shape.model.removed) continue;
            value = value && shape.model.lock;
            if (!value) break;
        }

        Logger.addEvent(Logger.EventType.lockObject, {
            count: this._currentShapes.length,
            value: !value,
        });

        for (let shape of shapes) {
            if (shape.model.removed) continue;
            if (shape.model.lock === value) {
                shape.model.switchLock();
            }
        }
    }

    switchActiveOccluded() {
        let shape = this._selectActive();
        if (shape && !shape.lock) {
            shape.switchOccluded(window.cvat.player.frames.current);
        }
    }

    switchActiveKeyframe() {
        let shape = this._selectActive();
        if (shape && shape.type === 'interpolation_box' && !shape.lock) {
            shape.switchKeyFrame(window.cvat.player.frames.current);
        }
    }

    switchActiveOutside() {
        let shape = this._selectActive();
        if (shape && shape.type === 'interpolation_box' && !shape.lock) {
            shape.switchOutside(window.cvat.player.frames.current);
        }
    }

    switchActiveHide() {
        //let shape = this._selectActive();
        let shape = this._activeShape;
        if (shape) {
            shape.switchHide();
        }
    }

    // add by jeff
    switchOthersHide(labelId) {
        let before_shape = this._activeShape;
        let hiddenShape = true;
        let hiddenText = true;
        let shapes = Number.isInteger(labelId) ? this._shapes.filter((el) => el.label === labelId) : this._shapes;
        for (let shape of shapes) {
            if (shape.removed || shape.active) continue;
            hiddenShape = hiddenShape && shape.hiddenShape;

            if (!hiddenShape) {
                break;
            }
        }
        if (!hiddenShape) {
            // all shapes invisible
            for (let shape of shapes) {
                if (shape.removed || shape.active) continue;
                while (!shape.hiddenShape) {
                    shape.switchHide();
                }
                console.log("invisile");
            }
        } else{
            // all shapes visible
            for (let shape of shapes) {
                if (shape.removed || shape.active) continue;
                while (shape.hiddenShape) {
                    shape.switchHide();
                }
                console.log("visible");
            }
        }
        if(before_shape)before_shape.active = true;
    }

    switchObjectsHide(labelId) {
        this.resetActive();
        let hiddenShape = true;
        let hiddenText = true;

        let shapes = Number.isInteger(labelId) ? this._shapes.filter((el) => el.label === labelId) : this._shapes;
        for (let shape of shapes) {
            if (shape.removed) continue;
            hiddenShape = hiddenShape && shape.hiddenShape;

            if (!hiddenShape) {
                break;
            }
        }

        if (!hiddenShape) {

            // all shapes invisible
            for (let shape of shapes) {
                if (shape.removed) continue;
                while (!shape.hiddenShape) {
                    shape.switchHide();
                }
                // console.log("invisile");
            }

        } else{

            // all shapes visible
            for (let shape of shapes) {
                if (shape.removed) continue;
                while (shape.hiddenShape) {
                    shape.switchHide();
                }
                // console.log("visible");
            }

        }
        $('.detectpoint').remove();


        // if (!hiddenShape) {
        //     // any shape visible
        //     for (let shape of shapes) {
        //         if (shape.removed) continue;
        //         hiddenText = hiddenText && shape.hiddenText;

        //         if (!hiddenText) {
        //             break;
        //         }
        //     }

        //     if (!hiddenText) {
        //         // any shape text visible
        //         for (let shape of shapes) {
        //             if (shape.removed) continue;
        //             while (shape.hiddenShape || !shape.hiddenText) {
        //                 shape.switchHide();
        //             }
        //         }
        //     }
        //     else {
        //         // all shape text invisible
        //         for (let shape of shapes) {
        //             if (shape.removed) continue;
        //             while (!shape.hiddenShape) {
        //                 shape.switchHide();
        //             }
        //         }
        //     }
        // }
        // else {
        //     // all shapes invisible
        //     for (let shape of shapes) {
        //         if (shape.removed) continue;
        //         while (shape.hiddenShape || shape.hiddenText) {
        //             shape.switchHide();
        //         }
        //     }
        // }
    }


    //add by jeff
    moveShape(direction) {
        menuScroll = true;
        let currentId = -1;
        let shapeModelTmp = [];
        for (let shape of this._currentShapes) {
            if (shape.model.removed) continue;
            shapeModelTmp.push({'obj_id':shape.model._obj_id, 'shape':shape.model});
        }

        shapeModelTmp = shapeModelTmp.sort(function (a, b) {
            return a.obj_id > b.obj_id ? 1 : -1;
        });
        if (this._activeShape)
            currentId = shapeModelTmp.findIndex(x => x.obj_id==this._activeShape._obj_id);
        else
            currentId = -1;
        
        this.resetActive();

        if (currentId == -1) {
            currentId = 0;
        }
        else {
            if (direction == 1) {
                currentId++;
                if(currentId > shapeModelTmp.length-1) currentId = 0;
            }
            else {
                currentId--;
                if(currentId < 0) currentId = shapeModelTmp.length-1;
            }
        }

        shapeModelTmp[currentId].shape.active = true;
        this._activeShape = shapeModelTmp[currentId].shape;
    }

    removePointFromActiveShape(idx) {
        if (this._activeShape && !this._activeShape.lock) {
            this._activeShape.removePoint(idx);
        }
    }

    split() {
        if (this._activeShape) {
            if (!this._activeShape.lock && this._activeShape.type.split('_')[0] === 'interpolation') {
                let list = this._splitter.split(this._activeShape, this._frame);
                let type = this._activeShape.type;
                for (let item of list) {
                    this.add(item, type);
                }

                // Undo/redo code
                let newShapes = this._shapes.slice(-list.length);
                let originalShape = this._activeShape;
                window.cvat.addAction('Split Object', () => {
                    for (let shape of newShapes) {
                        shape.removed = true;
                        shape.unsubscribe(this);
                    }
                    originalShape.removed = false;
                }, () => {
                    for (let shape of newShapes) {
                        shape.removed = false;
                        shape.subscribe(this);
                    }
                    originalShape.removed = true;
                    this.update();
                }, this._frame);
                // End of undo/redo code

                this._activeShape.removed = true;
                this.update();
            }
        }
    }

    selectAllWithLabel(labelId) {
        for (let shape of this.currentShapes) {
            if (shape.model.label === labelId) {
                shape.model.select();
            }
        }
    }

    deselectAll() {
        for (let shape of this.currentShapes) {
            shape.model.deselect();
        }
    }

    get activeShape() {
        return this._activeShape;
    }

    get currentShapes() {
        return this._currentShapes;
    }

    get lastPosition() {
        return this._lastPos;
    }

    set lastPosition(pos) {
        this._lastPos = pos;
    }

    set showAllInterpolation(value) {
        this._showAllInterpolation = value;
        this.update();
    }

    get filter() {
        return this._filter;
    }

    get shapes() {
        return this._shapes;
    }
}

class ShapeCollectionController {
    constructor(collectionModel) {
        this._model = collectionModel;
        this._menusObj = [];
        this._filterController = new FilterController(collectionModel.filter);
        setupCollectionShortcuts.call(this);

        function setupCollectionShortcuts() {
            let switchLockHandler = Logger.shortkeyLogDecorator(function() {
                if(document.activeElement.tagName=='INPUT'){return;}
                this.switchActiveLock();
            }.bind(this));

            let switchAllLockHandler = Logger.shortkeyLogDecorator(function() {
                if(document.activeElement.tagName=='INPUT'){return;}
                this.switchAllLock();
            }.bind(this));

            let switchOccludedHandler = Logger.shortkeyLogDecorator(function() {
                if(document.activeElement.tagName=='INPUT'){return;}
                this.switchActiveOccluded();
            }.bind(this));

            let switchActiveKeyframeHandler = Logger.shortkeyLogDecorator(function() {
                if(document.activeElement.tagName=='INPUT'){return;}
                this.switchActiveKeyframe();
            }.bind(this));

            let switchActiveOutsideHandler = Logger.shortkeyLogDecorator(function() {
                if(document.activeElement.tagName=='INPUT'){return;}
                this.switchActiveOutside();
            }.bind(this));

            let switchHideHandler = Logger.shortkeyLogDecorator(function() {
                if(document.activeElement.tagName=='INPUT'){return;}
                this.switchActiveHide();
            }.bind(this));

            let switchAllHideHandler = Logger.shortkeyLogDecorator(function() {
                if(document.activeElement.tagName=='INPUT'){return;}
                this.switchAllHide();
            }.bind(this));
            // add by jef
            let switchOthersHideHandler = Logger.shortkeyLogDecorator(function() {
                if(document.activeElement.tagName=='INPUT'){return;}
                this.switchOthersHide();
            }.bind(this));

            let removeActiveHandler = Logger.shortkeyLogDecorator(function(e) {
                if (document.activeElement.tagName == 'INPUT') {return;}
                this.removeActiveShape(e);
            }.bind(this));

            let switchLabelHandler = Logger.shortkeyLogDecorator(function(e) {
                if(document.activeElement.tagName=='INPUT'){return;}
                let activeShape = this._model.activeShape;
                if (activeShape) {
                    let labels = Object.keys(window.cvat.labelsInfo.labels());
                    let key = e.keyCode - '1'.charCodeAt(0);
                    if (key in labels) {
                        let labelId = +labels[key];
                        activeShape.changeLabel(labelId);
                    }
                }
                e.preventDefault();
            }.bind(this));

            let switchDefaultLabelHandler = Logger.shortkeyLogDecorator(function(e) {
                if(document.activeElement.tagName=='INPUT'){return;}
                $('#shapeLabelSelector option').eq(e.keyCode - '1'.charCodeAt(0)).prop('selected', true);
                $('#shapeLabelSelector').trigger('change');
            });

            let changeShapeColorHandler = Logger.shortkeyLogDecorator(function() {
                //this.switchActiveColor();
                // console.log("closed switchActiveColor by enter");
            }.bind(this));

            //add by jeff
            let detectPointHandler = Logger.shortkeyLogDecorator(function() {
                if(document.activeElement.tagName=='INPUT'){return;}
                let flag = true;
                for (let attrId in this._model.activeShape._attributes.mutable[this._model.activeShape._frame]) {
                    let attrInfo = window.cvat.labelsInfo.attrInfo(attrId);
                    if(attrInfo.name == "Dont_Care" || attrInfo.name == "看不見車頭車尾") {
                        let value = this._model.activeShape._attributes.mutable[this._model.activeShape._frame][attrId]
                        if(value) {
                            flag = false; 
                            break;
                        }
                    }
                    else if(attrInfo.name == "Type") {
                        let value = this._model.activeShape._attributes.mutable[this._model.activeShape._frame][attrId].toLowerCase();
                        if (value.includes("無人") || value.includes("人") || value.includes("background")) {
                            flag = false;
                            break;
                        }
                    }
                }
                if (flag) setDetectPoint(this._model.activeShape);
                else console.log("u can not set detectPoint");
            }.bind(this));

            //add by Eric
            let removedetectPointHandler = Logger.shortkeyLogDecorator(function() {
                // this.removeDetectPoint();
            }.bind(this));

            let incZHandler = Logger.shortkeyLogDecorator(function() {
                if(document.activeElement.tagName=='INPUT'){return;}
                if (window.cvat.mode === null) {
                    let activeShape = this._model.activeShape;
                    if (activeShape) {
                        activeShape.z_order = this._model.zOrder(window.cvat.player.frames.current).max;
                    }
                }
            }.bind(this));

            let decZHandler = Logger.shortkeyLogDecorator(function() {
                if(document.activeElement.tagName=='INPUT'){return;}
                if (window.cvat.mode === null) {
                    let activeShape = this._model.activeShape;
                    if (activeShape) {
                        activeShape.z_order = this._model.zOrder(window.cvat.player.frames.current).min;
                    }
                }
            }.bind(this));

            let shortkeys = window.cvat.config.shortkeys;

            let enableMovingKeyHandler = Logger.shortkeyLogDecorator(function() {
                if(document.activeElement.tagName=='INPUT'){return;}
                if (!mousedown_in_shape) {
                    this.resetActive();
                    move_background = true;
                }
            }.bind(this));
            let disableMovingKeyHandler = Logger.shortkeyLogDecorator(function() {
                if(document.activeElement.tagName=='INPUT'){return;}
                console.log("ssssss");
                move_background = false;
            }.bind(this));

            Mousetrap.bind('alt', enableMovingKeyHandler, 'keydown');
            Mousetrap.bind('alt', disableMovingKeyHandler, 'keyup');

            Mousetrap.bind(shortkeys["switch_lock_property"].value, switchLockHandler.bind(this), 'keydown');
            Mousetrap.bind(shortkeys["switch_all_lock_property"].value, switchAllLockHandler.bind(this), 'keydown');
            Mousetrap.bind(shortkeys["switch_occluded_property"].value, switchOccludedHandler.bind(this), 'keydown');
            Mousetrap.bind(shortkeys["switch_active_keyframe"].value, switchActiveKeyframeHandler.bind(this), 'keydown');
            Mousetrap.bind(shortkeys["switch_active_outside"].value, switchActiveOutsideHandler.bind(this), 'keydown');
            Mousetrap.bind(shortkeys["switch_hide_mode"].value, switchHideHandler.bind(this), 'keydown');
            Mousetrap.bind(shortkeys["switch_all_hide_mode"].value, switchAllHideHandler.bind(this), 'keydown');
            Mousetrap.bind(shortkeys["change_default_label"].value, switchDefaultLabelHandler.bind(this), 'keydown');
            Mousetrap.bind(shortkeys["change_shape_label"].value, switchLabelHandler.bind(this), 'keydown');
            Mousetrap.bind(shortkeys["delete_shape"].value, removeActiveHandler.bind(this), 'keydown');
            Mousetrap.bind(shortkeys["change_shape_color"].value, changeShapeColorHandler.bind(this), 'keydown');
            
            // add by jeff
            Mousetrap.bind(shortkeys["switch_others_hide_mode"].value, switchOthersHideHandler.bind(this), 'keydown');
            Mousetrap.bind(shortkeys["detect_point"].value, detectPointHandler.bind(this), 'keydown');
            Mousetrap.bind(shortkeys["remove_detect_point"].value, removedetectPointHandler.bind(this), 'keydown');

            let nextShapeHandler = Logger.shortkeyLogDecorator(function(e) {
                this._model.moveShape(1);
                e.preventDefault();
            }.bind(this));

            let prevShapeHandler = Logger.shortkeyLogDecorator(function(e) {
                this._model.moveShape(-1);
                e.preventDefault();
            }.bind(this));

            // add by jeff
            function shiftShape(direction){
                // console.log("shiftShape",direction);
                trainigsaveFlag = false;
                let shape =  $('.shape.selectedShape'); //this._uis.shape.node;//
                let deltaX = 0;
                let deltaY = 0;
                switch(direction){
                    case 8:deltaX=0;deltaY=-1;break;
                    case 2:deltaX=0;deltaY=1;break;
                    case 4:deltaX=-1;deltaY=0;break;
                    case 6:deltaX=1;deltaY=0;break;
                }
                // console.log(direction,deltaX,deltaY,"shiftShape");
                return {
                    xtl: +shape.attr('x') +deltaX,
                    ytl: +shape.attr('y') +deltaY,
                    xbr: +shape.attr('x') + +shape.attr('width') +deltaX,
                    ybr: +shape.attr('y') + +shape.attr('height') +deltaY,
                    occluded: shape.hasClass('occludedShape'),
                    outside: false,    // if drag or resize possible, track is not outside
                    z_order: +shape.attr('z_order'),
                };
            }

            let shiftShapeUp = Logger.shortkeyLogDecorator(function(e) {
                if(document.activeElement.tagName=='INPUT'){return;}
                if(this._model.activeShape){
                    let frame = window.cvat.player.frames.current;
                    this._model.activeShape.updatePosition(frame,shiftShape(8));
                }
                e.preventDefault();
            }.bind(this));
            let shiftShapeDown = Logger.shortkeyLogDecorator(function(e) {
                if(document.activeElement.tagName=='INPUT'){return;}
                if(this._model.activeShape){
                    let frame = window.cvat.player.frames.current;
                    this._model.activeShape.updatePosition(frame,shiftShape(2));
                }
                e.preventDefault();
            }.bind(this));
            let shiftShapeLeft = Logger.shortkeyLogDecorator(function(e) {
                if(document.activeElement.tagName=='INPUT'){return;}
                if(this._model.activeShape){
                    let frame = window.cvat.player.frames.current;
                    this._model.activeShape.updatePosition(frame,shiftShape(4));
                }
                e.preventDefault();
            }.bind(this));
            let shiftSapeRight = Logger.shortkeyLogDecorator(function(e) {
                if(document.activeElement.tagName=='INPUT'){return;}
                if(this._model.activeShape){
                    let frame = window.cvat.player.frames.current;
                    this._model.activeShape.updatePosition(frame,shiftShape(6));
                }
                e.preventDefault();
            }.bind(this));

            Mousetrap.bind(shortkeys["shift_shape_Up"].value, shiftShapeUp.bind(this), 'keydown');
            Mousetrap.bind(shortkeys["shift_shape_Down"].value, shiftShapeDown.bind(this), 'keydown');
            Mousetrap.bind(shortkeys["shift_shape_Left"].value, shiftShapeLeft.bind(this), 'keydown');
            Mousetrap.bind(shortkeys["shift_shape_Right"].value, shiftSapeRight.bind(this), 'keydown');

            Mousetrap.bind(shortkeys["my_next_shape"].value, nextShapeHandler.bind(this), 'keydown');
            Mousetrap.bind(shortkeys["my_prev_shape"].value, prevShapeHandler.bind(this), 'keydown');

            if (window.cvat.job.z_order) {
                Mousetrap.bind(shortkeys["inc_z"].value, incZHandler.bind(this), 'keydown');
                Mousetrap.bind(shortkeys["dec_z"].value, decZHandler.bind(this), 'keydown');
            }
        }
    }

    switchActiveOccluded() {
        if (!window.cvat.mode || window.cvat.mode === 'aam') {
            this._model.switchActiveOccluded();
        }
    }

    switchActiveKeyframe() {
        if (!window.cvat.mode) {
            this._model.switchActiveKeyframe();
        }
    }

    switchActiveOutside() {
        if (!window.cvat.mode) {
            this._model.switchActiveOutside();
        }
    }

    switchAllLock() {
        if (!window.cvat.mode || window.cvat.mode === 'aam') {
            this._model.switchObjectsLock();
        }
    }

    switchLabelLock(labelId) {
        if (!window.cvat.mode || window.cvat.mode === 'aam') {
            this._model.switchObjectsLock(labelId);
        }
    }

    switchActiveLock() {
        if (!window.cvat.mode || window.cvat.mode === 'aam') {
            this._model.switchActiveLock();
        }
    }
    // add by jeff
    switchOthersHide() {
        if (!window.cvat.mode || window.cvat.mode === 'aam') {
            this._model.switchOthersHide();
        }
    }
    
    switchAllHide() {
        if (!window.cvat.mode || window.cvat.mode === 'aam') {
            this._model.switchObjectsHide();
        }
    }

    switchLabelHide(lableId) {
        if (!window.cvat.mode || window.cvat.mode === 'aam') {
            this._model.switchObjectsHide(lableId);
        }
    }

    switchActiveHide() {
        if (!window.cvat.mode || window.cvat.mode === 'aam') {
            this._model.switchActiveHide();
        }
    }

    switchActiveColor() {
        let colorByInstanceInput = $('#colorByInstanceRadio');
        let colorByGroupInput = $('#colorByGroupRadio');
        let colorByLabelInput = $('#colorByLabelRadio');

        let activeShape = this._model.activeShape;
        if (activeShape) {
            if (colorByInstanceInput.prop('checked')) {
                activeShape.changeColor(this._model.nextColor());
            }
            else if (colorByGroupInput.prop('checked')) {
                if (activeShape.groupId) {
                    this._model.updateGroupIdx(activeShape.groupId);
                    colorByGroupInput.trigger('change');
                }
            }
            else {
                let labelId = +activeShape.label;
                window.cvat.labelsInfo.updateLabelColorIdx(labelId);
                $(`.labelContentElement[label_id="${labelId}"`).css('background-color',
                    this._model.colorsByGroup(window.cvat.labelsInfo.labelColorIdx(labelId)));
                colorByLabelInput.trigger('change');
            }
        }
    }

    // Modify by eric
    removeDetectPoint() {

        $(".detectpoint").remove();
        let activeShape = this._model.activeShape;

        if(activeShape){
            let DETECTPOINTAIM = "detectpointAim";

            $("#"+DETECTPOINTAIM + "_" + activeShape._id + "_L").remove();
            $("#"+DETECTPOINTAIM + "_" + activeShape._id + "_R").remove();

            let frame = activeShape._frame;

            for (let attrId in activeShape._attributes.mutable[frame]) {
                let attrInfo = window.cvat.labelsInfo.attrInfo(attrId);
                if(attrInfo.name == "DetectPoints") {
                    activeShape.updateAttribute(frame, attrId, "\"-1,-1,-1,-1\"");
                    break;
                }
            }
        }
    }

    switchDraggableForActive() {
        let activeShape = this._model.activeShape;
        if (activeShape && typeof(activeShape.draggable) != 'undefined') {
            activeShape.draggable = !activeShape.draggable;
        }
    }

    removeActiveShape(e) {
        if (window.cvat.mode === null) {
            //this._model.selectShape(this._model.lastPosition, false);
            let activeShape = this._model.activeShape;
            if (activeShape && (!activeShape.lock || e && e.shiftKey)) {
                // add by jeff
                //清除當前shape值
                let needDelgroupingID = [... activeShape._groupingID];
                let needDelgroupingOrder = [... activeShape._groupingOrder];
                if (PROJECT=='apacorner') {
                    //清除map中有關的group
                    for (let i = 0; i < needDelgroupingID.length; i++) {
                        if(!(this._model._groupMap[activeShape.frame][needDelgroupingID[i]] === undefined)) {
                            delete this._model._groupMap[activeShape.frame][needDelgroupingID[i]];
                        }
                    }
                    //清除shape中有關的group
                    this._model._currentShapes.forEach(function(shape) {
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
                        if(!(this._model._groupMap[activeShape.frame][needDelgroupingID[i]] === undefined)) {
                            let index = this._model._groupMap[activeShape.frame][needDelgroupingID[i]].indexOf([needDelgroupingOrder[i]]);
                            if(index!=-1) {
                                this._model._groupMap[activeShape.frame][needDelgroupingID[i]].splice(index, 1);
                            }
                            // if [] will delete
                            if(this._model._groupMap[activeShape.frame][needDelgroupingID[i]].length == 0) {
                                delete this._model._groupMap[activeShape.frame][needDelgroupingID[i]];
                            }
                        }
                    }
                }
                activeShape._grouping = '';
                activeShape._groupingID = [];
                activeShape._groupingOrder = [];
                //if (!this._groupMap.hasOwnProperty(this._currentGroupID))

                let index = this._menusObj.findIndex(x => x.obj_id==activeShape._obj_id);
                if (index > -1) {
                    this._menusObj.splice(index, 1);
                }

                activeShape.remove();
            }
        }
    }

    removePointFromActiveShape(idx) {
        this._model.removePointFromActiveShape(idx);
    }

    splitForActive() {
        this._model.split();
    }

    selectShape(pos, noActivation) {
        this._model.selectShape(pos, noActivation);
    }

    resetActive() {
        this._model.resetActive();
    }

    setLastPosition(pos) {
        this._model.lastPosition = pos;
    }

    setShowAllInterpolation(value) {
        this._model.showAllInterpolation = value;
    }

    colorsByGroup(groupId) {
        return this._model.colorsByGroup(groupId);
    }

    get filterController() {
        return this._filterController;
    }

    get activeShape() {
        return this._model.activeShape;
    }
}

class ShapeCollectionView {
    constructor(collectionModel, collectionController) {
        collectionModel.subscribe(this);
        this._controller = collectionController;
        this._frameContent = SVG.adopt($('#frameContent')[0]);
        this._UIContent = $('#uiContent');
        this._labelsContent = $('#labelsContent');
        this._showAllInterpolationBox = $('#showAllInterBox');
        this._fillOpacityRange = $('#fillOpacityRange');
        this._selectedFillOpacityRange = $('#selectedFillOpacityRange');
        this._blackStrokeCheckbox = $('#blackStrokeCheckbox');
        this._colorByInstanceRadio = $('#colorByInstanceRadio');
        this._colorByGroupRadio = $('#colorByGroupRadio');
        this._colorByLabelRadio = $('#colorByLabelRadio');
        this._colorByGroupCheckbox = $('#colorByGroupCheckbox');
        this._filterView = new FilterView(this._controller.filterController);
        this._currentViews = [];

        this._currentModels = [];
        this._frameMarker = null;

        // add by jeff for temp delete current (load a frame)
        this._tempViews = [];
        this._tempModels = [];
        

        this._activeShapeUI = null;
        this._scale = 1;
        this._colorSettings = {
            "fill-opacity": 0
        };

        this._showAllInterpolationBox.on('change', (e) => {
            this._controller.setShowAllInterpolation(e.target.checked);
        });

        this._fillOpacityRange.on('input', (e) => {
            let value = Math.clamp(+e.target.value, +e.target.min, +e.target.max);
            e.target.value = value;
            if (value >= 0) {
                this._colorSettings["fill-opacity"] = value;
                delete this._colorSettings['white-opacity'];

                for (let view of this._currentViews) {
                    view.updateColorSettings(this._colorSettings);
                }
            }
            else {
                value *= -1;
                this._colorSettings["white-opacity"] = value;

                for (let view of this._currentViews) {
                    view.updateColorSettings(this._colorSettings);
                }
            }
        });

        this._selectedFillOpacityRange.on('input', (e) => {
            let value = Math.clamp(+e.target.value, +e.target.min, +e.target.max);
            e.target.value = value;
            this._colorSettings["selected-fill-opacity"] = value;

            for (let view of this._currentViews) {
                view.updateColorSettings(this._colorSettings);
            }
        });

        this._blackStrokeCheckbox.on('click', (e) => {
            this._colorSettings["black-stroke"] = e.target.checked;

            for (let view of this._currentViews) {
                view.updateColorSettings(this._colorSettings);
            }
        });

        this._colorByInstanceRadio.on('change', () => {
            this._colorSettings['color-by-group'] = false;
            this._colorSettings['color-by-label'] = false;

            for (let view of this._currentViews) {
                view.updateColorSettings(this._colorSettings);
            }
        });

        this._colorByGroupRadio.on('change', () => {
            this._colorSettings['color-by-group'] = true;
            this._colorSettings['color-by-label'] = false;
            this._colorSettings['colors-by-group'] = this._controller.colorsByGroup.bind(this._controller);

            for (let view of this._currentViews) {
                view.updateColorSettings(this._colorSettings);
            }
        });

        this._colorByLabelRadio.on('change', () => {
            this._colorSettings['color-by-label'] = true;
            this._colorSettings['color-by-group'] = false;

            this._colorSettings['colors-by-label'] = this._controller.colorsByGroup.bind(this._controller);

            for (let view of this._currentViews) {
                view.updateColorSettings(this._colorSettings);
            }
        });

        this._frameContent.on('mousedown', (e) => {
            if (e.target === this._frameContent.node) {
                this._controller.resetActive();
            }
            if(window.cvat.mode=='creation' && PROJECT=='apacorner' && e.which === 3){
                Mousetrap.trigger('q','keydown');
                // let new_event = new MouseEvent(e.type, e)
                // $('#frameContent')[0].dispatchEvent(new_event);
                passNoShow = true;
            }
        });

        // $('#playerFrame').on('mouseleave', () => {
        //     if (!window.cvat.mode) {
        //         this._controller.resetActive();
        //     }
        // });

        this._frameContent.on('mousemove', function(e) {
            passNoShow = false;
            if (e.ctrlKey || e.which === 2 || e.target.classList.contains('svg_select_points')) {
                return;
            }

            let pos = translateSVGPos(this._frameContent.node, e.clientX, e.clientY);
            // if (!window.cvat.mode) {
            //     this._controller.selectShape(pos, false);
            // }

            this._controller.setLastPosition(pos);
        }.bind(this));

        //add by jeff
        // wait me
        this._frameContent.on('click', function(e) {
            if (mousedownAtDetectPoint || e.ctrlKey || e.altKey || e.which === 2 || e.target.classList.contains('svg_select_points')) {
                mousedownAtDetectPoint = false;
                return;
            }

            let pos = translateSVGPos(this._frameContent.node, e.clientX, e.clientY);
            if (!window.cvat.mode) {
                this._controller.selectShape(pos, false);
            }

            this._controller.setLastPosition(pos);

            if(!this._controller._model._activeShape && !window.cvat.mode && PROJECT=='apacorner' && e.which === 1) {
                Mousetrap.trigger('q','keydown');
                let new_event = new MouseEvent(e.type, e)
                $('#frameContent')[0].dispatchEvent(new_event);
            }

        }.bind(this));

        $('#shapeContextMenu li').click((e) => {
            $('.custom-menu').hide(100);

            switch($(e.target).attr("action")) {
            case "object_url": {
                let active = this._controller.activeShape;
                if (active) {
                    window.cvat.search.set('frame', window.cvat.player.frames.current);
                    window.cvat.search.set('filter', `*[id="${active.id}"]`);
                    copyToClipboard(window.cvat.search.toString());
                    window.cvat.search.set('frame', null);
                    window.cvat.search.set('filter', null);
                }
                break;
            }
            case "change_color":
                this._controller.switchActiveColor();
                break;
            case "remove_shape":
                this._controller.removeActiveShape();
                break;
            case "switch_occluded":
                this._controller.switchActiveOccluded();
                break;
            case "switch_lock":
                this._controller.switchActiveLock();
                break;
            case "split_track":
                this._controller.splitForActive();
                break;
            case "drag_polygon":
                this._controller.switchDraggableForActive();
                break;
            //add by jeff
            case "detect_point":
                //this._controller.setDetectPoint();
                setDetectPoint(this._controller.activeShape);
                break;
            //add by eric
            case "remove_detect_point":
                this._controller.removeDetectPoint();
                break;
            }
        });

        let shortkeys = window.cvat.config.shortkeys;
        for (let button of $('#shapeContextMenu li')) {
            switch(button.getAttribute('action')) {
            case "change_color":
                button.innerText = `Change Color (${shortkeys['change_shape_color'].view_value})`;
                break;
            case "remove_shape":
                button.innerText = `Remove Shape (${shortkeys['delete_shape'].view_value})`;
                break;
            case "switch_occluded":
                button.innerText = `Switch Occluded (${shortkeys['switch_occluded_property'].view_value})`;
                break;
            case "switch_lock":
                button.innerText = `Switch Lock (${shortkeys['switch_lock_property'].view_value})`;
                break;
            //add by jeff
            case "detect_point":
                button.innerText = `Detect Point (${shortkeys['detect_point'].view_value})`;
                break;
            //add by Eric
            case "remove_detect_point":
                button.innerText = `Remove Detect Point (${shortkeys['remove_detect_point'].view_value})`;
                break;
            }
        }

        $('#pointContextMenu li').click((e) => {
            let menu = $('#pointContextMenu');
            let idx = +menu.attr('point_idx');
            $('.custom-menu').hide(100);

            switch($(e.target).attr("action")) {
            case "remove_point":
                this._controller.removePointFromActiveShape(idx);
                break;
            }
        });

        let labels = window.cvat.labelsInfo.labels();
        for (let labelId in labels) {
            let lockButton = $(`<button> </button>`)
                .addClass('graphicButton lockButton')
                .attr('title', 'Switch lock for all object with same label')
                .on('click', () => {
                    this._controller.switchLabelLock(+labelId);
                });

            lockButton[0].updateState = function(button, labelId) {
                let models = this._currentModels.filter((el) => el.label === labelId);
                let locked = true;
                for (let model of models) {
                    locked = locked && model.lock;
                    if (!locked) {
                        break;
                    }
                }

                if (!locked) {
                    button.removeClass('locked');
                }
                else {
                    button.addClass('locked');
                }
            }.bind(this, lockButton, +labelId);

            let hiddenButton = $(`<button> </button>`)
                .addClass('graphicButton hiddenButton')
                .attr('title', 'Switch hide for all object with same label')
                .on('click', () => {
                    this._controller.switchLabelHide(+labelId);
                });

            hiddenButton[0].updateState = function(button, labelId) {
                let models = this._currentModels.filter((el) => el.label === labelId);
                let hiddenShape = true;
                let hiddenText = true;
                for (let model of models) {
                    hiddenShape = hiddenShape && model.hiddenShape;
                    hiddenText = hiddenText && model.hiddenText;
                    if (!hiddenShape && !hiddenText) {
                        break;
                    }
                }

                // console.log(hiddenShape, "hiddenShape");
                // console.log(hiddenText, "hiddenText")

                if (hiddenShape) {
                    button.removeClass('hiddenText');
                    button.addClass('hiddenShape');
                }
                else if (hiddenText) {
                    button.addClass('hiddenText');
                    button.removeClass('hiddenShape');
                }
                else {
                    button.removeClass('hiddenText hiddenShape');
                }
            }.bind(this, hiddenButton, +labelId);

            let buttonBlock = $('<center> </center>')
                .append(lockButton).append(hiddenButton)
                .addClass('buttonBlockOfLabelUI');

            let title = $(`<label> ${labels[labelId]} </label>`);

            let mainDiv = $('<div> </div>').addClass('labelContentElement h2 regular hidden')
                .css({
                    'background-color': collectionController.colorsByGroup(+window.cvat.labelsInfo.labelColorIdx(+labelId)),
                }).attr({
                    'label_id': labelId,
                }).on('mouseover mouseup', () => {
                    mainDiv.addClass('highlightedUI');
                    collectionModel.selectAllWithLabel(+labelId);
                }).on('mouseout mousedown', () => {
                    mainDiv.removeClass('highlightedUI');
                    collectionModel.deselectAll();
                }).append(title).append(buttonBlock);

            mainDiv[0].updateState = function() {
                lockButton[0].updateState();
                hiddenButton[0].updateState();
            };

            this._labelsContent.append(mainDiv);
        }

        let sidePanelObjectsButton = $('#sidePanelObjectsButton');
        let sidePanelLabelsButton = $('#sidePanelLabelsButton');

        sidePanelObjectsButton.on('click', () => {
            sidePanelObjectsButton.addClass('activeTabButton');
            sidePanelLabelsButton.removeClass('activeTabButton');
            this._UIContent.removeClass('hidden');
            this._labelsContent.addClass('hidden');
        });

        sidePanelLabelsButton.on('click', () => {
            sidePanelLabelsButton.addClass('activeTabButton');
            sidePanelObjectsButton.removeClass('activeTabButton');
            this._labelsContent.removeClass('hidden');
            this._UIContent.addClass('hidden');
        });
    }

    _updateLabelUIs() {
        this._labelsContent.find('.labelContentElement').addClass('hidden');
        let labels = new Set(this._currentModels.map((el) => el.label));
        for (let label of labels) {
            this._labelsContent.find(`.labelContentElement[label_id="${label}"]`).removeClass('hidden');
        }
        this._updateLabelUIsState();
    }

    _updateLabelUIsState() {
        for (let labelUI of this._labelsContent.find('.labelContentElement:not(.hidden)')) {
            labelUI.updateState();
        }
    }

    onCollectionUpdate(collection) {
        // Save parents and detach elements from DOM
        // in order to increase performance in the buildShapeView function

        // add by jeff
        // if(is_one_frame_mode) {
        //     is_one_frame_mode = false;
        //     this._controller._model.empty();
        //     this._controller._model.import(one_frame_data).updateHash();
        //     this._controller._model.update();
        // }

        let parents = {
            uis: this._UIContent.parent(),
            shapes: this._frameContent.node.parentNode
        };

        let oldModels = this._currentModels;
        let oldViews = this._currentViews;
        
        let newShapes = collection.currentShapes;
        let newModels = newShapes.map((el) => el.model);

        let frameChanged = this._frameMarker != window.cvat.player.frames.current;

        if (frameChanged) {
            this._frameContent.node.parent = null;
            this._UIContent.detach();
            this._controller._menusObj = [];
        }

        this._currentViews = [];
        this._currentModels = [];

        // Check which old models are new models
        for (let oldIdx = 0; oldIdx < oldModels.length; oldIdx ++) {
            let newIdx = newModels.indexOf(oldModels[oldIdx]);
            let significantUpdate = ['remove', 'keyframe', 'outside'].includes(oldModels[oldIdx].updateReason);

            // Changed frame means a changed position in common case. We need redraw it.
            // If shape has been restored after removing, it view already removed. We need redraw it.
            if (newIdx === -1 || significantUpdate || frameChanged) {
                let view = oldViews[oldIdx];
                view.unsubscribe(this);
                view.controller().model().unsubscribe(view);
                view.erase();

                if (newIdx != -1 && (frameChanged || significantUpdate)) {
                    drawView.call(this, newShapes[newIdx], newModels[newIdx]);
                }
            }
            else {
                this._currentViews.push(oldViews[oldIdx]);
                this._currentModels.push(oldModels[oldIdx]);
            }
        }

        // Now we need draw new models which aren't on previous collection
        for (let newIdx = 0; newIdx < newModels.length; newIdx ++) {
            if (!this._currentModels.includes(newModels[newIdx])) {
                drawView.call(this, newShapes[newIdx], newModels[newIdx]);
            }
        }

        if (frameChanged) {
            parents.shapes.append(this._frameContent.node);
            parents.uis.prepend(this._UIContent);
        }

        ShapeCollectionView.sortByZOrder();
        this._frameMarker = window.cvat.player.frames.current;
        this._updateLabelUIs();

        

        function drawView(shape, model) {
            let view = buildShapeView(model, buildShapeController(model), this._frameContent, this._UIContent, this._controller._menusObj);
            view.draw(shape.interpolation, model._id);
            view.updateColorSettings(this._colorSettings);
            model.subscribe(view);
            view.subscribe(this);
            this._currentViews.push(view);
            this._currentModels.push(model);
        }

    }

    onPlayerUpdate(player) {
        if (!player.ready())  this._frameContent.addClass('hidden');
        else this._frameContent.removeClass('hidden');

        if (this._scale === player.geometry.scale) return;

        this._scale = player.geometry.scale;
        let scaledR = POINT_RADIUS / this._scale;
        let scaledStroke = STROKE_WIDTH / this._scale;
        let scaledPointStroke = SELECT_POINT_STROKE_WIDTH / this._scale;
        $('.svg_select_points').each(function() {
            this.instance.radius(scaledR, scaledR);
            this.instance.attr('stroke-width', scaledPointStroke);
        });

        // $('.detectpoint').each(function() {
        //     let x = this.instance.attr('x');
        //     let y = this.instance.attr('y');
        //     let width = this.instance.attr('width');
        //     let height = this.instance.attr('height');
        //     let cx = x + 0.5*width;
        //     let cy = y + 0.5*height
        //     x = cx - scaledR*1.5;
        //     y = cy - scaledR*1.5;
        //     this.instance.attr('x', x);
        //     this.instance.attr('y', y);
        //     this.instance.attr('width', scaledR*3);
        //     this.instance.attr('height', scaledR*3);
        //     this.instance.attr('stroke-width', scaledPointStroke);
        //     this.instance.draggable({
        //         minX: xtl - scaledR*1.5,
        //         minY: ydr - scaledR*1.5,
        //         maxX: xbr + scaledR*1.5,
        //         maxY: ydr + scaledR*1.5,
        //         snapToGrid: 0.1 
        //     })
        // });

        $('.detectpointAim').each(function() {
            this.instance.attr('stroke-width', scaledPointStroke/2);
        });

        $('.tempMarker').each(function() {
            this.instance.radius(scaledR, scaledR);
            this.instance.attr('stroke-width', scaledStroke);
        });

        for (let view of this._currentViews) {
            view.updateShapeTextPosition();
        }
    }

    onShapeViewUpdate(view) {
        switch (view.updateReason) {
        case 'drag':
            if (view.dragging) {
                window.cvat.mode = 'drag';
            }
            else if (window.cvat.mode === 'drag') {
                window.cvat.mode = null;
            }
            break;
        case 'resize':
            if (view.resize) {
                window.cvat.mode = 'resize';
            }
            else if (window.cvat.mode === 'resize') {
                window.cvat.mode = null;
            }
            break;
        case 'remove': {
            let idx = this._currentViews.indexOf(view);
            view.unsubscribe(this);
            view.controller().model().unsubscribe(view);
            view.erase();
            this._currentViews.splice(idx, 1);
            this._currentModels.splice(idx, 1);
            this._updateLabelUIs();
            break;
        }
        case 'changelabel': {
            this._updateLabelUIs();
            break;
        }
        case 'lock':
            this._updateLabelUIsState();
            break;
        case 'hidden':
            this._updateLabelUIsState();
            break;
        }
    }

    // If ShapeGrouperModel was disabled, need to update shape appearence
    // In order to don't dublicate function, I simulate checkbox change event
    onGrouperUpdate(grouper) {
        if (!grouper.active && this._colorByGroupRadio.prop('checked')) {
            this._colorByGroupRadio.trigger('change');
        }
    }

    static sortByZOrder() {
        if (window.cvat.job.z_order) {
            let content = $('#frameContent');
            let shapes = $(content.find('.shape, .pointTempGroup, .shapeCreation, .aim').toArray().sort(
                (a,b) => (+a.attributes.z_order.nodeValue - +b.attributes.z_order.nodeValue)
            ));
            let children = content.children().not(shapes);

            for (let shape of shapes) {
                content.append(shape);
            }

            for (let child of children) {
                content.append(child);
            }

            shapes = $(content.find('.detectpointAim')).toArray();
            for (let shape of shapes) {
                content.append(shape);
            }
            shapes = $(content.find('.detectpoint')).toArray();
            for (let shape of shapes) {
                content.append(shape);
            }
        }
    }
}

// add by jeff
function setDetectPoint(activeShape){
    if(!['fcw_training', 'fcw_testing', 'bsd_training'].includes(PROJECT)){return;}
    $(".detectpoint").remove();

    if(activeShape._type !== "annotation_box"){return;}
    
    // console.log("in set ");
    if(activeShape && activeShape._hiddenShape===false){
        //menuScroll = true;

        let DETECTPOINT = "detectpoint";
        let DETECTPOINTAIM = "detectpointAim";

        $("#"+DETECTPOINTAIM + "_" + activeShape._id + "_L").remove();
        $("#"+DETECTPOINTAIM + "_" + activeShape._id + "_R").remove();
        
        let frame = activeShape._frame;
        let xtl = activeShape._positions[frame]['xtl'];
        let ytl = activeShape._positions[frame]['ytl'];
        let xbr = activeShape._positions[frame]['xbr'];
        let ybr = activeShape._positions[frame]['ybr'];
        
        let attrId = null;
        let attrId_detectpoint = null;'1,2  ,3,4'['','',3,4]
        let xdl, ydl, xdr, ydr;

        let isdontcare = false, withoutcarside = false, middlecarside = false;

        for (attrId in activeShape._attributes.mutable[frame]) {
            let attrInfo = window.cvat.labelsInfo.attrInfo(attrId);
            if(attrInfo.name == "DetectPoints") {
                let detectpoints = activeShape._attributes.mutable[frame][attrId].replace(/"/g, "").split(/[\s,]+/);
                xdl = parseFloat(detectpoints[0]);
                ydl = parseFloat(detectpoints[1]);
                xdr = parseFloat(detectpoints[2]);
                ydr = parseFloat(detectpoints[3]);
                attrId_detectpoint = attrId;
            }
            if(attrInfo.name == "Dont_Care") {
                if(activeShape._attributes.mutable[frame][attrId]){
                    isdontcare = true;
                    return;
                }
            }
            if(attrInfo.name == "Type") {
                let value = activeShape._attributes.mutable[frame][attrId].toLowerCase();
                if (value.includes("無人") || value.includes("人") || value.includes("background")) {
                    withoutcarside = true;
                    return;
                }
                if(value.includes("bike") || value.includes("動物")) {
                    middlecarside = true;
                }
            }
        }
        if (xdl == -1) return;
        
        //if (xdl == -1) xdl = parseFloat(1/10);
        if (ydl == -1) ydl = +parseFloat(ytl + (ybr - ytl) * 2/3).toFixed(6);
        //if (xdr == -1) xdr = parseFloat(9/10);
        if (ydr == -1) ydr = +parseFloat(ytl + (ybr - ytl) * 2/3).toFixed(6);

        let xdl_draw = +parseFloat(xtl + xdl * (xbr-xtl)).toFixed(6);
        let xdr_draw = +parseFloat(xtl + xdr * (xbr-xtl)).toFixed(6);

        let scaledR = POINT_RADIUS / window.cvat.player.geometry.scale;
        let thisframeContent = SVG.adopt($('#frameContent')[0]);

        if (activeShape.active) {
            thisframeContent.rect(scaledR*3,scaledR*3).draggable({
                minX: xtl - scaledR*1.5,
                minY: +ydl - scaledR*1.5,
                maxX: (middlecarside == false)?xbr + scaledR*1.5 : xtl + scaledR*1.5,
                maxY: +ydl + scaledR*1.5,
                snapToGrid: 0.1 
            }).center(xdl_draw,ydl).addClass(DETECTPOINT).fill('#ffff00').attr({
                'stroke-width': STROKE_WIDTH / window.cvat.player.geometry.scale * 1.5,
                'id': DETECTPOINT + "_" + activeShape._id + "_L"
            }).on('dragend', function(e){
                e.preventDefault();
                mousedownAtDetectPoint = false;

                let x = parseFloat(e.target.getAttribute('x')) + parseFloat(scaledR*1.5);

                let out_xl = +parseFloat((x - xtl) / (xbr - xtl)).toFixed(6);
                let out_xr = +parseFloat((xdr_draw - xtl) / (xbr - xtl)).toFixed(6);
                
                activeShape.updateAttribute(frame, attrId_detectpoint, "\"" + out_xl + "," + ydl + "," + out_xr + "," + ydl + "\"");

                xdl_draw = +parseFloat(xtl + out_xl * (xbr-xtl)).toFixed(6);
                xdr_draw = +parseFloat(xtl + out_xr * (xbr-xtl)).toFixed(6);

                let content = $('#frameContent');
                let shapes = $(content.find('.detectpointAim')).toArray();
                for (let shape of shapes) {
                    content.append(shape);
                }
                shapes = $(content.find('.detectpoint')).toArray();
                for (let shape of shapes) {
                    content.append(shape);
                }
            });
            

            thisframeContent.rect(scaledR*3,scaledR*3).draggable({
                minX: xtl - scaledR*1.5,
                minY: ydr - scaledR*1.5,
                maxX: xbr + scaledR*1.5,
                maxY: ydr + scaledR*1.5,
                snapToGrid: 0.1 
            }).center(xdr_draw,ydr).addClass(DETECTPOINT).fill('#ffff00').attr({
                'stroke-width': STROKE_WIDTH / window.cvat.player.geometry.scale * 1.5,
                'id': DETECTPOINT + "_" + activeShape._id + "_R"
            }).on('dragend', function(e){
                e.preventDefault();
                mousedownAtDetectPoint = false;

                let x = parseFloat(e.target.getAttribute('x')) + parseFloat(scaledR*1.5);

                let out_xl = +parseFloat((xdl_draw - xtl) / (xbr - xtl)).toFixed(6);
                let out_xr = +parseFloat((x - xtl) / (xbr - xtl)).toFixed(6);
                
                activeShape.updateAttribute(frame, attrId_detectpoint, "\"" + out_xl + "," + ydr + "," + out_xr + "," + ydr + "\"");

                xdl_draw = +parseFloat(xtl + out_xl * (xbr-xtl)).toFixed(6);
                xdr_draw = +parseFloat(xtl + out_xr * (xbr-xtl)).toFixed(6);

                let content = $('#frameContent');
                let shapes = $(content.find('.detectpointAim')).toArray();
                for (let shape of shapes) {
                    content.append(shape);
                }
                shapes = $(content.find('.detectpoint')).toArray();
                for (let shape of shapes) {
                    content.append(shape);
                }
            });
        }

        thisframeContent.line(xdl_draw, ytl, xdl_draw, ybr).attr({
            'stroke-width': STROKE_WIDTH / 2 / window.cvat.player.geometry.scale ,'stroke': '#ffff00',
            'id': DETECTPOINTAIM + "_" + activeShape._id + "_L"
        }).addClass(DETECTPOINTAIM);
    
        thisframeContent.line(xdr_draw, ytl, xdr_draw, ybr).attr({
            'stroke-width': STROKE_WIDTH / 2 / window.cvat.player.geometry.scale ,'stroke': '#ffff00',
            'id': DETECTPOINTAIM + "_" + activeShape._id + "_R"
        }).addClass(DETECTPOINTAIM);

        $("."+DETECTPOINT).each(function() {
            $(this).on('dragstart dragmove', () => {
                let currentAimId = $(this)[0].id.replace(DETECTPOINT, DETECTPOINTAIM);
                $("#"+currentAimId).remove();
                thisframeContent.line($(this)[0].getBBox().x+scaledR*1.5, ytl, $(this)[0].getBBox().x+scaledR*1.5, ybr).attr({
                    'stroke-width': STROKE_WIDTH / 2 / window.cvat.player.geometry.scale ,'stroke': '#ffff00',
                    'id': currentAimId
                }).addClass(DETECTPOINTAIM);
            }).on('mouseover', () => {
                this.instance.attr('stroke-width', STROKE_WIDTH * 2 / window.cvat.player.geometry.scale);
            }).on('mouseout', () => {
                this.instance.attr('stroke-width', STROKE_WIDTH / window.cvat.player.geometry.scale);
            });
        });

        let content = $('#frameContent');
        let shapes = $(content.find('.detectpoint')).toArray();
        for (let shape of shapes) {
            content.append(shape);
        }
    }
}
