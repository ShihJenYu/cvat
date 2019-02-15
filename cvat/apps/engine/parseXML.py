try:
    import xml.etree.cElementTree as ET
    print('use cElementTree')
except ImportError:
    import xml.etree.ElementTree as ET
    print('use ElementTree')


def parseFile(xml_file_path=None):
    #xml_file_path = r'/home/jeff/TestImg/20180320_15_50_52_603_001_F1045_00000.xml'

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
        print('A',pt_A,'pt_Bs',pt_Bs)
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
        print('obj: {} name: {} group: {}'.format(obj_id, objects[obj_id]['points'], objects[obj_id]['grouping']))
        z_order += 1

    return objects

