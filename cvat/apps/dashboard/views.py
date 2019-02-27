
# Copyright (C) 2018 Intel Corporation
#
# SPDX-License-Identifier: MIT

from django.http import HttpResponse, JsonResponse, HttpResponseBadRequest
from django.shortcuts import redirect
from django.shortcuts import render
from django.conf import settings
from django.contrib.auth.decorators import permission_required
from cvat.apps.authentication.decorators import login_required

from cvat.apps.engine import models, task
from cvat.apps.engine.models import Task as TaskModel
from cvat.apps.engine.models import FCWTrain as FCWTrainModel
from cvat.apps.engine.models import FCWTest as FCWTestModel
from cvat.apps.engine.models import APACorner as APACornerModel
from cvat.apps.engine.models import BSDTrain as BSDTrainModel
from cvat.apps.engine.models import DMSTrain as DMSTrainModel
from cvat.settings.base import JS_3RDPARTY

import os
from datetime import datetime

def ScanNode(directory,project=None):
    if '..' in directory.split(os.path.sep):
        return HttpResponseBadRequest('Permission Denied')

    act_dir = os.path.normpath(settings.SHARE_ROOT + directory)
    result = []

    nodes = os.listdir(act_dir)
    files = filter(os.path.isfile, map(lambda f: os.path.join(act_dir, f), nodes))
    dirs = filter(os.path.isdir, map(lambda d: os.path.join(act_dir, d), nodes))

    ProjectToFolder = {'fcw_training':'FCW_Train','fcw_testing':'FCW_Test',
                        'apacorner':'APA_Corner','bsd_training':'BSD_Train','dms_training':'DMS_Train',}

    for d in dirs:
        name = os.path.basename(d)
        if (directory =='/') and (project != None) and (name != ProjectToFolder[project]):
            continue

        children = len(os.listdir(d)) > 0
        node = {'id': directory + name + '/', 'text': name, 'children': children}
        result.append(node)

    for f in files:
        name = os.path.basename(f)
        node = {'id': directory + name, 'text': name, "icon" : "jstree-file"}
        result.append(node)

    return result

@login_required
@permission_required('engine.add_task', raise_exception=True)
def JsTreeView(request):
    node_id = None
    project = None
    if 'id' in request.GET:
        node_id = request.GET['id']

    if 'project' in request.GET:
        project = request.GET['project']

    if node_id is None or node_id == '#':
        node_id = '/'
        response = [{"id": node_id, "text": node_id, "children": ScanNode(node_id,project=project)}]
    else:
        response = ScanNode(node_id)

    return JsonResponse(response, safe=False,
        json_dumps_params=dict(ensure_ascii=False))


def MainTaskInfo(task, dst_dict):
    dst_dict["status"] = task.status
    dst_dict["num_of_segments"] = task.segment_set.count()
    dst_dict["mode"] = task.mode.capitalize()
    dst_dict["name"] = task.name
    dst_dict["nickname"] = task.nickname
    dst_dict["packagename"] = task.packagename
    dst_dict["task_id"] = task.id
    dst_dict["created_date"] = task.created_date
    dst_dict["updated_date"] = task.updated_date
    dst_dict["bug_tracker_link"] = task.bug_tracker
    dst_dict["has_bug_tracker"] = len(task.bug_tracker) > 0
    dst_dict["owner"] = 'undefined'
    dst_dict["id"] = task.id
    dst_dict["segments"] = []

def get_realframe(tid, frame):
    path = os.path.realpath(task.get_frame_path(tid, frame))
    realname = os.path.basename(path)
    realframe = os.path.splitext(realname)[0][-4:]
    return realframe

def DetailTaskInfo(request, task, dst_dict):
    scheme = request.scheme
    host = request.get_host()
    dst_dict['segments'] = []

    project = list(filter(None, request.path.split('/')))[1]

    for segment in task.segment_set.all():
        for job in segment.job_set.all():
            segment_url = "{0}://{1}/{2}/?id={3}".format(scheme, host, project, job.id)
            #url_fcw = "{0}://{1}/fcw?id={2}".format(scheme, host, job.id)
            url_fcw = "{0}://{1}/{2}/".format(scheme, host, project)
            url_fcw_key = "{0}://{1}/{2}/?id={3}&setKey=true".format(scheme, host, project, job.id)
            
            dst_dict["segments"].append({
                'id': job.id,
                'start': segment.start_frame,
                'stop': segment.stop_frame,
                'url': segment_url,
                'url_fcw': url_fcw,
                'url_fcw_key': url_fcw_key,
            })

    db_labels = task.label_set.prefetch_related('attributespec_set').all()
    attributes = {}
    for db_label in db_labels:
        attributes[db_label.id] = {}
        for db_attrspec in db_label.attributespec_set.all():
            attributes[db_label.id][db_attrspec.id] = db_attrspec.text

    dst_dict['labels'] = attributes

    db_Project = None
    db_keyFrame = None
    if project == 'fcw_training':
        db_Project = FCWTrainModel.objects.get(task_id=task.id)
        db_keyFrame = models.TaskFrameUserRecord.objects.filter(task_id=task.id)
    elif project == 'fcw_testing':
        db_Project = FCWTestModel.objects.get(task_id=task.id)
        db_keyFrame = models.FCWTest_FrameUserRecord.objects.filter(task_id=task.id)
    elif project == 'apacorner':
        db_Project = APACornerModel.objects.get(task_id=task.id)
        db_keyFrame = models.APACorner_FrameUserRecord.objects.filter(task_id=task.id)
    elif project == 'bsd_training':
        db_Project = BSDTrainModel.objects.get(task_id=task.id)
        db_keyFrame = models.BSDTrain_FrameUserRecord.objects.filter(task_id=task.id)
    elif project == 'dms_training':
        db_Project = DMSTrainModel.objects.get(task_id=task.id)
        db_keyFrame = models.DMSTrain_FrameUserRecord.objects.filter(task_id=task.id)
    
    packagenames = task.packagename
    packagenames = list(filter(None, packagenames.split(',')))
    if not 'default' in packagenames:
        packagenames.append('default')

    packstage = []
    for packagename in packagenames:
        pack_keyFrame = db_keyFrame.filter(packagename=packagename)
        keyframe_count = pack_keyFrame.count()
        checked_count = pack_keyFrame.filter(checked=True).count()
        need_modify_count = pack_keyFrame.filter(need_modify=True).count()
        unchecked_frames = list(pack_keyFrame.filter(user_submit=True).values_list('frame', flat=True))
        unchecked_count = len(unchecked_frames)
        unchecked_realframes = [ get_realframe(task.id, frame) for frame in unchecked_frames ]
        packstage.append({'packagename': packagename,
                        'keyframe_count': keyframe_count,
                        'unchecked_count':unchecked_count,
                        'checked_count': checked_count,
                        'need_modify_count': need_modify_count,
                        'undo_count': keyframe_count - unchecked_count - checked_count - need_modify_count,
                        'unchecked_realframes': unchecked_realframes})
    print('packstage',packstage)

    dst_dict['videostage'] = {
        'keyframe_count': db_Project.keyframe_count,
        'undo_count': db_Project.keyframe_count - db_Project.unchecked_count - db_Project.checked_count - db_Project.need_modify_count,
        'unchecked_count': db_Project.unchecked_count,
        'checked_count': db_Project.checked_count,
        'need_modify_count': db_Project.need_modify_count,
        'packstage': packstage,
        'priority': db_Project.priority,
        'priority_out': db_Project.priority_out,
    }
    print('videostage',dst_dict['videostage'] )


@login_required
@permission_required('engine.add_task', raise_exception=True)
def DashboardView(request):
    try:
        filter_name = request.GET['name'] if 'name' in request.GET else None
        filter_packagename = request.GET['packagename'] if 'packagename' in request.GET else None
        filter_nickname = request.GET['nickname'] if 'nickname' in request.GET else None
        filter_createdate = request.GET['createdate'] if 'createdate' in request.GET else None
        
        project = list(filter(None, request.path.split('/')))[1]
        
        qs = None
        if project == 'fcw_training':
            qs = FCWTrainModel.objects.all()
        elif project == 'fcw_testing':
            qs = FCWTestModel.objects.all()
        elif project == 'apacorner':
            qs = APACornerModel.objects.all()
        elif project == 'bsd_training':
            qs = BSDTrainModel.objects.all()
        elif project == 'dms_training':
            qs = DMSTrainModel.objects.all()

        id_list = list(qs.values_list('task_id', flat=True))

        tasks_query_set = list(TaskModel.objects.prefetch_related('segment_set').filter(id__in=id_list).order_by('-created_date').all())
        if filter_name is not None:
            tasks_query_set = list(filter(lambda x: filter_name.lower() in x.name.lower() and \
                                                    filter_packagename.lower() in x.packagename.lower() and \
                                                    filter_nickname.lower() in x.nickname.lower() and \
                                                    filter_createdate in datetime.strftime(x.created_date, '%Y/%m/%d'), tasks_query_set))
        data = []
        for task in tasks_query_set:
            task_info = {}
            MainTaskInfo(task, task_info)
            DetailTaskInfo(request, task, task_info)
            data.append(task_info)

        return render(request, 'dashboard/dashboard.html', {
            'project': project,
            'data': data,
            'max_upload_size': settings.LOCAL_LOAD_MAX_FILES_SIZE,
            'max_upload_count': settings.LOCAL_LOAD_MAX_FILES_COUNT,
            'share_path': os.getenv('CVAT_SHARE_URL', default=r'${cvat_root}/share'),
            'js_3rdparty': JS_3RDPARTY.get('dashboard', [])
        })
    except Exception as e:
        print(str(e))
        return HttpResponseBadRequest(str(e))
