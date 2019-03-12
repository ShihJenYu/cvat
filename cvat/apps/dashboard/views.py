
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

import os, time
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
    # dst_dict["packagename"] = task.packagename
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

def DetailTaskInfo(href, task, dst_dict):
    # scheme = request.scheme
    # host = request.get_host()
    dst_dict['segments'] = []

    url_base = href.replace('dashboard/','')

    project = href.split('/')[-1] #list(filter(None, request.path.split('/')))[-1]

    for segment in task.segment_set.all():
        for job in segment.job_set.all():
            #segment_url = "{0}://{1}/{2}/?id={3}".format(scheme, host, project, job.id)
            #url_fcw = "{0}://{1}/fcw?id={2}".format(scheme, host, job.id)
            #url_fcw = "{0}://{1}/{2}/".format(scheme, host, project)
            #url_fcw_key = "{0}://{1}/{2}/?id={3}&setKey=true".format(scheme, host, project, job.id)
            url = "{}/?id={}&setKey=true".format(url_base, job.id)
            
            dst_dict["segments"].append({
                'id': job.id,
                'start': segment.start_frame,
                'stop': segment.stop_frame,
                'url': url
                # 'url': segment_url,
                # 'url_fcw': url_fcw,
                # 'url_fcw_key': url_fcw_key,
            })

    # db_labels = task.label_set.prefetch_related('attributespec_set').all()
    # attributes = {}
    # for db_label in db_labels:
    #     attributes[db_label.id] = {}
    #     for db_attrspec in db_label.attributespec_set.all():
    #         attributes[db_label.id][db_attrspec.id] = db_attrspec.text

    # dst_dict['labels'] = attributes

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
    
    print('heeeeeeeeee')
    packagenames = list(models.TaskPackage.objects.filter(task_id=task.id).values_list('packagename__packagename', flat=True))
    # packagenames = task.packagename
    # packagenames = list(filter(None, packagenames.split(',')))
    # if not 'default' in packagenames:
    #     packagenames.append('default')
    if packagenames == []:
        packagenames.append('NULL')

    packstage = []
    for packagename in packagenames:
        pack_keyFrame = db_keyFrame.filter(packagename=packagename)
        keyframe_count = pack_keyFrame.count()
        checked_count = pack_keyFrame.filter(checked=True).count()
        need_modify_count = pack_keyFrame.filter(need_modify=True).count()
        unchecked_frames = list(pack_keyFrame.filter(user_submit=True).values_list('frame', flat=True))
        unchecked_count = len(unchecked_frames)
        unchecked_realframes = [ get_realframe(task.id, frame) for frame in unchecked_frames ]
        
        if project in ['fcw_testing', 'apacorner', 'dms_training']:
            if db_Project.user_submit == True:
                undo_count = 0
                unchecked_count = keyframe_count - checked_count - need_modify_count
            else:
                undo_count = keyframe_count - checked_count - need_modify_count
                unchecked_count = 0

        packstage.append({'packagename': packagename,
                        'keyframe_count': keyframe_count,
                        'unchecked_count':unchecked_count,
                        'checked_count': checked_count,
                        'need_modify_count': need_modify_count,
                        'undo_count': keyframe_count - unchecked_count - checked_count - need_modify_count,
                        'unchecked_realframes': unchecked_realframes})

    dst_dict['videostage'] = {
        # 'keyframe_count': db_Project.keyframe_count,
        # 'undo_count': db_Project.keyframe_count - db_Project.unchecked_count - db_Project.checked_count - db_Project.need_modify_count,
        # 'unchecked_count': db_Project.unchecked_count,
        # 'checked_count': db_Project.checked_count,
        # 'need_modify_count': db_Project.need_modify_count,
        'packstage': packstage,
        # 'priority': db_Project.priority,
        # 'priority_out': db_Project.priority_out,
    }


@login_required
@permission_required('engine.add_task', raise_exception=True)
def DashboardView(request):
    try:        
        project = list(filter(None, request.path.split('/')))[1]

        packages = getProjectPackage(project)

        return render(request, 'dashboard/dashboard.html', {
            'project': project,
            'packages': packages,
            'max_upload_size': settings.LOCAL_LOAD_MAX_FILES_SIZE,
            'max_upload_count': settings.LOCAL_LOAD_MAX_FILES_COUNT,
            'share_path': os.getenv('CVAT_SHARE_URL', default=r'${cvat_root}/share'),
            'js_3rdparty': JS_3RDPARTY.get('dashboard', [])
        })
    except Exception as e:
        print(str(e))
        return HttpResponseBadRequest(str(e))

@login_required
@permission_required('engine.add_task', raise_exception=True)
def newDashboardView(request):
    try:

        params = request.POST.dict()
        packagename = params['packagename']
        project = params['project']
        href = params['href']

        print('sssssssssssss')
        print('packagename',packagename)
        print('project',project)
        print('href',href)

        package_id = models.PackagePriority.objects.get(packagename=packagename).id
        print('package_id',package_id)
        tasks_per_package = models.TaskPackage.objects.filter(packagename_id=package_id)

        data = []
        for task_per_package in tasks_per_package:
            task_info = {}
            MainTaskInfo(task_per_package.task, task_info)
            DetailTaskInfo(href, task_per_package.task, task_info)
            data.append(task_info)

        return JsonResponse({'project':project, 'data':data}, safe=False)

    except Exception as e:
        print(str(e))
        return HttpResponseBadRequest(str(e))

@login_required
@permission_required('engine.add_task', raise_exception=True)
def searchDashboardView(request):
    try:

        params = request.POST.dict()
        href = params['href']
        project = params['project']
        taskname = params['taskname']

        id_list = None
        if project == 'fcw_training':
            id_list = list(FCWTrainModel.objects.values_list('task_id', flat=True))
        elif project == 'fcw_testing':
            id_list = list(FCWTestModel.objects.values_list('task_id', flat=True))
        elif project == 'apacorner':
            id_list = list(APACornerModel.objects.values_list('task_id', flat=True))
        elif project == 'bsd_training':
            id_list = list(BSDTrainModel.objects.values_list('task_id', flat=True))
        elif project == 'dms_training':
            id_list = list(DMSTrainModel.objects.values_list('task_id', flat=True))

        packagenames = list(filter(None, params['packagenames'].split(',')))

        print('search with project:{}, taskname:{}, packagenames:{}'.format(project, taskname, packagenames))

        start_time = time.time()
        tasks = None
        if packagenames:
            print("in here",taskname,packagenames)
            tasks = models.Task.objects.filter(name__icontains=taskname, id__in=id_list, taskpackage__packagename__packagename__in=packagenames)
        else:
            print("in hereB",taskname)
            tasks = models.Task.objects.filter(name__icontains=taskname, id__in=id_list, taskpackage=None)
        data = []
        #print('tasks id:',tasks.id," tasks name:" tasks.name)
        used_tasks = []
        for task in tasks:
            if task.id in used_tasks:
                continue
            else:
                used_tasks.append(task.id)
            task_info = {}
            print('doing now')
            MainTaskInfo(task, task_info)
            print('doing there',task)
            DetailTaskInfo(href, task, task_info)
            data.append(task_info)

        print("----- searchDashboardView cost: {} s -----".format(time.time() - start_time))

        return JsonResponse({'project':project, 'data':data}, safe=False)

    except Exception as e:
        print(str(e))
        return HttpResponseBadRequest(str(e))

@login_required
@permission_required('engine.add_task', raise_exception=True)
def setPackagePriority(request):
    try:
        print('setPackagePriority start')
        
        params = request.POST.dict()
        project = params['project']
        packagenames = params['packagenames'].split(',')
        office_priority = params['office_priority']
        soho_priority = params['soho_priority']

        print('packagenames',packagenames)
        print('office_priority',office_priority)
        print('soho_priority',soho_priority)

        db_packages = models.PackagePriority.objects.filter(packagename__in=packagenames)
        for package in db_packages:
            package.office_priority = office_priority
            package.soho_priority = soho_priority
            package.save()

        print('setPackagePriority done')

        packages = getProjectPackage(project)

        return JsonResponse({'packages':packages}, safe=False)

    except Exception as e:
        print(str(e))
        return HttpResponseBadRequest(str(e))


@login_required
@permission_required('engine.add_task', raise_exception=True)
def getAllPackagePriority(request):
    try:
        params = request.POST.dict()
        project = params['project']
        packages = getProjectPackage(project)

        return JsonResponse({'packages':packages}, safe=False)

    except Exception as e:
        print(str(e))
        return HttpResponseBadRequest(str(e))

def getProjectPackage(project):

    print('getProjectPackage start')

    id_list = None
    if project == 'fcw_training':
        id_list = list(FCWTrainModel.objects.values_list('task_id', flat=True))
    elif project == 'fcw_testing':
        id_list = list(FCWTestModel.objects.values_list('task_id', flat=True))
    elif project == 'apacorner':
        id_list = list(APACornerModel.objects.values_list('task_id', flat=True))
    elif project == 'bsd_training':
        id_list = list(BSDTrainModel.objects.values_list('task_id', flat=True))
    elif project == 'dms_training':
        id_list = list(DMSTrainModel.objects.values_list('task_id', flat=True))

    packages = []
    packages_names = []

    taskPackages = models.TaskPackage.objects.filter(task_id__in=id_list)
    for taskPackage in taskPackages:
        name = taskPackage.packagename.packagename
        if not name in packages_names:
            packages_names.append(name)
            packages.append({'name':name,
                            'office':taskPackage.packagename.office_priority,
                            'soho':taskPackage.packagename.soho_priority})
    
    print('getProjectPackage done')

    return packages


