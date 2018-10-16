
# Copyright (C) 2018 Intel Corporation
#
# SPDX-License-Identifier: MIT

import os
import json
import traceback

from django.http import HttpResponse, HttpResponseBadRequest, JsonResponse
from django.shortcuts import redirect, render
from django.conf import settings
from django.contrib.auth.decorators import permission_required
from django.views.decorators.gzip import gzip_page
from sendfile import sendfile

#add by jeff
from django.db.models import Q
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
    if request.method == 'GET' and 'id' in request.GET:
        return render(request, 'engine/annotation.html', {
            'js_3rdparty': JS_3RDPARTY.get('engine', [])
        })
    else:
        return redirect('/dashboard/')

@login_required
@permission_required('engine.add_task', raise_exception=True)
def create_task(request):
    """Create a new annotation task"""

    db_task = None
    params = request.POST.dict()
    params['owner'] = request.user
    global_logger.info("create task with params = {}".format(params))
    try:
        db_task = task.create_empty(params)
        target_paths = []
        source_paths = []
        upload_dir = db_task.get_upload_dirname()
        share_root = settings.SHARE_ROOT
        if params['storage'] == 'share':
            data_list = request.POST.getlist('data')
            data_list.sort(key=len)
            for share_path in data_list:
                relpath = os.path.normpath(share_path).lstrip('/')
                if '..' in relpath.split(os.path.sep):
                    raise Exception('Permission denied')
                abspath = os.path.abspath(os.path.join(share_root, relpath))
                if os.path.commonprefix([share_root, abspath]) != share_root:
                    raise Exception('Bad file path on share: ' + abspath)
                source_paths.append(abspath)
                target_paths.append(os.path.join(upload_dir, relpath))
        else:
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
        response = annotation.get_my(jid,request.user.username)
        #response = annotation.get(jid)
        
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
            annotation.save_job(jid, json.loads(data['annotation']))
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
    response = {'username': request.user.username}
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
        
        print ("qqqqqqqqqqqqqqqqqqqqqq")
        job_logger[jid].info("set {} currnet for {} job".format(request.user.username,jid))
        print ("wwwwwwwwwqqqqqqwwww")
        db_job = models.Job.objects.get(id=jid)
        print ("wwwwwwwwwwwww")
        # set current frame to submit
        user_record = None
        print ("wwwwwwwxxxxwwwwww")
        try:
            print ("wwwwwwwssssssssswwwwww")
            user_record = models.TaskFrameUserRecord.objects.get(task_id=db_job.segment.task.id,user=request.user.username,current=True)

            user_record.current = False
            user_record.user_submit = True
            user_record.need_modify = False
            user_record.save()
            print("fucking user_record.save()",user_record.frame)
            print ("AAuser=username find current",user_record.frame)
        except ObjectDoesNotExist:
            print ("user=username not found current",user_record.frame)
            print ("aaaaaaaaaaaaaaaaaaaaaa")
            
            
        # select need_modify
        user_record = None
        try:
            print("aaaabbbb")
            user_record = models.TaskFrameUserRecord.objects.filter(task_id=db_job.segment.task.id,user=request.user.username,need_modify=True).first()

            if user_record is None:
                try:
                    print("ccccc")
                    user_record = models.TaskFrameUserRecord.objects.filter(task_id=db_job.segment.task.id,user='').first()
                    print ("user='' find empty first frame",user_record.frame)
                except ObjectDoesNotExist:
                    print ("no user's need_modify or empty can set current!!",user_record.frame)

        except ObjectDoesNotExist:
            try:
                print("bbbbaaaaa")
                user_record = models.TaskFrameUserRecord.objects.filter(task_id=db_job.segment.task.id,user='').first()
                print ("user='' find empty first frame",user_record.frame)
            except ObjectDoesNotExist:
                print ("no user's need_modify or empty can set current!!",user_record.frame)
        print("zzzz")
        user_record.user = request.user.username
        user_record.current = True
        user_record.save()

    except Exception as e:
        print("fucking error is !!!!",str(e))
        job_logger[jid].error("cannot set {} currnet for {} job".format(request.user.username,jid), exc_info=True)
        print("fucking",user_record.frame)
        return HttpResponseBadRequest(str(e))
        

    
    print("fucking user_record.save() 2",user_record.frame)
    return JsonResponse({'frame': user_record.frame})