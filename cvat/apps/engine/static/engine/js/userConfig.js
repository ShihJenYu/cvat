/*
 * Copyright (C) 2018 Intel Corporation
 *
 * SPDX-License-Identifier: MIT
 */

/* exported Config */
"use strict";


class Config {
    constructor() {
        this._username = "_default_";
        this._shortkeys = {
            switch_lock_property: {
                value: "alt+l",
                view_value: "L",
                description: "switch lock property for active shape"
            },

            switch_all_lock_property: {
                value: "alt+t l",
                view_value: "T + L",
                description: "switch lock property for all shapes on current frame"
            },

            switch_occluded_property: {
                value: "alt+q,alt+/".split(','),
                view_value: "Q or Num Devision",
                description: "switch occluded property for active shape"
            },

            switch_draw_mode: {
                value: "q", //n
                view_value: "Q",
                description: "start draw / stop draw"
            },

            cancel_draw_mode: {
                value: "alt+q",
                view_value: "Alt + Q",
                description: "close draw mode without create"
            },

            switch_merge_mode: {
                value: "alt+m",
                view_value: "alt+M",
                description: "start merge / apply changes"
            },

            cancel_merge_mode: {
                value: "shift+alt+m",
                view_value: "shift + Alt + M",
                description: "close merge mode without apply the merge"
            },

            switch_group_mode: {
                value: "alt+g",
                view_value: "alt+G",
                description: "start group / apply changes"
            },

            cancel_group_mode: {
                value: "shift+alt+g",
                view_value: "shift + Alt + G",
                description: "close group mode without changes"
            },

            reset_group: {
                value: "ctrl+shift+g",
                view_value: "ctrl + Shift + G",
                description: "reset group for selected shapes"
            },

            change_shape_label: {
                value: "ctrl+1,ctrl+2,ctrl+3,ctrl+4,ctrl+5,ctrl+6,ctrl+7,ctrl+8,ctrl+9".split(','),
                view_value: "Ctrl + (1,2,3,4,5,6,7,8,9)",
                description: "change shape label for existing object"
            },

            change_default_label: {
                value: "shift+1,shift+2,shift+3,shift+4,shift+5,shift+6,shift+7,shift+8,shift+9".split(','),
                view_value: "Shift + (1,2,3,4,5,6,7,8,9)",
                description: "change label default label"
            },

            change_shape_color: {
                value: "alt+enter",
                view_value: "alt + Enter",
                description: "change color for highligted shape"
            },

            // add by jeff
            detect_point: {
                value: "w",
                view_value: "W",
                description: "set detect_point"
            },

            // add by Eric
            remove_detect_point: {
                value: "shift+w",
                view_value: "Shift + W",
                description: "remove detect_point"
            },

            change_player_brightness: {
                value: "shift+x,x".split(','),
                view_value: "shift+x,ctrl+x",
                description: "increase/decrease brightness of an image"
            },

            change_player_contrast: {
                value: "shift+c,c".split(','),
                view_value: "Shift+C / C",
                description: "increase/decrease contrast of an image"
            },

            change_player_saturation: {
                value: "ctrl+shift+s,ctrl+alt+s".split(','),
                view_value: "ctrl+Shift+S / ctrl+Alt+S",
                description: "increase/decrease saturation of an image"
            },

            switch_hide_mode: {
                value: "r",
                view_value: "R",
                description: "switch hide mode for active shape"
            },

            switch_active_keyframe: {
                value: "alt+p",
                view_value: "P",
                description: "switch keyframe property for active shape"
            },

            switch_active_outside: {
                value: "alt+o",
                view_value: "O",
                description: "switch outside property for active shape"
            },

            switch_all_hide_mode: {
                value: "shift+r",
                view_value: "Shift + r",
                description: "switch hide mode for all shapes"
            },
            // add by jeff
            switch_others_hide_mode: {
                value: "e",
                view_value: "e",
                description: "switch hide mode for all shapes"
            },

            delete_shape: {
                value: "del,shift+del".split(','),
                view_value: "Del, Shift + Del",
                description: "delete active shape (use shift for force deleting)"
            },

            focus_to_frame: {
                value: 'alt+`,alt+~'.split(','),
                view_value: '~ / `',
                description: "focus to 'go to frame' element"
            },

            next_frame: {
                value: "alt+f",
                view_value: "alt+F",
                description: "move to next player frame"
            },

            prev_frame: {
                value: "alt+d",
                view_value: "alt+D",
                description: "move to previous player frame"
            },

            forward_frame: {
                value: "alt+v",
                view_value: "alt+V",
                description: "move forward several frames"
            },

            backward_frame: {
                value: "alt+c",
                view_value: "alt+C",
                description: "move backward several frames"
            },

            next_key_frame: {
                value: "alt+r",
                view_value: "alt+R",
                description: "move to next key frame of highlighted track"
            },

            prev_key_frame: {
                value: "alt+e",
                view_value: "alt+E",
                description: "move to previous key frame of highlighted track"
            },

            prev_filter_frame: {
                value: 'pageup',
                view_value: 'Page Up',
                description: 'move to prev frame which satisfies the filter'
            },

            next_filter_frame: {
                value: 'pagedown',
                view_value: 'Page Down',
                description: 'move to next frame which satisfies the filter'
            },

            play_pause: {
                value: "alt+space",
                view_value: "Space",
                description: "switch play / pause of player"
            },

            open_help: {
                value: "f1",
                view_value: "F1",
                description: "open help window"
            },

            open_settings: {
                value: "f2",
                view_value: "F2",
                description: "open settings window "
            },

            save_work: {
                value: "ctrl+s",
                view_value: "Ctrl + S",
                description: "save work on the server"
            },

            copy_shape: {
                value: "ctrl+c",
                view_value: "Ctrl + C",
                description: "copy active shape to buffer"
            },

            propagate_shape: {
                value: "alt+ctrl+b",
                view_value: "Ctrl + B",
                description: "propagate active shape"
            },

            switch_paste: {
                value: "ctrl+v",
                view_value: "Ctrl + V",
                description: "swich paste mode"
            },

            switch_aam_mode: {
                value: "shift+enter",
                view_value: "Shift + Enter",
                description: "switch attribute annotation mode"
            },

            aam_next_attribute: {
                value: "alt+down",
                view_value: "Down Arrow",
                description: "move to next attribute in attribute annotation mode"
            },

            aam_prev_attribute: {
                value: "alt+up",
                view_value: "Up Arrow",
                description: "move to previous attribute in attribute annotation mode"
            },

            // aam_next_shape: {
            //     value: "tab",
            //     view_value: "Tab",
            //     description: "move to next shape in attribute annotation mode"
            // },

            // aam_prev_shape: {
            //     value: "shift+tab",
            //     view_value: "Shift + Tab",
            //     description: "move to previous shape in attribute annotation mode"
            // },
            //add by jeff
            my_next_shape: {
                value: "tab",
                view_value: "Tab",
                description: "move to next shape in attribute annotation mode"
            },

            my_prev_shape: {
                value: "shift+tab",
                view_value: "Shift + Tab",
                description: "move to previous shape in attribute annotation mode"
            },

            shift_shape_Up: {
                value: "up",
                view_value: "Up Arrow",
                description: "shift up shape pos"
            },

            shift_shape_Down: {
                value: "down",
                view_value: "Down Arrow",
                description: "shift down shape pos"
            },

            shift_shape_Left: {
                value: "left",
                view_value: "Left Arrow",
                description: "shift left shape pos"
            },

            shift_shape_Right: {
                value: "right",
                view_value: "Right Arrow",
                description: "shift right shape pos"
            },

            select_i_attribute: {
                value: "1,2,3,4,5,6,7,8,9,0".split(','),
                view_value: "1,2,3,4,5,6,7,8,9,0",
                description: "setup corresponding attribute value in attribute annotation mode"
            },

            change_grid_opacity: {
                value: ['alt+g+=', 'alt+g+-'],
                view_value: "Alt + G + '+', Alt + G + '-'",
                description: "increase/decrease grid opacity"
            },

            change_grid_color: {
                value: "alt+g+enter",
                view_value: "Alt + G + Enter",
                description: "change grid color"
            },

            undo: {
                value: "alt+ctrl+z",
                view_value: "Ctrl + Z",
                description: "undo"
            },

            redo: {
                value: ['alt+ctrl+shift+z', 'alt+ctrl+y'],
                view_value: "Ctrl + Shift + Z / Ctrl + Y",
                description: "redo"
            },
            
            cancel_mode: {
                value: 'esc',
                view_value: "Esc",
                description: "cancel active mode"
            }

        };

        if (window.cvat && window.cvat.job && window.cvat.job.z_order) {
            this._shortkeys['inc_z'] = {
                value: '+,='.split(','),
                view_value: '+',
                description: 'increase z order for active shape',
            };

            this._shortkeys['dec_z'] = {
                value: '-,_'.split(','),
                view_value: '-',
                description: 'decrease z order for active shape',
            };
        }

        this._settings = {
            player_step: {
                value: "10",
                description: "step size for player when move on several frames forward/backward"
            },

            player_speed: {
                value: "25 FPS",
                description: "playback speed of the player"
            },

            reset_zoom: {
                value: "false",
                description: "reset frame zoom when move beetween the frames"
            },

            enable_auto_save: {
                value: "false",
                description: "enable auto save ability"
            },

            auto_save_interval: {
                value: "15",
                description: "auto save interval (min)"
            },
        };

        this._defaultShortkeys = JSON.parse(JSON.stringify(this._shortkeys));
        this._defaultSettings = JSON.parse(JSON.stringify(this._settings));
    }


    reset() {
        this._shortkeys = JSON.parse(JSON.stringify(this._defaultShortkeys));
        this._settings = JSON.parse(JSON.stringify(this._defaultSettings));
    }


    get shortkeys() {
        return JSON.parse(JSON.stringify(this._shortkeys));
    }


    get settings() {
        return JSON.parse(JSON.stringify(this._settings));
    }
}