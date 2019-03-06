from django.apps import apps
from . import models

def get_ProjectModel(project):
    if project == 'fcw_training':
        return apps.get_model('engine', 'FCWTrain')
    elif project == 'bsd_training':
        return apps.get_model('engine', 'BSDTrain')
    elif project == 'dms_training':
        return apps.get_model('engine', 'DMSTrain')
    elif project == 'apacorner':
        return apps.get_model('engine', 'APACorner')
def get_FrameUserRecordModel(project):
    if project == 'fcw_training':
        return apps.get_model('engine', 'TaskFrameUserRecord')
    elif project == 'bsd_training':
        return apps.get_model('engine', 'BSDTrain_FrameUserRecord')
    elif project == 'dms_training':
        return apps.get_model('engine', 'DMSTrain_FrameUserRecord')
    elif project == 'apacorner':
        return apps.get_model('engine', 'APACorner_FrameUserRecord')

def new_ProjectObject(project):
    if project == 'fcw_training':
        return models.FCWTrain()
    elif project == 'bsd_training':
        return models.BSDTrain()
    elif project == 'dms_training':
        return models.DMSTrain()
    elif project == 'apacorner':
        return models.APACorner()
def new_FrameUserRecordObject(project):
    if project == 'fcw_training':
        return models.TaskFrameUserRecord()
    elif project == 'bsd_training':
        return models.BSDTrain_FrameUserRecord()
    elif project == 'dms_training':
        return models.DMSTrain_FrameUserRecord()
    elif project == 'apacorner':
        return models.APACorner_FrameUserRecord()

