""" FCWData.py
Last modified by: Sean Kuo
Date last modified: 2018/9/xx
Python version: 2.7

Description:
Class to handle FCW data.

Copyright 2018, oToBrite Electronic Inc.
"""

from DataUtils import Csv2Dict, Obj2XmlDict, MakeFCWXml
import cv2
import os

class oToFCWData():
    """
    Class for apply data process for FCW data.

    """
    def __init__(self, a_sImagePath, a_sLabelPath, a_bVerbose=False):
        """!
        @param a_sImagePath: 'string' path to image
        @param a_LabelPath: 'string' path to label file (.csv)

        """
        self.i_bVerbose = a_bVerbose
        self.i_listLabelData = None
        self.i_dictLabelData = None

        self.i_sImagePath = a_sImagePath
        self.i_sLabelPath = a_sLabelPath
        self.__LoadLabel()

    def __LoadLabel(self):
        """!
        Load self.i_sLabelPath to dict format by corresponding functions.

        """
        if '.csv' in self.i_sLabelPath:
            self.i_listLabelData = Csv2Dict(self.i_sLabelPath)
            self.__CsvProcess()

    def __CsvProcess(self):
        """!
        Function to perform Type-Name mapping and ignore conditions

        """
        # Mapping for ID (ID == 'Type' in .csv)
        dictNameMap = {'car': [0, 2, 1, 3, # car
                               200, 201, # car_obst
                               12, 14, 13, 15, # truck
                               204, 205, # truck_obst
                               6, 8, 7, 9, # van
                               202, 203, # van_obst
                               18, 20, 19, 21, # bus
                               206, 207, # bus_obst
                               47, 55, # scooter
                               56, 57, # scooter_obst
                               60, 61, # constructive trcuk
                               62, 63, # constructive trcuk_obst
                               ],
                       'motorbike': [24, 26, 25, 27, # motor
                                     208,209, # motor_obst
                                     46, 50, # bike
                                     51, 52, # bike_obst
                                ],
                       'noridermotor': [210, # motor
                                        211, # bike
                                    ],
                       'ignore': [48, # noridermotor group
                                  49, # bike group
                                ]
                    }
        # ID which should link to others
        listFrontRear = [4, 35, # car
                         16, 37, # truck
                         10, 36, # van
                         22, 38, # bus
                         58, 59, # scooter
                         64, 65, # constructive trcuk
                         28, 39, # motor
                         53, 54, # bike
                    ]

        # ID Obstructed
        listObstructed = [200, 201, # car_obst
                          204, 205, # truck_obst
                          202, 203, # van_obst
                          206, 207, # bus_obst
                          56, 57, # scooter_obst
                          62, 63, # constructive trcuk_obst
                          208,209, # motor_obst
                          51, 52, # bike_obst
                          ]

        # make dict from list
        self.i_dictLabelData = {}
        for dictLabelData in self.i_listLabelData:
            # add car-body objects 
            # remove ID == 0 (key frame mark)
            if not (int(dictLabelData['Type']) in listFrontRear) and not (int(dictLabelData['ID']) == 0):
                self.i_dictLabelData[int(dictLabelData['ID'])] = dictLabelData.copy()
                assert not 0 in self.i_dictLabelData.keys()
        
        # add carside
        for dictLabelData in self.i_listLabelData:
            if int(dictLabelData['Type']) in listFrontRear:
                try:
                    self.i_dictLabelData[int(dictLabelData['LinkedID'])]['carside_x_left'] = int(dictLabelData['2DBB_tl_x'])
                    self.i_dictLabelData[int(dictLabelData['LinkedID'])]['carside_x_right'] = int(dictLabelData['2DBB_br_x'])
                except KeyError:
                    if self.i_bVerbose:
                        print(self.i_sLabelPath, 'Link target not found: ID:{}, Type:{}, LinkedID:{}'.format(int(dictLabelData['ID']), int(dictLabelData['Type']), int(dictLabelData['LinkedID'])))

        setUndefined = set()
        # add Name and ignore to self.i_listLabelData
        for nID in self.i_dictLabelData:
            dictLabelData = self.i_dictLabelData[nID]
            # find name
            for sName in dictNameMap:
                if int(dictLabelData['Type']) in dictNameMap[sName]:
                    self.i_dictLabelData[nID]['name'] = sName
            #assert 'name' in self.i_dictLabelData[nID], 'name not found for Type {}'.format(self.i_dictLabelData[nID]['Type'])

            self.i_dictLabelData[nID]['ignore'] = 0

            # store undefined type 
            if not 'name' in dictLabelData:
                setUndefined.add(nID)
            else:
                if dictLabelData['name'] in ['ignore', 'noridermotor']:
                    self.i_dictLabelData[nID]['name'] = 'noridermotor'
                    self.i_dictLabelData[nID]['ignore'] = 1
            # apply ignore condition
            if int(dictLabelData['Occluded']) == 2:
                self.i_dictLabelData[nID]['ignore'] = 1
            if int(dictLabelData['DontCare']) == 1:
                self.i_dictLabelData[nID]['ignore'] = 1
            if float(dictLabelData['Truncated']) > 0.7:
                self.i_dictLabelData[nID]['ignore'] = 1
            bBow_w = int(dictLabelData['2DBB_br_x']) - int(dictLabelData['2DBB_tl_x'])
            bBow_h = int(dictLabelData['2DBB_br_y']) - int(dictLabelData['2DBB_tl_y'])
            if min(bBow_w, bBow_h) < 8:
                self.i_dictLabelData[nID]['ignore'] = 1
        
        # remove undefined type
        for nID in setUndefined:
            del self.i_dictLabelData[nID]

        # delete Obstructed obj # in-dev
        for nID in list(self.i_dictLabelData.keys()):
            if int(self.i_dictLabelData[nID]['Type']) in listObstructed:
                del self.i_dictLabelData[nID]

        # check if all body have been linked
        for nID in self.i_dictLabelData:
            if self.i_dictLabelData[nID]['ignore'] == 0 and not self.i_dictLabelData[nID]['name'] == 'noridermotor':
                if not 'carside_x_left' in self.i_dictLabelData[nID]:
                    if self.i_bVerbose:
                        print('[oToFCWData.__CsvProcess]', '{} ID {} Type {} not been linked'.format(self.i_sLabelPath, nID, self.i_dictLabelData[nID]['Type']))
                    #assert 'carside_x_left' in self.i_dictLabelData[nID], 'ID {} not been linked'.format(nID)
                    self.i_dictLabelData[nID]['carside_ignore'] = True

    def Export(self, a_listCropRegion, a_listTargettSize, a_nRoINumber, a_sSavePath_img, a_sSavePath_xml, a_nOverlap_th=0.5, a_bDebug=False):
        """!
        Create cropped image xml and with fixed box coordinate according to crop region.

            @param a_listCropRegion: 'list' [tl_x, tl_y, w, h]
            @param a_listTargettSize: 'list' [target_w, target_h]
            @param a_nRoINumber: 'int' RoI number
            @param a_sSavePath_img: 'string' path to save cropped image
            @param a_sSavePath_xml: 'string' path to export .xml file
            @param a_nOverlap_th: 'float' threshold for ignore partial-cropped object (default = 0.5)
            @param a_bDebug: 'bool' True for show image instead of export xml (default = False)
        """

        listCropBBox = [a_listCropRegion[0], a_listCropRegion[1], a_listCropRegion[0] + a_listCropRegion[2], a_listCropRegion[1] + a_listCropRegion[3]]
        imgRaw = cv2.imread(self.i_sImagePath)
        imgCropped = imgRaw[listCropBBox[1]:listCropBBox[3],
                            listCropBBox[0]:listCropBBox[2],
                            :]
        imgResized = cv2.resize(imgCropped, (a_listTargettSize[0], a_listTargettSize[1]))

        nScale_w =  float(a_listTargettSize[0]) / a_listCropRegion[2]
        nScale_h =  float(a_listTargettSize[1]) / a_listCropRegion[3]

        # get obj in new coordinates
        listCroppedLabel = []
        for nID in self.i_dictLabelData:
            dictLabel = self.i_dictLabelData[nID].copy()
            listRawBBox = [int(dictLabel['2DBB_tl_x']), int(dictLabel['2DBB_tl_y']), int(dictLabel['2DBB_br_x']), int(dictLabel['2DBB_br_y'])]
            # compute IoU with crop region
            try:
                nIntersection = (_intersection(listRawBBox, listCropBBox)/float((listRawBBox[2] - listRawBBox[0]) * (listRawBBox[3] - listRawBBox[1])))
            except ZeroDivisionError:
                nIntersection = 0

            if nIntersection == 0:
                continue
            if nIntersection < a_nOverlap_th:
                dictLabel['ignore'] = 1

            # ignore invisible carside points
            if not 'carside_ignore' in dictLabel:
                if int(dictLabel['2DBB_br_y']) > (a_listCropRegion[1] + a_listCropRegion[3]) or dictLabel['ignore']:
                    dictLabel['carside_ignore'] = True
                else:
                    dictLabel['carside_ignore'] = False

            # coordinate shift
            dictLabel['2DBB_tl_x'] = int(max(0, int(dictLabel['2DBB_tl_x']) - a_listCropRegion[0]) * nScale_w)
            dictLabel['2DBB_tl_y'] = int(max(0, int(dictLabel['2DBB_tl_y']) - a_listCropRegion[1]) * nScale_h)
            dictLabel['2DBB_br_x'] = int(max(0, int(dictLabel['2DBB_br_x']) - a_listCropRegion[0]) * nScale_w)
            dictLabel['2DBB_br_y'] = int(max(0, int(dictLabel['2DBB_br_y']) - a_listCropRegion[1]) * nScale_h)

            dictLabel['2DBB_br_x'] = min(a_listTargettSize[0], int(dictLabel['2DBB_br_x']))
            dictLabel['2DBB_br_y'] = min(a_listTargettSize[1], int(dictLabel['2DBB_br_y']))

            if 'carside_x_left' in dictLabel:
                dictLabel['carside_x_left'] = int(max(0, int(dictLabel['carside_x_left']) - a_listCropRegion[0]) * nScale_w)
                dictLabel['carside_x_right'] = int(max(0, int(dictLabel['carside_x_right']) - a_listCropRegion[0]) * nScale_w)

            if a_bDebug:
                color = (255, 255, 0) if dictLabel['ignore'] == 0 else (0, 0, 255)
                cv2.rectangle(imgResized, 
                            (dictLabel['2DBB_tl_x'] , dictLabel['2DBB_tl_y']),
                            (dictLabel['2DBB_br_x'] , dictLabel['2DBB_br_y']),
                            color)
                if 'carside_x_left' in dictLabel:
                    cv2.circle(imgResized, (dictLabel['carside_x_left'], dictLabel['2DBB_br_y']), 1, (0, 255, 255), 1)
                    cv2.circle(imgResized, (dictLabel['carside_x_right'], dictLabel['2DBB_br_y']), 1, (0, 255, 0), 1)
            listCroppedLabel.append(dictLabel)

        if a_bDebug:
            cv2.imshow('export', imgResized)
            cv2.waitKey()
        else:
            cv2.imwrite(a_sSavePath_img, imgResized)
            listCroppedLabel_new = Obj2XmlDict(listCroppedLabel)
            MakeFCWXml(listCroppedLabel_new, a_nRoINumber, a_listTargettSize[0], a_listTargettSize[1], a_sSavePath_xml)

def _intersection(a_listBBox1, a_listBBox2):
    """!
    Compute the intersection area size.

        @param a_listBBox1: 'list' [xmin, ymin, xmax, ymax]
        @param a_listBBox2: 'list' [xmin, ymin, xmax, ymax]
        @return nAreaOverlap: 'int' intersection area size
    """
    
    if a_listBBox1[2] < a_listBBox1[0] or a_listBBox1[3] < a_listBBox1[1] or a_listBBox2[2] < a_listBBox2[0] or a_listBBox2[3] < a_listBBox2[1]:
        return 0.
    nXmin_jac = float(max(a_listBBox1[0], a_listBBox2[0]))
    nYmin_jac = float(max(a_listBBox1[1], a_listBBox2[1]))
    nXmax_jac = float(min(a_listBBox1[2], a_listBBox2[2]))
    nYmax_jac = float(min(a_listBBox1[3], a_listBBox2[3]))
    nH_jac = max(float(nYmax_jac - nYmin_jac), 0)
    nW_jac = max(float(nXmax_jac - nXmin_jac), 0)
    nAreaOverlap = nH_jac * nW_jac

    return nAreaOverlap

def FCWData_test():
    sRefImgPath = '/home/share/Seankuo/Data/FCW/Images/20180130_15_09_53_055_000/20180130_15_09_53_055_000_0561.bmp'
    sRefCsvPath = '/home/share/Seankuo/Data/FCW/Labels/20180130_15_09_53_055_000/key_20180130_15_09_53_055_000_0561.csv'
    sImgSavePath = '/home/share/Seankuo/TEMP/FCW/img/20180130_15_09_53_055_000_0561.bmp'
    sCsvSavePath = '/home/share/Seankuo/TEMP/FCW/xml/20180130_15_09_53_055_000_0561.xml'
    FCWObj = oToFCWData(sRefImgPath, sRefCsvPath)
    listRoI = [640, 415, 1280, 580]
    listInputSize = [352, 160]
    #listRoI = [640, 179, 480, 240]
    #listInputSize = [256, 128]
    nRoINumber = 2
    listCropRoI = [int(listRoI[0] - listRoI[2]/2), int(listRoI[1] - listRoI[3]/2), listRoI[2], listRoI[3]]
    FCWObj.Export(listCropRoI, listInputSize, nRoINumber, sImgSavePath, sCsvSavePath)
    print('[FCWData_test] Done.')

if __name__ == '__main__':
    FCWData_test()
    