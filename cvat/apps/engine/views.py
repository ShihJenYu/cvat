# coding=utf-8
# Copyright (C) 2018 Intel Corporation
#
# SPDX-License-Identifier: MIT

import os,errno,copy
import io
import csv
import json
import math
import traceback
import glob
import shutil
# add by jeff
import time, random, operator, functools
from django.utils import timezone
from ipware import get_client_ip

from django.http import HttpResponse, HttpResponseBadRequest, JsonResponse
from django.shortcuts import redirect, render
from django.conf import settings
from django.contrib.auth.decorators import permission_required
from django.views.decorators.gzip import gzip_page
from sendfile import sendfile

#add by jeff
from django.apps import apps

from django.db import transaction
from django.db.models import Q, Max, Min, F
from django.core.exceptions import ObjectDoesNotExist

from . import annotation, task, parseXML, read_DMS_CSV, models
from cvat.settings.base import JS_3RDPARTY
from cvat.apps.authentication.decorators import login_required
from requests.exceptions import RequestException
import logging
from .logging import task_logger, job_logger, global_logger, job_client_logger

from .common import get_ProjectModel, get_FrameUserRecordModel, new_ProjectObject, new_FrameUserRecordObject

############################# High Level server API
@login_required
@permission_required('engine.view_task', raise_exception=True)
def catch_client_exception(request, jid):
    data = json.loads(request.body.decode('utf-8'))
    for event in data['exceptions']:
        job_client_logger[jid].error(json.dumps(event))

    return HttpResponse()

@login_required
def dispatch_request(request):
    """An entry point to dispatch legacy requests"""
    project = list(filter(None, request.path.split('/')))[0]
    if request.user.groups.filter(name='admin').exists():
        if request.method == 'GET' and 'id' in request.GET:
            return render(request, 'engine/annotation_keyframe.html', {
                'js_3rdparty': JS_3RDPARTY.get('engine', []),
                'project': project,
            })
        else:
            print ("url is",request.path)
            project = list(filter(None, request.path.split('/')))[0]
            return redirect('/dashboard/' + project)
    else:
        web = ''
        if project == 'fcw_training' and request.user.groups.filter(name__in=['fcw_training','otofcw_training']).exists():
            web = 'annotation_training'
        elif project == 'fcw_testing' and request.user.groups.filter(name__in=['fcw_testing','otofcw_testing']).exists():
            web = 'annotation_fcw_testing'
        elif project == 'apacorner' and request.user.groups.filter(name__in=['apacorner','otoapacorner']).exists():
            web = 'annotation_apacorner'
        elif project == 'dms_training' and request.user.groups.filter(name__in=['dms_training','otodms_training']).exists():
            web = 'annotation_dms_training'
        elif project == 'bsd_training' and request.user.groups.filter(name__in=['bsd_training','otobsd_training']).exists():
            web = 'annotation_training'
        else:
            return redirect('/')
        return render(request, 'engine/{}.html'.format(web), {
            'js_3rdparty': JS_3RDPARTY.get('engine', [])
        })

# def get_ProjectModel(project):
#     if project == 'fcw_training':
#         return apps.get_model('engine', 'FCWTrain')
#     elif project == 'bsd_training':
#         return apps.get_model('engine', 'BSDTrain')
#     elif project == 'dms_training':
#         return apps.get_model('engine', 'DMSTrain')
#     elif project == 'apacorner':
#         return apps.get_model('engine', 'APACorner')
# def get_FrameUserRecordModel(project):
#     if project == 'fcw_training':
#         return apps.get_model('engine', 'TaskFrameUserRecord')
#     elif project == 'bsd_training':
#         return apps.get_model('engine', 'BSDTrain_FrameUserRecord')
#     elif project == 'dms_training':
#         return apps.get_model('engine', 'DMSTrain_FrameUserRecord')
#     elif project == 'apacorner':
#         return apps.get_model('engine', 'APACorner_FrameUserRecord')

# def new_ProjectObject(project):
#     if project == 'fcw_training':
#         return models.FCWTrain()
#     elif project == 'bsd_training':
#         return models.BSDTrain()
#     elif project == 'dms_training':
#         return models.DMSTrain()
#     elif project == 'apacorner':
#         return models.APACorner()
# def new_FrameUserRecordObject(project):
#     if project == 'fcw_training':
#         return models.TaskFrameUserRecord()
#     elif project == 'bsd_training':
#         return models.BSDTrain_FrameUserRecord()
#     elif project == 'dms_training':
#         return models.DMSTrain_FrameUserRecord()
#     elif project == 'apacorner':
#         return models.APACorner_FrameUserRecord()


# return packagename, videoname, camera 
def get_imagesDir_Info(project=None,src_path=None):

    #upload/fcw/images/package/video
    #upload/apa/images/package/video/camera

    if project is None or src_path is None:
        return None, None, None

    elements = src_path.split('/')
    if project in ['fcw_training','bsd_training','dms_training']:
        return elements[-2], elements[-1], None
    elif project == 'apacorner':
        return elements[-3], elements[-2], elements[-1]


# Add by jeff
@login_required
@transaction.atomic
@permission_required('engine.add_task', raise_exception=True)
def insert_images(request):
    try:
        #upload/fcw/Images/pd/video/images
        #upload/apa/Images/pd/video/camera/images

        sShare_Root = settings.SHARE_ROOT
        list_paths = request.POST.getlist('data')
        params = request.POST.dict()
        project = params['project']

        _ProjectModel = get_ProjectModel(project)
        _FrameUserRecordModel = get_FrameUserRecordModel(project)

        will_do_paths = []
        not_do_paths = []

        for a_path in list_paths:
            # if has any .ext will pass
            if os.path.splitext(a_path)[-1] != '':
                continue

            a_srcpath = os.path.normpath(a_path).lstrip('/')
            a_abs_srcpath = os.path.abspath(os.path.join(sShare_Root, a_srcpath))

            # check path is images dir 
            images_per_dir = glob.glob('{}/*.{}'.format(a_abs_srcpath,'png'))
            print("doing",images_per_dir)
            if images_per_dir:
                # get packagename videoname, camera
                packagename, videoname, camera = get_imagesDir_Info(project=project, src_path=a_abs_srcpath)

                print('packagename={}, videoname={}, camera={}'.format(packagename, videoname, camera))
                print('videoname',videoname)
                print('images_per_dir',images_per_dir)

                # find task in project, because videoname may be repeated in different projects
                project_tids = None
                video_task = None

                project_tids = list(_ProjectModel.objects.all().values_list('task_id', flat=True))
                
                try:
                    video_task = models.Task.objects.select_for_update().get(name=videoname, id__in=project_tids)
                except ObjectDoesNotExist:
                    not_do_paths.append({'path':a_abs_srcpath, 'reason':'not found video in data'})
                    continue
                
                video_tid = video_task.id
                video_size = video_task.size
                video_path = video_task.path
                
                # get image path in .upload
                realvideopath = glob.glob('{}/*/Images/*/*'.format(video_task.get_upload_dirname())) # new formate
                if len(realvideopath) == 0:
                    realvideopath = glob.glob('{}/*/*'.format(video_task.get_upload_dirname())) # old formate
                    if len(realvideopath) > 1:
                        not_do_paths.append({'path':a_abs_srcpath, 'reason':'multi dir in upload folder'})
                        continue
                    elif len(realvideopath) == 0:
                        not_do_paths.append({'path':a_abs_srcpath, 'reason':'no dir in upload folder'})
                        continue
                
                # copy image from share to realpath
                for image in images_per_dir:
                    shutil.copy(image, realvideopath[0])
                
                # get imgAbspath list
                insertedImages = []
                for img in sorted(os.listdir(realvideopath[0])):
                    img_fullpath = os.path.join(realvideopath[0], img)
                    insertedImages.append(img_fullpath)
                
                # create new link
                print("create new link")
                after_size = 0
                for frame, image_orig_path in enumerate(insertedImages):
                    image_dest_path = task._get_frame_path(frame, video_task.get_data_dirname())
                    image_orig_path = os.path.abspath(image_orig_path)

                    after_size += 1
                    dirname = os.path.dirname(image_dest_path)
                    if not os.path.exists(dirname):
                        os.makedirs(dirname)
                    try:
                        os.symlink(image_orig_path, image_dest_path)
                    except OSError as e:
                        if e.errno == errno.EEXIST:
                            os.remove(image_dest_path)
                            os.symlink(image_orig_path, image_dest_path)
                        else:
                            raise e

                # #add package
                # history_packagenames = list(video_task.taskpackage_set.all().values_list('packagename__packagename', flat=True))
                # if not packagename in history_packagenames:
                #     try:
                #         db_package = models.PackagePriority.objects.get(packagename=packagename)
                #         taskPackage = models.TaskPackage()
                #         taskPackage.task = video_task
                #         taskPackage.packagename = db_package
                #         taskPackage.save()
                #     except ObjectDoesNotExist:
                #         packagePriority = models.PackagePriority()
                #         packagePriority.packagename = packagename
                #         packagePriority.save()
                #         taskPackage = models.TaskPackage()
                #         taskPackage.task = video_task
                #         taskPackage.packagename = packagePriority
                #         taskPackage.save()

                # save new size
                print("save new size")
                video_task.size = after_size
                video_task.save()
                task._make_image_meta_cache(db_task)

                video_seg = models.Segment.objects.select_for_update().get(task_id=video_tid)
                video_seg.stop_frame = after_size-1
                video_seg.save()

                # update exist frame with tid
                print("update exist frame with tid")
                db_framenames = models.FrameName.objects.select_for_update().filter(task_id=video_tid).order_by('-name')
                for db_framename in db_framenames:
                    before_frame = db_framename.frame
                    before_name = db_framename.name
                    if not before_name.endswith('.png'):
                        before_name += '.png'

                    after_index = insertedImages.index(os.path.join(realvideopath[0], before_name))
                    print('video {} update {} to {}'.format(video_tid, before_frame, after_index))
                    if after_index != before_frame:
                        # framename
                        db_framename.frame = after_index
                        db_framename.save()
                        # keyframe
                        db_keyframe = _FrameUserRecordModel.objects.select_for_update().get(task_id=video_tid, frame=before_frame)
                        db_keyframe.frame = after_index
                        db_keyframe.save()
                        #box
                        models.LabeledBox.objects.select_for_update().filter(job_id=video_tid, frame=before_frame).update(frame=after_index)
        print("done")

        if len(not_do_paths):
            response = {'data':not_do_paths}
            return JsonResponse(response, safe=False)
        else:
            response = {'data':"Success insert_frames"}
            return JsonResponse(response, safe=False)

    except Exception as e:
        print("error is !!!!",str(e))
        return HttpResponseBadRequest(str(e))


# Add by Eric
@login_required
@transaction.atomic
@permission_required('engine.add_task', raise_exception=True)
def upload_keyframe(request):
    """Upload keyframe"""
    try:
        params = request.POST.dict()
        project = params['project']
        data_list = request.FILES.getlist('data')

        if len(data_list) != 1:
            raise Exception('just select a json file')

        data_content = ''
        for chunk in data_list[0].chunks():
            data_content += chunk.decode('utf-8')
        
        dictKeyframe = json.loads(data_content) # {packagename, video1, video2}
        packagename = dictKeyframe['packagename']

        _ProjectModel = get_ProjectModel(project)
        _FrameUserRecordModel = get_FrameUserRecordModel(project)

        has_update_video = []
        no_update_video = []


        project_tids = list(_ProjectModel.objects.all().values_list('task_id', flat=True))
        print('project_tids',project_tids)

        for sVideoName in dictKeyframe.keys():
            if sVideoName == 'packagename': # process pass packagename
                continue

            if type(dictKeyframe[sVideoName]) == int: # change a frame to [frame]
                dictKeyframe[sVideoName] = [dictKeyframe[sVideoName]]

            db_task = None
            try:
                print('sVideoName',sVideoName)
                db_task = models.Task.objects.select_for_update().get(id__in=project_tids, name=sVideoName)
            except ObjectDoesNotExist:
                no_update_video.append({'video':sVideoName, 'frame':'all', 'reason':'video not exist'})
                continue

            #add package
            history_packagenames = list(db_task.taskpackage_set.all().values_list('packagename__packagename', flat=True))
            if not packagename in history_packagenames:
                try:
                    db_package = models.PackagePriority.objects.get(packagename=packagename)
                    taskPackage = models.TaskPackage()
                    taskPackage.task = db_task
                    taskPackage.packagename = db_package
                    taskPackage.save()
                except ObjectDoesNotExist:
                    packagePriority = models.PackagePriority()
                    packagePriority.packagename = packagename
                    packagePriority.save()
                    taskPackage = models.TaskPackage()
                    taskPackage.task = db_task
                    taskPackage.packagename = packagePriority
                    taskPackage.save()

            tid = db_task.id
            start_time = time.time()
            dictRealToFrame = {} # {realframe:linkframe}
            root = db_task.get_data_dirname()

            for subDir in sorted(os.listdir(root)):
                subRoot = os.path.join(root,subDir)
                for subDir_sec in sorted(os.listdir(subRoot)):
                    subRoot_sec = os.path.join(subRoot,subDir_sec)
                    for mfile in sorted(os.listdir(subRoot_sec)):
                        mfile_path = os.path.join(subRoot_sec,mfile)
                        frame = int(os.path.splitext(mfile)[0])
                        realname = os.path.basename(os.path.realpath(mfile_path))
                        realframe = int(os.path.splitext(realname)[0][-4:])
                        dictRealToFrame[realframe] = frame
            print("--- create dictRealToFrame cost %s seconds ---" % (time.time() - start_time))

            for nFrameStr in dictKeyframe[sVideoName]:
                if sVideoName == 'packagename':
                    continue

                listTaskKeyframeExist = list(_FrameUserRecordModel.objects.filter(task_id=tid).values_list('frame', flat=True))
                nFrameNumber = dictRealToFrame[int(nFrameStr)]
                
                if nFrameNumber in listTaskKeyframeExist:
                    print(nFrameNumber, 'Aleady is keyframe')
                    no_update_video.append({'video':sVideoName, 'frame':str(nFrameStr), 'index':str(nFrameNumber), 'reason':'frame was exist'})
                    continue
                
                

                db_frameUserRecord = new_FrameUserRecordObject(project)
                db_frameUserRecord.task = db_task
                db_frameUserRecord.frame = nFrameNumber
                db_frameUserRecord.packagename = packagename
                db_frameUserRecord.save()

                db_project = _ProjectModel.objects.select_for_update().get(task_id=tid)
                db_project.keyframe_count += 1
                db_project.save()

                path = os.path.realpath(task.get_frame_path(tid, nFrameNumber))
                realname = os.path.splitext(os.path.basename(path))[0]
                db_FrameName = models.FrameName()
                db_FrameName.task = db_task
                db_FrameName.frame = nFrameNumber
                db_FrameName.name = realname
                db_FrameName.save()

                print("tid:{} frame:{} is add".format(tid,nFrameNumber))

        if len(no_update_video):
            response = {'data':no_update_video}
            return JsonResponse(response, safe=False)
        else:
            response = {'data':"Success update frames"}
            return JsonResponse(response, safe=False)
 
    except Exception as e:

        print("error is !!!!",str(e))
        return HttpResponseBadRequest(str(e))


# Add by Jeff
@login_required
@transaction.atomic
@permission_required('engine.add_task', raise_exception=True)
def upload_Label(request):
    """ use labelme xml, in apa ldws """

    print('doing label')
    try:
        params = request.POST.dict()
        listLabelfile = request.POST.getlist('data')
        share_root = settings.SHARE_ROOT

        _ProjectModel = get_ProjectModel(params['project'])
        _FrameUserRecordModel = get_FrameUserRecordModel(params['project'])


        project_tids = list(_ProjectModel.objects.all().values_list('task_id', flat=True))

        print('listLabelfile',listLabelfile)
        not_do_paths = []
        for sLabelpath in listLabelfile:
            relpath = os.path.normpath(sLabelpath).lstrip('/')
            if '..' in relpath.split(os.path.sep):
                raise Exception('Permission denied')
            abspath = os.path.abspath(os.path.join(share_root, relpath))
            if os.path.commonprefix([share_root, abspath]) != share_root:
                raise Exception('Bad file path on share: ' + abspath)

            print('abspath',abspath)
            print('target_paths',relpath)

            
            
            if params['project'] == 'apacorner':
                Camaras = ['TopLeft','TopLeft_full','TopRight','TopRight_full','TopRear','TopRear_full']
                for camara in Camaras:
                    xmls_list = glob.glob('{}/{}/*.{}'.format(abspath,camara,'xml'))
                    if xmls_list:
                        tid = None
                        videoname = os.path.basename(abspath) + "_" + camara
                        print(videoname)
                        try:
                            db_task = models.Task.objects.select_for_update().get(name=videoname, id__in=project_tids)
                            tid = db_task.id
                        except ObjectDoesNotExist:
                            not_do_paths.append({'path':videoname, 'reason':'not found video in data'})
                            continue

                        dictRealToFrame = {} # {realframe:linkframe}
                        root = db_task.get_data_dirname()
                        start_time = time.time()

                        for subDir in sorted(os.listdir(root)):
                            subRoot = os.path.join(root,subDir)
                            for subDir_sec in sorted(os.listdir(subRoot)):
                                subRoot_sec = os.path.join(subRoot,subDir_sec)
                                for mfile in sorted(os.listdir(subRoot_sec)):
                                    mfile_path = os.path.join(subRoot_sec,mfile)
                                    frame = int(os.path.splitext(mfile)[0])
                                    realname = os.path.basename(os.path.realpath(mfile_path))
                                    realframe = int(os.path.splitext(realname)[0][-4:])
                                    dictRealToFrame[realframe] = frame
                        print("--- create dictRealToFrame cost %s seconds ---" % (time.time() - start_time))
                        print(dictRealToFrame)

                        listTaskKeyframeExist = list(_FrameUserRecordModel.objects.filter(task_id=tid).values_list('frame', flat=True))
                        
                        db_project = _ProjectModel.objects.select_for_update().get(task_id=tid)
                        db_project.save()

                        print('has xmls_list')
                        for xml in xmls_list:
                            nFrameNumber = dictRealToFrame[int(os.path.splitext(xml)[0][-4:])]
                            
                            if not nFrameNumber in listTaskKeyframeExist:
                                print(nFrameNumber, 'not is keyframe')
                                not_do_paths.append({'video':xml, 'frame':str(nFrameNumber), 'reason':'frame not exist'})
                                continue

                            file_objects = parseXML.parseFile(params['project'], xml)
                            print('xml',xml)
                            print(file_objects)
                            dictData = {"boxes":[],"box_paths":[],"points":[],"points_paths":[],
                                        "polygons":[],"polygon_paths":[],"polylines":[],"polyline_paths":[]}


                            attributesID = {} #name to id, label_id
                            
                            for sDb_attr in models.AttributeSpec.objects.filter(label__task__id=tid):
                                attributesID[sDb_attr.get_name()] = [int(sDb_attr.id), int(sDb_attr.label_id)]

                            for s_obj_id in file_objects:
                                obj_id = int(s_obj_id)
                                isPolygon = True if file_objects[s_obj_id]['points'].count(' ') > 2 else False
                                item = {}
                                item['points'] = file_objects[s_obj_id]['points']
                                item['occluded'] = file_objects[s_obj_id]['occluded']
                                item['z_order'] = file_objects[s_obj_id]['z_order']
                                
                                item['attributes'] = [{'id':attributesID['大標'][0],'value':file_objects[s_obj_id]['name'].replace(' ','_')},
                                                        {'id':attributesID['小標'][0],'value':str(list(filter(None,file_objects[s_obj_id]['attributes'].split(','))))}]
                                item['label_id'] = attributesID['大標'][1]
                                item['group_id'] = 0
                                item['grouping'] = ','.join(file_objects[s_obj_id]['grouping'])
                                item['obj_id'] = obj_id
                                item['frame'] = nFrameNumber

                                print('will save item',item)

                                if isPolygon:
                                    dictData["polygons"].append(item)
                                else:
                                    dictData["polylines"].append(item)
                                

                            if request.user.groups.filter(name='admin').exists():
                                print('Save xml Job', "Tid:",tid, " Frame:", nFrameNumber)
                                annotation.save_job(tid, dictData, oneFrameFlag=True,frame=nFrameNumber)
                            else:
                                # annotation.save_job(nTid, dictData,oneFrameFlag=True,frame=current_frame)
                                print("You cant save if you're not admin.")
                                pass
                        print('------------------')
                    else:
                        print('no xmls_list')
            elif params['project'] == 'dms_training':
                csvs_list = glob.glob('{}/*.{}'.format(abspath,'csv'))

                if csvs_list:
                    tid = None
                    videoname = os.path.basename(abspath)
                    print(videoname)

                    try:
                        db_task = models.Task.objects.select_for_update().get(name=videoname, id__in=project_tids)
                        tid = db_task.id
                    except ObjectDoesNotExist:
                        not_do_paths.append({'path':abspath, 'reason':'not found video in data'})
                        continue

                    dictRealToFrame = {} # {realframe:linkframe}
                    root = db_task.get_data_dirname()
                    start_time = time.time()

                    for subDir in sorted(os.listdir(root)):
                        subRoot = os.path.join(root,subDir)
                        for subDir_sec in sorted(os.listdir(subRoot)):
                            subRoot_sec = os.path.join(subRoot,subDir_sec)
                            for mfile in sorted(os.listdir(subRoot_sec)):
                                mfile_path = os.path.join(subRoot_sec,mfile)
                                frame = int(os.path.splitext(mfile)[0])
                                realname = os.path.basename(os.path.realpath(mfile_path))
                                realframe = int(os.path.splitext(realname)[0][-4:])
                                dictRealToFrame[realframe] = frame
                    print("--- create dictRealToFrame cost %s seconds ---" % (time.time() - start_time))

                    listTaskKeyframeExist = list(_FrameUserRecordModel.objects.filter(task_id=tid).values_list('frame', flat=True))

                    EN_to_CH = {'face':'臉', 'nose':'鼻子', 'mouth':'嘴巴', 'cheek':'臉頰',
                                'eye_left':'左眼睛', 'eye_right':'右眼睛', 'brow_left':'左眉毛', 'brow_right':'右眉毛'}

                    #add package

                    history_packagenames = list(db_task.taskpackage_set.all().values_list('packagename__packagename', flat=True))
                    

                    print('has csvs_list')
                    for a_csv in csvs_list:
                        print('a_csv',a_csv)
                        frame_str = os.path.splitext(os.path.basename(a_csv))[0][-4:]
                        nFrameNumber = dictRealToFrame[int(frame_str)]
                        packagename = os.path.basename(os.path.dirname(os.path.dirname(a_csv)))
                        if nFrameNumber in listTaskKeyframeExist:
                            print(nFrameNumber, 'was keyframe')
                            not_do_paths.append({'path':a_csv, 'frame':str(frame_str), 'index':str(nFrameNumber), 'reason':'frame was exist'})
                            continue
                        if not packagename in history_packagenames:
                            try:
                                db_package = models.PackagePriority.objects.get(packagename=packagename)
                                taskPackage = models.TaskPackage()
                                taskPackage.task = db_task
                                taskPackage.packagename = db_package
                                taskPackage.save()
                            except ObjectDoesNotExist:
                                packagePriority = models.PackagePriority()
                                packagePriority.packagename = packagename
                                packagePriority.save()
                                taskPackage = models.TaskPackage()
                                taskPackage.task = db_task
                                taskPackage.packagename = packagePriority
                                taskPackage.save()

                            history_packagenames.append(packagename)

                        db_frameName = models.FrameName()
                        db_frameName.task = db_task
                        db_frameName.frame = nFrameNumber
                        db_frameName.name = os.path.splitext(os.path.basename(a_csv))[0]
                        db_frameName.save()

                        db_frameUserRecord = new_FrameUserRecordObject(params['project'])
                        db_frameUserRecord.task = db_task
                        db_frameUserRecord.frame = nFrameNumber
                        db_frameUserRecord.packagename = packagename
                        db_frameUserRecord.save()


                        file_objects = read_DMS_CSV.parseFile(params['project'], a_csv)
                        dictData = {"boxes":[],"box_paths":[],"points":[],"points_paths":[],
                                    "polygons":[],"polygon_paths":[],"polylines":[],"polyline_paths":[]}
                        

                        attributesID = {} #name to id, label_id
                        labelAtt = {}
                        for sDb_attr in models.AttributeSpec.objects.filter(label__task__id=tid):
                            if not sDb_attr.label.name in attributesID:
                                attributesID[sDb_attr.label.name] = {}
                            attributesID[sDb_attr.label.name][sDb_attr.get_name().lower()] = [int(sDb_attr.id), int(sDb_attr.label_id)]
                        
                        n_zorder = 1
                        for obj in file_objects:
                            obj_id = int(obj['id'])
                            obj_label_name = obj['Type']
                            isBox = True if obj_label_name == '臉' else False

                            item = {}
                            obj['Points'] = obj['Points'].strip()
                            if isBox:
                                pointTL, pointBR = obj['Points'].split(' ')
                                pointTL_x, pointTL_y = pointTL.split(',')
                                pointBR_x, pointBR_y = pointBR.split(',')
                                item['xtl'] = float(pointTL_x)
                                item['ytl'] = float(pointTL_y)
                                item['xbr'] = float(pointBR_x)
                                item['ybr'] = float(pointBR_y)
                            else:
                                # doing
                                item['points'] = obj['Points']

                            item['occluded'] = False
                            item['z_order'] = n_zorder
                            n_zorder += 1

                            item['attributes'] = []
                            
                            if obj['Rotation'] != '-1':
                                item['attributes'].append({'id':attributesID[obj_label_name]['rotation'][0], 'value':obj['Rotation']})
                                item['label_id'] = attributesID[obj_label_name]['rotation'][1]

                            if obj['Pitch'] != '-1':
                                item['attributes'].append({'id':attributesID[obj_label_name]['pitch'][0], 'value':obj['Pitch']})
                                item['label_id'] = attributesID[obj_label_name]['pitch'][1]
                            
                            if obj['Occluded'] != '-1':
                                item['attributes'].append({'id':attributesID[obj_label_name]['occluded'][0], 'value':obj['Occluded']})
                                item['label_id'] = attributesID[obj_label_name]['occluded'][1]

                            if obj['Key_face'] != '-1':
                                item['attributes'].append({'id':attributesID[obj_label_name]['key_face'][0], 'value':obj['Key_face']})
                                item['label_id'] = attributesID[obj_label_name]['key_face'][1]


                            item['group_id'] = 0
                            item['grouping'] = obj['grouping']
                            item['obj_id'] = obj_id
                            item['frame'] = nFrameNumber

                            print('will save item',item)

                            if isBox:
                                dictData["boxes"].append(item)
                            else:
                                dictData["points"].append(item)
                        print('a_csv parse done')

                        db_project = _ProjectModel.objects.select_for_update().get(task_id=tid)
                        db_project.keyframe_count = _FrameUserRecordModel.objects.filter(task_id=tid).count()
                        db_project.save()


                        if request.user.groups.filter(name='admin').exists():
                            print('Save a_csv Job', "Tid:",tid, " Frame:", nFrameNumber, 'dictData ', dictData)
                            annotation.save_job(tid, dictData, oneFrameFlag=True,frame=nFrameNumber)
                            print('Save a_csv done')
                        else:
                            # annotation.save_job(nTid, dictData,oneFrameFlag=True,frame=current_frame)
                            print("You cant save if you're not admin.")
                            pass
                else:
                    not_do_paths.append({'path':abspath, 'reason':'not found csv'})
                    print('no csvs_list')
        
        if len(not_do_paths):
            return JsonResponse({'data':not_do_paths})
        else:
            print("Upload End.")
            return JsonResponse({'data':"success"})

    except Exception as e:
        print('error',str(e))
        return HttpResponseBadRequest(str(e))


# Add by Eric
@login_required
@transaction.atomic
@permission_required('engine.add_task', raise_exception=True)
def upload_CSV(request, a_bIgnore_not_keyframe=True):
    """Upload CSV"""
    try:
        listCSVfile = request.POST.getlist('data')

        sShare_Root = settings.SHARE_ROOT
        fileSetting = r'/home/django/cvat/dump_data/FCW_Setting_training20181210.ini'

        listABSfile = []
        
        oCSVcontainer = upload_CSV_container()
        oCSVcontainer.Read_Setting_files(a_Setting_file=fileSetting)

        for sCSVpath in listCSVfile:

            fileCSV_uploadpath = os.path.normpath(sCSVpath).lstrip('/')
            fileCSV_abs_uploadpath = os.path.abspath(os.path.join(sShare_Root, fileCSV_uploadpath))

            fileTaskName = os.path.basename(fileCSV_abs_uploadpath)

            if fileTaskName.endswith(".csv"):
                continue

            for root, dirs, files in os.walk(fileCSV_abs_uploadpath):
                fileRoot = root
                for fileCSV in files:
                    if not fileCSV.endswith(".csv"):
                        continue
                    if (not fileCSV.startswith("key_")):  # prevent bug for no root path
                        continue
                    if 'VideoParam' in fileCSV:
                        continue
                    fileCSV_Abspath = os.path.join(fileRoot, fileCSV)

                    listABSfile.append(fileCSV_Abspath)

        listABSfile = list(set(listABSfile))

        listPackage_name = []
        project = None
        print("Input files")
        print(listABSfile)
        print("Start Reading")
        for sfile in listABSfile:
            
            if 'FCW_Train' in sfile:
                project = 'fcw_training'
            if 'FCW_Test' in sfile:
                project = 'fcw_testing'
            if 'BSD_Train' in sfile:
                project = 'bsd_training'

            sPackage_name = os.path.basename(os.path.dirname(os.path.dirname(sfile)))

            if sPackage_name not in listPackage_name:
                listPackage_name.append(sPackage_name)

            oCSVcontainer.Reading_CSV(a_sCSV_path=sfile)

        print(project, "project name!!!")
        print(listPackage_name, "listPackage_name!!!")
        assert project is not None
        assert len(listPackage_name) == 1
        
        sPackagename = listPackage_name[0]

        _ProjectModel = get_ProjectModel(project)
        _FrameUserRecordModel = get_FrameUserRecordModel(project)

        project_tids = list(_ProjectModel.objects.all().values_list('task_id', flat=True))

        oCSVcontainer.Get_Task_ID(a_listTask_ID=project_tids)
        oCSVcontainer.Get_db_labels_ID()
        oCSVcontainer.Get_Attribute_ID()

        oCSVcontainer.Import_FrameMap(a_listProject_TIDs=project_tids)
        oCSVcontainer.Convert_CSV2Server(a_bIgnore_not_keyframe=a_bIgnore_not_keyframe)
        # print(oCSVcontainer.i_dictSever_Bbox)
        
        for nTid in oCSVcontainer.i_dictSever_Bbox.keys():

            sVideoName = oCSVcontainer.i_dictID_Taskname[nTid]  

            db_task = models.Task.objects.select_for_update().filter(id__in=project_tids, name=sVideoName)[0]

            #add package
            history_packagenames = list(db_task.taskpackage_set.all().values_list('packagename__packagename', flat=True))
            if not sPackagename in history_packagenames:
                try:
                    db_package = models.PackagePriority.objects.get(packagename=sPackagename)
                    taskPackage = models.TaskPackage()
                    taskPackage.task = db_task
                    taskPackage.packagename = db_package
                    taskPackage.save()
                except ObjectDoesNotExist:
                    packagePriority = models.PackagePriority()
                    packagePriority.packagename = sPackagename
                    packagePriority.save()
                    taskPackage = models.TaskPackage()
                    taskPackage.task = db_task
                    taskPackage.packagename = packagePriority
                    taskPackage.save()

            print("Packagename save", sPackagename, " History packagenames", history_packagenames)    

            db_Model = _ProjectModel.objects.select_for_update().get(task_id=nTid)     

            for nframe in oCSVcontainer.i_dictSever_Bbox[nTid].keys():

                print(nframe, "database_frame")
                dictData = oCSVcontainer.i_dictSever_Bbox[nTid][nframe]

                # Also, set uploadframe as keyframe.
                qs = _FrameUserRecordModel.objects.select_for_update().filter(task_id=nTid,frame=nframe)

                if len(qs) == 0:

                    if a_bIgnore_not_keyframe:
                        qs_name = models.FrameName.objects.select_for_update().filter(task_id=nTid,frame=nframe)

                        if len(qs_name) == 0:
                            db_frameName = models.FrameName()
                            db_frameName.task_id = nTid
                            db_frameName.frame = nframe
                            db_frameMap = oCSVcontainer.i_dictFrameMap[sVideoName]
                            nReal_Frame = list(db_frameMap.keys())[list(db_frameMap.values()).index(nframe)]
                            db_frameName.name = (sVideoName + "_%04d")%(nReal_Frame)
                            db_frameName.save()  
                            print("db_frameName", " Tid: ",nTid, " DataBaseFrame: ", nframe)                  

                    db_frameUserRecord = new_FrameUserRecordObject(project)
                    db_frameUserRecord.task = db_task
                    db_frameUserRecord.frame = nframe

                    db_frameUserRecord.packagename = sPackagename
                    db_frameUserRecord.save()  

                    db_Model.keyframe_count = _FrameUserRecordModel.objects.filter(task_id=nTid).count()
                    # db_Model.priority = 0
                    # db_Model.priority_out = 0
                    db_Model.save()

                    if request.user.groups.filter(name='admin').exists():
                        print('Save CSV Job', "Tid:",nTid, " Frame:", nframe)
                        annotation.save_job(nTid, dictData, oneFrameFlag=True,frame=nframe)
                    else:
                        # annotation.save_job(nTid, dictData,oneFrameFlag=True,frame=current_frame)
                        print("You cant save if you're not admin.")
                        pass

            print("Upload CSV End.")

        print("ALL done")

        return JsonResponse({'data':"success"})
    except RequestException as e:
        job_logger[nTid].error("cannot send annotation logs for job {}".format(nTid), exc_info=True)
        return HttpResponseBadRequest(str(e))
    except Exception as e:
        job_logger[nTid].error("cannot save annotation for job {}".format(nTid), exc_info=True)
        return HttpResponseBadRequest(str(e))
 




@login_required
@permission_required('engine.add_task', raise_exception=True)
def create_task(request):
    """Create a new annotation task"""
    db_task = None
    params = request.POST.dict()
    params['owner'] = request.user
    global_logger.info("create task with params = {}".format(params))
    try:
        PROJECT_FOLDER = ['/FCW_Train/','/FCW_Test/','/LVSA_Train/','/LVSA_Test/','/APA_Corner/','/APA_Segment/','/LDWS/']
        share_root = settings.SHARE_ROOT

        target_paths = []
        source_paths = []

        _ProjectModel = get_ProjectModel(params['project'])

        # if models.PackagePriority.objects.filter(packagename=params['task_packagename']).count() > 0:
        #     print('Packagename was exist')
        #     raise Exception('Packagename was exist')
        # else:
        #     packagePriority = models.PackagePriority()
        #     packagePriority.packagename = params['task_packagename']
        #     packagePriority.save()

        if params['storage'] == 'share':
            data_list = request.POST.getlist('data')
            data_list.sort(key=len)
            createList = []
            createNameList = []
            createTidList = []
            passList = []

            for share_path in data_list:
                relpath = os.path.normpath(share_path).lstrip('/')
                if '..' in relpath.split(os.path.sep):
                    raise Exception('Permission denied')
                abspath = os.path.abspath(os.path.join(share_root, relpath))
                if os.path.commonprefix([share_root, abspath]) != share_root:
                    raise Exception('Bad file path on share: ' + abspath)

                print('abspath',abspath)
                print('target_paths',relpath)
                


                if params['project'] in ['fcw_training','bsd_training','dms_training']:
                    imgs_list = glob.glob('{}/*.{}'.format(abspath,'png'))
                    if imgs_list:
                        task_name = os.path.basename(abspath)

                        tids = _ProjectModel.objects.all().values_list('task_id', flat=True)
                        exist_count = models.Task.objects.filter(name=task_name, id__in=tids).count()
                        print('tids,exist_count',tids,exist_count)
                        if exist_count == 1:
                            passList.append(abspath)
                            continue
                        if exist_count > 1:
                            passList.append(abspath + ', more_{}'.format(exist_count))
                            continue
                        if task_name in createNameList:
                            passList.append(abspath + ', is exist in your created task_name: {}'.format(task_name))
                            continue

                        params['task_name'] = task_name
                        db_task = task.create_empty(params)
                        upload_dir = db_task.get_upload_dirname()

                        target_paths = []
                        source_paths = []

                        source_paths.append(abspath)
                        target_paths.append(os.path.join(upload_dir, relpath))
                        print('source_paths',source_paths)
                        print('target_paths',target_paths)

                        params['SOURCE_PATHS'] = source_paths
                        params['TARGET_PATHS'] = target_paths
                        task.create(db_task.id, params)
                        createList.append(task_name + ', ' + abspath)
                        createNameList.append(task_name)
                        createTidList.append(db_task.id)
                
                if params['project'] == 'apacorner':

                    Camaras = ['TopLeft','TopLeft_full','TopRight','TopRight_full','TopRear','TopRear_full']
                    for camara in Camaras:

                        imgs_list = glob.glob('{}/{}/*.{}'.format(abspath,camara,'png'))

                        print('imgs_list ',imgs_list)
                        if imgs_list:
                            task_name = os.path.basename(abspath) + '_{}'.format(camara)

                            tids = models.APACorner.objects.all().values_list('task_id', flat=True)

                            print('task_name',task_name)
                            print('tids',tids)
                            exist_count = models.Task.objects.filter(name=task_name, id__in=tids).count()

                            print('exist_count',exist_count)
                            if exist_count == 1:
                                passList.append(os.path.join(abspath,camara))
                                continue
                            if exist_count > 1:
                                passList.append(os.path.join(abspath,camara) + ' more_{}'.format(exist_count))
                                continue
                            if task_name in createNameList:
                                passList.append(os.path.join(abspath,camara) + ', is exist in your created task_name: {}'.format(task_name))
                                continue

                            params['task_name'] = task_name
                            db_task = task.create_empty(params)
                            upload_dir = db_task.get_upload_dirname()

                            target_paths = []
                            source_paths = []

                            source_paths.append(os.path.join(abspath, camara))
                            target_paths.append(os.path.join(*[upload_dir, relpath, camara]))
                            print('source_paths',source_paths)
                            print('target_paths',target_paths)

                            params['SOURCE_PATHS'] = source_paths
                            params['TARGET_PATHS'] = target_paths
                            task.create(db_task.id, params)
                            createList.append(os.path.join(abspath,camara))
                            createNameList.append(task_name)
                            createTidList.append(db_task.id)

            return JsonResponse({'createList':{'names':createList,'tids':createTidList},'passList':passList})

        else:

            db_task = task.create_empty(params)
            target_paths = []
            source_paths = []
            upload_dir = db_task.get_upload_dirname()
            data_list = request.FILES.getlist('data')

            if len(data_list) > settings.LOCAL_LOAD_MAX_FILES_COUNT:
                raise Exception('Too many files. Please use download via share')
            common_size = 0
            for f in data_list:
                common_size += f.size
            if common_size > settings.LOCAL_LOAD_MAX_FILES_SIZE:
                raise Exception('Too many size. Please use download via share')

            for data_file in data_list:
                source_paths.append(data_file.name)
                path = os.path.join(upload_dir, data_file.name)
                target_paths.append(path)
                with open(path, 'wb') as upload_file:
                    for chunk in data_file.chunks():
                        upload_file.write(chunk)

            params['SOURCE_PATHS'] = source_paths
            params['TARGET_PATHS'] = target_paths

            task.create(db_task.id, params)
            return JsonResponse({'createList':{'tids':[db_task.id]}})

        
    except Exception as exc:
        global_logger.error("cannot create task {}".format(params['task_name']), exc_info=True)
        db_task.delete()
        return HttpResponseBadRequest(str(exc))

    return JsonResponse({'tid': db_task.id})

@login_required
@permission_required('engine.view_task', raise_exception=True)
def check_task(request, tid):
    """Check the status of a task"""

    try:
        global_logger.info("check task #{}".format(tid))
        response = task.check(tid)
        response['tid'] = tid
    except Exception as e:
        global_logger.error("cannot check task #{}".format(tid), exc_info=True)
        return HttpResponseBadRequest(str(e))

    return JsonResponse(response)

@login_required
@permission_required('engine.view_task', raise_exception=True)
def get_frame(request, tid, frame):
    """Stream corresponding from for the task"""

    try:
        # Follow symbol links if the frame is a link on a real image otherwise
        # mimetype detection inside sendfile will work incorrectly.
        path = os.path.realpath(task.get_frame_path(tid, frame))
        return sendfile(request, path)
    except Exception as e:
        task_logger[tid].error("cannot get frame #{}".format(frame), exc_info=True)
        return HttpResponseBadRequest(str(e))

@login_required
@permission_required('engine.delete_task', raise_exception=True)
def delete_task(request, tid):
    """Delete the task"""
    try:
        global_logger.info("delete task #{}".format(tid))
        if not task.is_task_owner(request.user, tid):
            return HttpResponseBadRequest("You don't have permissions to delete the task.")

        task.delete(tid)
    except Exception as e:
        global_logger.error("cannot delete task #{}".format(tid), exc_info=True)
        return HttpResponseBadRequest(str(e))

    return HttpResponse()

@login_required
@permission_required('engine.change_task', raise_exception=True)
def update_task(request, tid):
    """Update labels for the task"""
    try:
        task_logger[tid].info("update task request")
        if not task.is_task_owner(request.user, tid):
            return HttpResponseBadRequest("You don't have permissions to change the task.")

        labels = request.POST['labels']
        task.update(tid, labels)
    except Exception as e:
        task_logger[tid].error("cannot update task", exc_info=True)
        return HttpResponseBadRequest(str(e))

    return HttpResponse()

@login_required
@permission_required(perm='engine.view_task', raise_exception=True)
def get_task(request, tid):
    try:
        task_logger[tid].info("get task request")
        response = task.get(tid)
    except Exception as e:
        task_logger[tid].error("cannot get task", exc_info=True)
        return HttpResponseBadRequest(str(e))

    return JsonResponse(response, safe=False)

@login_required
@permission_required(perm=['engine.view_task', 'engine.view_annotation'], raise_exception=True)
def get_job(request, jid):
    try:
        job_logger[jid].info("get job #{} request".format(jid))
        response = task.get_job(jid)
    except Exception as e:
        job_logger[jid].error("cannot get job #{}".format(jid), exc_info=True)
        return HttpResponseBadRequest(str(e))

    return JsonResponse(response, safe=False)

@login_required
@permission_required(perm=['engine.view_task', 'engine.view_annotation'], raise_exception=True)
def dump_annotation(request, tid):
    try:
        task_logger[tid].info("dump annotation request")
        annotation.dump(tid, annotation.FORMAT_XML, request.scheme, request.get_host())
    except Exception as e:
        task_logger[tid].error("cannot dump annotation", exc_info=True)
        return HttpResponseBadRequest(str(e))

    return HttpResponse()

@login_required
@gzip_page
@permission_required(perm=['engine.view_task', 'engine.view_annotation'], raise_exception=True)
def check_annotation(request, tid):
    try:
        task_logger[tid].info("check annotation")
        response = annotation.check(tid)
    except Exception as e:
        task_logger[tid].error("cannot check annotation", exc_info=True)
        return HttpResponseBadRequest(str(e))

    return JsonResponse(response)


@login_required
@gzip_page
@permission_required(perm=['engine.view_task', 'engine.view_annotation'], raise_exception=True)
def download_annotation(request, tid):
    try:
        task_logger[tid].info("get dumped annotation")
        db_task = models.Task.objects.get(pk=tid)
        response = sendfile(request, db_task.get_dump_path(), attachment=True,
            attachment_filename='{}_{}.xml'.format(db_task.id, db_task.name))
    except Exception as e:
        task_logger[tid].error("cannot get dumped annotation", exc_info=True)
        return HttpResponseBadRequest(str(e))

    return response


@login_required
@gzip_page
@permission_required(perm=['engine.view_task', 'engine.view_annotation'], raise_exception=True)
def get_annotation(request, jid):
    try:
        job_logger[jid].info("get annotation for {} job".format(jid))
        #change by jeff
        project = list(filter(None, request.path.split('/')))[0]
        response = annotation.get(jid, project=project, requestUser=request.user)
        
    except Exception as e:
        job_logger[jid].error("cannot get annotation for job {}".format(jid), exc_info=True)
        return HttpResponseBadRequest(str(e))

    return JsonResponse(response, safe=False)

@login_required
@gzip_page
@permission_required(perm=['engine.view_task', 'engine.view_annotation'], raise_exception=True)
def get_annotation_frame(request, jid, frame):
    try:
        job_logger[jid].info("get annotation for {} job".format(jid))
        #change by jeff
        project = list(filter(None, request.path.split('/')))[0]
        response = annotation.get(jid, project=project, requestUser=request.user,frame=frame)
        
    except Exception as e:
        job_logger[jid].error("cannot get annotation for job {}".format(jid), exc_info=True)
        return HttpResponseBadRequest(str(e))

    return JsonResponse(response, safe=False)

@login_required
@permission_required(perm=['engine.view_task', 'engine.change_annotation'], raise_exception=True)
def save_annotation_for_job(request, jid):
    try:
        job_logger[jid].info("save annotation for {} job".format(jid))
        data = json.loads(request.body.decode('utf-8'))
        if 'annotation' in data:
            if request.user.groups.filter(name='admin').exists():
                annotation.save_job(jid, json.loads(data['annotation']),oneFrameFlag=True,frame=data['current_frame'])
            else:
                
                project = list(filter(None, request.path.split('/')))[0]
                if project == 'fcw_training':
                    with transaction.atomic():
                        print('save before select_for_update')
                        user_record = models.TaskFrameUserRecord.objects.select_for_update().get(user=request.user.username,current=True)
                        # print ("user: {} find current {}".format(request.user.username,user_record.frame))
                        if user_record.need_modify:
                            print('save before need_modify')
                            user_record.userModifySave_date = timezone.now()
                            print('save aa need_modify')
                        else:
                            print('save before userSave_date')
                            user_record.userSave_date = timezone.now()
                            print('save aa userSave_date')
                        user_record.save()
                elif project == 'fcw_testing':
                    pass

                print('save before save_job')
                annotation.save_job(jid, json.loads(data['annotation']),oneFrameFlag=True,frame=data['current_frame'])
                  
        if 'logs' in data:
            for event in json.loads(data['logs']):
                job_client_logger[jid].info(json.dumps(event))
    except RequestException as e:
        job_logger[jid].error("cannot send annotation logs for job {}".format(jid), exc_info=True)
        return HttpResponseBadRequest(str(e))
    except Exception as e:
        job_logger[jid].error("cannot save annotation for job {}".format(jid), exc_info=True)
        return HttpResponseBadRequest(str(e))

    return HttpResponse()


@login_required
@permission_required(perm=['engine.view_task', 'engine.change_annotation'], raise_exception=True)
def save_annotation_for_task(request, tid):
    try:
        task_logger[tid].info("save annotation request")
        data = json.loads(request.body.decode('utf-8'))
        annotation.save_task(tid, data)
    except Exception as e:
        task_logger[tid].error("cannot save annotation", exc_info=True)
        return HttpResponseBadRequest(str(e))

    return HttpResponse()

@login_required
def get_username(request):
    client_ip, is_routable = get_client_ip(request)
    response = {'username': request.user.username,'ip':client_ip}
    return JsonResponse(response, safe=False)

@login_required
def get_isAdmin(request):
    response = {'isAdmin': request.user.groups.filter(name='admin').exists()}
    return JsonResponse(response, safe=False)

def rq_handler(job, exc_type, exc_value, tb):
    job.exc_info = "".join(traceback.format_exception_only(exc_type, exc_value))
    job.save()
    module = job.id.split('.')[0]
    if module == 'task':
        return task.rq_handler(job, exc_type, exc_value, tb)
    elif module == 'annotation':
        return annotation.rq_handler(job, exc_type, exc_value, tb)

    return True


# add by jeff
@login_required
@transaction.atomic
@permission_required('engine.add_task', raise_exception=True)
def set_frame_isKeyFrame(request, tid, frame, flag):
    try:
        project = list(filter(None, request.path.split('/')))[0]

        _ProjectModel = get_ProjectModel(project)
        _FrameUserRecordModel = get_FrameUserRecordModel(project)


        if project in ['fcw_training','bsd_training']:
            print('project is',project)
            keyframe_full_name = ''
            db_project = _ProjectModel.objects.select_for_update().get(task_id=tid)
            if flag:
                db_task = models.Task.objects.select_for_update().get(pk=tid)
                db_frameUserRecord = new_FrameUserRecordObject(project)
                db_frameUserRecord.task = db_task
                db_frameUserRecord.frame = frame
                db_frameUserRecord.packagename = 'default'
                db_frameUserRecord.save()
                
                db_project.keyframe_count += 1
                # db_project.priority = 0
                # db_project.priority_out = 0
                db_project.save()

                path = os.path.realpath(task.get_frame_path(tid, frame))
                print('realpath is ', path)
                realname = os.path.basename(path).replace(".png", "")
                keyframe_full_name = realname
                db_FrameName = models.FrameName()
                db_FrameName.task = db_task
                db_FrameName.frame = frame
                db_FrameName.name = realname
                db_FrameName.save()

                print("tid:{} frame:{} is add".format(tid,frame))
            else:
                try:
                    keyframe = _FrameUserRecordModel.objects.get(task_id=tid,frame=frame)
                    keyframe.delete()
                    realname = models.FrameName.objects.get(task_id=tid,frame=frame)
                    realname.delete()

                    db_project.keyframe_count -= 1
                    db_project.checked_count = _FrameUserRecordModel.objects.filter(task_id=tid,checked=True).count()
                    db_project.unchecked_count = _FrameUserRecordModel.objects.filter(task_id=tid,user_submit=True).count()
                    db_project.need_modify_count = _FrameUserRecordModel.objects.filter(task_id=tid,need_modify=True).count()
                    db_project.save()

                except ObjectDoesNotExist:
                    print("tid:{} frame:{} is delete".format(tid,frame))

            qs = _FrameUserRecordModel.objects.select_for_update().filter(task_id=tid)
            frames = qs.values_list('frame', flat=True)
            print(list(frames))
            return JsonResponse({'frames': list(frames), 'full_name': keyframe_full_name}, safe=False)

        elif project in ['fcw_testing', 'apacorner','dms_training']:
            print('project is',project)
            qs = _FrameUserRecordModel.objects.select_for_update().filter(task_id=tid)
            frames = qs.values_list('frame', flat=True)
            print(list(frames),'but test not show ')
            return JsonResponse({'frames': []}, safe=False)
    except Exception as e:
        print("error is !!!!",str(e))
        return HttpResponseBadRequest(str(e))

@login_required
@transaction.atomic
@permission_required('engine.view_task', raise_exception=True)
def get_frame_isKeyFrame(request, tid, frame):
    try: 
        response = None
        try:
            keyframe = models.TaskFrameUserRecord.objects.select_for_update().get(task_id=tid,frame=frame)
            response = {'isKeyFrame': True}
        except ObjectDoesNotExist:
            response = {'isKeyFrame': False}

        return JsonResponse(response, safe=False)
    except Exception as e:
        print("error is !!!!",str(e))
        return HttpResponseBadRequest(str(e))


@login_required
@transaction.atomic
@permission_required('engine.view_task', raise_exception=True)
def get_keyFrame_stage(request, tid, frame):
    try:
        project = list(filter(None, request.path.split('/')))[0]
        _ProjectModel = get_ProjectModel(project)
        _FrameUserRecordModel = get_FrameUserRecordModel(project)

        response = None
        if project in ['fcw_training', 'bsd_training']:
            keyframe = _FrameUserRecordModel.objects.select_for_update().get(task_id=tid,frame=frame)
            response = {
                'annotator': keyframe.user,
                'current': keyframe.current,
                'user_submit': keyframe.user_submit,
                'need_modify': keyframe.need_modify,
                'checked': keyframe.checked,
                'comment': keyframe.comment
            }
        elif project in ['fcw_testing', 'apacorner', 'dms_training']:
            keyframe = _FrameUserRecordModel.objects.select_for_update().get(task_id=tid,frame=frame)
            video_user = _ProjectModel.objects.select_for_update().get(task_id=tid).user
                
            response = {
                'annotator': video_user,
                'current': keyframe.current,
                'user_submit': keyframe.user_submit,
                'need_modify': keyframe.need_modify,
                'checked': keyframe.checked,
                'comment': keyframe.comment
            }
        if response:
            return JsonResponse(response, safe=False)
        else:
            return HttpResponseBadRequest("no get_keyFrame_stage")
    except Exception as e:
        print("error is !!!!",str(e))
        return HttpResponseBadRequest(str(e))

@login_required
@transaction.atomic
@permission_required('engine.add_task', raise_exception=True)
def set_frame_isComplete(request, tid, frame, flag):
    try:
        project = list(filter(None, request.path.split('/')))[0]

        _ProjectModel = get_ProjectModel(project)
        _FrameUserRecordModel = get_FrameUserRecordModel(project)

        keyframe = None
        db_project = None
        qs_project = None

        keyframe = _FrameUserRecordModel.objects.select_for_update().get(task_id=tid,frame=frame)
        db_project = _ProjectModel.objects.select_for_update().get(task_id=tid)

        if flag:
            keyframe.checker = request.user.username
            keyframe.checked = True
            keyframe.checked_date = timezone.now()
            keyframe.user_submit = False
            keyframe.save()
            print("tid:{} frame:{} is Complete".format(tid,frame))
        else:
            keyframe.checker = request.user.username
            keyframe.checked = False
            keyframe.user_submit = True
            keyframe.save()

        db_project.checked_count = _FrameUserRecordModel.objects.filter(task_id=tid,checked=True).count()
        db_project.unchecked_count = _FrameUserRecordModel.objects.filter(task_id=tid,user_submit=True).count()
        db_project.need_modify_count = _FrameUserRecordModel.objects.filter(task_id=tid,need_modify=True).count()
        db_project.save()

        response = {'frame': frame,'isComplete':flag}
        return JsonResponse(response, safe=False)
    except Exception as e:
        print("error is !!!!",str(e))
        return HttpResponseBadRequest(str(e))

@login_required
@transaction.atomic
@permission_required('engine.add_task', raise_exception=True)
def set_job_isComplete(request, tid, flag):
    try:
        project = list(filter(None, request.path.split('/')))[0]

        _ProjectModel = get_ProjectModel(project)
        db_project = _ProjectModel.objects.select_for_update().get(task_id=tid)

        if flag:
            db_project.checker = request.user.username
            db_project.checked = True
            db_project.checked_date = timezone.now()
            db_project.user_submit = False
            db_project.save()
            print("tid:{} is Complete".format(tid))
        else:
            db_project.checker = request.user.username
            db_project.checked = False
            db_project.user_submit = True
            db_project.save()

        response = {'job': tid,'isComplete':flag}
        return JsonResponse(response, safe=False)
    except Exception as e:
        print("error is !!!!",str(e))
        return HttpResponseBadRequest(str(e))

@login_required
@transaction.atomic
@permission_required('engine.add_task', raise_exception=True)
def set_frame_isRedo(request, tid, frame, flag):
    try:
        
        project = list(filter(None, request.path.split('/')))[0]

        _ProjectModel = get_ProjectModel(project)
        _FrameUserRecordModel = get_FrameUserRecordModel(project)

        keyframe = None
        db_project = None
        qs_project = None

        keyframe = _FrameUserRecordModel.objects.select_for_update().get(task_id=tid,frame=frame)
        db_project = _ProjectModel.objects.select_for_update().get(task_id=tid)

        if flag:
            keyframe.checker = request.user.username
            keyframe.need_modify = True
            keyframe.need_modify_date = timezone.now()
            keyframe.user_submit = False
            keyframe.save()
            print("tid:{} frame:{} is Redo".format(tid,frame))
        else:
            keyframe.checker = request.user.username
            keyframe.need_modify = False
            keyframe.user_submit = True
            keyframe.save()

        db_project.checked_count = _FrameUserRecordModel.objects.filter(task_id=tid,checked=True).count()
        db_project.unchecked_count = _FrameUserRecordModel.objects.filter(task_id=tid,user_submit=True).count()
        db_project.need_modify_count = _FrameUserRecordModel.objects.filter(task_id=tid,need_modify=True).count()
        db_project.save()

        response = {'frame': frame,'isRedo':flag}
        return JsonResponse(response, safe=False)
    except Exception as e:
        print("error is !!!!",str(e))
        return HttpResponseBadRequest(str(e))

@login_required
@transaction.atomic
@permission_required('engine.add_task', raise_exception=True)
def set_job_isRedo(request, tid, flag):
    try:
        project = list(filter(None, request.path.split('/')))[0]

        _ProjectModel = get_ProjectModel(project)        
        db_project = _ProjectModel.objects.select_for_update().get(task_id=tid)

        if flag:
            db_project.checker = request.user.username
            db_project.need_modify = True
            db_project.need_modify_date = timezone.now()
            db_project.user_submit = False
            db_project.save()
            print("tid:{} is Redo".format(tid))
        else:
            db_project.checker = request.user.username
            db_project.need_modify = False
            db_project.user_submit = True
            db_project.save()

        response = {'job': tid,'isRedo':flag}
        return JsonResponse(response, safe=False)
    except Exception as e:
        print("error is !!!!",str(e))
        return HttpResponseBadRequest(str(e))

@login_required
@transaction.atomic
@permission_required('engine.add_task', raise_exception=True)
def set_frame_redoComment(request, tid, frame, comment):
    try:
        if comment == 'ok':
            comment = ''
        project = list(filter(None, request.path.split('/')))[0]

        _ProjectModel = get_ProjectModel(project)
        _FrameUserRecordModel = get_FrameUserRecordModel(project)

        keyframe = _FrameUserRecordModel.objects.select_for_update().get(task_id=tid,frame=frame)
        
        keyframe.checker = request.user.username
        keyframe.comment = comment
        keyframe.save()
        print("tid:{} frame:{} is Redo".format(tid,frame))

        response = {'frame': frame,'comment':comment}
        return JsonResponse(response, safe=False)
    except Exception as e:
        print("error is !!!!",str(e))
        return HttpResponseBadRequest(str(e))

## will not use
@login_required
@transaction.atomic
@permission_required('engine.add_task', raise_exception=True)
def set_tasks_priority(request):
    """Create a new annotation task"""
    try:
         db_task = None
        # params = request.POST.dict()
        # priority = params['priority']
        # inCompany = params['inCompany']
        # project = params['project']

        # _ProjectModel = get_ProjectModel(project)
        # _FrameUserRecordModel = get_FrameUserRecordModel(project)

        # print('project', project)

        # inCompany = True if inCompany == 'true' else False

        # print('inCompany',inCompany,'priority',priority)

        # if(params['selectTasks'] != ''):
        #     tasks = params['selectTasks'].split(',')
        #     for tid in tasks:
        #         db_project = _ProjectModel.objects.select_for_update().get(task_id=int(tid))
        #         if inCompany:
        #             print('db_project.priority = priority')
        #             db_project.priority = priority
        #         else:
        #             print('db_project.priority_out = priority')
        #             db_project.priority_out = priority
        #         db_project.save()

    except Exception as e:
        print("error is !!!!",str(e))
        return HttpResponseBadRequest(str(e))

    return JsonResponse({'data':params}, safe=False)

# add by eric
@login_required
@transaction.atomic
@permission_required('engine.add_task', raise_exception=True)
def set_Video_Catogory(request, tid, catogory):
    try:
        task = models.Task.objects.select_for_update().get(pk=tid)
        task.category = catogory
        task.save()
    except Exception as e:
        print("error is !!!!",str(e))
        return HttpResponseBadRequest(str(e))

    return JsonResponse("success.", safe=False)


@login_required
@transaction.atomic
@permission_required('engine.add_task', raise_exception=True)
def set_task_nickname(request, tid, nickname):
    try:
        if nickname == 'default' :
            nickname = ''
        task = models.Task.objects.select_for_update().get(pk=tid)
        task.nickname = nickname
        task.save()
    except Exception as e:
        print("error is !!!!",str(e))
        return HttpResponseBadRequest(str(e))

    return JsonResponse({'nickname':nickname}, safe=False)

# add by jeff, but not use
@login_required
def get_FCW_Job(request):
    try: 
        response = None

        # db_userRecord = None
        # try:
        #     db_userRecord = models.TaskFrameUserRecord.objects.get(user=request.user.username,current=True)
        #     response = {'jid': db_userRecord.task.id}
        #     return JsonResponse(response, safe=False)
        # except ObjectDoesNotExist:
        #     pass
            

        # db_fcwTrains = models.FCWTrain.objects.filter(~Q(priority=0)).order_by('-priority', 'task__created_date')
        # print ("db_fcwTrains,",db_fcwTrains)
        # print ("len  db_fcwTrains,",len(db_fcwTrains))
        # db_fcwTrain = db_fcwTrains.first()

        # if db_fcwTrain:
        #     print("~Q(undo=0),Q(priority=1)",db_fcwTrain.priority)
        #     response = {'jid': db_fcwTrain.task.id}
        # else:
        #     response = None
        #     raise Exception('no priority > 0!') 
        
        # return JsonResponse(response, safe=False)
    except Exception as e:
        print("error is !!!!",str(e))
        return HttpResponseBadRequest(str(e))


# add by jeff
@login_required
@permission_required(perm=['engine.view_task', 'engine.change_annotation'], raise_exception=True)
def save_currentJob(request):
    try:        
       
        user_record = None
        tid = None # use taskid

        project = list(filter(None, request.path.split('/')))[0]

        _ProjectModel = get_ProjectModel(project)
        _FrameUserRecordModel = get_FrameUserRecordModel(project)
        
        if project in ['fcw_training','bsd_training']:
            try:
                with transaction.atomic():
                    user_record = _FrameUserRecordModel.objects.select_for_update().get(user=request.user.username,current=True)
                    tid = user_record.task_id
                    print ("user: {} find current {}".format(request.user.username,user_record.frame))
                    user_record.current = False
                    user_record.user_submit = True
                    
                    if user_record.need_modify:
                        user_record.userModifySubmit_date = timezone.now()
                    else:
                        user_record.userSubmit_date = timezone.now()

                    user_record.need_modify = False
                    user_record.save()

                print ("user: {}'s user_record.save()".format(request.user.username))
            except ObjectDoesNotExist:
                print ("user: {}'s not found current frame".format(request.user.username))
                raise Exception('user_record is None')
        elif project in ['fcw_testing', 'apacorner', 'dms_training']:
            try:
                with transaction.atomic():
                    user_record = _ProjectModel.objects.select_for_update().get(user=request.user.username,current=True)
                    tid = user_record.task_id
                    print ("user: {} find current {}".format(request.user.username,tid))
                    user_record.current = False
                    user_record.user_submit = True
                    
                    if user_record.need_modify:
                        user_record.userModifySubmit_date = timezone.now()
                    else:
                        user_record.userSubmit_date = timezone.now()

                    user_record.need_modify = False
                    user_record.save()

                print ("user: {}'s user_record.save()".format(request.user.username))
            except ObjectDoesNotExist:
                print ("user: {}'s not found current frame".format(request.user.username))
                raise Exception('user_record is None')

        db_project = None
        qs_project = None
        with transaction.atomic():
            db_project = _ProjectModel.objects.select_for_update().get(task_id=tid)

            db_project.checked_count = _FrameUserRecordModel.objects.filter(task_id=tid,checked=True).count()
            db_project.unchecked_count = _FrameUserRecordModel.objects.filter(task_id=tid,user_submit=True).count()
            db_project.need_modify_count = _FrameUserRecordModel.objects.filter(task_id=tid,need_modify=True).count()
            db_project.save()

        return JsonResponse({'data':"success"})

    except Exception as e:
        print("error is !!!!",str(e))
        job_logger[jid].error("cannot set {} currnet for {} job".format(request.user.username,jid), exc_info=True)
        return HttpResponseBadRequest(str(e))

# add by jeff
@login_required
@transaction.atomic
@permission_required('engine.view_task', raise_exception=True)
def get_currentJob(request):
    try:
        project = list(filter(None, request.path.split('/')))[0]

        # find current jid, job
        # if no current return no current
        #    js will ask user get new job ? yes or not
        jid = None
        job = None
        data = None

        user_record = None
        try:
            if project == 'fcw_training':
                user_record = models.TaskFrameUserRecord.objects.select_for_update().get(user=request.user.username,current=True)
            elif project == 'fcw_testing':
                user_record = models.FCWTest.objects.select_for_update().get(user=request.user.username,current=True)
            elif project == 'apacorner':
                user_record = models.APACorner.objects.select_for_update().get(user=request.user.username,current=True)
            elif project == 'dms_training':
                user_record = models.DMSTrain.objects.select_for_update().get(user=request.user.username,current=True)
            jid = user_record.task_id
        except ObjectDoesNotExist:
            return JsonResponse("you need to get new work", safe=False)

        try:
            job_logger[jid].info("get job #{} request".format(jid))
            job = task.get_job(jid)
        except Exception as e:
            job_logger[jid].error("cannot get job #{}".format(jid), exc_info=True)
            return HttpResponseBadRequest(str(e))

        try:
            job_logger[jid].info("get annotation for {} job".format(jid))
            data = annotation.get(jid, project=project, requestUser=request.user)
        except Exception as e:
            job_logger[jid].error("cannot get annotation for job {}".format(jid), exc_info=True)
            return HttpResponseBadRequest(str(e))

        return JsonResponse({'project':project,'jid':jid,'job':job,'data':data}, safe=False)

    except Exception as e:
        print("error is !!!!",str(e))
        return HttpResponseBadRequest(str(e))

def set_currentWithJob(username,qs=None,time=None):
    new_jid = None
    if qs:
        try:
            new_jid = qs.task_id
            qs.user = username
            qs.current = True
            if time == 'modify':
                qs.userModifyGet_date = timezone.now()
            if time == 'new':
                qs.userGet_date = timezone.now()
            qs.save()
        except ObjectDoesNotExist:
            print("error in set_currentWithJob tid:{}".format(qs.task_id))
    return qs, new_jid

# add by jeff
@login_required
@transaction.atomic
@permission_required('engine.view_task', raise_exception=True)
def set_currentJob(request):
    try:
        project = list(filter(None, request.path.split('/')))[0]

        _ProjectModel = get_ProjectModel(project)
        _FrameUserRecordModel = get_FrameUserRecordModel(project)

        username = request.user.username.lower()
        user_record = None
        new_jid = None

        user_priority = None
        user_priority_sec = None
        user_workSpace = None
        if username.startswith('oto',0,3):
            user_priority = {'task__taskpackage__packagename__office_priority':0,}#{'office_priority':0,}
            user_priority_sec = {'office_priority':0,}
        else:
            user_priority = {'task__taskpackage__packagename__soho_priority':0,}#{'soho_priority':0,}
            user_priority_sec = {'soho_priority':0,}
        user_priority_key = list(user_priority.keys())[0]

        user_workSpace = {'username':request.user.username, 'project':project}
        #task_id_list = list(_ProjectModel.objects.values_list('task_id', flat=True))
        try:
            print('user_workSpace',user_workSpace)

            real_can_use_packagenames = list(models.PackagePriority.objects.filter(~Q(**user_priority_sec)).values_list('packagename',flat=True))
            packagenames = list(models.UserWorkSpace.objects.filter(**user_workSpace).values_list('packagename',flat=True))
            packagenames = list(set(packagenames)&set(real_can_use_packagenames))
            print('packagenames',packagenames)

            if len(packagenames) == 0:
                return JsonResponse({'status':"A01",'text':"你沒被分配到工作, 請聯絡管理員哦"})
            # query = functools.reduce(operator.or_, (Q(packagename__icontains = item) for item in packagenames))
            # task_id_list = models.Task.objects.filter(query).values_list('id',flat=True)
        except ObjectDoesNotExist:
            return JsonResponse({'status':"A01",'text':"你沒被分配到工作, 請聯絡管理員哦"})

        # tids = list(models.TaskPackage.objects.filter(Q(task_id__in=task_id_list),Q(packagename__packagename__in=packagenames),~Q(**user_priority2)).order_by('-packagename__{}'.format(user_priority_key)).values_list('task_id',flat=True))
        # tids = sorted(tids)

        if project in ['fcw_training','bsd_training']:
            start_time = time.time()
            tids = list(_ProjectModel.objects.filter(Q(task__taskpackage__packagename__packagename__in=packagenames),~Q(**user_priority)).order_by('-{}'.format(user_priority_key)).values_list('task_id',flat=True))
            print('tids',tids)
            if tids:
                for tid in tids:
                    tmp_tid = tid
                    with transaction.atomic():
                        qs = _FrameUserRecordModel.objects.select_for_update().filter(task_id=tmp_tid,user=request.user.username,need_modify=True,packagename__in=packagenames)
                        ids = list(qs.values_list('id', flat=True))
                        print('ids',ids)
                        if len(ids):
                            index = random.randint(0, len(ids)-1)
                            try:
                                user_record = qs[index]
                                new_jid = tmp_tid

                                user_record.user = request.user.username
                                user_record.current = True
                                user_record.userModifyGet_date = timezone.now()
                                user_record.save()
                                break
                            except ObjectDoesNotExist:
                                print("error in set_currentJob fcw_training modify")
                                user_record = None
                                new_jid = None
            end_time = time.time()
            print ("use random pk cost time : ",(end_time - start_time))
            if user_record:
                print ("get modify is success job",new_jid,user_record.frame)
            else:
                print("need modify is none, try get new frame")
                start_time = time.time()
                # db_projects = _ProjectModel.objects.filter(Q(task_id__in=task_list) & ~Q(**user_priority)).order_by('-{}'.format(list(user_priority.keys())[0]), 'task__created_date')
                # print ("db_projects,",db_projects)
                # print ("len  db_projects,",len(db_projects))
                # if db_projects and len(db_projects):
                # maybe can pass search again
                tids = list(_ProjectModel.objects.filter(Q(task__taskpackage__packagename__packagename__in=packagenames),~Q(**user_priority)).order_by('-{}'.format(user_priority_key)).values_list('task_id',flat=True))
                if tids:
                    for tid in tids:
                    # print ("db_projects has {} data".format(len(db_projects)))
                    # for db_project in db_projects:
                        tmp_tid = tid
                        with transaction.atomic():
                            qs = _FrameUserRecordModel.objects.select_for_update().filter(task_id=tmp_tid,user='',packagename__in=packagenames)
                            ids = list(qs.values_list('id', flat=True))
                            print('ids',ids)
                            if len(ids):
                                index = random.randint(0, len(ids)-1)
                                try:
                                    user_record = qs[index]
                                    new_jid = tmp_tid

                                    user_record.user = request.user.username
                                    user_record.current = True
                                    user_record.userGet_date = timezone.now()
                                    user_record.save()
                                    break
                                except ObjectDoesNotExist:
                                    user_record = None
                                    new_jid = None
                end_time = time.time()
                print ("use random pk cost time : ",(end_time - start_time))
            if user_record:
                print ("try get new is success job",new_jid,user_record.frame)
            else:
                return JsonResponse({'status':"A01",'text':"找不到{}的工作, 請聯絡管理員哦".format(project)})

        elif project in ['fcw_testing', 'apacorner', 'dms_training']:
            #task_id_list = list(_ProjectModel.objects.filter(Q(user=request.user.username) & Q(need_modify=True)).values_list('task_id', flat=True))
            start_time = time.time()
            #db_Project = _ProjectModel.objects.filter(~Q(**user_priority) & Q(user=request.user.username) & Q(need_modify=True)).order_by('-{}'.format(list(user_priority.keys())[0]), 'task__created_date')
            db_Project = _ProjectModel.objects.filter(Q(need_modify=True),Q(task__taskpackage__packagename__packagename__in=packagenames),~Q(**user_priority)).order_by('-{}'.format(user_priority_key)).first()
            user_record, new_jid = set_currentWithJob(request.user.username, db_Project, time='modify')
            end_time = time.time()
            print ("use random pk cost time : ",(end_time - start_time))
            
            if user_record is None:
                print("need modify is none, try get new frame")
                start_time = time.time()
                db_Project = _ProjectModel.objects.filter(Q(userGet_date=None),Q(task__taskpackage__packagename__packagename__in=packagenames),~Q(**user_priority)).order_by('-{}'.format(user_priority_key)).first()
                user_record, new_jid = set_currentWithJob(request.user.username, db_Project, time='new')
                end_time = time.time()
                print ("use random pk cost time : ",(end_time - start_time))
                
            if user_record:
                print ("try get new Assign is success job",new_jid)
            else:
                print("need modify is none, try get new frame")
                start_time = time.time()
                db_Project = _ProjectModel.objects.filter(Q(user=''),Q(task__taskpackage__packagename__packagename__in=packagenames),~Q(**user_priority)).order_by('-{}'.format(user_priority_key)).first()
                user_record, new_jid = set_currentWithJob(request.user.username, db_Project, time='new')
                end_time = time.time()
                print ("use random pk cost time : ",(end_time - start_time))
            
            if user_record:
                print ("try get new Empty is success job",new_jid)
            else:
                return JsonResponse({'status':"A01",'text':"找不到{}的工作, 請聯絡管理員哦".format(project)})

    except Exception as e:
        user_record = None
        print("error is !!!!",str(e))
        job_logger[new_jid].error("cannot set {} currnet for {} job".format(request.user.username,new_jid), exc_info=True)
        return HttpResponseBadRequest(str(e))
        
    if user_record:
        print ("have current")
        job_logger[new_jid].info("set {} currnet for {} job".format(request.user.username,new_jid))
        return JsonResponse({'jid':new_jid})
    else:
        print ("user_record is None, will error")
        return JsonResponse({'status':"A01",'text':"找不到任何的工作, 請聯絡管理員哦"})


# add by jeff, but not use
@login_required
def get_FCW_Job_Name(request, tid):
    try: 
        db_task = models.Task.objects.get(pk=tid)
        if db_task:
            return JsonResponse({'task_name':db_task.name}, safe=False)
    except Exception as e:
        print("error is !!!!",str(e))
        return JsonResponse({'task_name':"Error"}, safe=False)

@login_required
@transaction.atomic
@permission_required('engine.view_task', raise_exception=True)
def get_keyFrames(request, tid):
    try:
        project = list(filter(None, request.path.split('/')))[0]
        
        if project == 'fcw_training':
            qs = models.TaskFrameUserRecord.objects.select_for_update().filter(task_id=tid)
            frames = qs.values_list('frame', flat=True)
            return JsonResponse({'frames': list(frames)}, safe=False)
        elif project in ['fcw_testing', 'apacorner', 'dms_training']:
            print(project,'no show keyframe')
            return JsonResponse({'frames': []}, safe=False)
    except Exception as e:
        print("error is !!!!",str(e))
        return HttpResponseBadRequest(str(e))

@login_required
@transaction.atomic
@permission_required('engine.add_task', raise_exception=True)
def get_next_task(request):
    try:
        project = list(filter(None, request.path.split('/')))[0]
        if project != 'bsd_training':
            raise Exception('u can not do it')

        _ProjectModel = get_ProjectModel(project)

        project_tids = list( _ProjectModel.objects.filter(~Q(keyframe_count=F('checked_count'))).values_list('task_id', flat=True))
        recods = models.Task.objects.filter(id__in=project_tids).order_by('name')
        if recods.count() > 0:
            return JsonResponse({'next_tid': recods[0].id}, safe=False)
        else:
            raise Exception('no video')

    except Exception as e:
        print("error is !!!!",str(e))
        return HttpResponseBadRequest(str(e))


###################################
# add by ericlou
class upload_CSV_container:
    def __init__(self):
        self.i_dictItemStrMap = {}
        self.i_dictIDItemMap = {}      
        self.i_dictCSV_webType = {}  

        self.i_dictID_attributes = {}
        self.i_dictTaskname_ID = {}
        self.i_dictID_Taskname = {}

        self.i_dictTaskID_labelID = {}
        self.i_dictTaskname_Frame_BBoxInfor = {}

        self.i_dictSever_Bbox = {}

        self.i_dictFrameMap = {}

    def Read_Setting_files(self, a_Setting_file):

        sFilename = a_Setting_file

        with io.open(sFilename, 'r') as file:
            for listline in file:
                if 'Item' in listline:
                    if '_ID' in listline:
                        nIDNum = int(listline.strip().split('=')[-1])
                        nItemNum = int((listline.strip().split('Item')[-1].split('_ID=')[0]))
                        self.i_dictIDItemMap[nIDNum] = nItemNum
                    else:
                        nItemNum = int(listline.strip().split('Item')[-1].split('=')[0])
                        sItemStr = listline.strip().split('=')[-1]
                        self.i_dictItemStrMap[nItemNum] = sItemStr

                if 'SubType' in listline:
                    break

        self.i_dictCSV_webType = {'的car':"car", #的car
                                '的motorbike':"motorBike", #的MotorBike
                                '的truck':"truck", #的truck
                                  
                                '的bus':"bus", #的bus
                                '的bike':"Bike", #的bike
                                '的van':"van", #的van
        
                                '的代步車':'代步車', #的代步車
                                '的工程車':'工程車', #的工程車
                                '的有殼三輪車':'有殼三輪車', #的有殼三輪車
                                '的無殼三輪車':'無殼三輪車' #的無殼三輪車                                  
        }

    def Reading_CSV(self, a_sCSV_path):
        
        sTask_name = os.path.basename(a_sCSV_path)
        sTask_name = sTask_name.replace("key_", "").replace(".csv", "")
        sTask_name = sTask_name.split('_')

        nframe = int(sTask_name[-1])
        sTask_name = '_'.join(sTask_name[:-1])

        if sTask_name not in self.i_dictTaskname_ID.keys():
            self.i_dictTaskname_ID[sTask_name] = []

        distBBoxSave = self.i_dictTaskname_Frame_BBoxInfor

        if sTask_name not in distBBoxSave.keys():
            distBBoxSave[sTask_name] = {}
        if nframe not in distBBoxSave[sTask_name].keys():
            distBBoxSave[sTask_name][nframe] = {}
            distBBoxSave[sTask_name][nframe]['ID']=[]
            distBBoxSave[sTask_name][nframe]['Type']=[]
            distBBoxSave[sTask_name][nframe]['tl_x']=[]
            distBBoxSave[sTask_name][nframe]['tl_y']=[]
            distBBoxSave[sTask_name][nframe]['br_x']=[]
            distBBoxSave[sTask_name][nframe]['br_y']=[]
            distBBoxSave[sTask_name][nframe]['Rotation']=[]
            distBBoxSave[sTask_name][nframe]['Occluded']=[]
            distBBoxSave[sTask_name][nframe]['Truncated']=[]
            distBBoxSave[sTask_name][nframe]['DontCare']=[]
            distBBoxSave[sTask_name][nframe]['LinkedID']=[]

        with open(a_sCSV_path, "r") as fileCSV:
            fileCSVreaded = csv.reader(fileCSV)
            for listRow in fileCSVreaded:
                if listRow[0] == 'Version':
                    continue

                distBBoxSave[sTask_name][nframe]['ID'].append(listRow[1])
                distBBoxSave[sTask_name][nframe]['Type'].append(listRow[2])
                distBBoxSave[sTask_name][nframe]['tl_x'].append(listRow[5])
                distBBoxSave[sTask_name][nframe]['tl_y'].append(listRow[6])
                distBBoxSave[sTask_name][nframe]['br_x'].append(listRow[7])
                distBBoxSave[sTask_name][nframe]['br_y'].append(listRow[8])
                distBBoxSave[sTask_name][nframe]['Rotation'].append(listRow[16])
                distBBoxSave[sTask_name][nframe]['Occluded'].append(listRow[17])
                distBBoxSave[sTask_name][nframe]['Truncated'].append(listRow[18])
                distBBoxSave[sTask_name][nframe]['DontCare'].append(listRow[19])
                distBBoxSave[sTask_name][nframe]['LinkedID'].append(listRow[24])

        print("Reading CSV done.")

    def Get_Task_ID(self, a_listTask_ID):
        
        for sVideoDate in self.i_dictTaskname_ID.keys():

            oDB_task = models.Task.objects.select_for_update().filter(id__in=a_listTask_ID, name=sVideoDate)[0]
            nTid = int(oDB_task.id)
            print(nTid, "ASDASDASFWEQW")
            self.i_dictTaskname_ID[sVideoDate] = nTid
            self.i_dictID_Taskname[nTid] = sVideoDate

        print("Get_Task_ID done.")

    def Get_db_labels_ID(self):

        for nTid in self.i_dictTaskname_ID.values():
            
            db_task = models.Task.objects.select_for_update().get(id=nTid)
            test_db_labels = db_task.label_set.all().prefetch_related('attributespec_set')

            for db_label in test_db_labels:

                if nTid not in self.i_dictTaskID_labelID.keys():
                    self.i_dictTaskID_labelID[nTid] = db_label.id

        print(self.i_dictTaskID_labelID)

    def Get_Attribute_ID(self):

        for sVideoDate in self.i_dictTaskname_ID.keys():

            nTid = self.i_dictTaskname_ID[sVideoDate]

            if nTid not in self.i_dictID_attributes.keys():
                self.i_dictID_attributes[nTid] = {}
            
            for sDb_attr in models.AttributeSpec.objects.filter(label__task__id=nTid):
                self.i_dictID_attributes[nTid][sDb_attr.get_name()] = int(sDb_attr.id)

        print("Get_Attribute_ID done.")

    def Import_FrameMap(self, a_listProject_TIDs):

        for sVideoName in self.i_dictTaskname_Frame_BBoxInfor.keys():

            db_task = models.Task.objects.select_for_update().filter(id__in=a_listProject_TIDs, name=sVideoName)[0]

            if sVideoName not in self.i_dictFrameMap.keys():
                self.i_dictFrameMap[sVideoName] = {}

            TaskRoot = db_task.get_data_dirname()
            print(TaskRoot, "TaskRoot")
            for subDir in sorted(os.listdir(TaskRoot)):
                subRoot = os.path.join(TaskRoot, subDir)
                for subDir_sec in sorted(os.listdir(subRoot)):
                    subRoot_sec = os.path.join(subRoot, subDir_sec)
                    for mfile in sorted(os.listdir(subRoot_sec)):
                        mfile_path = os.path.join(subRoot_sec, mfile)
                        frame = int(os.path.splitext(mfile)[0])
                        realname = os.path.basename(os.path.realpath(mfile_path))
                        realframe = int(os.path.splitext(realname)[0][-4:])
                        self.i_dictFrameMap[sVideoName][realframe] = frame

        print(self.i_dictFrameMap, "dictRealToFrame")       


    def Convert_CSV2Server(self, a_bIgnore_not_keyframe=True):

        print("Convert_CSV2Server Start.")

        for sVideoName in self.i_dictTaskname_Frame_BBoxInfor.keys():
            
            nTid = self.i_dictTaskname_ID[sVideoName]

            if nTid not in self.i_dictSever_Bbox.keys():
                self.i_dictSever_Bbox[nTid] = {}    

            listFrameNumber = list(self.i_dictTaskname_Frame_BBoxInfor[sVideoName].keys())
            listFrameNumber.sort()

            for nframe in listFrameNumber:
                
                print("Start to Convert VideoName", sVideoName, "FrameNumber", nframe)

                dictBBoxFrameInfor = self.i_dictTaskname_Frame_BBoxInfor[sVideoName][nframe]

                if a_bIgnore_not_keyframe: # for only save keyframe in database
                    nframe_in_db = self.i_dictFrameMap[sVideoName][nframe]

                if nframe_in_db not in self.i_dictSever_Bbox[nTid].keys():
                    self.i_dictSever_Bbox[nTid][nframe_in_db] = {'boxes':[],'points': [], 'polygons': [], 
                    'points_paths': [], 'box_paths': [], 'polygon_paths': [], 'polylines': [], 'polyline_paths': []}    

                # Get Linked information first
                dictLinkedID_objIndex = {}
                
                for nIndex in range(0, len(dictBBoxFrameInfor['ID'])):
                    
                    sLinkedID = str(dictBBoxFrameInfor['LinkedID'][nIndex])

                    if sLinkedID != '-1': 
                        # dont need to create carside as one BBox in Server
                        # put CareSide in Next Loop
                        if sLinkedID not in dictLinkedID_objIndex.keys():
                            dictLinkedID_objIndex[sLinkedID] = nIndex

                nZorder = 1

                for nIndex in range(0, len(dictBBoxFrameInfor['ID'])):
                    
                    sID = str(dictBBoxFrameInfor['ID'][nIndex])
                    if sID == '0':
                        continue

                    sLinkedID = str(dictBBoxFrameInfor['LinkedID'][nIndex])
                    
                    if sLinkedID != '-1': 
                        continue                    
                    
                    nType = int(dictBBoxFrameInfor['Type'][nIndex])
                    sTl_x = dictBBoxFrameInfor['tl_x'][nIndex]
                    sTl_y = dictBBoxFrameInfor['tl_y'][nIndex]
                    sBr_x = dictBBoxFrameInfor['br_x'][nIndex]
                    sBr_y = dictBBoxFrameInfor['br_y'][nIndex]

                    sRotation = dictBBoxFrameInfor['Rotation'][nIndex]
                    nOccluded = int(dictBBoxFrameInfor['Occluded'][nIndex])
                    sTruncated = str(dictBBoxFrameInfor['Truncated'][nIndex])

                    sDontCare = dictBBoxFrameInfor['DontCare'][nIndex]
                    
                    ## Rotation
                    nNew_Rotation = str(round(float(sRotation) /math.pi * float(180)))
                    
                    ## Occluded
                    if nOccluded == 0:
                        sNew_Occluded = 'Fully_Visible'
                    elif nOccluded == 1:
                        sNew_Occluded = 'Partly_Occluded'
                    elif nOccluded == 2:
                        sNew_Occluded = 'Largely_Occluded'
                    elif nOccluded == 3:
                        sNew_Occluded = 'Unknow'

                    ## DontCare
                    if int(sDontCare) == 1:
                        bNew_DontCare = True
                    elif int(sDontCare) == 0:
                        bNew_DontCare = False

                    ## Type Convert            
                    if nType not in self.i_dictIDItemMap:
                        continue
                    sSTR_Type = self.i_dictItemStrMap[int(self.i_dictIDItemMap[nType])]

                    ## 有開燈
                    bLight_state = False
                    if '有開燈' in sSTR_Type:
                        bLight_state = True
                    
                    ## 有障礙物的
                    bObstacle = False
                    if '有障礙物的' in sSTR_Type:
                        bObstacle = True

                    # Match type to get type in Server
                    listMatch = self.i_dictCSV_webType.keys()

                    for sSTR_Match in listMatch:
                        if sSTR_Match in sSTR_Type:  
                            sSTR_Type = self.i_dictCSV_webType[sSTR_Match]
                            continue
                    
                    # for lower problem in setting files
                    sSTR_Type = sSTR_Type.replace('motorbike', "motorBike")
                    sSTR_Type = sSTR_Type.replace('pedestrian', "Pedestrian")
                    sSTR_Type = sSTR_Type.replace('personsitting', "PersonSitting")
                    sSTR_Type = sSTR_Type.replace('misc', 'Misc')
                    sSTR_Type = sSTR_Type.replace('background', 'Background')
                    sSTR_Type = sSTR_Type.replace('tram', 'Tram')

                    ## for Linked_ID
                    ## 完全不見的車頭
                    bCheckCarSide = False
                    sCarSidePoint = "-1,-1,-1,-1"
                    
                    if sID in dictLinkedID_objIndex.keys(): # have CarSide
                        nLink_ID_Index = int(dictLinkedID_objIndex[sID])
                        
                        sLink_Type = int(dictBBoxFrameInfor['Type'][nLink_ID_Index])

                        ## Type Convert            
                        sLink_STR_Type = self.i_dictItemStrMap[int(self.i_dictIDItemMap[sLink_Type])]  
                        
                        if '完全不見的車頭' in sLink_STR_Type:
                            bCheckCarSide = True   
                        else:
                            sLink_tl_x = float(dictBBoxFrameInfor['tl_x'][nLink_ID_Index])
                            sLink_br_x = float(dictBBoxFrameInfor['br_x'][nLink_ID_Index])

                            nLeft_x = min(float(sBr_x), float(sTl_x))
                            nRight_x = max(float(sBr_x), float(sTl_x))

                            nWidth = nRight_x - nLeft_x

                            if nWidth == 0:
                                print(nframe_in_db, sID, "Width = 0")
                                nWidth = 0.0001

                            nleft_ratio = round((sLink_tl_x - nLeft_x) / nWidth, 6)
                            nRight_ratio = round((sLink_br_x - nLeft_x) / nWidth, 6)

                            if nleft_ratio == 1.0: nleft_ratio = 1
                            if nleft_ratio == 0.0: nleft_ratio = 0

                            if nRight_ratio == 1.0: nRight_ratio = 1
                            if nRight_ratio == 0.0: nRight_ratio = 0

                            sCarSidePoint = str(nleft_ratio)+",-1,"+str(nRight_ratio)+",-1"

                    ## Save Into DataBase form
                    dictLoadInBBox = {}

                    dictLoadInBBox['obj_id'] = int(sID)
                    dictLoadInBBox['ybr'] = float(sBr_y)
                    dictLoadInBBox['ytl'] = float(sTl_y)
                    dictLoadInBBox['xtl'] = float(sTl_x)
                    dictLoadInBBox['xbr'] = float(sBr_x)

                    dictLoadInBBox['occluded'] = False
                    dictLoadInBBox['group_id'] = 0
                    dictLoadInBBox['grouping'] = ''
                    dictLoadInBBox['frame'] = nframe_in_db
                    
                    dictLoadInBBox['z_order'] = nZorder
                    nZorder += 1

                    dictLoadInBBox['label_id'] = self.i_dictTaskID_labelID[nTid]
                    ## Attribute

                    dictLoadInBBox['attributes'] = []
                    dictLoadInBBox['attributes'].append({'id': self.i_dictID_attributes[nTid]['Type'], 'value': sSTR_Type})
                    dictLoadInBBox['attributes'].append({'id': self.i_dictID_attributes[nTid]['障礙物'], 'value': bObstacle})
                    dictLoadInBBox['attributes'].append({'id': self.i_dictID_attributes[nTid]['有開燈'], 'value': bLight_state})
                    dictLoadInBBox['attributes'].append({'id': self.i_dictID_attributes[nTid]['Rotation'], 'value': nNew_Rotation})
                    dictLoadInBBox['attributes'].append({'id': self.i_dictID_attributes[nTid]['Occluded'], 'value': sNew_Occluded})
                    dictLoadInBBox['attributes'].append({'id': self.i_dictID_attributes[nTid]['看不見車頭車尾'], 'value': bCheckCarSide})
                    dictLoadInBBox['attributes'].append({'id': self.i_dictID_attributes[nTid]['DetectPoints'], 'value': sCarSidePoint})
                    dictLoadInBBox['attributes'].append({'id': self.i_dictID_attributes[nTid]['Truncated'], 'value': sTruncated})
                    dictLoadInBBox['attributes'].append({'id': self.i_dictID_attributes[nTid]['Dont_Care'], 'value': bNew_DontCare})

                    self.i_dictSever_Bbox[nTid][nframe_in_db]['boxes'].append(dictLoadInBBox)

        print("Convert_CSV2Server End.")
        return
