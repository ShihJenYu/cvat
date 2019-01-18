from django.shortcuts import render

# Create your views here.

from datetime import datetime
from ipware import get_client_ip

from cvat.apps.authentication.decorators import login_required
@login_required
def show_project_list(request):

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