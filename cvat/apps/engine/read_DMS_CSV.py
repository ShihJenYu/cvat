import csv

def occludedMap(value):
    if value == '0':
        return 'Fully_Visible'
    elif value == '1':
        return 'Partly_Occluded'
    elif value == '2':
        return 'Largely_Occluded'
    else:
        return '-1'

def rotationMap(value):
    if value == '0':
        return '0'
    elif value == '1':
        return '45'
    elif value == '2':
        return '90'
    else:
        return '-1'

def pitchMap(value):
    if value == '0':
        return '平視'
    elif value == '1':
        return '抬頭'
    elif value == '2':
        return '低頭'
    else:
        return '-1'
        
def keyfaceMap(value):
    if value == '0':
        return False
    elif value == '1':
        return True
    else:
        return '-1'

EN_to_CH = {'face':'臉', 'nose':'鼻子', 'mouth':'嘴吧', 'cheek':'臉頰',
            'eye_left':'左眼睛', 'eye_right':'右眼睛', 'brow_left':'左眉毛', 'brow_right':'右眉毛'}
        

def parseFile(project=None, xml_file_path=None):
    objects = []
    ignoreFace_ids = []

    dict_groupId = {} # link to group
    dict_groupOrders = {}

    group_id = 1
    with open(xml_file_path, newline='') as csvfile:
        rows = csv.DictReader(csvfile)
        for row in rows:
            objects.append(row)
            if row['type'] == 'face':
                if row['rotation'] == '-1':
                    ignoreFace_ids.append(row['id'])
                else:
                    if not row['id'] in dict_groupId:
                        dict_groupId[row['id']] = group_id
                        dict_groupOrders[group_id] = []
                        group_id += 1
    response = []
    for obj in objects:
        if obj['link_id'] in ignoreFace_ids or obj['id'] in ignoreFace_ids:
            continue
        
        if obj['id'] in dict_groupId:
            gid = dict_groupId[obj['id']]
            obj['grouping'] = '{}-{}'.format(gid,len(dict_groupOrders[gid])+1)
            dict_groupOrders[gid].append(obj['id'])
        elif obj['link_id'] in dict_groupId:
            gid = dict_groupId[obj['link_id']]
            obj['grouping'] = '{}-{}'.format(gid,len(dict_groupOrders[gid])+1)
            dict_groupOrders[gid].append(obj['id'])

        obj['occluded'] = occludedMap(obj['occluded'])
        obj['rotation'] = rotationMap(obj['rotation'])
        obj['pitch'] = pitchMap(obj['pitch'])
        obj['key_face'] = keyfaceMap(obj['key_face'])

        obj['type'] = EN_to_CH[obj['type']]

        response.append(obj)

    print(response)
    return(response)