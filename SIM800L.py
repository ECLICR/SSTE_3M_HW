import uasyncio
import time
from machine import RTC
from SMS_PDU import SMSList

class SIM800L():
    __UART = None
    __RSTP = None
    __swriter = None
    __sreader = None
    __response = None
    __communicator = None
    __status = 0
    __verbose = 0x17
    
    __moduleProductID = None
    __moduleRevision = None
    __IMEI = None
    __IMSI = None
    __CallReady = False
    __SMSReady = False
    
    __OperatorCode = None
    __OperatorName = None
    __CellID = None
    __RSSI = None
    __BER = None
    
    __DT = None
    
    __SMSReadRq = False
    __SMSCount = None
    __SMSTotal = 0
    
    __SMS = None
    
    def __init__(self, UART, RST_pin=None, verbose = 0x17):
        self.__UART = UART
        self.__RSTP = RST_pin
        self.__verbose = verbose
        
        self.__ReaderLoop = uasyncio.get_event_loop()
        self.__swriter = uasyncio.StreamWriter(self.__UART, ())
        self.__sreader = uasyncio.StreamReader(self.__UART)        
        
        print(" -> GSM activating ...                   ", end = '')
        if self.__RSTP != None:
            self.__RSTP.value(1)
        self.__SMS = SMSList(False)
        print('done')
        
        
        self.__comm = uasyncio.create_task(self.__CommunicatorLoopAsync())
        
    async def __CommunicatorLoopAsync(self):
        await uasyncio.sleep_ms(3000)
        # Module test
        while self.__response == None:
            await self.__Command('AT', 1)
        self.__status = 1
        print(' -> GSM module found')
        
        # Disable echo
        if self.__response[0] == 'AT':
            await self.__Command('ATE0')
        
        # Set report error with verbose
        await self.__Command('AT+CMEE=2')
        
        await self.__Command('AT+CREG=2')
        
        await self.__Command('AT+CLTS=1')
        
        # Module product information
        await self.__Command('ATI')
        while "" in self.__response:
            self.__response.remove('')
        self.__moduleProductID = self.__response[0]
        
        # Module revision
        await self.__Command('AT+CGMR')
        while "" in self.__response:
            self.__response.remove('')
        self.__moduleRevision = self.__response[0].split(':')[1]
        
        # IMEI
        await self.__Command('AT+GSN')        
        while "" in self.__response:
            self.__response.remove('')
        self.__IMEI = self.__response[0]
        
        print(' -> GSM module initialized')
        self.__status = 2
        
        
        # SIM Pin
        await uasyncio.sleep_ms(800)
        while True:
            await self.__Command('AT+CPIN?')
            if self.__response[1] == '+CPIN: READY':
                break
        
        print(' -> GSM module accept PIN')
        
        
        # IMSI
        await self.__Command('AT+CIMI')
        while "" in self.__response:
            self.__response.remove('')
        self.__IMSI = self.__response[0]
        
        self.__status = 3
        # Wait for network registration
        while self.__status == 3:
            try:
                await uasyncio.wait_for(self.__recv(), 0.5)
            except uasyncio.TimeoutError:
                pass
    
        await self.__Command('AT+CMGF=0')
    
        #await self.__Command('AT+CPMS?') # SMS message storage
        
        #await self.__Command('AT+CMGL=4,1', 10)
        
        
        
        
        
        #while True:
        #    await uasyncio.sleep_ms(10000) 
        
        
        
        
        while True:
            try:
                if self.__status == 4:
                    await self.__Command('AT+CSQ', 2)       # signal quality
                    await uasyncio.sleep_ms(333)
                    await self.__Command('AT+CREG?', 2)     # registration status
                    await uasyncio.sleep_ms(333)
                    await self.__Command('AT+CBC', 2)       # battery status
                    await uasyncio.sleep_ms(333)
                    if self.__SMSCount == None:
                        self.__status = 5
                    await uasyncio.wait_for(self.__recv(), 0.5)                    
                elif self.__status == 5:
                    await self.__Command('AT+CPMS?', 10)
                    while "" in self.__response:
                        self.__response.remove('')
                    for p in range(len(self.__response)):
                        if self.__response[p].startswith('+CPMS'):
                            p1 = self.__response[p].split(':')
                            p2 = p1[1].split(',')
                            self.__SMSCount = int(p2[1])
                            self.__SMSTotal = int(p2[2])
                            self.__SMS.CreateList(self.__SMSCount)
                            self.__status = 6
                elif self.__status == 6:
                    await self.__Command('AT+CMGL=4,1', 20)
                    if self.__response == None:
                        self.__status = 5;
                    else:
                        while "" in self.__response:
                            self.__response.remove('')
                        for p in range(len(self.__response)):
                            if self.__response[p].startswith('+CMGL:'):
                                p1 = self.__response[p].split(':')
                                p2 = p1[1].split(',')
                                smsID = int(p2[0])
                                p += 1
                                b = bytearray.fromhex(self.__response[p].strip())
                                self.__SMS.AddPDU(smsID - 1, b)
                        self.__SMS.Parse()
                        print(self.__SMS)
                        self.__status = 4                    
            except uasyncio.TimeoutError:
                pass
            
    async def __recv(self):
        while True:
            res = await self.__sreader.readline()
            ress = res.decode('utf-8').rstrip()
            processed = False
            
            if ress == 'Call Ready':
                self.__CallReady = True
                processed = True
            elif ress == 'SMS Ready':
                self.__SMSReady = True
                processed = True
            else:
                self.__response.append(ress)
                
            if ress == 'OK':
                if ((self.__status < 4 and self.__verbose & 0x01) or
                    (self.__status == 4 and self.__verbose & 0x02) or
                    (self.__status == 5 and self.__verbose & 0x04) ):
                        print('      - GSM rx: ', ress)
                break;
            
            elif ress.startswith('*PSUTTZ:'):
                p1 = ress.split(':')
                p2 = p1[1].split(',')
                tzv = p2[6].strip('"')
                tmp = time.mktime((int(p2[0]), int(p2[1]), int(p2[2]), int(p2[3]), int(p2[4]), int(p2[5]), 0, 0))
                tz = int(tzv) * 900
                self.__DT = tmp + tz
                v = time.localtime(self.__DT)
                rtc = RTC()
                rtc.datetime((v[0], v[1], v[2], 0, v[3], v[4], v[5], 0))
                processed = True

            elif ress.startswith('+CIEV:'):
                if self.__OperatorCode == None:
                    p1 = ress.split(':')
                    p2 = p1[1].split(',')
                    self.__OperatorCode = p2[1].strip('"')
                    self.__OperatorName = p2[2].strip('"')
                processed = True
                    
            elif ress.startswith('+CREG:'):               
                p1 = ress.split(':')
                p2 = p1[1].split(',')
                if len(p2) == 4:
                    p2.pop(0) # remove first item from list
                status = int(p2[0])
                if status == 1 or status == 5:
                    if self.__status < 4:
                        self.__status = 4
                    self.__CellID = int(p2[2].strip('"'), 16)
                else:
                    self.__CellID = None
                processed = True
             
            elif ress.startswith('+CSQ:'):
                p1 = ress.split(':')
                p2 = p1[1].split(',')
                self.__RSSI = int(p2[0])
                self.__BER = int(p2[1])
                processed = 0
                    
            elif 'ERROR' in ress:
                print('      - GSM    ', ress)
                break
                
            if ((self.__status < 4 and self.__verbose & 0x01) or
                (self.__status == 4 and self.__verbose & 0x02) or
                (self.__status == 5 and self.__verbose & 0x04) or
                (not processed and self.__verbose & 0x08)):
                    if(ress == '' and self.__verbose & 0x10) or ress != '':
                        print('      - GSM rx: ', ress)

    
    async def __send(self, command):
        self.__response = []
        if ((self.__status < 4 and self.__verbose & 0x01) or
                (self.__status == 4 and self.__verbose & 0x02) or
                (self.__status == 5 and self.__verbose & 0x04)):
            print('      - GSM tx: ', command)
        await self.__swriter.awrite("{}\r\n".format(command))
    
    async def __Command(self, Command, timeout = 4):
        await self.__send(Command)
        try:
            await uasyncio.wait_for(self.__recv(), timeout)
        except uasyncio.TimeoutError:
            self.__response = None
            print('      - GSM     ==== RECEIVE TIMEOUT ==== ')
    
    
    
    @property
    def status(self):
        return self.__status
    
    @property
    def IMEI(self):
        return self.__IMEI
    
    @property
    def IMSI(self):
        return self.__IMSI
    
    @property
    def ModuleProductID(self):
        return self.__moduleProductID
    
    @property
    def ModuleRevision(self):
        return self.__moduleRevision
    
    @property
    def OperatorName(self):
        return self.__OperatorName
    
    @property
    def OperatorCode(self):
        return self.__OperatorCode
    
    @property
    def CellID(self):
        return self.__CellID
    
    @property
    def RSSI(self):
        return self.__RSSI
    
    @property
    def ReceivedSMS(self):
        return self.__SMS
    
    @property
    def SIM_SMSCapacity(self):
        return self.__SMSTotal

    @property
    def SIM_SMSCount(self):
        return self.__SMSCount
    
    def deinit(self):
        self.__comm.cancel()
        if self.__RSTP != None:
            self.__RSTP.value(0)