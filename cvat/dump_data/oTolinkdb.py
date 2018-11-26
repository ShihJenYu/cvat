# -*- coding: utf-8 -*-

""" oToLinkdb.py

Last modified by: Eric Lou
Date last modified: 2018/10/xx
Python version: 2.7

Description:
Function to link postgreSQL.

Copyright 2018, oToBrite Electronic Inc.
"""

import os
import re
import csv, math
import pickle
import psycopg2

class oToPostgreSQLData():
    """
    Class for Getting data from PostgreSQL database.
    """
    def __init__(self, a_sDatabase="cvat",
                       a_sUser="postgres",
                       a_sPassword="postgres0000",
                       a_sHost="localhost",
                       a_sPort="2345"):
        """!
            @param a_sDatabase: 'string' Database name
            @param a_sUser: 'string' Database user name
            @param a_sPassword: 'string' Database password
            @param a_sHost: 'string' Database host ip
            @param a_sPort: 'string' Database port
        """
        self.i_sDatabase = a_sDatabase
        self.i_sUser = a_sUser
        self.i_sPassword = a_sPassword
        self.i_sHost = a_sHost
        self.i_sPort = a_sPort

        self.i_oConnect = None
        self.i_dictVideoID_indb = None
        self.i_dictAttriID_indb = None
        self.i_listBboxID_indb = None
        self.i_dictBBox = None
        
        self.i_dictItemStrMap = None
        self.i_dictIDItemMap = None
        self.i_dictCarCarsideMap = None
        self.i_dictCarNoCarsideMap = None

        self.__Connect()

    def Read_Setting_Files(self, a_Setting_file):

        self.i_dictItemStrMap = {}
        self.i_dictIDItemMap = {}

        sFilename = a_Setting_file

        with open(sFilename, 'r') as file:
            for listline in file:
                if 'Item' in listline:
                    if '_ID' in listline:
                        nIDNum = int(listline.strip().split('=')[-1])
                        nItemNum = int((listline.strip().split('Item')[-1].split('_ID=')[0]))
                        self.i_dictIDItemMap[nIDNum] = nItemNum
                    else:
                        nItemNum = int(listline.strip().split('Item')[-1].split('=')[0])
                        sItemStr = listline.strip().split('=')[-1]
                        self.i_dictItemStrMap[nItemNum] = sItemStr

                if 'SubType' in listline:
                    break

        with open(sFilename.replace('.ini', '_check.txt'), 'w') as file:
            file.write('%4s, %4s, %s\n' % ('ID', 'Item', 'Describe'))
            for sID in self.i_dictIDItemMap:
                file.write('%4d, %4d, %s\n' % (sID, self.i_dictIDItemMap[sID], self.i_dictItemStrMap[self.i_dictIDItemMap[sID]]))
        
        self.i_dictCarCarsideMap = { 4: [ 0,  1,  2,  3, 200, 201], #   4 for 'car的車頭/車尾'
                                    10: [ 6,  7,  8,  9, 202, 203], #  10 for 'van的車頭/車尾'
                                    16: [12, 13, 14, 15, 204, 205], #  16 for 'truck的車頭/車尾'
                                    22: [18, 19, 20, 21, 206, 207], #  22 for 'bus的車頭/車尾'
                                    28: [24, 25, 26, 27, 208, 209], #  28 for 'motorBike的車頭/車尾' 
                                    53: [46, 50, 51, 52]          , #  53 for 'Bike的車頭/車尾'
                                    58: [47, 55, 56, 57]          , #  58 for '代步車的車頭/車尾'
                                    64: [60, 61, 62, 63]          , #  64 for '工程車的車頭/車尾'
                                   304: [300, 301, 302, 303]     , # 304 for '無殼三輪車的車頭/車尾'
                                   311: [307, 308, 309, 310]       # 311 for '有殼三輪車的車頭/車尾'
        }

        self.i_dictCarNoCarsideMap = { 35: [ 0,  1,  2,  3, 200, 201], #  35 for 'car_完全不見的車頭/車尾'
                                       36: [ 6,  7,  8,  9, 202, 203], #  36 for 'van_完全不見的車頭/車尾'
                                       37: [12, 13, 14, 15, 204, 205], #  37 for 'truck_完全不見的車頭/車尾'
                                       38: [18, 19, 20, 21, 206, 207], #  38 for 'bus_完全不見的車頭/車尾'
                                       39: [24, 25, 26, 27, 208, 209], #  39 for 'motorBike_完全不見的車頭/車尾' 
                                       54: [46, 50, 51, 52]          , #  54 for 'Bike_完全不見的車頭/車尾'
                                       59: [47, 55, 56, 57]          , #  59 for '代步車_完全不見的車頭/車尾'
                                       65: [60, 61, 62, 63]          , #  65 for '工程車_完全不見的車頭/車尾'
                                      305: [300, 301, 302, 303]      , # 305 for '無殼三輪車_完全不見的車頭/車尾'
                                      312: [307, 308, 309, 310]        # 312 for '有殼三輪車_完全不見的車頭/車尾'
        }  
        
    def __Connect(self):
        """!
        Connecting postgreSQL by psycopg2 functions.

        """
        self.i_oConnect = psycopg2.connect(database=self.i_sDatabase, 
                                           user=self.i_sUser, 
                                           password=self.i_sPassword, 
                                           host=self.i_sHost, 
                                           port=self.i_sPort)

        print("Opened PostgreSQL database successfully")

    def Cursor_from_db(self, 
                        a_listSELECT=["*"], a_sFROM="public.engine_labeledbox", 
                        a_sWHEREcolumn=None, a_listWHEREcolumnValue=None):
        """!
        This function is creating cursor to databse, creating simply postgreSQL code automatically
        and return usable cursor.

        In this versvion code, you may only use one column to select value you want.
        Such as frame id is 0, 4, 6. Only can select frame column.
        If a_sWHEREcolumn and a_listWHEREcolumnValue both is None, means no select by speific column.

            @param a_listSELECT: 'list' get data from database table by column names
            @param a_sFROM: 'string' Database table name
            @param a_sWHEREcolumn: 'string' Database password
            @param a_listWHEREcolumnValue: 'list' Database host ip
        """
        assert(a_listSELECT is not None), "Please entry the column you want to get data."
        assert(a_sFROM is not None), "Please entry the data_table you want to get data."

        sReqest_sql_code = "SELECT "

        # To assgin SELECT column you want to get
        for sSelect in a_listSELECT:
            if len(a_listSELECT) == 1: # if only one column you want to get
                sReqest_sql_code += str(sSelect) + " "
            else:
                if sSelect == a_listSELECT[len(a_listSELECT)-1]: # last column with out ", "
                    sReqest_sql_code += str(sSelect) + " "
                else:
                    sReqest_sql_code += str(sSelect) + ", "
        
        # To assgin database table you want to get, only get one once
        sReqest_sql_code += "FROM "
        sReqest_sql_code += a_sFROM + " "

        # Conditional Select by other column.
        if a_sWHEREcolumn is None and a_listWHEREcolumnValue is None:
            # No Select by other column.
            pass
        else:
            # Only select by one column in this version code.
            sReqest_sql_code += "WHERE "
            sReqest_sql_code += a_sWHEREcolumn + " IN "

            # Onlu select by one column in this version code.
            sReqest_sql_code += "("
            for sIndexValue in a_listWHEREcolumnValue:
                if len(a_listWHEREcolumnValue) == 1:
                    sReqest_sql_code += str(sIndexValue) # only one value.
                else:
                    # Mutiple value.
                    if sIndexValue == a_listWHEREcolumnValue[len(a_listWHEREcolumnValue)-1]:
                        sReqest_sql_code += str(sIndexValue)
                    else:
                        sReqest_sql_code += str(sIndexValue) + ", "
            sReqest_sql_code += ")"
        
        # print("PostgresSOL script: " + sReqest_sql_code + "\n")

        oCursor = self.i_oConnect.cursor() # use cursor to Get data from database.
        oCursor.execute(sReqest_sql_code)  # use postgreSQL script to get data.

        return oCursor

    def Get_Video_link_ID(self):
        """!
        To Get conversion table between Job_ID and videonames.
        Return a dictionary that videonames as key and ID as value.

            @param a_listCursor: 'list' get data from database table by column names.
        """

        oCursorIDname = self.Cursor_from_db(a_listSELECT=["id", "name"], a_sFROM="public.engine_task")
        listCursordata = oCursorIDname.fetchall()

        self.i_dictVideoID_indb = {}
        for listRow in listCursordata:
            # listRow[1] is Date, listRow[0] is Job_ID
            self.i_dictVideoID_indb[listRow[1]] = listRow[0]

        print("Dictionary about Job_Id and videonames being saved!")
        oCursorIDname.close()

    def Get_Attribute_Id(self):
        """!
        To Get Attribute repesent id in data base.
        Save to i_dictAttriID_indb
        """
        # To get Attribute Id from postgresql database.
        oCursorAttribute = self.Cursor_from_db(a_listSELECT=["*"], a_sFROM="public.engine_attributespec")
        listAttriId = oCursorAttribute.fetchall()

        self.i_dictAttriID_indb = {}
        for listRow in listAttriId:
            # use regular expression to get Attribute from Attribute table.
            sAttri = re.sub(pattern=":.*", repl="", string=listRow[1]) # content about attribute.
            sAttri = re.sub(pattern=".*=", repl="", string=sAttri)
            if sAttri not in self.i_dictAttriID_indb.keys():
                self.i_dictAttriID_indb[sAttri] = []
            self.i_dictAttriID_indb[sAttri].append(listRow[0])              # listRow[0] is attribute id in datatable.
            
        print("Dictionary about Label_Id and Attributed being saved!")
        
        oCursorAttribute.close()

    def Get_labelbox(self, a_listVideoDate):
        """!
        To Get BBox value by VideoDate that assgined.
        Return BBox, xtl, ytl, xbr, ybr and occluded value to instance varibale i_dictBBox.

            @param a_listVideoDate: 'list' The video date that you want to get Bbox.
        """

        # To Create dict for getting BBox value that videodate you sgin.
        # Create Date and Id first.
        self.i_dictBBox = {}
        for nDate in a_listVideoDate:
            nJob_ID = self.i_dictVideoID_indb[nDate]
            self.i_dictBBox[nJob_ID] = {}
            self.i_dictBBox[nJob_ID]["Date"] = nDate

        # Use Job_Id to get labeledbox from postgresql database
        listId_sql_index = self.i_dictBBox.keys()
        oCursorBBox = self.Cursor_from_db(a_listSELECT=["*"], a_sFROM="public.engine_labeledbox",
                                            a_sWHEREcolumn="job_id", a_listWHEREcolumnValue=listId_sql_index)
        listRawBBox = oCursorBBox.fetchall()

        # Put in BBox value also put in by previous attribute value got from Get_labelboxAttr function.
        self.i_listBboxID_indb = {}
        for listRow in listRawBBox:
            nJob_ID = listRow[7]
            nBBOX_ID = int(listRow[0])
            nframe = int(listRow[1])

            if nframe not in self.i_dictBBox[nJob_ID].keys():
                self.i_dictBBox[nJob_ID][nframe] = {}

            self.i_dictBBox[nJob_ID][nframe][nBBOX_ID] = {} # for put in BBox value.         
            self.i_dictBBox[nJob_ID][nframe][nBBOX_ID]["xtl"] = int(listRow[2])
            self.i_dictBBox[nJob_ID][nframe][nBBOX_ID]["ytl"] = int(listRow[3])
            self.i_dictBBox[nJob_ID][nframe][nBBOX_ID]["xbr"] = int(listRow[4])
            self.i_dictBBox[nJob_ID][nframe][nBBOX_ID]["ybr"] = int(listRow[5])
            
            # BBox id is index for put in BBox attributes.
            if nJob_ID not in self.i_listBboxID_indb.keys():
                self.i_listBboxID_indb[nJob_ID] = {}
            if nframe not in self.i_listBboxID_indb[nJob_ID]:
                self.i_listBboxID_indb[nJob_ID][nframe] = []
            self.i_listBboxID_indb[nJob_ID][nframe].append(nBBOX_ID) 
        
        print("Dictionary about RawBox data being saved!")

        oCursorBBox.close()

    def Get_labelboxAttr(self):
        """!
        To Get BBox Attritubes that BBox already downloaded by i_listBboxID_indb.
        Return Attritubes value to instance varibale i_dictBBox.
        """

        listBBoxID_to_get = []
        listBBoxID_by_frame = {}
        for nJob_ID in self.i_listBboxID_indb.keys():
            for nframe_num in self.i_listBboxID_indb[nJob_ID].keys():
                for nBBox_id in self.i_listBboxID_indb[nJob_ID][nframe_num]:
                    listBBoxID_to_get.append(nBBox_id)
                    listBBoxID_by_frame[nBBox_id] = [nJob_ID, nframe_num]

        # Use bbox_Id to get Bbox attribute from postgresql database.
        oCursorBBoxAttri = self.Cursor_from_db(a_listSELECT=["*"], a_sFROM="public.engine_labeledboxattributeval",
                                          a_sWHEREcolumn="box_id", a_listWHEREcolumnValue=listBBoxID_to_get)
        listRawBBoxAttri = oCursorBBoxAttri.fetchall()

        # To put in BBoxAttri value.
        listBBoxAttri = {}
        for listRow in listRawBBoxAttri:
            nBoxID = listRow[2]
            nAtrriID = listRow[3]
            nValue = listRow[1]

            # to match attribute name id in databaes.
            for sAttrName, nId in self.i_dictAttriID_indb.items():
                if nAtrriID in nId:
                    sAttriNameInDict = sAttrName
            if nBoxID not in listBBoxAttri.keys():
                listBBoxAttri[nBoxID] = {}
            listBBoxAttri[nBoxID][sAttriNameInDict] = nValue

        for nJob_ID in self.i_dictBBox.keys():
            for nframe_num in self.i_dictBBox[nJob_ID].keys():
                if nframe_num == 'Date':
                    continue
                for nBBox_id in self.i_dictBBox[nJob_ID][nframe_num].keys():
                    for sAttr in listBBoxAttri[nBBox_id].keys():
                        self.i_dictBBox[nJob_ID][nframe_num][nBBox_id][sAttr] = listBBoxAttri[nBBox_id][sAttr]

        print("Data about RawBox Attributes being saved!")

        oCursorBBoxAttri.close()    
    
    def CsvPreProcess(self, a_listVideoDate):
        """!
        To create carside points and Type-ID to instance varibale i_dictBBox that VideoDate assgined.

            @param a_listVideoDate: 'list' The video date that you want to convert carside object.
        """

        for nVideoDate in a_listVideoDate:
            if nVideoDate in self.i_dictVideoID_indb.keys():
                nVideoID = self.i_dictVideoID_indb[str(nVideoDate)]
                sCSV_OBJ_ID = 1 # ID for creating object data by row in csv files.
                for nframe_num in self.i_dictBBox[nVideoID].keys():

                    if nframe_num == 'Date':
                        continue
                    
                    for nOBJ_ID in self.i_dictBBox[nVideoID][nframe_num].keys():
                        
                        dictBBoxData = self.i_dictBBox[nVideoID][nframe_num]

                        dictBBoxData[nOBJ_ID]["CSV_ID"] = sCSV_OBJ_ID
                        sCSV_OBJ_ID += 1

                        # To convert Type ID number for csv.
                        sType_in_db = dictBBoxData[nOBJ_ID]['Type']

                        nItem_in_csv = self.i_dictItemStrMap.keys()[self.i_dictItemStrMap.values().index(sType_in_db)]
                        nID_in_csv = self.i_dictIDItemMap.keys()[self.i_dictIDItemMap.values().index(nItem_in_csv)]
                    
                        dictBBoxData[nOBJ_ID]['CSV_OBJ_ID'] = nID_in_csv

                        # To Convert absolute carSide X point.
                        nxmin = float(dictBBoxData[nOBJ_ID]['xtl'])
                        nxmax = float(dictBBoxData[nOBJ_ID]['xbr'])
                        nwidth = abs(nxmax - nxmin)

                        sCarside = dictBBoxData[nOBJ_ID]['DetectPoints'].split(" ")

                        if sCarside == ['-1,-1,', '-1,-1']:
                            nCarside_x_min = -1
                            nCarside_x_max = -1
                        else:
                            nCarside_x_point1 = float(re.sub('"', "", sCarside[0].split(",")[0]))
                            nCarside_x_point2 = float(re.sub('"', "", sCarside[1].split(",")[0]))

                            nCarside_x_min = int((min(nCarside_x_point1, nCarside_x_point2) * nwidth) + nxmin)
                            nCarside_x_max = int((max(nCarside_x_point1, nCarside_x_point2) * nwidth) + nxmin)

                        dictBBoxData[nOBJ_ID]['side_x_min'] = nCarside_x_min
                        dictBBoxData[nOBJ_ID]['side_x_max'] = nCarside_x_max   

        print("Csv pre-processing done!")           

    def CsvExport(self, a_listVideoDate, a_sSavePath_csv):
        """!
        To Export Csv files.

            @param a_listVideoDate: 'list' The video date that you want to convert carside object.
            @param a_sSavePath_csv: 's' The dir that you want to write out dir including csv files.
        """
        
        colnames = ["Version", "ID", "Type", "BBoxType", "SubType", "2DBB_tl_x", "2DBB_tl_y", "2DBB_br_x", "2DBB_br_y", 
                    "Location_x", "Location_y", "Location_z", "Dimension_x", "Dimension_y", "Dimension_z", 
                    "Alpha", "Rotation_y", "Occluded", "Truncated", "DontCare", "IsStartFrame", "IsEndFrame", "TrackingMethod", "LockPosition", "LinkedID"]

        for nVideoDate in a_listVideoDate:
            if nVideoDate in self.i_dictVideoID_indb.keys():
                nVideoID = self.i_dictVideoID_indb[str(nVideoDate)]
            
            # Create Dir by VideoDate
            sCSVDir = os.path.join(a_sSavePath_csv, nVideoDate)
            if not os.path.exists(sCSVDir):
                os.makedirs(sCSVDir)

            for nframe in self.i_dictBBox[nVideoID].keys():
                if nframe == 'Date':
                    continue

                sCSV_file_name = "key_%s_%04d.csv" %(nVideoDate, int(nframe)+1)
                sCSVPath = os.path.join(sCSVDir, sCSV_file_name)

                sCSV_show_file_name = re.sub("key_", "", sCSV_file_name)
                sCSV_show_file = os.path.join(sCSVDir, sCSV_show_file_name)

                # remove files that create by oToBrite Annotation Tool
                if os.path.exists(sCSV_show_file):
                    os.remove(sCSV_show_file)

                fileCSV = open(sCSVPath, mode='w')
                fileCSV = csv.writer(fileCSV, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
                fileCSV.writerow(colnames)

                for nID in self.i_dictBBox[nVideoID][nframe].keys():
                    
                    sCSVID = self.i_dictBBox[nVideoID][nframe][nID]['CSV_ID']
                    sType_ID = self.i_dictBBox[nVideoID][nframe][nID]['CSV_OBJ_ID']

                    stl_x = self.i_dictBBox[nVideoID][nframe][nID]['xtl']
                    stl_y = self.i_dictBBox[nVideoID][nframe][nID]['ytl']
                    sbr_x = self.i_dictBBox[nVideoID][nframe][nID]['xbr']
                    sbr_y = self.i_dictBBox[nVideoID][nframe][nID]['ybr']

                    nRawRotation = (float(self.i_dictBBox[nVideoID][nframe][nID]['Rotation']) / float(180)) * math.pi
                    if nRawRotation > 0:
                        sRotation_y = str(nRawRotation)[:-5]
                    else:
                        sRotation_y = str(nRawRotation)[:9]

                    if self.i_dictBBox[nVideoID][nframe][nID]['Occluded'] == 'Fully_Visible':
                        sOccluded = 0
                    elif self.i_dictBBox[nVideoID][nframe][nID]['Occluded'] == 'Partly_Occluded':
                        sOccluded = 1
                    elif self.i_dictBBox[nVideoID][nframe][nID]['Occluded'] == 'Largely_Occluded':
                        sOccluded = 2
                    elif self.i_dictBBox[nVideoID][nframe][nID]['Occluded'] == 'Unknown':
                        sOccluded = 3
                        
                    sTruncated = self.i_dictBBox[nVideoID][nframe][nID]['Truncated']

                    if self.i_dictBBox[nVideoID][nframe][nID]['Dont_Care'] == 'true':
                        sDontCare = 1
                    elif self.i_dictBBox[nVideoID][nframe][nID]['Dont_Care'] == 'false':
                        sDontCare = 0

                    col = [2, sCSVID, sType_ID, 2, 0,                     # "Version", "ID", "Type", "BBoxType", "SubType", 
                           stl_x, stl_y, sbr_x, sbr_y,                    # "2DBB_tl_x", "2DBB_tl_y", "2DBB_br_x", "2DBB_br_y", 
                           -1000000, -1000000, -1000000,                  # "Location_x", "Location_y", "Location_z", 
                           -1000000, -1000000, -1000000, -10,             # "Dimension_x", "Dimension_y", "Dimension_z", "Alpha",
                           sRotation_y, sOccluded, sTruncated, sDontCare, # "Rotation_y", "Occluded", "Truncated", "DontCare", 
                           0, 0, 0, 0, -1                                 # "IsStartFrame", "IsEndFrame", "TrackingMethod", "LockPosition", "LinkedID"]
                    ]
                    fileCSV.writerow(col)

                    sCarSideID = "5%03d" % sCSVID
                    sSide_stl_x = self.i_dictBBox[nVideoID][nframe][nID]['side_x_min']
                    sSide_sbr_x = self.i_dictBBox[nVideoID][nframe][nID]['side_x_max']

                    if sSide_stl_x == -1 and sSide_stl_x == -1:
                        continue

                    if self.i_dictBBox[nVideoID][nframe][nID]['Tolotally_NoCarSide'] == 'false':
                        dictCheckCarSide = self.i_dictCarCarsideMap
                    elif self.i_dictBBox[nVideoID][nframe][nID]['Tolotally_NoCarSide'] == 'true':
                        dictCheckCarSide = self.i_dictCarNoCarsideMap
                        if sbr_x < 640:
                            sSide_stl_x = 1
                            sSide_sbr_x = 1
                        if stl_x > 640:
                            sSide_stl_x = 1279
                            sSide_sbr_x = 1279

                    sSideType = None
                    for nCarID in dictCheckCarSide.keys():
                        if sType_ID in dictCheckCarSide[nCarID]:
                            sSideType = nCarID
                    if sSideType is None:
                        continue

                    col = [2, sCarSideID, sSideType, 2, 0,                # "Version", "ID", "Type", "BBoxType", "SubType", 
                           sSide_stl_x, stl_y, sSide_sbr_x, sbr_y,        # "2DBB_tl_x", "2DBB_tl_y", "2DBB_br_x", "2DBB_br_y", 
                           -1000000, -1000000, -1000000,                  # "Location_x", "Location_y", "Location_z", 
                           -1000000, -1000000, -1000000, -10,             # "Dimension_x", "Dimension_y", "Dimension_z", "Alpha",
                           sRotation_y, sOccluded, sTruncated, sDontCare, # "Rotation_y", "Occluded", "Truncated", "DontCare", 
                           0, 0, 0, 0, sCSVID                             # "IsStartFrame", "IsEndFrame", "TrackingMethod", "LockPosition", "LinkedID"]
                    ]
                    fileCSV.writerow(col)                        
            
if __name__ == '__main__':
    test = oToPostgreSQLData()
    test.Get_Video_link_ID()
    test.Get_Attribute_Id()

    FCW_Setting_file = r"/home/ericlou/CVAT/cvat_web/cvat/dump_data/FCW_Setting_training20181122.ini"
    CSV_write_out_dir = r"/home/share/Ericlou/Dataset/"

    test.Read_Setting_Files(a_Setting_file=FCW_Setting_file)

    listVideoToGet = ["20180526_19_34_52_392_000", "20180526_19_40_33_230_000"]
    test.Get_labelbox(a_listVideoDate=listVideoToGet)
    test.Get_labelboxAttr()
    test.CsvPreProcess(a_listVideoDate=listVideoToGet)
    test.CsvExport(a_listVideoDate=listVideoToGet, a_sSavePath_csv=CSV_write_out_dir)
    
    



   
    

    


