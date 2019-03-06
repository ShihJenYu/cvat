""" MakeLMDB.py
Last modified by: Sean Kuo
Date last modified: 2018/9/xx
Python version: 2.7

Description:
Class to use create_annoset.py

Copyright 2018, oToBrite Electronic Inc.
"""

from Config.config import oToFCW_Config
from FCWData import oToFCWData
from YUVutils.functions import GetImage
from YUVReader.lib_yuv import get_FCW_ROI_list
from multiprocessing import Process
import argparse
import glob
import tqdm
import os

class oToFCW_LMDBMaker():
    def __init__(self, a_sScriptPath='/home/seankuo/caffe/jobs/create_data_FCW.sh',
                       a_sCaffeRoot='/home/seankuo/caffe',
                       a_sOutputDir='/home/ssd1/Seankuo/FCW/Data/lmdb',
                       a_sMapFile='/home/ssd1/Seankuo/FCW/Data/FCW_labelmap.prototxt'
                       ):
        self.i_sScriptPath = a_sScriptPath
        self.i_sCaffeRoot = a_sCaffeRoot
        self.i_sOutputDir = a_sOutputDir
        self.i_sMapFile = a_sMapFile
        self.i_sLabelType = 'detection'

    def Make(self, a_sRoot, a_sListFile, a_sLMDBName, a_bRedo):
        """!
        Run create_annoset.py to generate lmdb.

            @param a_sRoot: 'string' prefix to file paths
            @param a_sListFile: 'string' path to list file
            @param a_sLMDBName: 'string' name of created lmdb
            @param a_bRedo: 'bool' force to overwrite exists lmdb

        """
        sCmdStr = 'python2 '
        sCmdStr += '{}/scripts/create_annoset.py '.format(self.i_sCaffeRoot)
        sCmdStr += '--anno-type={} '.format(self.i_sLabelType)
        sCmdStr += '--label-map-file={} '.format(self.i_sMapFile)
        sCmdStr += '--check-label '
        sCmdStr += '--shuffle '
        sCmdStr += '--encode-type=bmp '
        sCmdStr += '--encoded '
        if a_bRedo:
            sCmdStr += '--redo '
        sCmdStr += '{} '.format(a_sRoot)
        sCmdStr += '{} '.format(a_sListFile)
        sCmdStr += '{} '.format(os.path.join(self.i_sOutputDir, a_sLMDBName))
        sCmdStr += '{}'.format(os.path.join(self.i_sCaffeRoot, 'data', 'lmdb'))

        os.system(sCmdStr)

def _MakeDir(a_listPath):
    """!
    Simplify for oa.path.join, os.path.exists and os.mkdir.

        @param a_listPath: 'list' of 'string's define the folder path

        @return sDirPath: 'string' path to the final folder
    """
    sDirPath = a_listPath[0]
    assert os.path.exists(sDirPath), 'Root path {} not found'.format(sDirPath)
    for SubFolderName in a_listPath[1:]:
        sDirPath = os.path.join(sDirPath, str(SubFolderName))
        if not os.path.exists(sDirPath):
            os.mkdir(sDirPath)
    return sDirPath

def _VideoDateNum(a_sVideoName):
    """!
    Convert video date to number.

        @param a_sVideoName: 'string' video name

        @return nVideoNum: 'int' video date as integer
    """
    return int(a_sVideoName[a_sVideoName.find('201'):a_sVideoName.find('201')+8])

def _DataPreparation(a_nRoINum, a_FCWConfig, a_sRawLabelRoot, a_sDataOutRoot, a_sLogFile):
    """!
    Read .csv, read bmp, and apply off-line augmentation to cropping.

    """
    listVideoName = os.listdir(a_sRawLabelRoot)
    # Remove video date before 20180200 for RoI 0,1 (no calibration data)
    if a_nRoINum in [0, 1]:
        listVideoName = [sVideoName for sVideoName in listVideoName if _VideoDateNum(sVideoName) > 20180200]

    listInputSize = a_FCWConfig.InputSize()[a_nRoINum]
    listCropSize = a_FCWConfig.CropSize()[a_nRoINum]

    ## for Debug
    #listVideoName = ['20180720_14_28_24_733_000']

    # Augmentation Parameters (in pixel)
    dictAugExtend = {0: {'LR': [-160, 160], 'TD': [-16, 16]},
                     1: {'LR': [-120, 120], 'TD': [-16, 16]},
                     2: {'LR': [0, 0], 'TD': [-25, 5]}}
    
    # For each video
    print('[DataPreparation] for RoI:', a_nRoINum)
    ProgressBar = tqdm.trange(len(listVideoName))
    for sVideoName in listVideoName:
        sVideoDir = os.path.join(a_sRawLabelRoot, sVideoName)
        # For each key frame
        listCSVName = [sCSVName for sCSVName in os.listdir(sVideoDir) if 'key_' in sCSVName]

        for sCSVName in listCSVName:
            ## for debug
            #if not '0249' in sCSVName:
            #    continue

            nFrameNum = int(sCSVName.split('_')[-1].split('.')[0])
            sCSVPath = os.path.join(sVideoDir, sCSVName)
            # using path tricks to get bmp path
            sImgPath = sCSVPath.replace('key_', '').replace('Labels', 'Images').replace('.csv', '.bmp')
            if not os.path.exists(sImgPath):
                GetImage(sVideoName, nFrameNum, save_path=sImgPath)

            # create fcw label obj for process
            FCW_LabelObj = oToFCWData(sImgPath, sCSVPath, a_bVerbose=True)

            # get crop center and size
            listCropCenter = a_FCWConfig.GetCropCenter(sVideoName, nFrameNum, a_nRoINum)

            sBmpOutDir = _MakeDir([a_sDataOutRoot, 'bmp', a_nRoINum, sVideoName])
            sXmlOutDir = _MakeDir([a_sDataOutRoot, 'xml', a_nRoINum, sVideoName])
            sImgSavePath = os.path.join(sBmpOutDir, sCSVName.replace('.csv', '.bmp'))
            sXmlSavePath = os.path.join(sXmlOutDir, sCSVName.replace('.csv', '.xml'))
                    
            ## compute crop region
            # shift crop center
            listCropCenter_new = [listCropCenter[0] + int(sum(dictAugExtend[a_nRoINum]['LR'])), listCropCenter[1] + int(sum(dictAugExtend[a_nRoINum]['TD']))]

            # Extend crop size
            listCropSize_extend = [listCropSize[0] + int(dictAugExtend[a_nRoINum]['LR'][1] - dictAugExtend[a_nRoINum]['LR'][0]),
                                   listCropSize[1] + int(dictAugExtend[a_nRoINum]['TD'][1] - dictAugExtend[a_nRoINum]['TD'][0]),]
            
            # correct the cropping ceter to prevent out of image
            listCropCenter_new[0] = max(listCropCenter_new[0], listCropSize_extend[0]//2)
            listCropCenter_new[0] = min(listCropCenter_new[0], 1280 - listCropSize_extend[0]//2)
            listCropCenter_new[1] = max(listCropCenter_new[1], listCropSize_extend[1]//2)
            listCropCenter_new[1] = min(listCropCenter_new[1], 720 - listCropSize_extend[1]//2)

            # compute target size
            nScaleRatio_0 = float(listCropSize[0]) / listInputSize[0]
            nScaleRatio_1 = float(listCropSize[1]) / listInputSize[1]
            listTargetSize = [int(listCropSize_extend[0]//nScaleRatio_0), int(listCropSize_extend[1]//nScaleRatio_1)]

            listCropRegion = [listCropCenter_new[0] - int(listCropSize_extend[0]//2), listCropCenter_new[1] - int(listCropSize_extend[1]//2),
                              listCropSize_extend[0], listCropSize_extend[1]]
        
            FCW_LabelObj.Export(listCropRegion, listTargetSize, a_nRoINum, sImgSavePath, sXmlSavePath)

        ProgressBar.update(1)

    print('[_DataPreparation] for RoI {} Done.'.format(a_nRoINum))
    with open(a_sLogFile, 'a') as fileLog:
        fileLog.write('[_DataPreparation.listCropSize_extend] for RoI {} is {}.\n'.format(a_nRoINum, [listTargetSize[0], listTargetSize[1]]))
        fileLog.write('[_DataPreparation] prefer_crop_size for RoI {} is {}.\n'.format(a_nRoINum, [float(listInputSize[0])/listTargetSize[0], float(listInputSize[1])/listTargetSize[1]]))

def _CreateList():
    '''!
    Return []

    '''
    pass

def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--recrop', default=False, action='store_true', help='re-crop all images')
    parser.add_argument('--MP', default=False, action='store_true', help='enable multi-process')
    return parser.parse_args()

def main():
    sRawLabelRoot = '/home/share/Seankuo/Data/FCW/Labels'
    sDataOutRoot = '/home/ssd1/Seankuo/FCW/Data'
    args = get_args()

    sLogFile = os.path.join(sDataOutRoot, 'MakeLMDB.log')
    if os.path.exists(sLogFile):
        os.remove(sLogFile)

    LMDBMaker = oToFCW_LMDBMaker()

    # Get config
    FCWConfig = oToFCW_Config()
    
    for nRoINum in [0, 1, 2]:
        # Datapreparation
        if args.recrop:
            if args.MP:
                p = Process(target=_DataPreparation, args=(nRoINum, FCWConfig, sRawLabelRoot, sDataOutRoot, sLogFile))
                p.start()
            else:
                _DataPreparation(nRoINum, FCWConfig, sRawLabelRoot, sDataOutRoot, sLogFile)

        # Create List
        sListName = 'FCW_lmdb_yuv_RoI_{}_InputSize_{}_{}.txt'.format(nRoINum, FCWConfig.InputSize()[nRoINum][0], FCWConfig.InputSize()[nRoINum][1])
        sListPath = os.path.join(sDataOutRoot, 'list', sListName)
        listBMP = sorted(glob.glob(os.path.join(sDataOutRoot, 'bmp', str(nRoINum), '*', '*.bmp')))
        listXML = sorted(glob.glob(os.path.join(sDataOutRoot, 'xml', str(nRoINum), '*', '*.xml')))
        with open(sListPath, 'w') as fileList:
            for sBMPPath, sXMLPath in zip(listBMP, listXML):
                # check
                assert os.path.basename(sBMPPath.split('.')[0]) == os.path.basename(sXMLPath.split('.')[0]), 'Check Failed.'
                fileList.write('{} {}\n'.format(sBMPPath.replace(sDataOutRoot, ''), sXMLPath.replace(sDataOutRoot, '')))
            
        # Make LMDB
        LMDBMaker.Make(sDataOutRoot, sListPath, sListName.replace('.txt', ''), True)

def QuickTest():
    print(_MakeDir(['/home/ssd1/Seankuo/FCW/Data','bmp','A', 'B', 'C']))

if __name__ == '__main__':
    main()
    #QuickTest()
