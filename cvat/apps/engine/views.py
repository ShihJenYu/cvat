
# Copyright (C) 2018 Intel Corporation
#
# SPDX-License-Identifier: MIT

import os
import json
import traceback
# add by jeff
import time, random
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
        if project == 'fcw_training' and request.user.groups.filter(name='fcw_training').exists():
            web = 'annotation_training'
        elif project == 'fcw_testing' and request.user.groups.filter(name='fcw_testing').exists():
            web = 'annotation_fcw_testing'
        else:
            return redirect('/')



        return render(request, 'engine/{}.html'.format(web), {
            'js_3rdparty': JS_3RDPARTY.get('engine', [])
        })


# Add by Eric
@login_required
@transaction.atomic
@permission_required('engine.add_task', raise_exception=True)
def update_keyframe(request):
    """Upload keyframe"""
    try:

        dictKeyframe = json.loads(request.body.decode('utf-8'))

        print(dictKeyframe)
        print(type(dictKeyframe))

        for sVideoDate in dictKeyframe.keys():
            if type(dictKeyframe[sVideoDate]) == int:
                
                db_task = models.Task.objects.select_for_update().get(name=sVideoDate)
                tid = db_task.id
                listTaskKeyframeExist = list(models.TaskFrameUserRecord.objects.filter(task_id=tid).values_list('frame', flat=True))

                db_taskFrameUserRecord = models.TaskFrameUserRecord()
                db_taskFrameUserRecord.task = db_task

                nFrameNumber = dictKeyframe[sVideoDate]
                nFrameNumber = int(nFrameNumber) - 1

                if nFrameNumber in listTaskKeyframeExist:
                    print(nFrameNumber, 'Aleady is keyframe')
                    continue
                db_taskFrameUserRecord.frame = nFrameNumber

                db_fcwTrain = models.FCWTrain.objects.select_for_update().get(task_id=tid)
                db_fcwTrain.keyframe_count += 1
                db_fcwTrain.priority = 0

                db_fcwTrain.save()
                db_taskFrameUserRecord.save()
                print("tid:{} frame:{} is add".format(tid,nFrameNumber))
            else :
                for nFrameNumber in dictKeyframe[sVideoDate]:

                    db_task = models.Task.objects.select_for_update().get(name=sVideoDate)
                    tid = db_task.id
                    listTaskKeyframeExist = list(models.TaskFrameUserRecord.objects.filter(task_id=tid).values_list('frame', flat=True))

                    db_taskFrameUserRecord = models.TaskFrameUserRecord()
                    db_taskFrameUserRecord.task = db_task

                    nFrameNumber = int(nFrameNumber) - 1

                    if nFrameNumber in listTaskKeyframeExist:
                        print(nFrameNumber, 'Aleady is keyframe')
                        continue
                    db_taskFrameUserRecord.frame = nFrameNumber

                    db_fcwTrain = models.FCWTrain.objects.select_for_update().get(task_id=tid)
                    db_fcwTrain.keyframe_count += 1
                    db_fcwTrain.priority = 0

                    db_fcwTrain.save()
                    db_taskFrameUserRecord.save()
                    print("tid:{} frame:{} is add".format(tid,nFrameNumber))

        response = {'data':"Success upload Keyframe"}
        return JsonResponse(response, safe=False)
 
    except Exception as e:

        print("error is !!!!",str(e))
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

# add by jeff
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
            print('fcw_training',project)
            db_fcwTrain = models.FCWTrain.objects.select_for_update().get(task_id=tid)
            if flag:
                db_task = models.Task.objects.select_for_update().get(pk=tid)
                db_taskFrameUserRecord = models.TaskFrameUserRecord()
                db_taskFrameUserRecord.task = db_task
                db_taskFrameUserRecord.frame = frame
                
                db_fcwTrain.keyframe_count += 1
                db_fcwTrain.priority = 0
                db_fcwTrain.save()

                db_taskFrameUserRecord.save()
                print("tid:{} frame:{} is add".format(tid,frame))
            else:
                try:
                    keyframe = models.TaskFrameUserRecord.objects.get(task_id=tid,frame=frame)
                    keyframe.delete()

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
            return JsonResponse({'frames': list(frames)}, safe=False)

        elif project == 'fcw_testing':
            print('fcw_testing',project)
            qs = models.FCWTest_FrameUserRecord.objects.select_for_update().filter(task_id=tid)
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
        elif project == 'fcw_testing':
            keyframe = models.FCWTest_FrameUserRecord.objects.select_for_update().get(task_id=tid,frame=frame)
            video_user = models.FCWTest.objects.select_for_update().get(task_id=tid).user
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

        if flag:
            keyframe.checker = request.user.username
            keyframe.checked = True
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

        if flag:
            keyframe.checker = request.user.username
            keyframe.need_modify = True
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

        project = params['project']
        print('project', project)

        if(params['selectTasks'] != ''):
            tasks = params['selectTasks'].split(',')
            if project == 'fcw_training':
                for tid in tasks:
                    db_fcwTrain = models.FCWTrain.objects.select_for_update().get(task_id=int(tid))
                    db_fcwTrain.priority = priority
                    db_fcwTrain.save()
            elif project == 'fcw_testing':
                for tid in tasks:
                    db_fcwTest = models.FCWTest.objects.select_for_update().get(task_id=int(tid))
                    db_fcwTest.priority = priority
                    db_fcwTest.save()

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
        elif project == 'fcw_testing':
            try:
                with transaction.atomic():
                    user_record = models.FCWTest.objects.select_for_update().get(user=request.user.username,current=True)
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

        user_record = None
        new_jid = None

        if project == 'fcw_training':
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
                return JsonResponse({'status':"A01",'text':"找不到fcw_training的工作, 請聯絡管理員哦"})

        elif project == 'fcw_testing':
            start_time = time.time()
            db_fcwTests = models.FCWTest.objects.filter(~Q(priority=0) & Q(user=request.user.username) & Q(need_modify=True)).order_by('-priority', 'task__created_date')
            print ("db_fcwTrains,",db_fcwTests)
            print ("len  db_fcwTrains,",len(db_fcwTests))
            user_record, new_jid = set_currentWithJob(request.user.username, db_fcwTests, time='modify')
            end_time = time.time()
            print ("use random pk cost time : ",(end_time - start_time))
            
            if user_record is None:
                print("need modify is none, try get new frame")
                start_time = time.time()
                db_fcwTests = models.FCWTest.objects.filter(~Q(priority=0),Q(user=request.user.username),Q(userGet_date=None)).order_by('-priority', 'task__created_date')
                print ("db_fcwTests,",db_fcwTests)
                print ("len  db_fcwTests,",len(db_fcwTests))
                user_record, new_jid = set_currentWithJob(request.user.username, db_fcwTests, time='new')
                end_time = time.time()
                print ("use random pk cost time : ",(end_time - start_time))
                
            if user_record:
                print ("try get new Assign is success job",new_jid)
            else:
                print("need modify is none, try get new frame")
                start_time = time.time()
                db_fcwTests = models.FCWTest.objects.filter(~Q(priority=0),Q(user='')).order_by('-priority', 'task__created_date')
                print ("db_fcwTests,",db_fcwTests)
                print ("len  db_fcwTests,",len(db_fcwTests))
                user_record, new_jid = set_currentWithJob(request.user.username, db_fcwTests, time='new')
                end_time = time.time()
                print ("use random pk cost time : ",(end_time - start_time))
            
            if user_record:
                print ("try get new Empty is success job",new_jid)
            else:
                return JsonResponse({'status':"A01",'text':"找不到fcw_testing的工作, 請聯絡管理員哦"})

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
        elif project == 'fcw_testing':
            print('fcw_testing no show keyframe')
            return JsonResponse({'frames': []}, safe=False)
    except Exception as e:
        print("error is !!!!",str(e))
        return HttpResponseBadRequest(str(e))
