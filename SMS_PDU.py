import ubinascii
import math
import time

class SMSList():
    __PDUs = None
    __Debug = False
    __SMS = []
    GSM7_BASIC = ('@£$¥èéùìòÇ\nØø\rÅåΔ_ΦΓΛΩΠΨΣΘΞ\x1bÆæßÉ !\"#¤%&\'()*+,-./0123456789:;<=>?¡ABCDEFGHIJKLMNOPQRSTUVWXYZÄÖÑÜ`¿abcdefghijklmnopqrstuvwxyzäöñüà')
    GSM7_EXTENDED = {chr(0xFF): 0x0A,
                     #CR2: chr(0x0D),
                     '^':  chr(0x14),
                     #SS2: chr(0x1B),
                     '{':  chr(0x28),
                     '}':  chr(0x29),
                     '\\': chr(0x2F),
                     '[':  chr(0x3C),
                     '~':  chr(0x3D),
                     ']':  chr(0x3E),
                     '|':  chr(0x40),
                     '€':  chr(0x65)}
    
    def __init__(self, Debug = False):
        self.__Debug = Debug
    
    def CreateList(self, Size):
        self.__PDUs = [None] * Size
        
    def AddPDU(self, Index, Data):
        self.__PDUs[Index] = Data
        
    def Parse(self):
        SMSbF = []
        for n in range(len(self.__PDUs)):
            if self.__Debug:
                print(ubinascii.hexlify(self.__PDUs[n]))
            bf = self.__PDUs[n]
            # SMSC
            bf = bf[(bf[0] + 1):]
            if (bf[0] & 0x03) == 0:     # SMS-DELIVER or SMD-DELIVER-REPORT 
                UDH_present = (bf[0] & 0x40) >> 6
                if self.__Debug:
                    print('PDU type : {0:02X}'.format(bf[0]))
                    print('     UDH : {0}'.format(str(UDH_present)))
                bf = bf[1:]
                # Originator address            
                
                OABytes = int(math.ceil(bf[0] / 2))
                OA = bf[:OABytes + 2]
                addr = self.decodeAddress(OA)
                if self.__Debug:
                    print('Originator Address :   {0}    length {1:d} nibbles ({2:d} bytes), type {3:02X}'.format(addr, OA[0], OABytes, OA[1]))
                bf = bf[(OABytes + 2):]
                
                ProtocolID = bf[0]
                DataCoding = (bf[1] & 0x0C)
                if self.__Debug:
                    print('Data coding :  {0} '.format(DataCoding))
                
                bf = bf[2:]
                
                recb = bf[:7]
                
                recstr = self.decodeSemiOctets(recb, 7)
                received = self.convertDateTime(recstr)
                
                bf = bf[7:]
                SMS_text = None
                if UDH_present:
                    UDL = bf[0]
                    UDHL = bf[1]
                    bf = bf[2:]
                    UDH = bf[:UDHL]
                    if self.__Debug:
                        print('UDH :  {0} (ref {1:02X}, tot {2}, num {3}) '.format(ubinascii.hexlify(UDH), UDH[2], UDH[3], UDH[4]))
                    bf = bf[UDHL:]
                    if DataCoding == 0:        # GSM-7
                        shift = ((UDHL + 1) * 8) % 7
                        prevOctet = bf[0]
                        shift += 1
                        UD_septets = self.unpackSeptets(bf[1:], UDL, prevOctet, shift)
                        SMS_text = self.decodeGsm7(UD_septets)
                    elif DataCoding == 2:      # UCS2
                        SMS_text = self.decodeUcs2(bf, UDL)
                    else:
                        userdata = []
                        for b in bf:
                            userdata.append(chr(b))
                        SMS_text = ''.join(userdata)
                    SMSData = {}
                    SMSData['From'] = addr
                    SMSData['Received'] = received
                    SMSData['Text'] = SMS_text
                    SMSData['SIMID'] = n
                    SMSData['UDH_MID'] = int(UDH[2])
                    SMSData['UDH_MNum'] = int(UDH[4])
                    SMSData['UDH_MLen'] = int(UDH[3])
                    SMSbF.append(SMSData)
                    
                else:
                    TP_UDL = bf[0]
                    bf = bf[1:]
                    if DataCoding == 0:        # GSM-7
                        UD_septets = self.unpackSeptets(bf, TP_UDL)
                        SMS_text = self.decodeGsm7(UD_septets)
                    elif DataCoding == 2:      # UCS2
                        SMS_text = self.decodeUcs2(bf, TP_UDL)
                    else:
                        userdata = []
                        for b in bf:
                            userdata.append(chr(b))
                        SMS_text = ''.join(userdata)
                    SMSData = {}
                    SMSData['From'] = addr
                    SMSData['Received'] = received
                    SMSData['Text'] = SMS_text
                    SMSData['SIMID'] = n
                    SMSData['UDH_MID'] = None
                    SMSData['UDH_MNum'] = None
                    SMSData['UDH_MLen'] = None
                    SMSbF.append(SMSData)
                if self.__Debug:                            
                    print(SMS_text)
                    print('------')
        # Concatenating SMS
        n = int(0)
        while n < len(SMSbF) - 1:
            SMSitem = {}
            SMSitem['From'] = SMSbF[n]['From']
            SMSitem['Received'] = SMSbF[n]['Received']
            SMSitem['Parts'] = []
            if SMSbF[n]['UDH_MID'] != None:
                MID = SMSbF[n]['UDH_MID']
                M = list(filter(lambda it: it['UDH_MID'] == MID, SMSbF))
                SMSt =''
                for p in range(len(M)):
                    ps = next(item for item in M if item['UDH_MNum'] == (p + 1))
                    SMSt += ps['Text']
                    SMSitem['Parts'].append(n + 1)
                SMSitem['Text'] = SMSt
                n += len(M)
            else:
                SMSitem['Text'] = SMSbF[n]['Text']
                SMSitem['Parts'].append(n + 1)
                n += 1
            self.__SMS.append(SMSitem)
            
            
        SMSbF = None
        
            
    # https://github.com/faucamp/python-gsmmodem/blob/834c68b1387ca2c91e2210faa8f75526b39723b5/gsmmodem/pdu.py      
    def decodeAddress(self, AddrBytes, smscField = False):
        addrLen = AddrBytes[0]
        
        if addrLen > 0:
            toa = AddrBytes[1]
            ton = (toa & 0x70)    # bits 6,5,4 of type-of-address == type-of-number
            if ton == 0x50:       # Alphanumeric address
                septets = self.unpackSeptets(AddrBytes[2:], int(math.ceil(addrLen / 2)))
                return self.decodeGsm7(septets)
            else:
                if smscField:
                    addressValue = decodeSemiOctets(AddrBytes, addressLen-1)
                else:
                    if addrLen % 2:
                        addrLen = int(addrLen / 2) + 1
                    else:
                        addrLen = int(addrLen / 2)                
                    addressValue = self.decodeSemiOctets(AddrBytes[2:], addrLen)
                    addrLen += 1 # for the return value, add the toa byte
                if ton == 0x10: # International number
                    addressValue = '+' + addressValue
                return addressValue
        else:
            return None
        
    
    
    def unpackSeptets(self, septets, numberOfSeptets=None, prevOctet=None, shift=7):
        result = bytearray()    
        if type(septets) == str:
            septets = iter(rawStrToByteArray(septets))
        elif type(septets) == bytearray:
            septets = iter(septets)    
        if numberOfSeptets == None:        
            numberOfSeptets = MAX_INT # Loop until StopIteration
        i = 0
        for octet in septets:
            i += 1
            if shift == 7:
                shift = 1
                if prevOctet != None:                
                    result.append(prevOctet >> 1)            
                if i <= numberOfSeptets:
                    result.append(octet & 0x7F)
                    prevOctet = octet                
                if i == numberOfSeptets:
                    break
                else:
                    continue
            b = ((octet << shift) & 0x7F) | (prevOctet >> (8 - shift))
            
            prevOctet = octet        
            result.append(b)
            shift += 1
            
            if i == numberOfSeptets:
                break
        if shift == 7:
            b = prevOctet >> (8 - shift)
            if b:
                # The final septet value still needs to be unpacked
                result.append(b)        
        return result
            
    def decodeGsm7(self, encoded):
        result = []
        iterEncoded = iter(encoded)
        for b in iterEncoded:
            if b == 0x1B: # ESC - switch to extended table
                c = chr(next(iterEncoded))
                for char, value in dict.items(self.GSM7_EXTENDED):
                    if c == value:
                        result.append(char)
                        break
            else:
                result.append(self.GSM7_BASIC[b])
        return ''.join(result)
        
    def decodeSemiOctets(self, encodedNumber, numberOfOctets = None):
        number = []
        if type(encodedNumber) in (str, bytes):
            encodedNumber = bytearray(codecs.decode(encodedNumber, 'hex_codec'))
        i = 0
        for octet in encodedNumber:        
            hexVal = '{:02s}'.format(hex(octet)[2:])  
            number.append(hexVal[1])
            if hexVal[0] != 'f':
                number.append(hexVal[0])
            else:
                break
            if numberOfOctets != None:
                i += 1
                if i == numberOfOctets:
                    break
        return ''.join(number)
            
    def decodeUcs2(self, dataBytes, numBytes):
        userData = []
        i = 0
        
        try:
            while i < numBytes:
                userData.append(chr((next(dataBytes) << 8) | next(dataBytes)))
                i += 2
        except StopIteration:
            pass
        return ''.join(userData)
    
    def convertDateTime(self, DT_string):
        year = int(DT_string[:2]) + 2000
        month = int(DT_string[2:4])
        day = int(DT_string[4:6])
        hour = int(DT_string[6:8])
        minute = int(DT_string[8:10])
        second = int(DT_string[10:12])
        tmp = time.mktime((year,month, day, hour, minute, second, 0, 0))
        offs = (int(DT_string[12:14]) & 0x7F) * 900
        if (int(DT_string[12:14]) & 0x80) == 0x80:
            offs *= -1
        tmp += offs
        if self.__Debug:
            print(time.localtime(tmp))
        return tmp
        
        
    def __str__(self):
        for i in range(len(self.__SMS)):
            print('{0} ... {1}'.format(self.__SMS[i]['From'], time.localtime(self.__SMS[i]['Received'])))
            print(self.__SMS[i]['Text'])
            print()