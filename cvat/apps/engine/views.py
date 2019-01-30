
# Copyright (C) 2018 Intel Corporation
#
# SPDX-License-Identifier: MIT

import os,errno
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

from django.db import transaction
from django.db.models import Q, Max, Min
from django.core.exceptions import ObjectDoesNotExist

from . import annotation, task, models
from cvat.settings.base import JS_3RDPARTY
from cvat.apps.authentication.decorators import login_required
from requests.exceptions import RequestException
import logging
from .logging import task_logger, job_logger, global_logger, job_client_logger

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
    # if request.method == 'GET' and 'id' in request.GET:
    #     if request.user.groups.filter(name='admin').exists() and 'setKey' in request.GET and request.GET['setKey'].upper() == "TRUE":
    #         return render(request, 'engine/annotation_keyframe.html', {
    #             'js_3rdparty': JS_3RDPARTY.get('engine', [])
    #         })
    #     else:
    #         return render(request, 'engine/annotation_training.html', {
    #             'js_3rdparty': JS_3RDPARTY.get('engine', [])
    #         })
    # else:
    #     return redirect('/dashboard/')
    project = list(filter(None, request.path.split('/')))[0]
    if request.user.groups.filter(name='admin').exists(): #and request.method == 'GET' and 'setKey' in request.GET and request.GET['setKey'].upper() == "TRUE":
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
        if project == 'fcw_training':# and request.user.groups.filter(name='fcw_training').exists():
            web = 'annotation_training'
        elif project == 'fcw_testing':# and request.user.groups.filter(name='fcw_testing').exists():
            web = 'annotation_fcw_testing'
        elif project == 'apacorner':# and request.user.groups.filter(name='fcw_testing').exists():
            web = 'annotation_apacorner'
        else:
            return redirect('/')



        return render(request, 'engine/{}.html'.format(web), {
            'js_3rdparty': JS_3RDPARTY.get('engine', [])
        })

# Add by jeff
@login_required
@transaction.atomic
@permission_required('engine.add_task', raise_exception=True)
def insert_keyframes(request):
    try:
        print("doing")

        listKeyFrames = request.POST.getlist('data')
        sShare_Root = settings.SHARE_ROOT

        for framePath in listKeyFrames:
            if os.path.splitext(framePath)[-1] != '':
                continue

            frame_uploadpath = os.path.normpath(framePath).lstrip('/')
            frame_abs_uploadpath = os.path.abspath(os.path.join(sShare_Root, frame_uploadpath))

            images_per_video = glob.glob('{}/*.{}'.format(frame_abs_uploadpath,'png'))
            if images_per_video :
                packagename, videoname = frame_abs_uploadpath.split('/')[-2:]

                print('packagename',packagename)
                print('videoname',videoname)
                print('images_per_video',images_per_video)
                
                #插入圖片再這個影片的這個批次
                video_task = models.Task.objects.select_for_update().get(name=videoname)
                #插入一個全新的批次再已經有的影片
                video_tid = video_task.id
                video_size = video_task.size
                video_path = video_task.path

                # get image path in .upload
                realvideopath = glob.glob('{}/*/*'.format(video_task.get_upload_dirname()))
                if len(realvideopath) != 1:
                    raise Exception('find two folder in realvideopath ')
                
                video_project = realvideopath[0].split('/')[-2]
                #copy image from share to real
                for image in images_per_video:
                    shutil.copy(image, realvideopath[0])
                
                #create fullpath list
                insertedImages =[]
                for f in sorted(os.listdir(realvideopath[0])):
                    fullname = os.path.join(realvideopath[0], f)
                    insertedImages.append(fullname)
                
                after_size = 0
                # create new link
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

                # save new size
                video_task.size = after_size
                video_task.save()
                video_seg = models.Segment.objects.select_for_update().get(task_id=video_tid)
                video_seg.stop_frame = after_size-1
                video_seg.save()

                #update exist frame with tid
                db_framenames = models.FrameName.objects.select_for_update().filter(task_id=video_tid)
                for db_framename in db_framenames:
                    before_frame = db_framename.frame
                    before_name = db_framename.name
                    if not before_name.endswith('.png'):
                        before_name += '.png'

                    after_index = insertedImages.index(os.path.join(realvideopath[0], before_name))
                    if after_index!=-1 and after_index!=before_frame:
                        #framename
                        db_framename.frame=after_index
                        db_framename.save()
                        #keyframe
                        db_keyframe = models.TaskFrameUserRecord.objects.select_for_update().get(task_id=video_tid,frame=before_frame)
                        db_keyframe.frame = after_index
                        db_keyframe.save()
                        #box
                        db_labelboxs = models.LabeledBox.objects.select_for_update().filter(job_id=video_tid,frame=before_frame).update(frame=after_index)

                #insert new frame
                for image in images_per_video:
                    imagename = os.path.basename(image)

                    after_index = insertedImages.index(os.path.join(realvideopath[0], imagename))
                    print('imagename',imagename)
                    print('after_index',after_index)

                    db_fcwTrain = models.FCWTrain.objects.select_for_update().get(task_id=video_tid)

                    try:
                        db_taskFrameUserRecord = models.TaskFrameUserRecord.objects.select_for_update().get(task_id=video_tid,frame=after_index)
                        print('db_taskFrameUserRecord is exist will pass')
                    except ObjectDoesNotExist:
                        db_taskFrameUserRecord = models.TaskFrameUserRecord()
                        db_taskFrameUserRecord.task = video_task
                        db_taskFrameUserRecord.frame = after_index
                        db_taskFrameUserRecord.packagename = packagename
                        db_taskFrameUserRecord.save()
                        db_fcwTrain.keyframe_count += 1
                        db_fcwTrain.priority = 0
                        db_fcwTrain.priority_out = 0
                        db_fcwTrain.save()

                    try:
                        db_FrameName = models.FrameName.objects.select_for_update().get(task_id=video_tid,frame=after_index)
                        print('db_FrameName is exist will pass')
                    except ObjectDoesNotExist:
                        realname = imagename.replace(".png", "")
                        db_FrameName = models.FrameName()
                        db_FrameName.task = video_task
                        db_FrameName.frame = after_index
                        db_FrameName.name = realname
                        db_FrameName.save()

        print("done")

        response = {'data':"Success insert_keyframes"}
        return JsonResponse(response, safe=False)
 
    except Exception as e:

        print("error is !!!!",str(e))
        return HttpResponseBadRequest(str(e))


# Add by Eric
@login_required
@transaction.atomic
@permission_required('engine.add_task', raise_exception=True)
def update_keyframe(request):
    """Upload keyframe"""
    try:
        dictKeyframe = json.loads(request.body.decode('utf-8'))
        packagename = dictKeyframe['packagename']

        for sVideoDate in dictKeyframe.keys():
            if sVideoDate == 'packagename':
                continue

            if type(dictKeyframe[sVideoDate]) == int: 
                dictKeyframe[sVideoDate] = [dictKeyframe[sVideoDate]]

            fcwTrain_ids = list(models.FCWTrain.objects.all().values_list('task_id', flat=True))
            db_task = models.Task.objects.select_for_update().filter(pk__in=fcwTrain_ids, name=sVideoDate)[0]

            history_packagenames = db_task.packagename
            history_packagenames = list(filter(None, history_packagenames.split(',')))
            if not packagename in history_packagenames: 
                history_packagenames.append(packagename)

            db_task.packagename = ','.join(history_packagenames)
            db_task.save()

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
            print(dictRealToFrame)

            for nFrameNumber in dictKeyframe[sVideoDate]:
                if sVideoDate == 'packagename':
                    continue

                listTaskKeyframeExist = list(models.TaskFrameUserRecord.objects.filter(task_id=tid).values_list('frame', flat=True))
                nFrameNumber = dictRealToFrame[int(nFrameNumber)]
                
                if nFrameNumber in listTaskKeyframeExist:
                    print(nFrameNumber, 'Aleady is keyframe')
                    continue

                db_taskFrameUserRecord = models.TaskFrameUserRecord()
                db_taskFrameUserRecord.task = db_task
                db_taskFrameUserRecord.frame = nFrameNumber
                db_taskFrameUserRecord.packagename = packagename
                db_taskFrameUserRecord.save()

                db_fcwTrain = models.FCWTrain.objects.select_for_update().get(task_id=tid)
                db_fcwTrain.keyframe_count += 1
                db_fcwTrain.priority = 0
                db_fcwTrain.priority_out = 0
                db_fcwTrain.save()

                path = os.path.realpath(task.get_frame_path(tid, nFrameNumber))
                realname = os.path.basename(path).replace(".png", "")
                db_FrameName = models.FrameName()
                db_FrameName.task = db_task
                db_FrameName.frame = nFrameNumber
                db_FrameName.name = realname
                db_FrameName.save()

                print("tid:{} frame:{} is add".format(tid,nFrameNumber))

        response = {'data':"Success upload Keyframe"}
        return JsonResponse(response, safe=False)
 
    except Exception as e:

        print("error is !!!!",str(e))
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

        listPackage_name = []

        oCSVcontainer = upload_CSV_container()
        oCSVcontainer.Read_Setting_files(a_Setting_file=fileSetting)

        for sCSVpath in listCSVfile:
            
            fileCSV_uploadpath = os.path.normpath(sCSVpath).lstrip('/')
            fileCSV_abs_uploadpath = os.path.abspath(os.path.join(sShare_Root, fileCSV_uploadpath))

            fileTaskName = os.path.basename(fileCSV_abs_uploadpath)

            if fileTaskName.endswith(".csv"):
                continue
            
            for root, dirs, files in os.walk(fileCSV_abs_uploadpath):
                print(root, dirs, files)
                fileRoot = root
                for fileCSV in files:
                    if not fileCSV.endswith(".csv"):
                        continue
                    if (not fileCSV.startswith("key_")):  # prevent bug for no root path
                        continue            
                    if 'VideoParam' in fileCSV:
                        continue      
                    fileCSV_Abspath = os.path.join(fileRoot, fileCSV)

                    sPackage_name = os.path.basename(os.path.dirname(os.path.dirname(fileCSV_Abspath)))
                    print(sPackage_name)
                    if sPackage_name not in listPackage_name:
                        listPackage_name.append(sPackage_name)
                    print('fileCSV_Abspath',fileCSV_Abspath)
                    oCSVcontainer.Reading_CSV(a_sCSV_path=fileCSV_Abspath)

        assert len(listPackage_name) == 1

        sPackagename = listPackage_name[0]

        oCSVcontainer.Get_Task_ID()
        oCSVcontainer.Get_db_labels_ID()
        oCSVcontainer.Get_Attribute_ID()
        oCSVcontainer.Convert_CSV2Server(a_bIgnore_not_keyframe=a_bIgnore_not_keyframe)
        # print(oCSVcontainer.i_dictSever_Bbox)

        fcwTrain_ids = list(models.FCWTrain.objects.all().values_list('task_id', flat=True))

        for nTid in oCSVcontainer.i_dictSever_Bbox.keys():

            sVideoName = oCSVcontainer.i_dictID_Taskname[nTid]  

            db_task = models.Task.objects.select_for_update().filter(pk__in=fcwTrain_ids, name=sVideoName)[0]

            history_packagenames = db_task.packagename
            history_packagenames = list(filter(None, history_packagenames.split(',')))
            if not sPackagename in history_packagenames: 
                history_packagenames.append(sPackagename)

            db_task.packagename = ','.join(history_packagenames)
            db_task.save()   
            print("Packagename save", sPackagename, " History packagenames", history_packagenames)    

            db_fcwTrain = models.FCWTrain.objects.select_for_update().get(task_id=nTid)     

            for nframe in oCSVcontainer.i_dictSever_Bbox[nTid].keys():
            
                current_frame = nframe - 1
                dictData = oCSVcontainer.i_dictSever_Bbox[nTid][nframe]

                # Also, set uploadframe as keyframe.
                qs = models.TaskFrameUserRecord.objects.select_for_update().filter(task_id=nTid,frame=current_frame)

                if len(qs) == 0:

                    if a_bIgnore_not_keyframe:
                        qs_name = models.FrameName.objects.select_for_update().filter(task_id=nTid,frame=current_frame)
                        if len(qs_name) == 0:
                            db_frameName = models.FrameName()
                            db_frameName.task_id = nTid
                            db_frameName.name = (sVideoName + "_%04d")%(oCSVcontainer.i_dictFrameMap[nTid][nframe])
                            db_frameName.frame = current_frame
                            db_frameName.save()  
                            print("db_frameName", " Tid: ",nTid, " Frame: ", nframe)                  
                    
                    db_taskFrameUserRecord = models.TaskFrameUserRecord()
                    db_taskFrameUserRecord.task = db_task
                    db_taskFrameUserRecord.frame = current_frame

                    db_taskFrameUserRecord.packagename = sPackagename
                    db_taskFrameUserRecord.save()  

                    db_fcwTrain.keyframe_count = models.TaskFrameUserRecord.objects.filter(task_id=nTid).count()
                    db_fcwTrain.priority = 0
                    db_fcwTrain.save()

                    if request.user.groups.filter(name='admin').exists():
                        print('Save CSV Job', "Tid:",nTid, " Frame:", nframe)
                        annotation.save_job(nTid, dictData, oneFrameFlag=True,frame=current_frame)
                    else:
                        # annotation.save_job(nTid, dictData,oneFrameFlag=True,frame=current_frame)
                        print("You cant save if you're not admin.")
                        pass

            print("Upload CSV End.")


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
        projects = ['/FCW_Train/','/FCW_Test/','/LVSA_Train/','/LVSA_Test/','/APA_Corner/','/APA_Segment/','/LDWS/']
        share_root = settings.SHARE_ROOT
        if params['storage'] == 'share':
            data_list = request.POST.getlist('data')
            data_list.sort(key=len)
            tmp = []
            data_list_len = 1 if len(data_list) == 1 else 0
            task_list = {}
            if len(data_list)==1 and (data_list[0] in projects):
                relpath = os.path.normpath(data_list[0]).lstrip('/')
                if '..' in relpath.split(os.path.sep):
                    raise Exception('Permission denied')
                abspath = os.path.abspath(os.path.join(share_root, relpath))
                if os.path.commonprefix([share_root, abspath]) != share_root:
                    raise Exception('Bad file path on share: ' + abspath)
                for name in os.listdir(abspath):
                    path = os.path.join(abspath, name)
                    if os.path.isdir(path):
                        path = path.replace(share_root,'') + '/'
                        tmp.append(path)
            else:
                for share_path in data_list:
                    if share_path.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp')):
                        share_path = share_path.rsplit('/')[0] + '/'
                        # print("share_path:",share_path)
                    if (not share_path in tmp) and (not share_path in projects) and (share_path != '/'):
                        tmp.append(share_path)

            # print("\n\n\n\n\ntmp:{}\n\n\n\n\n".format(tmp))

            for share_path in tmp:
                params['task_name'] = os.path.split(share_path.rstrip('/'))[-1]

                db_task = task.create_empty(params)
                ###########################################
                target_paths = []
                source_paths = []
                upload_dir = db_task.get_upload_dirname()

                relpath = os.path.normpath(share_path).lstrip('/')
                if '..' in relpath.split(os.path.sep):
                    raise Exception('Permission denied')
                abspath = os.path.abspath(os.path.join(share_root, relpath))
                
                if os.path.commonprefix([share_root, abspath]) != share_root:
                    raise Exception('Bad file path on share: ' + abspath)
                source_paths.append(abspath)
                # print("------------source_paths; ",abspath,"------------\n\n\n\n")
                target_paths.append(os.path.join(upload_dir, relpath))
                # print("------------target_paths; ",os.path.join(upload_dir, relpath),"------------\n\n\n\n")
                
                params['SOURCE_PATHS'] = source_paths
                params['TARGET_PATHS'] = target_paths
                task.create(db_task.id, params)
                task_list['tid'] = db_task.id

            return JsonResponse(task_list)
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
            return JsonResponse({'tid': db_task.id})

        
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

# add by jeff, not used
@login_required
@permission_required(perm=['engine.view_task', 'engine.change_annotation'], raise_exception=True)
def set_user_currnet(request, jid):
    try:        
        job_logger[jid].info("set {} currnet for {} job".format(request.user.username,jid))
        
        #db_job = models.Job.objects.get(id=jid)
        
        user_record = None
        new_jid = None # use taskid
        
        # set current frame to submit
        try:
            with transaction.atomic():
                user_record = models.TaskFrameUserRecord.objects.select_for_update().get(user=request.user.username,current=True)
                db_fcwTrain = models.FCWTrain.objects.select_for_update().get(task_id=user_record.task_id)
                print ("user: {} find current {}".format(request.user.username,user_record.frame))
                user_record.current = False
                user_record.user_submit = True
                
                if user_record.need_modify:
                    user_record.userModifySubmit_date = timezone.now()
                    tmp = db_fcwTrain.need_modify_count
                    db_fcwTrain.need_modify_count = tmp-1 if tmp-1>0 else 0
                else:
                    user_record.userSubmit_date = timezone.now()
                user_record.need_modify = False

                db_fcwTrain.unchecked_count += 1 
                user_record.save()
                db_fcwTrain.save()
            print ("user: {}'s user_record.save()".format(request.user.username))
        except ObjectDoesNotExist:
            print ("user: {}'s not found current frame".format(request.user.username))
            raise Exception('user_record is None')

        return JsonResponse({'data':"success"})

    except Exception as e:
        print("error is !!!!",str(e))
        job_logger[jid].error("cannot set {} currnet for {} job".format(request.user.username,jid), exc_info=True)
        return HttpResponseBadRequest(str(e))
# add by jeff, not used
@login_required
@permission_required(perm=['engine.view_task', 'engine.change_annotation'], raise_exception=True)
def get_user_currnet(request, jid):
    try:        
        job_logger[jid].info("set {} currnet for {} job".format(request.user.username,jid))
        
        #db_job = models.Job.objects.get(id=jid)
        
        user_record = None
        new_jid = None # use taskid
        
        # set current frame to submit
        try:
            with transaction.atomic():
                user_record = models.TaskFrameUserRecord.objects.select_for_update().get(user=request.user.username,current=True)
                db_fcwTrain = models.FCWTrain.objects.select_for_update().get(task_id=user_record.task_id)
                print ("user: {} find current {}".format(request.user.username,user_record.frame))
                return JsonResponse({'jid':user_record.task_id,'frame': user_record.frame})

        except ObjectDoesNotExist:
            print ("user: {}'s not found current frame".format(request.user.username))            
            
        # select need_modify
        user_record = None
        try:
            print("try get need_modify frame first")
            #user_record = models.TaskFrameUserRecord.objects.filter(task_id=db_job.segment.task.id,user=request.user.username,need_modify=True).first()
            start_time = time.time()
            db_fcwTrains = models.FCWTrain.objects.filter(~Q(priority=0)).order_by('-priority', 'task__created_date')
            print ("db_fcwTrains,",db_fcwTrains)
            print ("len  db_fcwTrains,",len(db_fcwTrains))
            if db_fcwTrains and len(db_fcwTrains):
                print ("db_fcwTrains has {} data".format(len(db_fcwTrains)))
                for db_fcwTrain in db_fcwTrains:
                    tmp_tid = db_fcwTrain.task.id
                    with transaction.atomic():
                        qs = models.TaskFrameUserRecord.objects.filter(task_id=tmp_tid,user=request.user.username,need_modify=True)
                        ids = qs.values_list('id', flat=True)
                        if len(ids):
                            index = random.randint(0, len(ids)-1)
                            try:
                                user_record = qs[index]#models.TaskFrameUserRecord.objects.select_for_update().get(pk=ids[index])
                                new_jid = tmp_tid

                                user_record.user = request.user.username
                                user_record.current = True
                                user_record.userModifyGet_date = timezone.now()
                                user_record.save()
                                break
                            except ObjectDoesNotExist:
                                user_record = None
                                new_jid = None
            end_time = time.time()
            print ("use random pk cost time : ",(end_time - start_time))

            if user_record is None:
                print("need modify is none, try get new frame")
                #user_record = models.TaskFrameUserRecord.objects.filter(task_id=db_job.segment.task.id,user='').first()
                start_time = time.time()
                db_fcwTrains = models.FCWTrain.objects.filter(~Q(priority=0)).order_by('-priority', 'task__created_date')
                print ("db_fcwTrains,",db_fcwTrains)
                print ("len  db_fcwTrains,",len(db_fcwTrains))
                if db_fcwTrains and len(db_fcwTrains):
                    print ("db_fcwTrains has {} data".format(len(db_fcwTrains)))
                    for db_fcwTrain in db_fcwTrains:
                        tmp_tid = db_fcwTrain.task.id
                        with transaction.atomic():
                            qs = models.TaskFrameUserRecord.objects.select_for_update().filter(task_id=tmp_tid,user='')
                            ids = qs.values_list('id', flat=True)
                            if len(ids):
                                index = random.randint(0, len(ids)-1)
                                try:
                                    user_record = qs[index]# models.TaskFrameUserRecord.objects.get(pk=ids[index])
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
                print ("try get new frame is success",user_record.frame)

        except Exception as e:
            user_record = None
            print("error is !!!!",str(e))
        
        if user_record:
            print ("have current")
            return JsonResponse({'jid':user_record.task_id,'frame': user_record.frame})
        else:
            print ("user_record is None, will error")
            return "you need to get new work"
            #raise Exception('user_record is None')

        # db_job = models.Job.objects.get(id=new_jid)

        # mAnnotation = annotation._AnnotationForJob(db_job)
        # mAnnotation.init_from_db(user_record.frame)
        # return JsonResponse({'jid':new_jid,'frame': user_record.frame})

    except Exception as e:
        print("error is !!!!",str(e))
        job_logger[jid].error("cannot set {} currnet for {} job".format(request.user.username,jid), exc_info=True)
        return HttpResponseBadRequest(str(e))


# add by jeff
@login_required
@transaction.atomic
@permission_required('engine.add_task', raise_exception=True)
def set_frame_isKeyFrame(request, tid, frame, flag):
    try:
        project = list(filter(None, request.path.split('/')))[0]

        if project == 'fcw_training':
            print('project is',project)
            keyframe_full_name = ''
            db_fcwTrain = models.FCWTrain.objects.select_for_update().get(task_id=tid)
            if flag:
                db_task = models.Task.objects.select_for_update().get(pk=tid)
                db_taskFrameUserRecord = models.TaskFrameUserRecord()
                db_taskFrameUserRecord.task = db_task
                db_taskFrameUserRecord.frame = frame
                db_taskFrameUserRecord.packagename = 'default'
                db_taskFrameUserRecord.save()
                
                db_fcwTrain.keyframe_count += 1
                db_fcwTrain.priority = 0
                db_fcwTrain.priority_out = 0
                db_fcwTrain.save()

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
                    keyframe = models.TaskFrameUserRecord.objects.get(task_id=tid,frame=frame)
                    keyframe.delete()
                    realname = models.FrameName.objects.get(task_id=tid,frame=frame)
                    realname.delete()

                    db_fcwTrain.keyframe_count -= 1
                    db_fcwTrain.checked_count = models.TaskFrameUserRecord.objects.filter(task_id=tid,checked=True).count()
                    db_fcwTrain.unchecked_count = models.TaskFrameUserRecord.objects.filter(task_id=tid,user_submit=True).count()
                    db_fcwTrain.need_modify_count = models.TaskFrameUserRecord.objects.filter(task_id=tid,need_modify=True).count()
                    db_fcwTrain.save()

                except ObjectDoesNotExist:
                    print("tid:{} frame:{} is delete".format(tid,frame))

            qs = models.TaskFrameUserRecord.objects.select_for_update().filter(task_id=tid)
            frames = qs.values_list('frame', flat=True)
            print(list(frames))
            return JsonResponse({'frames': list(frames), 'full_name': keyframe_full_name}, safe=False)

        elif project in ['fcw_testing', 'apacorner']:
            print('project is',project)
            qs = None
            if project == 'fcw_testing':
                qs = models.FCWTest_FrameUserRecord.objects.select_for_update().filter(task_id=tid)
            elif project == 'apacorner':
                qs = models.APACorner_FrameUserRecord.objects.select_for_update().filter(task_id=tid)
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
        response = None
        if project == 'fcw_training':
            keyframe = models.TaskFrameUserRecord.objects.select_for_update().get(task_id=tid,frame=frame)
            response = {
                'annotator': keyframe.user,
                'current': keyframe.current,
                'user_submit': keyframe.user_submit,
                'need_modify': keyframe.need_modify,
                'checked': keyframe.checked,
                'comment': keyframe.comment
            }
        elif project in ['fcw_testing', 'apacorner']:
            keyframe = None
            video_user = None
            if project == 'fcw_testing':
                keyframe = models.FCWTest_FrameUserRecord.objects.select_for_update().get(task_id=tid,frame=frame)
                video_user = models.FCWTest.objects.select_for_update().get(task_id=tid).user
            elif project == 'apacorner':
                keyframe = models.APACorner_FrameUserRecord.objects.select_for_update().get(task_id=tid,frame=frame)
                video_user = models.APACorner.objects.select_for_update().get(task_id=tid).user
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
        keyframe = None
        db_project = None
        qs_project = None

        if project == 'fcw_training':
            keyframe = models.TaskFrameUserRecord.objects.select_for_update().get(task_id=tid,frame=frame)
            db_project = models.FCWTrain.objects.select_for_update().get(task_id=tid)
            qs_project = models.TaskFrameUserRecord.objects.all()
        elif project == 'fcw_testing':
            keyframe = models.FCWTest_FrameUserRecord.objects.select_for_update().get(task_id=tid,frame=frame)
            db_project = models.FCWTest.objects.select_for_update().get(task_id=tid)
            qs_project = models.FCWTest_FrameUserRecord.objects.all()
        elif project == 'apacorner':
            keyframe = models.APACorner_FrameUserRecord.objects.select_for_update().get(task_id=tid,frame=frame)
            db_project = models.APACorner.objects.select_for_update().get(task_id=tid)
            qs_project = models.APACorner_FrameUserRecord.objects.all()

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

        db_project.checked_count = qs_project.filter(task_id=tid,checked=True).count()
        db_project.unchecked_count = qs_project.filter(task_id=tid,user_submit=True).count()
        db_project.need_modify_count = qs_project.filter(task_id=tid,need_modify=True).count()
        db_project.save()

        response = {'frame': frame,'isComplete':flag}
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
        keyframe = None
        db_project = None
        qs_project = None

        if project == 'fcw_training':
            keyframe = models.TaskFrameUserRecord.objects.select_for_update().get(task_id=tid,frame=frame)
            db_project = models.FCWTrain.objects.select_for_update().get(task_id=tid)
            qs_project = models.TaskFrameUserRecord.objects.all()
        elif project == 'fcw_testing':
            keyframe = models.FCWTest_FrameUserRecord.objects.select_for_update().get(task_id=tid,frame=frame)
            db_project = models.FCWTest.objects.select_for_update().get(task_id=tid)
            qs_project = models.FCWTest_FrameUserRecord.objects.all()
        elif project == 'apacorner':
            keyframe = models.APACorner_FrameUserRecord.objects.select_for_update().get(task_id=tid,frame=frame)
            db_project = models.APACorner.objects.select_for_update().get(task_id=tid)
            qs_project = models.APACorner_FrameUserRecord.objects.all()

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

        db_project.checked_count = qs_project.filter(task_id=tid,checked=True).count()
        db_project.unchecked_count = qs_project.filter(task_id=tid,user_submit=True).count()
        db_project.need_modify_count = qs_project.filter(task_id=tid,need_modify=True).count()
        db_project.save()

        response = {'frame': frame,'isRedo':flag}
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
        keyframe = None
        if project == 'fcw_training':
            keyframe = models.TaskFrameUserRecord.objects.select_for_update().get(task_id=tid,frame=frame)
        elif project == 'fcw_testing':
            keyframe = models.FCWTest_FrameUserRecord.objects.select_for_update().get(task_id=tid,frame=frame)
        elif project == 'apacorner':
            keyframe = models.APACorner_FrameUserRecord.objects.select_for_update().get(task_id=tid,frame=frame)
        
        keyframe.checker = request.user.username
        keyframe.comment = comment
        keyframe.save()
        print("tid:{} frame:{} is Redo".format(tid,frame))

        response = {'frame': frame,'comment':comment}
        return JsonResponse(response, safe=False)
    except Exception as e:
        print("error is !!!!",str(e))
        return HttpResponseBadRequest(str(e))

@login_required
@transaction.atomic
@permission_required('engine.add_task', raise_exception=True)
def set_tasks_priority(request):
    """Create a new annotation task"""
    try:
        db_task = None
        params = request.POST.dict()
        priority = params['priority']
        inCompany = params['inCompany']
        project = params['project']
        print('project', project)

        inCompany = True if inCompany == 'true' else False

        print('inCompany',inCompany,'priority',priority)

        if(params['selectTasks'] != ''):
            tasks = params['selectTasks'].split(',')
            if project == 'fcw_training':
                for tid in tasks:
                    db_Project = models.FCWTrain.objects.select_for_update().get(task_id=int(tid))
                    if inCompany:
                        print('db_Project.priority = priority')
                        db_Project.priority = priority
                    else:
                        print('db_Project.priority_out = priority')
                        db_Project.priority_out = priority
                    db_Project.save()
            elif project == 'fcw_testing':
                for tid in tasks:
                    db_Project = models.FCWTest.objects.select_for_update().get(task_id=int(tid))
                    if inCompany:
                        db_Project.priority = priority
                    else:
                        db_Project.priority_out = priority
                    db_Project.save()
            elif project == 'apacorner':
                for tid in tasks:
                    db_Project = models.APACorner.objects.select_for_update().get(task_id=int(tid))
                    if inCompany:
                        db_Project.priority = priority
                    else:
                        db_Project.priority_out = priority
                    db_Project.save()

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

        db_userRecord = None
        try:
            db_userRecord = models.TaskFrameUserRecord.objects.get(user=request.user.username,current=True)
            response = {'jid': db_userRecord.task.id}
            return JsonResponse(response, safe=False)
        except ObjectDoesNotExist:
            pass
            

        db_fcwTrains = models.FCWTrain.objects.filter(~Q(priority=0)).order_by('-priority', 'task__created_date')
        print ("db_fcwTrains,",db_fcwTrains)
        print ("len  db_fcwTrains,",len(db_fcwTrains))
        db_fcwTrain = db_fcwTrains.first()

        if db_fcwTrain:
            print("~Q(undo=0),Q(priority=1)",db_fcwTrain.priority)
            response = {'jid': db_fcwTrain.task.id}
        else:
            response = None
            raise Exception('no priority > 0!') 
        
        return JsonResponse(response, safe=False)
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
        
        if project == 'fcw_training':
            try:
                with transaction.atomic():
                    user_record = models.TaskFrameUserRecord.objects.select_for_update().get(user=request.user.username,current=True)
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
        elif project in ['fcw_testing', 'apacorner']:
            try:
                with transaction.atomic():
                    if project == 'fcw_testing':
                        user_record = models.FCWTest.objects.select_for_update().get(user=request.user.username,current=True)
                    elif project == 'apacorner':
                        user_record = models.APACorner.objects.select_for_update().get(user=request.user.username,current=True)
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
            if project == 'fcw_training':
                db_project = models.FCWTrain.objects.select_for_update().get(task_id=tid)
                qs_project = models.TaskFrameUserRecord.objects.all()
            elif project == 'fcw_testing':
                db_project = models.FCWTest.objects.select_for_update().get(task_id=tid)
                qs_project = models.FCWTest_FrameUserRecord.objects.all()
            elif project == 'apacorner':
                db_project = models.APACorner.objects.select_for_update().get(task_id=tid)
                qs_project = models.APACorner_FrameUserRecord.objects.all()

            db_project.checked_count = qs_project.filter(task_id=tid,checked=True).count()
            db_project.unchecked_count = qs_project.filter(task_id=tid,user_submit=True).count()
            db_project.need_modify_count = qs_project.filter(task_id=tid,need_modify=True).count()
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
    user_record = None
    new_jid = None
    ids = qs.values_list('id', flat=True)
    if len(ids):
        index = random.randint(0, len(ids)-1)
        try:
            user_record = qs[index]
            new_jid = user_record.task_id

            user_record.user = username
            user_record.current = True
            if time == 'modify':
                user_record.userModifyGet_date = timezone.now()
            if time == 'new':
                user_record.userGet_date = timezone.now()
            user_record.save()
        except ObjectDoesNotExist:
            print("error in set_currentJob fcw_training modify")
            user_record = None
            new_jid = None
    return user_record, new_jid

# add by jeff
@login_required
@transaction.atomic
@permission_required('engine.view_task', raise_exception=True)
def set_currentJob(request):
    try:
        project = list(filter(None, request.path.split('/')))[0]
        username = request.user.username.lower()
        user_record = None
        new_jid = None

        user_priority = None
        user_workSpace = None
        if username.startswith('oto',0,3):
            user_priority = {'priority':0,}
        else:
            user_priority = {'priority_out':0,}

        user_workSpace = {'username':request.user.username, 'project':project}
        task_list = None
        try:
            # print('user_workSpace',user_workSpace)
            # packagename = models.UserWorkSpace.objects.get(**user_workSpace).packagename
            # print('packagename',packagename)
            # task_list = models.Task.objects.filter(packagename__icontains=packagename).values_list('id',flat=True)
            # print('task_list',task_list)
            print('user_workSpace',user_workSpace)
            packagenames = list(models.UserWorkSpace.objects.filter(**user_workSpace).values_list('packagename',flat=True))

            print('hahahahahahahaha packagenames',packagenames)
            if len(packagenames) == 0:
                return JsonResponse({'status':"A01",'text':"你沒被分配到工作, 請聯絡管理員哦"})
            query = functools.reduce(operator.or_, (Q(packagename__icontains = item) for item in packagenames))
            task_list = models.Task.objects.filter(query).values_list('id',flat=True)
            print('hahahahahahahaha task_list',task_list)
        except ObjectDoesNotExist:
            return JsonResponse({'status':"A01",'text':"你沒被分配到工作, 請聯絡管理員哦"})
        

        if project == 'fcw_training':
            start_time = time.time()
            db_fcwTrains = models.FCWTrain.objects.filter(~Q(**user_priority)).order_by('-{}'.format(list(user_priority.keys())[0]), 'task__created_date')
            print ("db_fcwTrains,",db_fcwTrains)
            print ("len  db_fcwTrains,",len(db_fcwTrains))
            if db_fcwTrains and len(db_fcwTrains):
                print ("db_fcwTrains has {} data".format(len(db_fcwTrains)))
                for db_fcwTrain in db_fcwTrains:
                    tmp_tid = db_fcwTrain.task.id
                    with transaction.atomic():
                        qs = models.TaskFrameUserRecord.objects.filter(task_id=tmp_tid,user=request.user.username,need_modify=True)
                        ids = qs.values_list('id', flat=True)
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
                db_fcwTrains = models.FCWTrain.objects.filter(Q(task_id__in=task_list) & ~Q(**user_priority)).order_by('-{}'.format(list(user_priority.keys())[0]), 'task__created_date')
                print ("db_fcwTrains,",db_fcwTrains)
                print ("len  db_fcwTrains,",len(db_fcwTrains))
                if db_fcwTrains and len(db_fcwTrains):
                    print ("db_fcwTrains has {} data".format(len(db_fcwTrains)))
                    for db_fcwTrain in db_fcwTrains:
                        tmp_tid = db_fcwTrain.task.id
                        with transaction.atomic():
                            qs = models.TaskFrameUserRecord.objects.select_for_update().filter(task_id=tmp_tid,user='')
                            ids = qs.values_list('id', flat=True)
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

        elif project in ['fcw_testing', 'apacorner']:
            start_time = time.time()
            if project == 'fcw_testing':
                db_Project = models.FCWTest.objects.filter(~Q(**user_priority) & Q(user=request.user.username) & Q(need_modify=True)).order_by('-{}'.format(list(user_priority.keys())[0]), 'task__created_date')
            elif project == 'apacorner':
                db_Project = models.APACorner.objects.filter(~Q(**user_priority) & Q(user=request.user.username) & Q(need_modify=True)).order_by('-{}'.format(list(user_priority.keys())[0]), 'task__created_date')
            print ("db_Project,",db_Project)
            print ("len  db_Project,",len(db_Project))
            user_record, new_jid = set_currentWithJob(request.user.username, db_Project, time='modify')
            end_time = time.time()
            print ("use random pk cost time : ",(end_time - start_time))
            
            if user_record is None:
                print("need modify is none, try get new frame")
                start_time = time.time()
                if project == 'fcw_testing':
                    db_Project = models.FCWTest.objects.filter(Q(task_id__in=task_list) & ~Q(**user_priority) & Q(user=request.user.username) & Q(userGet_date=None)).order_by('-{}'.format(list(user_priority.keys())[0]), 'task__created_date')
                elif project == 'apacorner':
                    db_Project = models.APACorner.objects.filter(Q(task_id__in=task_list) & ~Q(**user_priority) & Q(user=request.user.username) & Q(userGet_date=None)).order_by('-{}'.format(list(user_priority.keys())[0]), 'task__created_date')
                print ("db_Project,",db_Project)
                print ("len  db_Project,",len(db_Project))
                user_record, new_jid = set_currentWithJob(request.user.username, db_Project, time='new')
                end_time = time.time()
                print ("use random pk cost time : ",(end_time - start_time))
                
            if user_record:
                print ("try get new Assign is success job",new_jid)
            else:
                print("need modify is none, try get new frame")
                start_time = time.time()
                if project == 'fcw_testing':
                    db_Project = models.FCWTest.objects.filter(Q(task_id__in=task_list) & ~Q(**user_priority) & Q(user='')).order_by('-{}'.format(list(user_priority.keys())[0]), 'task__created_date')
                elif project == 'apacorner':
                    db_Project = models.APACorner.objects.filter(Q(task_id__in=task_list) & ~Q(**user_priority) & Q(user='')).order_by('-{}'.format(list(user_priority.keys())[0]), 'task__created_date')
                print ("db_Project,",db_Project)
                print ("len  db_Project,",len(db_Project))
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
            print(list(frames))
            return JsonResponse({'frames': list(frames)}, safe=False)
        elif project in ['fcw_testing', 'apacorner']:
            print(project,'no show keyframe')
            return JsonResponse({'frames': []}, safe=False)
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

    def Get_Task_ID(self):
        
        for sVideoDate in self.i_dictTaskname_ID.keys():

            oDB_task = models.Task.objects.select_for_update().get(name=sVideoDate)
            nTid = int(oDB_task.id)

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

    def Convert_CSV2Server(self, a_bIgnore_not_keyframe=True):

        print("Convert_CSV2Server Start.")

        for sVideoName in self.i_dictTaskname_Frame_BBoxInfor.keys():
            
            nTid = self.i_dictTaskname_ID[sVideoName]

            if nTid not in self.i_dictSever_Bbox.keys():
                self.i_dictSever_Bbox[nTid] = {}    

            if a_bIgnore_not_keyframe: # for only save keyframe in database
                db_frame_count = 1                
                self.i_dictFrameMap[nTid] = {}

            listFrameNumber = list(self.i_dictTaskname_Frame_BBoxInfor[sVideoName].keys())
            listFrameNumber.sort()

            for nframe in listFrameNumber:
                
                print("Start to Convert VideoName", sVideoName, "FrameNumber", nframe)

                dictBBoxFrameInfor = self.i_dictTaskname_Frame_BBoxInfor[sVideoName][nframe]

                if a_bIgnore_not_keyframe: # for only save keyframe in database
                    self.i_dictFrameMap[nTid][db_frame_count] = nframe
                    nframe = db_frame_count
                    db_frame_count += 1

                if nframe not in self.i_dictSever_Bbox[nTid].keys():
                    self.i_dictSever_Bbox[nTid][nframe] = {'boxes':[],'points': [], 'polygons': [], 
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
                                print(nframe, sID, "Width = 0")
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
                    dictLoadInBBox['frame'] = (nframe - 1)
                    
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

                    self.i_dictSever_Bbox[nTid][nframe]['boxes'].append(dictLoadInBBox)

        print("Convert_CSV2Server End.")
        return

        








