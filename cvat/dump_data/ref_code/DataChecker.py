""" DataChecker.py
Last modified by: Sean Kuo
Date last modified: 2018/9/xx
Python version: 2.7

Description:
Script to visualize cropped image and xml file for check.

Copyright 2018, oToBrite Electronic Inc.
"""

import xml.sax
import glob
import cv2
import os

class FCWxmlReader(xml.sax.ContentHandler):
    """
    Reader for FCW xml label.

    """
    def __init__(self):
        """!
        Initail variables for each object

        """
        self.Objs = []
        self.BoxType = None
        self.CurrentData = None
        self.name = None
        self.ignore = None
        self.bbox = None
        self.carside = None
 
    def startElement(self, tag, attributes):
        self.CurrentData = tag
        if self.CurrentData == 'object':
            self.clear()
        if self.CurrentData in ['carbndbox', 'carfrontpoint', 'carfronttotallytruncatedpoint']:
            self.BoxType = tag

    def endElement(self, tag):
        if tag == 'object':
            # create dict obj
            obj = {}
            obj['name'] = self.name
            obj['ignore'] = self.ignore
            obj['bbox'] = self.bbox
            obj['carside'] = self.carside
            self.Objs.append(obj)

    def characters(self, content):
        if self.CurrentData == 'name':
            self.name = content
        
        if self.CurrentData == 'car_ignore':
            self.ignore = int(content)

        if self.BoxType == 'carbndbox':
            if self.CurrentData == 'xmin':
                self.bbox = [int(content)]
            else:
                self.bbox.append(int(content))

        if self.BoxType == 'carfrontpoint':
            if self.CurrentData == 'x':
                self.carside = [int(content)]

        if self.BoxType == 'carfronttotallytruncatedpoint':
            if self.CurrentData == 'x':
                self.carside.append(int(content))

    def get_objs(self):
        return self.Objs

    def clear(self):
        self.CurrentData = None
        self.name = None
        self.ignore = None
        self.bbox = None
        self.carside = None


class FCW_xml_parser():
    def __init__(self):
        self.Handler = FCWxmlReader()
        self.parser = self.create_parser()

    def create_parser(self):
        # create XMLReader
        parser = xml.sax.make_parser()
        # turn off namespace
        parser.setFeature(xml.sax.handler.feature_namespaces, 0)
        # overwrite ContextHandler
        parser.setContentHandler(self.Handler)
        return parser

    def parse(self, xml_path):
        self.Handler.clear()
        self.parser.parse(xml_path)
        return self.Handler.get_objs()

def main():
    sRoot = '/home/share/Seankuo/Data/FCW/FCW'
    sImgDir = os.path.join(sRoot, 'JPEGImages')
    sIAnnoDir = os.path.join(sRoot, 'Annotations')

    XmlParser = FCW_xml_parser()

    sCrop = '2_2'

    sVideoName = '20180130_15_09_53_055_000'
    nFrameNum = 561

    sImgPath = os.path.join(sImgDir, sCrop, sVideoName, 'key_%s_%04d.bmp' % (sVideoName, nFrameNum))
    sXmlPath = os.path.join(sIAnnoDir, sCrop, sVideoName, 'key_%s_%04d.xml' % (sVideoName, nFrameNum))

    dictObjs = XmlParser.parse(sXmlPath)

    imgRaw = cv2.imread(sImgPath)
    for obj in dictObjs:
        bbox = obj['bbox']
        cv2.rectangle(imgRaw, (bbox[0], bbox[1]), (bbox[2], bbox[3]), (255, 255, 0), 1)

    cv2.imshow('imshow', imgRaw)
    cv2.waitKey()

if __name__ == '__main__':
    main()