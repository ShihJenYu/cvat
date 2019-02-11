from django.shortcuts import render

# Create your views here.

from datetime import datetime
from ipware import get_client_ip

import pytz

from django.contrib.auth.decorators import permission_required
from cvat.apps.authentication.decorators import login_required
from django.contrib.auth.models import User, Group
from cvat.apps.engine import models, task

from django.db.models import Q, Max, Min
from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponse, HttpResponseBadRequest, JsonResponse

@login_required
def show_project_list(request, raise_exception=True):

    client_ip, is_routable = get_client_ip(request)

    special_groups = ['user', 'admin', 'annotator', 'tester']
    projects = [x[3:] if x.startswith('oto',0,3) else x for x in list(request.user.groups.values_list('name',flat=True)) if not x in special_groups]
    projects = list(set(projects))
    permission = '管理員' if request.user.groups.filter(name='admin').exists() else '標記員'

    return render(request, 'others/select_project.html', {
        'username': request.user.username,
        'permission': permission,
        'ip': client_ip,
        'is_routable': is_routable,
        'projects': projects,
    })

@login_required
def efficiencyTable(request, raise_exception=True):
    try:
        username = request.user.username 
        isAdmin = request.user.groups.filter(name='admin').exists()
        
        params = request.POST.dict()
        response = {}
        efficiencyTable = []
        
        print(params)

        project = params['search_project']
        office = params['office']

        dateTime_str = params['startDate']
        print('start_str',dateTime_str)
        startDateTime = datetime.strptime(dateTime_str, '%Y-%m-%d %H:%M:%S.%f').replace(tzinfo=pytz.utc)
        
        dateTime_str = params['endDate']
        print('end_str',dateTime_str)
        endDateTime = datetime.strptime(dateTime_str, '%Y-%m-%d %H:%M:%S.%f').replace(tzinfo=pytz.utc)

        if isAdmin:
            project_group = project
            if office == 'Company':
                project_group = 'oto' + project
            
            users = list(User.objects.filter(groups__name=project_group).values_list('username', flat=True))
            admins = list(User.objects.filter(groups__name='admin').values_list('username', flat=True))

            users = list(filter(lambda x: x not in admins, users))

            for user in users:
                personEfficiency = getPersonEfficiency(user=user, project=project, startDateTime=startDateTime, endDateTime=endDateTime)
                efficiencyTable.append(personEfficiency)
        else:
            personEfficiency = getPersonEfficiency(user=username, project=project, startDateTime=startDateTime, endDateTime=endDateTime)
            efficiencyTable.append(personEfficiency)

        response = {'efficiencyTable':efficiencyTable}
        return JsonResponse(response, safe=False)

    except Exception as e:
        print("error is !!!!",str(e))
        return HttpResponseBadRequest(str(e))

def getPersonEfficiency(user=None, project=None, startDateTime=None, endDateTime=None):

    #時間內標記多少張（修改的送出時間先看 沒有的話看第一次送出時間）
    #時間內檢查好的有幾張 與上個相同 但是多了檢查好  >>>
    #時間內待修改還有幾張 與上個相同 但是多了待修改  >>>
    #時間內沒檢查還有幾張 與上個相同 但是多了以送出  >>>
    #用退件時間看 這時間內退了幾張
    #用完成時間看 這時間內完成幾張 ~~~ 這個算錢
    print('user',user)
    print('project',project)
    print('startDateTime',startDateTime)
    print('endDateTime',endDateTime)

    search_targets = None
    checked = None
    uncheck = None
    need_modify = None
    excellent = None
    terrible = None

    if project == 'fcw_training':
        search_targets = models.TaskFrameUserRecord.objects.filter(Q(user=user) & Q(current=False) & (Q(userModifySubmit_date__range=(startDateTime, endDateTime))|
                            (Q(userModifySubmit_date=None)&Q(userSubmit_date__range=(startDateTime, endDateTime)))))
        
        checked = search_targets.filter(checked=True)
        uncheck = search_targets.filter(user_submit=True)
        need_modify = search_targets.filter(need_modify=True)

        excellent = models.TaskFrameUserRecord.objects.filter(Q(user=user) & Q(current=False) & Q(checked_date__range=(startDateTime, endDateTime)))
        terrible = models.TaskFrameUserRecord.objects.filter(Q(user=user) & Q(current=False) & Q(need_modify_date__range=(startDateTime, endDateTime)))

    response = {'user':user,
                'search_targets':search_targets.count(),
                'search_targets_objs':getObjsCount(list(search_targets.values_list('task_id','frame'))),
                'checked': checked.count(),
                'checked_objs': getObjsCount(list(checked.values_list('task_id','frame'))),
                'uncheck': uncheck.count(),
                'uncheck_objs': getObjsCount(list(uncheck.values_list('task_id','frame'))),
                'need_modify': need_modify.count(),
                'need_modify_objs': getObjsCount(list(need_modify.values_list('task_id','frame'))),
                'excellent': excellent.count(),
                'excellent_objs': getObjsCount(list(excellent.values_list('task_id','frame'))),
                'terrible': terrible.count(),
                'terrible_objs': getObjsCount(list(terrible.values_list('task_id','frame'))),}
    return response


#getRealNameList(list(terrible.values_list('task_id','frame')))
def getRealNameList(arrTidsFrames=None):
    dictTidsFrames = {}
    realnames = []

    for tid, frame in arrTidsFrames:
        print('tid, frame',tid, frame)
        if not tid in dictTidsFrames:
            dictTidsFrames[tid] = []
            print(dictTidsFrames[tid])
        dictTidsFrames[tid].append(frame)

    for tid, frames in dictTidsFrames.items():
        qs = models.FrameName.objects.filter(frame__in=frames,task_id=tid)
        realnames.extend(list(qs.values_list('name', flat=True)))
    
    return realnames


def getObjsCount(arrTidsFrames=None):
    dictTidsFrames = {}
    counts = 0

    for tid, frame in arrTidsFrames:
        print('tid, frame',tid, frame)
        if not tid in dictTidsFrames:
            dictTidsFrames[tid] = []
            print(dictTidsFrames[tid])
        dictTidsFrames[tid].append(frame)

    for tid, frames in dictTidsFrames.items():
        qs = models.LabeledBox.objects.filter(frame__in=frames,job_id=tid)
        counts += qs.count()
    
    return counts


@login_required
@permission_required('engine.add_task', raise_exception=True)
def get_packagename(request, project):
    try:
        nameList = []
        print('nameList',nameList)
        if request.user.groups.filter(name='admin').exists():
            tid_list = None
            if project == 'fcw_training':
                tid_list = list(models.FCWTrain.objects.all().values_list('task_id', flat=True))
            elif project == 'bsd_training':
                tid_list = list(models.BSDTrain.objects.all().values_list('task_id', flat=True))
            elif project == 'fcw_testing':
                tid_list = list(models.FCWTest.objects.all().values_list('task_id', flat=True))
            elif project == 'apacorner':
                tid_list = list(models.APACorner.objects.all().values_list('task_id', flat=True))

            print('tid_list',tid_list)
            packagename_list = list(models.Task.objects.filter(id__in=tid_list).values_list('packagename', flat=True))
            print('packagename_list',packagename_list)
            for packagename in packagename_list:
                names = packagename.split(',')
                print('names',names)
                for name in names:
                    if not name in nameList:
                        nameList.append(name)
                        print('nameList',nameList)

        response = {'packagenames':nameList}
        return JsonResponse(response, safe=False)
    except Exception as e:
        print(str(e))
        return HttpResponseBadRequest(str(e))


@login_required
@permission_required('engine.add_task', raise_exception=True)
def get_workSpace(request, user, project):
    try:
        packagename = ''
        if request.user.groups.filter(name='admin').exists():
            try:
                packagename = ','.join(list(models.UserWorkSpace.objects.filter(username=user,project=project).values_list('packagename', flat=True)))
            except ObjectDoesNotExist:
                packagename = 'not found'

        response = {'packagename':packagename}
        return JsonResponse(response, safe=False)
    except Exception as e:
        print(str(e))
        return HttpResponseBadRequest(str(e))


@login_required
@permission_required('engine.add_task', raise_exception=True)
def get_workSpaceUsers(request, project, package):
    try:
        inWorkSpaceUsers = [] #project=project, packagename=package
        outWorkSpaceUsers = [] # all user exclude  if UserWorkSpace project=project will exclude, and
        if request.user.groups.filter(name='admin').exists():
            
            inWorkSpaceUsers = list(models.UserWorkSpace.objects.filter(project=project, packagename=package).values_list('username', flat=True))
            print('inWorkSpaceUsers',inWorkSpaceUsers)
            #sameProjectUsers = list(models.UserWorkSpace.objects.filter(project=project).values_list('username', flat=True))
            
            users = list(User.objects.filter(groups__name__icontains=project).values_list('username', flat=True))
            print('users',users)
            admins = list(User.objects.filter(groups__name='admin').values_list('username', flat=True))
            print('admins',admins)
            #outWorkSpaceUsers = list(filter(lambda x: x not in admins and x not in sameProjectUsers, users))
            outWorkSpaceUsers = list(filter(lambda x: x not in admins and x not in inWorkSpaceUsers, users))
            print('outWorkSpaceUsers',outWorkSpaceUsers)



        response = {'inWorkSpaceUsers':inWorkSpaceUsers,'outWorkSpaceUsers':outWorkSpaceUsers}
        return JsonResponse(response, safe=False)
    except Exception as e:
        print(str(e))
        return HttpResponseBadRequest(str(e))


@login_required
@permission_required('engine.add_task', raise_exception=True)
def set_workSpaceUsers(request):
    try:
        params = request.POST.dict()

        project = params['project']
        package = params['package']
        inUsers = list(filter(None, params['inUsers'].split(',')))
        outUsers = list(filter(None, params['outUsers'].split(',')))

        print('inUsers',inUsers)
        print('outUsers',outUsers)

        if outUsers:
            models.UserWorkSpace.objects.filter(Q(project=project) & Q(packagename=package) & Q(username__in=outUsers)).delete()
        
        if inUsers:
            preInWorkSpaceUsers = list(models.UserWorkSpace.objects.filter(project=project, packagename=package).values_list('username', flat=True))

            print('preInWorkSpaceUsers',preInWorkSpaceUsers)
            willInWorkSpaceUsers = list(filter(lambda x: x not in preInWorkSpaceUsers, inUsers))
            print('willInWorkSpaceUsers',willInWorkSpaceUsers)
            insert_list = []
            for user in willInWorkSpaceUsers:
                insert_list.append(models.UserWorkSpace(username=user,project=project,packagename=package))

            models.UserWorkSpace.objects.bulk_create(insert_list)
            print(insert_list)

        response = {'inUsers':inUsers,'outUsers':outUsers}
        return JsonResponse(response, safe=False)
    except Exception as e:
        print(str(e))
        return HttpResponseBadRequest(str(e))