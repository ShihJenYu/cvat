

def main():
    sFilename = r'FCW_Setting_training20181016.ini'
    dictItemStrMap = {}
    dictIDItemMap = {}

    with open(sFilename, 'r') as file:
        for line in file:
            if 'Item' in line:
                if '_ID' in line:
                    nIDNum = int(line.strip().split('=')[-1])
                    nItemNum = int((line.strip().split('Item')[-1].split('_ID=')[0]))
                    dictIDItemMap[nIDNum] = nItemNum
                else:
                    nItemNum = int(line.strip().split('Item')[-1].split('=')[0])
                    sItemStr = line.strip().split('=')[-1]
                    dictItemStrMap[nItemNum] = sItemStr

            if 'SubType' in line:
                break

    with open(sFilename.replace('.ini', '_check.txt'), 'w') as file:
        file.write('%4s, %4s, %s\n' % ('ID', 'Item', 'Describe'))
        for ID in dictIDItemMap:
            file.write('%4d, %4d, %s\n' % (ID, dictIDItemMap[ID], dictItemStrMap[dictIDItemMap[ID]]))

if __name__ == '__main__':
    main()