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
        tree = ET.parse(xml_file_path)
        root = tree.getroot()

        faces = root.findall("face")

        group_id = 1
        group_order = 1
        objects = []
        for face in faces:
            if face.find("rotation").text == '-1':
                continue
            face_obj = {}
            face_obj['points'] = []
            face_obj['attributes'] = {'rotation':''}
            
            face_obj['id'] = face.find("id").text
            face_obj['name'] = face.tag
            face_obj['attributes']['rotation'] = rotationMap(face.find("rotation").text)

            face_obj['grouping'] = ['{}-{}'.format(group_id, group_order)]
            
            points = face.findall("points/pt")
            for point in points:
                point_str = '{},{}'.format(point.find("x").text, point.find("y").text)
                face_obj['points'].append(point_str)

            objects.append(face_obj)
            group_order += 1

            features = face.findall("features/*")
            for feature in features:
                feature_obj = {}
                feature_obj['points'] = []
                feature_obj['attributes'] = {'occluded':''}

                feature_obj['id'] = feature.find("id").text
                feature_obj['name'] = feature.tag
                feature_obj['attributes']['occluded'] = occludedMap(feature.find("occluded").text)

                feature_obj['grouping'] = ['{}-{}'.format(group_id, group_order)]

                points = feature.findall("points/pt")
                for point in points:
                    point_str = '{},{}'.format(point.find("x").text, point.find("y").text)
                    feature_obj['points'].append(point_str)

                objects.append(feature_obj)
                group_order += 1

            group_id += 1
            group_order = 1

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