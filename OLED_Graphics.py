import Font
import gc
import framebuf
from machine import RTC
import ubinascii

def rect(disp, X, Y, Width, Height, Fill=False):
    disp.rect(X, Y, Width, Height, 1, Fill)
    disp.pixel(X, Y, 0)
    disp.pixel(X + Width - 1, Y, 0)
    disp.pixel(X, Y + Height - 1, 0)
    disp.pixel(X + Width - 1, Y + Height - 1, 0)
    
def APIndicator(disp, X, Y, BlinkFlags, AP = None):
    disp.rect(X, Y, 17, 9, 0, False)
    #rect(disp, X, Y, 17, 9, False)
    if AP == None:
        Font.PrintString(disp, "--", X + 2, Y + 1, 1, 1)
    else:
        sts = AP.status()
        if sts == 0: # Link down
            #rect(disp, X, Y, 17, 9, False)
            Font.PrintString(disp, 'AP', X + 3, Y + 1, 1, 1)

def STAIndicator(disp, X, Y, BlinkFlags, STA = None):
    disp.rect(X, Y, 22, 9, 0, False)
    #rect(disp, X, Y, 22, 9, False)
    if STA == None:
        Font.PrintString(disp, "--", X + 4, Y + 1, 1, 1)
    else:
        sts = STA.status()
        if sts == 0: # Link down
            #rect(disp, X, Y, 17, 9, False)
            Font.PrintString(disp, 'STA', X + 1, Y + 1, 1, 1)
        elif sts == 1 or sts == 2: # Link join or No IP
            if (BlinkFlags & 0x02) == 0x02:
                Font.PrintString(disp, 'STA', X + 1, Y + 1, 1, 1)
            else:
                disp.rect(X, Y, 22, 9, 0, True)
        elif sts == 3: # Link Up
            rect(disp, X, Y, 22, 9, True)
            Font.PrintString(disp, 'STA', X + 1, Y + 1, 0, 0)
        elif sts == -1: # Link Fail
            pass
        elif sts == -2: # No net
            pass
        elif sts == -3: # Bad authentication
            pass;
        if sts < 0:
            if (BlinkFlags & 0x01) == 0x01:
                rect(disp, X, Y, 22, 9, True)
                Font.PrintString(disp, 'STA', X + 1, Y + 1, 0, 0)
            else:
                disp.rect(X, Y, 22, 9, 0, True)
            

def DigitalIndicator(disp, X, Name, State, Selected):
    if Selected:
        disp.hline(X, 26, 5, 1)
        disp.hline(X+9, 26, 5, 1)
        disp.hline(X, 59, 5, 1)
        disp.hline(X+9, 59, 5, 1)
        disp.vline(X, 26, 5, 1)
        disp.vline(X+14, 26, 5, 1)
        disp.vline(X, 54, 5, 1)
        disp.vline(X+14, 54, 5, 1)
    rect(disp, X + 2, 28, 11, 30, State)
    if State:      
        Font.PrintStringV(disp, Name, X+4, 54, 1, 0)
    else:
        Font.PrintStringV(disp, Name, X+4, 54, 1, 1)
        
def MenuSelector(disp):
    disp.vline(42, 17, 10, 1)
    disp.vline(43, 17, 5, 1)
    disp.hline(43, 16, 10, 1)
    disp.hline(44, 17, 4, 1)
    disp.vline(42, 48, 10, 1)
    disp.vline(43, 53, 4, 1)
    disp.hline(43, 58, 10, 1)
    disp.hline(43, 57, 5, 1)
    
    disp.vline(85, 17, 10, 1)
    disp.vline(84, 17, 5, 1)
    disp.hline(75, 16, 10, 1)
    disp.hline(80, 17, 4, 1)
    disp.vline(83, 53, 4, 1)
    disp.vline(84, 48, 10, 1)
    disp.hline(75, 58, 10, 1)
    disp.hline(80, 57, 5, 1)
    
    
    #disp.vline(85, 16, 42, 1)

def PaintTitle(disp, BlinkFlags, Title = None, Subtitle = None, STA=None, AP=None):
    if Title != None and Subtitle != None:
        Font.PrintString(disp, Title, 0, 0, 0, 1)
        Font.PrintString(disp, Subtitle, 0, 8, 0, 1)
    else:
        dt = RTC().datetime()
        disp.rect(0, 0, 85, 15, 0, True)
        Font.PrintString(disp, '{:02d}'.format(dt[4]), 0, 0, 2, 1)
        if (BlinkFlags & 1) == 1:
            Font.PrintString(disp, ':', 23, 0, 2, 1)
        Font.PrintString(disp, '{:02d}'.format(dt[5]), 32, 0, 2, 1)    
        Font.PrintString(disp, '{0:02d}'.format(dt[6]), 59, 0, 1, 1)
    
    rect(disp, 86, 0, 41, 4)
    disp.rect(87, 1, 30 , 2, 0, True)
    mp = gc.mem_alloc() / (gc.mem_free() + gc.mem_alloc())
    disp.rect(87, 1, int(30 * mp), 2, 1, True)    
    
    APIndicator(disp, 86, 6, BlinkFlags, AP)
    STAIndicator(disp, 105, 6, BlinkFlags, STA)

def PageTitle(disp, Title):
    disp.hline(0, 18, 6, 1)
    disp.hline(0, 20, 6, 1)
    disp.hline(0, 22, 6, 1)
    x = Font.PrintString(disp, Title, 8, 17, 0, 1) + 1
    disp.hline(x, 18, 128 - x, 1)
    disp.hline(x, 20, 128 - x, 1)
    disp.hline(x, 22, 128 - x, 1)

def ScreenGSMStatus(disp, BlinkFlags, SIM800L, Update):
    if not Update:
        PageTitle(disp, 'GSM')
    disp.rect(0, 24, 128, 36, 0, True)
    if SIM800L != None:
        if SIM800L.status == 0:
            Font.PrintString(disp, 'SIM800L', 46, 30, 1, 1)
            Font.PrintString(disp, 'BOOTING', 46, 42, 1, 1)
        elif SIM800L.status == 1:
            Font.PrintString(disp, 'SIM800L', 46, 30, 1, 1)
            Font.PrintString(disp, 'INITIALIZING', 30, 42, 1, 1)
        elif SIM800L.status == 2:
            Font.PrintString(disp, 'SIM', 54, 30, 1, 1)
            Font.PrintString(disp, 'UNLOCKING', 37, 42, 1, 1)
        elif SIM800L.status == 3:
            Font.PrintString(disp, 'GSM NETWORK', 35, 30, 1, 1)
            Font.PrintString(disp, 'REGISTRATION', 32, 42, 1, 1)
        elif SIM800L.status >= 4:            
            if SIM800L.OperatorName != None:
                x = int((120 - (len(SIM800L.OperatorName) * 7)) / 2)
                Font.PrintString(disp, SIM800L.OperatorName, x, 28, 0, 1)
            if SIM800L.OperatorCode != None:
                Font.PrintString(disp, SIM800L.OperatorCode, 0, 40, 1, 1)
            if SIM800L.CellID != None:
                Font.PrintString(disp, '{0:04X}'.format(SIM800L.CellID), 36, 40, 1, 1)
            if SIM800L.RSSI != None:
                rect(disp, 120, 25, 6, 35, False)
                disp.rect(122, 58 - SIM800L.RSSI, 2, SIM800L.RSSI, 1, True)
                
            Font.PrintString(disp, 'SMS:', 0, 50, 1, 1)
            if SIM800L.SIM_SMSCount == None:
                Font.PrintString(disp, '-/-', 30, 50, 0, 1)
            else:
                if (SIM800L.SIM_SMSCount / SIM800L.SIM_SMSCapacity) < 0.75 or (BlinkFlags & 0x01) == 0x01:
                    Font.PrintString(disp, '{0:d}/{1:d}'.format(SIM800L.SIM_SMSCount, SIM800L.SIM_SMSCapacity), 30, 50, 0, 1)
    return (None, None, True)

def ScreenSHT40(disp, BlinkFlags, SHT40, Update):
    if not Update:
        PageTitle(disp, ' TEMPERATURE ')
    
    
    if SHT40 == None and Update:
        if (BlinkFlags & 0x01) == 0x01:
            Font.PrintString(disp, 'SENSOR', 45, 28, 0, 1)
            Font.PrintString(disp, 'ERROR', 49, 38, 0, 1)
        else:
            disp.rect(0, 28, 127, 18, 0, True)
    if SHT40 != None:
        if Update:
            disp.rect(40, 26, 74, 14, 0, True)
            disp.rect(40, 45, 74, 14, 0, True)
            Font.PrintString(disp, '{0:6.2f}'.format(SHT40.Temperature), 40, 26, 2, 1)
            Font.PrintString(disp, '{0:6.2f}'.format(SHT40.RelativeHumidity), 40, 45, 2, 1)
            
        else:
            Font.PrintString(disp, '°C', 114, 26, 0, 1)
            Font.PrintString(disp, '%', 117, 44, 0, 1)
            Font.PrintString(disp, 'RH', 114, 52, 0, 1)
            with open('/Icons/Thermometer.pbm', 'rb') as f:
                f.readline() # Magic number
                f.readline() # Creator comment
                f.readline() # Dimensions
                data = bytearray(f.read())
                fbuf = framebuf.FrameBuffer(data, 14, 16, framebuf.MONO_HLSB)
                disp.blit(fbuf, 0, 25)
            with open('/Icons/Humidity.pbm', 'rb') as f:
                f.readline() # Magic number
                f.readline() # Creator comment
                f.readline() # Dimensions
                data = bytearray(f.read())
                fbuf = framebuf.FrameBuffer(data, 14, 16, framebuf.MONO_HLSB)
                disp.blit(fbuf, 0, 44)
            for x in range(0, 128, 3):
                disp.pixel(x, 42, 1)
    return (None, None, True)

def ScreenBH1750(disp, BlinkFlags, ALS, Update):
    if not Update:
        PageTitle(disp, ' LIGHT ')
    
    if ALS == None and Update:
        if (BlinkFlags & 0x01) == 0x01:
            Font.PrintString(disp, 'SENSOR', 45, 28, 0, 1)
            Font.PrintString(disp, 'ERROR', 49, 38, 0, 1)
        else:
            disp.rect(0, 28, 127, 18, 0, True)
    if ALS != None:
        if Update:
            disp.rect(16, 26, 98, 14, 0, True)
            Font.PrintString(disp, '{0:8.1f}'.format(ALS.AmbientLight), 16, 26, 2, 1)
        else:
            Font.PrintString(disp, 'lx', 114, 26, 0, 1)
    return (None, None, True)


def ScreenWiFiSTA(disp, BlinkFlags, WiFiSTA, Update):
    if not Update:
        PageTitle(disp, 'WiFi Station')
        Font.PrintString(disp, 'MAC', 0, 35, 0, 1)
        Font.PrintString(disp, 'IP', 0, 44, 0, 1)
        Font.PrintString(disp, 'DG', 0, 53, 0, 1)
        mac = ubinascii.hexlify(WiFiSTA.config('mac'),':').decode().upper()
        Font.PrintString(disp, mac, 26, 35, 1, 1)
    else:
        disp.rect(0, 26, 127, 8, 0, True)
        if not WiFiSTA.active():
            Font.PrintString(disp, 'INACTIVE', 0, 26, 0, 1)
        else:
            sts = WiFiSTA.status()
            if sts == 0: # Link down
                Font.PrintString(disp, 'LINK DOWN', 0, 26, 0, 1)
            elif sts == 1: # Link join
                Font.PrintString(disp, 'LINK JOIN', 0, 26, 0, 1)
            elif sts == 2: # No IP
                Font.PrintString(disp, 'NO IP ADDR', 0, 26, 0, 1)
            elif sts == 3: # Link Up
                Font.PrintString(disp, 'LINK UP', 0, 26, 0, 1)
            elif sts == -1: # Link Fail
                Font.PrintString(disp, 'LINK FAIL', 0, 26, 0, 1)
            elif sts == -2: # No net
                Font.PrintString(disp, 'NO NETWORK', 0, 26, 0, 1)
            elif sts == -3: # Bad authentication
                Font.PrintString(disp, 'BAD AUTH', 0, 26, 0, 1)
            
            ip = WiFiSTA.ifconfig()[0]
            x = 128 - (len(ip) * 6)
            disp.rect(16, 44, 111, 8, 0, True)
            Font.PrintString(disp, ip, x, 44, 1, 1)
            
            dg = WiFiSTA.ifconfig()[2]
            x = 128 - (len(dg) * 6)
            disp.rect(16, 53, 111, 8, 0, True)
            Font.PrintString(disp, dg, x, 53, 1, 1)
            
            rssi = WiFiSTA.status('rssi')
            if rssi == 0:
                rssic = 0
            else:
                rssic = 90 + rssi
                if rssic < 0:
                    rssic = 0
                elif rssic > 60:
                    rssic = 60
            rssic = int(rssic / 2)
            rect(disp, 96, 27, 30, 4, False)
            disp.rect(96, 28, rssic, 2, 1, True)
            
        
        
    return (None, None, True)

def ScreenPowerStatus(disp, BlinkFlags, Update):
    if not Update:
        PageTitle(disp, 'POWER')
    return (None, None, True)

def ScreenInputStatus(disp, BlinkFlags, Update):
    if not Update:
        PageTitle(disp, 'DIGITAL INPUTS')
        DigitalIndicator(disp, (0 * 16), 'RST', False, False)
        DigitalIndicator(disp, (1 * 16), 'RDY', True, False)
        DigitalIndicator(disp, (2 * 16), '', False, False)
        DigitalIndicator(disp, (3 * 16), '', False, False)
        DigitalIndicator(disp, (4 * 16), '', False, False)
        DigitalIndicator(disp, (5 * 16), '', False, False)
        DigitalIndicator(disp, (6 * 16), '', False, False)
        DigitalIndicator(disp, (7 * 16), '', False, False)
    return (None, None, True)

def ScreenOutputStatus(disp, BlinkFlags, Update):
    if not Update:
        PageTitle(disp, 'DIGITAL OUTPUTS')
        DigitalIndicator(disp, (0 * 16), 'DOOR', True, False)
        DigitalIndicator(disp, (1 * 16), 'AIR', False, False)
        DigitalIndicator(disp, (2 * 16), 'HEAT', False, False)
        DigitalIndicator(disp, (3 * 16), 'COOL', False, False)
        DigitalIndicator(disp, (4 * 16), '', False, False)
        DigitalIndicator(disp, (5 * 16), '', False, False)
        DigitalIndicator(disp, (6 * 16), '', False, False)
        DigitalIndicator(disp, (7 * 16), '', False, False)
    return (None, None, True)

def ScreenMenuMessages(disp, BlinkFlags, Update):
    if not Update:
        MenuSelector(disp)
        with open('/Icons/Messages.pbm', 'rb') as f:
            f.readline() # Magic number
            f.readline() # Creator comment
            f.readline() # Dimensions
            data = bytearray(f.read())
            fbuf = framebuf.FrameBuffer(data, 26, 26, framebuf.MONO_HLSB)
            disp.blit(fbuf, 50, 20)
        with open('/Icons/WiFi.pbm', 'rb') as f:
            f.readline() # Magic number
            f.readline() # Creator comment
            f.readline() # Dimensions
            data = bytearray(f.read())
            fbuf = framebuf.FrameBuffer(data, 26, 26, framebuf.MONO_HLSB)
            disp.blit(fbuf, 93, 20)
        Font.PrintString(disp, 'SMS', 54, 49, 0, 1)
        Font.PrintString(disp, 'WiFi', 92, 49, 0, 1)
    return("MENU","", True)



