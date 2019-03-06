""" DataUtils.py
Last modified by: Sean Kuo
Date last modified: 2018/9/xx
Python version: 2.7

Description:
Functions would used for generate xml file for FCW.

Copyright 2018, oToBrite Electronic Inc.
"""

import xml.etree.cElementTree as ET

def MakeFCWXml(a_listObjs, a_nROI_number, a_nWidth, a_nHeight, a_sSavePath):
    """!
    Create xml file. Using ugly key name here to keep pace with caffe code.

        @param a_listObjs: 'list' of dict_obj
        @param a_nROI_number: 'int' RoI number
        @param a_nWidth: 'int' width of image
        @param a_nHeight: 'int' height of image
        @param a_sSavePath: 'string' path to save xml file
    """

    e_annotation = ET.Element('annotation')
    e_size = ET.SubElement(e_annotation, 'size')
    ET.SubElement(e_size, 'width').text = str(a_nWidth)
    ET.SubElement(e_size, 'height').text = str(a_nHeight)
    ET.SubElement(e_size, 'depth').text = '3'
    ET.SubElement(e_annotation, 'segmented').text = '0'

    for dictObj in a_listObjs:
        e_obj = ET.SubElement(e_annotation, 'object')
        ET.SubElement(e_obj, 'name').text = dictObj['name']
        ET.SubElement(e_obj, 'difficult').text = str(dictObj['difficult'])
        ET.SubElement(e_obj, 'ROI_number').text = str(a_nROI_number)
        ET.SubElement(e_obj, 'car_ignore').text = str(dictObj['car_ignore'])
        # carbndbox 
        # object bounding box
        e_carbndbox = ET.SubElement(e_obj, 'carbndbox')
        ET.SubElement(e_carbndbox, 'xmin').text = str(dictObj['carbndbox']['xmin'])
        ET.SubElement(e_carbndbox, 'ymin').text = str(dictObj['carbndbox']['ymin'])
        ET.SubElement(e_carbndbox, 'xmax').text = str(dictObj['carbndbox']['xmax'])
        ET.SubElement(e_carbndbox, 'ymax').text = str(dictObj['carbndbox']['ymax'])
        # carfrontpoint
        # left carside for FCW
        # y equal to ymin of bounding box 
        e_carfrontpoint = ET.SubElement(e_obj,'carfrontpoint')
        ET.SubElement(e_carfrontpoint, 'flag').text = str(dictObj['carfrontpoint']['flag'])
        ET.SubElement(e_carfrontpoint, 'x').text = str(dictObj['carfrontpoint']['x'])
        ET.SubElement(e_carfrontpoint, 'y').text = str(dictObj['carfrontpoint']['y'])
        # lightbndbox 
        # not used for FCW, should all be -1
        e_lightbndbox = ET.SubElement(e_obj,'lightbndbox')
        ET.SubElement(e_lightbndbox, 'flag').text = str(dictObj['lightbndbox']['flag'])
        ET.SubElement(e_lightbndbox, 'xmin').text = str(dictObj['lightbndbox']['xmin'])
        ET.SubElement(e_lightbndbox, 'ymin').text = str(dictObj['lightbndbox']['ymin'])
        ET.SubElement(e_lightbndbox, 'xmax').text = str(dictObj['lightbndbox']['xmax'])
        ET.SubElement(e_lightbndbox, 'ymax').text = str(dictObj['lightbndbox']['ymax'])
        # carfronttotallytruncatedpoint
        # right carside for FCW
        # y equal to ymax of bounding box 
        e_carfronttotallytruncatedpoint = ET.SubElement(e_obj,'carfronttotallytruncatedpoint')
        ET.SubElement(e_carfronttotallytruncatedpoint, 'flag').text = str(dictObj['carfronttotallytruncatedpoint']['flag'])
        ET.SubElement(e_carfronttotallytruncatedpoint, 'x').text = str(dictObj['carfronttotallytruncatedpoint']['x'])
        ET.SubElement(e_carfronttotallytruncatedpoint, 'y').text = str(dictObj['carfronttotallytruncatedpoint']['y'])

    tree = ET.ElementTree(e_annotation)
    tree.write(a_sSavePath)


def Obj2XmlDict(a_listObjs):
    """!
    Make dict for MakeFCWXml ready from obj with meaningful key names.

        @param a_listObjs: 'list' with correct key names

        @return new_listObjs: 'dict' with ugly key name for MakeFCWXml
    """
    new_listObjs = []
    for dictObj in a_listObjs:
        dictObj_tmp = {}
        dictObj_tmp['name'] = dictObj['name']
        dictObj_tmp['difficult'] = 0 # not used
        dictObj_tmp['car_ignore'] = dictObj['ignore']
        # bounding box
        dictObj_tmp['carbndbox'] = {}
        dictObj_tmp['carbndbox']['xmin'] = dictObj['2DBB_tl_x']
        dictObj_tmp['carbndbox']['ymin'] = dictObj['2DBB_tl_y']
        dictObj_tmp['carbndbox']['xmax'] = dictObj['2DBB_br_x']
        dictObj_tmp['carbndbox']['ymax'] = dictObj['2DBB_br_y']
        # carsides
        dictObj_tmp['carfrontpoint'] = {}
        dictObj_tmp['carfronttotallytruncatedpoint'] = {}
        if dictObj['carside_ignore']:
            dictObj_tmp['carfrontpoint']['flag'] = 0
            dictObj_tmp['carfrontpoint']['x'] = -1
            dictObj_tmp['carfrontpoint']['y'] = -1
            dictObj_tmp['carfronttotallytruncatedpoint']['flag'] = 0
            dictObj_tmp['carfronttotallytruncatedpoint']['x'] = -1
            dictObj_tmp['carfronttotallytruncatedpoint']['y'] = -1
        else:
            # carside_left
            dictObj_tmp['carfrontpoint']['flag'] = 1
            try:
                dictObj_tmp['carfrontpoint']['x'] = dictObj['carside_x_left']
                dictObj_tmp['carfrontpoint']['y'] = dictObj['2DBB_tl_y']
            except:
                print(dictObj)
            # carside_right
            dictObj_tmp['carfronttotallytruncatedpoint']['flag'] = 1
            dictObj_tmp['carfronttotallytruncatedpoint']['x'] = dictObj['carside_x_right']
            dictObj_tmp['carfronttotallytruncatedpoint']['y'] = dictObj['2DBB_br_y']
        # lightbndbox (not used)
        dictObj_tmp['lightbndbox'] = {}
        dictObj_tmp['lightbndbox']['flag'] = 0
        dictObj_tmp['lightbndbox']['xmin'] = -1
        dictObj_tmp['lightbndbox']['ymin'] = -1
        dictObj_tmp['lightbndbox']['xmax'] = -1
        dictObj_tmp['lightbndbox']['ymax'] = -1

        new_listObjs.append(dictObj_tmp)
    return new_listObjs

def Csv2Dict(a_sCSVPath):
    """!
    Read csv file and save in dictionary.
    
        @param a_sCSVPath: 'string' path to csv file

        @return listCsvData: 'list' of 'dict' with label information
    """
    listCsvData = []
    with open(a_sCSVPath, 'r') as fileCSV:
        dictIndex2Key = {}
        for i, RowData in enumerate(fileCSV):
            dictRowData = {}
            listRowData = RowData.strip().split(',')
            for idx, Data in enumerate(listRowData):
                # get tag names
                if i == 0:
                    dictIndex2Key[idx] = Data
                # get values
                else:
                    dictRowData[dictIndex2Key[idx]] = Data
            if i > 0:
                listCsvData.append(dictRowData)

    return listCsvData

def DataUtils_test():
    sRefCsvPath = '/home/share/Seankuo/Data/FCW/Labels/20180404_09_50_23_227_002/key_20180404_09_50_23_227_002_0640.csv'
    print(Csv2Dict(sRefCsvPath))

if __name__ == '__main__':
    DataUtils_test()
    pass