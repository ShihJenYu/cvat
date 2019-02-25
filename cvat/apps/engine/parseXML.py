import xml.etree.ElementTree as ET

def parseFile(project=None, xml_file_path=None):
    
    if project == 'apacorner':
        objects = {}

        object_elements = {}
        object_elements['points'] = []
        object_elements['grouping'] = []
        point_count = 0
        point_x = None
        point_y = None

        for event, elem in ET.iterparse(xml_file_path):
            if event == 'end':
                if elem.tag == 'name':
                    object_elements['name'] = elem.text if elem.text else ''
                elif elem.tag == 'deleted':
                    object_elements['deleted'] = int(elem.text) if elem.text else ''
                # elif elem.tag == 'verified':
                #     object_elements['verified'] = int(elem.text) if elem.text else ''
                # elif elem.tag == 'occluded':
                #     object_elements['occluded'] = elem.text if elem.text else ''
                elif elem.tag == 'attributes':
                    object_elements['attributes'] = elem.text if elem.text else ''
                elif elem.tag == 'hasparts':
                    object_elements['hasparts'] = list(filter(None, elem.text.split(','))) if elem.text else []
                elif elem.tag == 'ispartof':
                    object_elements['ispartof'] = list(filter(None, elem.text.split(','))) if elem.text else []
                # elif elem.tag == 'date':
                #     object_elements['date'] = elem.text if elem.text else ''
                elif elem.tag == 'id':
                    object_elements['id'] = elem.text if elem.text else ''
                elif elem.tag == 'username':
                    object_elements['username'] = elem.text if elem.text else ''
                elif elem.tag == 'x':
                    point_count += 1
                    point_x = int(elem.text) if elem.text else None
                elif elem.tag == 'y':
                    point_y = int(elem.text) if elem.text else None
                elif elem.tag == 'pt':
                    object_elements['points'].append('{},{}'.format(point_x, point_y))
                    point_x = None
                    point_y = None
                elif elem.tag == 'object':
                    if object_elements['id'] in objects:
                        raise Exception('has same object\'s id:{}'.format(object_elements['id']))
                    if not object_elements['deleted']:
                        objects[object_elements['id']] = object_elements
                    object_elements = {}
                    object_elements['points'] = []
                    object_elements['grouping'] = []
            elem.clear() # discard the element

        grouping_stauts = {}

        for obj_id, obj in objects.items():
            hasparts = obj['hasparts']
            ispartof = obj['ispartof']

            if len(ispartof) > 1:
                raise Exception('object\'s id:{} ispartof has multi'.format(obj_id))
            elif len(ispartof) == 1:
                try:
                    if obj_id in objects[ispartof[0]]['hasparts']:
                        if not ispartof[0] in grouping_stauts:
                            grouping_stauts[ispartof[0]] = []
                        grouping_stauts[ispartof[0]].append(obj_id)
                    else:
                        raise Exception('object\'s id:{} ispartof not match'.format(obj_id))
                except KeyError as name:
                    raise Exception('object\'s id:{} ispartof was deleted'.format(obj_id))
                except Exception as e:
                    raise e

        gid = 1
        iid = 1
        for pt_A, pt_Bs in grouping_stauts.items():
            objects[pt_A]['grouping'].append('{}-{}'.format(gid, iid))
            iid += 1
            for pt_B in pt_Bs:
                objects[pt_B]['grouping'].append('{}-{}'.format(gid, iid))
                iid += 1
            gid += 1
            iid = 1

        z_order = 1
        for obj_id, obj in objects.items():
            objects[obj_id]['occluded'] = False
            objects[obj_id]['z_order'] = z_order
            objects[obj_id]['points'] = " ".join(objects[obj_id]['points'])
            z_order += 1

        return objects

    elif project == 'dms_training':
        objects = []
        object_elements = {}
        for event, elem in ET.iterparse(xml_file_path,events=['start','end']):
            if event == 'start':
                if elem.tag in ['face', 'eye_left', 'eye_right', 'brow_left', 'brow_right', 'nose', 'mouth', 'cheek']:
                    if object_elements == {}:
                        pass
                    else:
                        objects.append(object_elements)
                    object_elements = {}
                    object_elements['id'] = ''
                    object_elements['name'] = elem.tag
                    object_elements['points'] = []
                    object_elements['attributes'] = {'rotation':'', 'occluded':''}
                    object_elements['grouping'] = []
                elif elem.tag == 'id':
                    object_elements['id'] =  elem.text if elem.text else ''
                elif elem.tag == 'rotation':
                    object_elements['attributes']['rotation'] = rotationMap(elem.text) if elem.text else ''
                elif elem.tag == 'occluded':
                    object_elements['attributes']['occluded'] = occludedMap(elem.text) if elem.text else ''
                elif elem.tag == 'x':
                    point_x = int(elem.text) if elem.text else None
                elif elem.tag == 'y':
                    point_y = int(elem.text) if elem.text else None
                    object_elements['points'].append('{},{}'.format(point_x, point_y))
            if event == 'end':
                if elem.tag in ['face', 'eye_left', 'eye_right', 'brow_left', 'brow_right', 'nose', 'mouth', 'cheek']:
                    if object_elements != None and object_elements != {}:
                        objects.append(object_elements)
                        object_elements = {}
            elem.clear()
        return objects

def occludedMap(value):
    if value == '0':
        return 'Fully_Visible'
    elif value == '1':
        return 'Partly_Occluded'
    elif value == '2':
        return 'Largely_Occluded'
    else:
        return 'Unknown'

def rotationMap(value):
    if value == '0':
        return '0'
    elif value == '1':
        return '30'
    elif value == '2':
        return '60'
    elif value == '3':
        return '90'
    else:
        return 'Unknown'