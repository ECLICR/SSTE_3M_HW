from machine import Pin, PWM, I2C, SPI, ADC, RTC, UART
import uasyncio, utime, framebuf
import neopixel
from SSD1306 import SSD1306_I2C
from OLED_Graphics import *
import Font
from AppSettings import ApplicationName
from SHT40 import *
from BH1750 import *

class BSP():
    ####################################################################################################
    # CONSTANTS                                                                                        #
    ####################################################################################################
    BTN_MIN_PRESS_TIME       = const(20)
    BTN_MAX_SHORT_PRESS_TIME = const(500)
    BTN_LONG_PRESS_TIME      = const(2000)
    pix_res_x                = const(128)     # SSD1306 horizontal resolution
    pix_res_y                = const(64)      # SSD1306 vertical resolution
    ADC_LSB = 3.3 / (65535)
    
    SCR_STATUS_START         = const(0)
    SCR_STATUS_END           = const(5)
    
    SCR_MENU_START           = const(50)
    SCR_MENU_END             = const(50)
    
    ####################################################################################################
    # VARIABLES                                                                                        #
    ####################################################################################################
    Sys_I2C = None
    UART0 = None
    OLED = None                               # display
    NeoLEDs = None                            # NeoPixel LEDs
    THS = None                                # Temperature and humidity sensor (SHT40)
    ALS = None                                # Ambient Light Sensor (BH1750)
    CPU_TEMP = None                           # Raspberry Pico Onboard Temperature sensor
    Time = None                               # Real Time Clock
    GSM = None
    
    SysWarning = False
    SysAlarm = False
    
    __btnESC = Pin(3, Pin.IN, Pin.PULL_UP)    # ESC button (left top)
    __btnMinus = Pin(22, Pin.IN, Pin.PULL_UP) # - button (left bottom)
    __btnENT = Pin(20, Pin.IN, Pin.PULL_UP)   # ENT button (right top)
    __btnPlus = Pin(21, Pin.IN, Pin.PULL_UP)  # + button (right bottom)
    __btn_pt = [None, None, None, None]       # Buttons press ticks tuple
    __NeoLED = Pin(6, Pin.OUT)                # NeoPixel LEDs pin
    __PwrON = Pin(2, Pin.OUT)                 # Power ON pin
    __I2C1_SCL = Pin(11)
    __I2C1_SDA = Pin(10)
    
    
    __UART0_TX = Pin(16)
    __UART0_RX = Pin(17)
    __GSM_RST = Pin(19, Pin.OUT, value=0)
    
    __BaseScreen = None                       # Current displayed screen
    __ScreenRequest = None                    # Requested screen
    __scrTitle = None                         # Title for screen
    __scrSubtitle = None                      # Subtitle for screen
    __scrHasTitle = None                      # Screen has title displayed
    __WiFiSTA = None
    __WiFiAP = None
    Periodic = None                           # Periodic task
    Sensors = None                            # Sensor reading task
    __LastSTAStatus = None
    
    __btnESC_ShortPress = None
    __btnESC_LongPress = None
    __btnMinus_ShortPress = None
    __btnMinus_LongPress = None
    __btnENT_ShortPress = None
    __btnENT_LongPress = None
    __btnPlus_ShortPress = None
    __btnPlus_LongPress = None
    
    __CPU_Temperature = None                  # Onboard temperature
    
    async def SensorService(self):
        while True:
            if self.THS != None:
                await self.THS.MeasureAsync(SHT4X_Meas_HighP_NoHeat)
            else:
                await uasyncio.sleep_ms(20)
            if self.ALS != None:
                await self.ALS.MeasureAsync()
            else:
                await uasyncio.sleep_ms(20)
            if self.CPU_TEMP != None:
                TV = self.CPU_TEMP.read_u16() * self.ADC_LSB
                self.__CPU_Temperature = 27 - (TV - 0.706) / 0.001721
                await uasyncio.sleep_ms(1)
            else:
                await uasyncio.sleep_ms(20)
                
    
    
    ####################################################################################################
    # PERIODIC ASYNCHRONOUS FUNCTION                                                                   #
    ####################################################################################################
    async def PeriodicAsync(self):
        InitCycles = 0
        CycleCnt = 0
        Ticks_500ms = None
        Ticks_200ms = None
        Time_Flags = 0
        sec = self.Time.datetime()[6]
        while self.Time.datetime()[6] == sec:
            pass
        v = utime.ticks_ms()
        Ticks_500ms = Ticks_200ms = v
        BootLED = True
        Ticks_500ms_EdgeBuffer = False
        WiFiLED_CycleCounter = 0
        while True:
            if self.__btnESC.value() == 0 and self.__btn_pt[0] != None:
                delta = utime.ticks_diff(utime.ticks_ms(), self.__btn_pt[0])
                if delta > BTN_LONG_PRESS_TIME:
                    self.__btn_pt[0] = None
                    if self.__btnESC_LongPress != None:
                        self.__btnESC_LongPress()
            if self.__btnMinus.value() == 0 and self.__btn_pt[1] != None:
                delta = utime.ticks_diff(utime.ticks_ms(), self.__btn_pt[1])
                if delta > BTN_LONG_PRESS_TIME:
                    self.__btn_pt[1] = None
                    if self.__btnMinus_LongPress != None:
                        self.__btnMinus_LongPress()
            if self.__btnENT.value() == 0 and self.__btn_pt[2] != None:
                delta = utime.ticks_diff(utime.ticks_ms(), self.__btn_pt[2])
                if delta > BTN_LONG_PRESS_TIME:
                    self.__btn_pt[2] = None
                    if self.__btnENT_LongPress != None:
                        self.__btnENT_LongPress()
            if self.__btnPlus.value() == 0 and self.__btn_pt[3] != None:
                delta = utime.ticks_diff(utime.ticks_ms(), self.__btn_pt[3])
                if delta > BTN_LONG_PRESS_TIME:
                    self.__btn_pt[3] = None
                    if self.__btnPlus_LongPress != None:
                        self.__btnPlus_LongPress()
            if utime.ticks_diff(utime.ticks_ms(), Ticks_500ms) > 500:
                Ticks_500ms += 500
                Time_Flags ^= 1
                Time_Flags |= 4
            if utime.ticks_diff(utime.ticks_ms(), Ticks_200ms) > 200:
                Ticks_200ms += 200
                Time_Flags ^= 2
                Time_Flags |= 4
            if InitCycles != None:
                if self.OLED != None:
                    self.OLED.vline(InitCycles + 2, 59, 3, 1)
                InitCycles += 2;
                if BootLED:
                    self.NeoLEDs[0] = (15, 15, 15)
                    BootLED = False
                else:
                    self.NeoLEDs[0] = (0, 0, 0)
                    BootLED = True
                if InitCycles > 124:
                    InitCycles = None
                    if self.OLED != None:
                        self.OLED.fill(0)
                    self.NeoLEDs[0] = (0, 0, 0)
                    self.__ScreenRequest = 0                
                self.NeoLEDs.write()
                if self.OLED != None:
                    self.OLED.show()
            else:
                NeoChanged = False
                WFUpdate = False
                (r, g, b) = self.NeoLEDs[0]
                (r1, g1, b1) = self.NeoLEDs[1]
                if (g1 != 0 or r1 != 0 or b1 != 0) and self.__WiFiSTA.active():
                    self.NeoLEDs[1] = (0, 0, 0)
                    NeoChanged = True
                if g != 0 or r != 0:
                    self.NeoLEDs[0] = (0, 0, b)
                    NeoChanged = True
                elif ((Time_Flags & 1) == 1 and not Ticks_500ms_EdgeBuffer): 
                    self.NeoLEDs[0] = (0, 50, b)
                    WFUpdate = True
                    NeoChanged = True
                elif ((Time_Flags & 1) == 0 and Ticks_500ms_EdgeBuffer):
                    WFUpdate = True
                    if self.SysAlarm:
                        self.NeoLEDs[0] = (100, 0, b)
                        NeoChanged = True
                    elif self.SysWarning:
                        self.NeoLEDs[0] = (40, 40, b)
                        NeoChanged = True
                if WFUpdate and self.__WiFiSTA.active():
                    if WiFiLED_CycleCounter == 0:
                        self.NeoLEDs[1] = (30, 30, 30)
                        NeoChanged = True
                    elif WiFiLED_CycleCounter == 1:
                        NeoChanged = True
                        if self.__WiFiSTA.status() >= 0 and self.__WiFiSTA.status() < 3:
                            self.NeoLEDs[1] = (30, 30, 0)
                        elif self.__WiFiSTA.status() >= 3:
                            self.NeoLEDs[1] = (0, 0, 30)
                        else:
                            self.NeoLEDs[1] = (100, 0, 0)
                    elif WiFiLED_CycleCounter == 2:
                        self.NeoLEDs[1] = (30, 0, 0)
                        NeoChanged = True
                    elif WiFiLED_CycleCounter == 3:
                        self.NeoLEDs[1] = (30, 30, 0)
                        NeoChanged = True
                    WiFiLED_CycleCounter += 1
                    if WiFiLED_CycleCounter == 6:
                        WiFiLED_CycleCounter = 0
                if NeoChanged:
                    self.NeoLEDs.write()
                    
                if (Time_Flags & 4) == 4 and self.OLED != None:
                    Time_Flags &= ~4
                    scrUpdate = True
                    if self.__BaseScreen == None or self.__BaseScreen != self.__ScreenRequest:
                        self.OLED.fill(0)
                        scrUpdate = False
                        self.__BaseScreen = self.__ScreenRequest
                    if self.__BaseScreen == 0:
                        #(self.__scrTitle, self.__scrSubtitle, self.__scrHasTitle) = ScreenGSMStatus(self.OLED, Time_Flags, self.GSM, scrUpdate)
                        (self.__scrTitle, self.__scrSubtitle, self.__scrHasTitle) = ScreenSHT40(self.OLED, Time_Flags, self.THS, scrUpdate)
                    elif self.__BaseScreen == 1:
                        (self.__scrTitle, self.__scrSubtitle, self.__scrHasTitle) = ScreenBH1750(self.OLED, Time_Flags, self.ALS, scrUpdate)
                    elif self.__BaseScreen == 2:
                        (self.__scrTitle, self.__scrSubtitle, self.__scrHasTitle) = ScreenWiFiSTA(self.OLED, Time_Flags, self.__WiFiSTA, scrUpdate)
                    elif self.__BaseScreen == 3:
                        (self.__scrTitle, self.__scrSubtitle, self.__scrHasTitle) = ScreenPowerStatus(self.OLED, Time_Flags, scrUpdate)
                    elif self.__BaseScreen == 4:
                        (self.__scrTitle, self.__scrSubtitle, self.__scrHasTitle) = ScreenInputStatus(self.OLED, Time_Flags, scrUpdate)
                    elif self.__BaseScreen == 5:
                        (self.__scrTitle, self.__scrSubtitle, self.__scrHasTitle) = ScreenOutputStatus(self.OLED, Time_Flags, scrUpdate)
                    elif self.__BaseScreen == 50:
                        (self.__scrTitle, self.__scrSubtitle, self.__scrHasTitle) = ScreenMenuMessages(self.OLED, Time_Flags, scrUpdate)
                        
                    
                    
                    if self.__scrHasTitle:
                        PaintTitle(self.OLED, Time_Flags, self.__scrTitle, self.__scrSubtitle, self.__WiFiSTA, self.__WiFiAP)
                    
                    if not scrUpdate:
                        num = None
                        pos = None
                        
                        if SCR_STATUS_START <= self.__BaseScreen <= SCR_STATUS_END:
                            num = SCR_STATUS_END - SCR_STATUS_START
                            pos = self.__BaseScreen
                        elif SCR_MENU_START <= self.__BaseScreen <= SCR_MENU_END:
                            num = SCR_MENU_END - SCR_MENU_START
                            pos = self.__BaseScreen - 50
                        if num != None and pos != None:
                            for x in range(0, 128, 3):
                                self.OLED.pixel(x, 62, 1)
                            wdth = int(128 / (num + 1))
                            x = pos * wdth
                        rect(self.OLED, x, 61, wdth, 3, True)    
                    if self.__LastSTAStatus != self.__WiFiSTA.status() :
                        if self.__WiFiSTA.status() ==  -1:
                            print(" -> Network STA error : Link fail")
                        elif self.__WiFiSTA.status() ==  -2:
                            print(" -> Network STA error : no network")
                        elif self.__WiFiSTA.status() ==  -3:
                            print(" -> Network STA error : bad authentication")
                        self.__LastSTAStatus = self.__WiFiSTA.status()
                    self.OLED.show()
            
            Ticks_500ms_EdgeBuffer = (Time_Flags & 1) == 1
            await uasyncio.sleep_ms(0)
    
    ####################################################################################################
    # BUTTONS IRQ HANDLER                                                                              #
    #################################################################################################### 
    def btn_IRQHandler(self, Pin):
        if Pin == self.__btnESC:
            if self.__btnESC.value() == 0 and self.__btn_pt[0] == None:
                self.__btn_pt[0] = utime.ticks_ms()
            elif self.__btnESC.value() == 1 and self.__btn_pt[0] != None:
                delta = utime.ticks_diff(utime.ticks_ms(), self.__btn_pt[0])
                self.__btn_pt[0] = None
                if delta > BTN_MIN_PRESS_TIME and  delta < BTN_MAX_SHORT_PRESS_TIME:
                    self.__btnESC_LocalShortPress()
                    if self.__btnESC_ShortPress != None:
                        self.__btnESC_ShortPress()                   
        elif Pin == self.__btnMinus:
            if self.__btnMinus.value() == 0 and self.__btn_pt[1] == None:
                self.__btn_pt[1] = utime.ticks_ms()
            elif self.__btnMinus.value() == 1 and self.__btn_pt[1] != None:
                delta = utime.ticks_diff(utime.ticks_ms(), self.__btn_pt[1])
                self.__btn_pt[1] = None
                if delta > BTN_MIN_PRESS_TIME and  delta < BTN_MAX_SHORT_PRESS_TIME:
                    self.__btnMinus_LocalShortPress()
                    if self.__btnMinus_ShortPress != None:
                        self.__btnMinus_ShortPress()
        elif Pin == self.__btnENT:
            if self.__btnENT.value() == 0 and self.__btn_pt[2] == None:
                self.__btn_pt[2] = utime.ticks_ms()
            elif self.__btnENT.value() == 1 and self.__btn_pt[2] != None:
                delta = utime.ticks_diff(utime.ticks_ms(), self.__btn_pt[2])
                self.__btn_pt[2] = None
                if delta > BTN_MIN_PRESS_TIME and  delta < BTN_MAX_SHORT_PRESS_TIME: 
                    self.__btnENT_LocalShortPress()
                    if self.__btnENT_ShortPress != None:
                        self.__btnENT_ShortPress()
        elif Pin == self.__btnPlus:
            if self.__btnPlus.value() == 0 and self.__btn_pt[3] == None:
                self.__btn_pt[3] = utime.ticks_ms()
            elif self.__btnPlus.value() == 1 and self.__btn_pt[3] != None:
                delta = utime.ticks_diff(utime.ticks_ms(), self.__btn_pt[3])
                self.__btn_pt[3] = None
                if delta > BTN_MIN_PRESS_TIME and  delta < BTN_MAX_SHORT_PRESS_TIME:
                    self.__btnPlus_LocalShortPress()
                    if self.__btnPlus_ShortPress != None:
                        self.__btnPlus_ShortPress()
    
    # Local buttons press function
    def __btnMinus_LocalShortPress(self):
        if SCR_STATUS_START <= self.__BaseScreen <= SCR_STATUS_END and self.__BaseScreen > SCR_STATUS_START:
            self.__ScreenRequest = self.__BaseScreen - 1
    
    def __btnPlus_LocalShortPress(self):
         if SCR_STATUS_START <= self.__BaseScreen <= SCR_STATUS_END and self.__BaseScreen < SCR_STATUS_END:
            self.__ScreenRequest = self.__BaseScreen + 1
    
    def __btnENT_LocalShortPress(self):
         if SCR_STATUS_START <= self.__BaseScreen <= SCR_STATUS_END:
             self.__ScreenRequest = SCR_MENU_START
    
    def __btnESC_LocalShortPress(self):
         if SCR_MENU_START <= self.__BaseScreen <= SCR_MENU_END:
             self.__ScreenRequest = SCR_STATUS_START
    
    # Buttons press callback functions
    def btnESC_ShortPress(self, callback):
        self.__btnESC_ShortPress = callback
        
    def btnESC_LongPress(self, callback):
        self.__btnESC_LongPress = callback
    
    def btnMinus_ShortPress(self, callback): 
        self.__btnMinus_ShortPress = callback
    
    def btnMinus_LongPress(self, callback):
        self.__btnMinus_LongPress = callback
    
    def btnENT_ShortPress(self, callback):
        self.__btnENT_ShortPress = callback
    
    def btnENT_LongPress(self, callback):
        self.__btnENT_LongPress = callback
        
    def btnPlus_ShortPress(self, callback):
        self.__btnPlus_ShortPress = callback
        
    def btnPlus_LongPress(self, callback):
        self.__btnPlus_LongPress = callback
    
    def __init__(self):
        print(" -> Switching power ON ...               ", end='')
        self.__PwrON.value(1)
        print('done')
        print(" -> NeoPixel LED initialization ...      ", end='')
        self.NeoLEDs = neopixel.NeoPixel(self.__NeoLED, 6)
        for i in range(self.NeoLEDs.n):
            self.NeoLEDs[i] = (0, 0, 0)
        self.NeoLEDs.write()
        print('done')
        print(" -> Buttons initialization ...           ", end='')    
        self.__btnESC.irq(trigger=Pin.IRQ_FALLING | Pin.IRQ_RISING, handler = self.btn_IRQHandler)
        self.__btnMinus.irq(trigger=Pin.IRQ_FALLING | Pin.IRQ_RISING, handler = self.btn_IRQHandler)
        self.__btnENT.irq(trigger=Pin.IRQ_FALLING | Pin.IRQ_RISING, handler = self.btn_IRQHandler)
        self.__btnPlus.irq(trigger=Pin.IRQ_FALLING | Pin.IRQ_RISING, handler = self.btn_IRQHandler)
        print('done')
        print(" -> Onboard temperature sensor init ...  ", end='')
        self.CPU_TEMP = ADC(4)
        TV = self.CPU_TEMP.read_u16() * self.ADC_LSB
        self.__CPU_Temperature = 27 - (TV - 0.706) / 0.001721
        print('done')
        print('            - Voltage             : {0:7.3f} V'.format(TV))
        print('            - Temperature         : {0:6.2f} °C'.format(self.__CPU_Temperature))
        self.Periodic = uasyncio.create_task(self.PeriodicAsync())
        print(" -> System I2C initialization ...        ", end = '')
        self.SysI2C = I2C(1, scl=self.__I2C1_SCL, sda=self.__I2C1_SDA, freq=400000)
        print('done')
        print("      - {}".format(self.SysI2C))
        print("      - I2C scanning ...                 ",end = '')
        int_i2c_dev = self.SysI2C.scan()
        print("done")
        print(int_i2c_dev)
        
        if 0x3C in int_i2c_dev:
            print("        - SSD1306 found on address 3Ch")
            print("        - initializing display ...       ",end = "")
            self.OLED = SSD1306_I2C(pix_res_x, pix_res_y, self.SysI2C)      # oled controller
            self.OLED.fill(0)
            self.OLED.contrast(100)
            with open('/Images/BTECHi.pbm', 'rb') as f:
                f.readline() # Magic number
                f.readline() # Creator comment
                f.readline() # Dimensions
                data = bytearray(f.read())
                fbuf = framebuf.FrameBuffer(data, 128, 55, framebuf.MONO_HLSB)
            self.OLED.blit(fbuf, 0, 9)
            rect(self.OLED, 0, 0, 127, 16, True)
            Font.PrintString(self.OLED, ApplicationName, 25, 4, 0, 0)
            #self.OLED.rect(0,57, 124, 7, 1)
            rect(self.OLED, 0, 57, 128, 7)
            self.OLED.show()
            print("done")
        if 0x44 in int_i2c_dev:
            print("        - SHT40 found on address 44h")
            print("        - initializing SHT40 ...         ",end = "")
            self.THS = SHT40(self.SysI2C)
            ( humidity, temp ) = self.THS.Measure(SHT4X_Meas_HighP_NoHeat)
            print('done')
            print('            - SHT40 serial number :  {0:08X}'.format(self.THS.SerialNumber))
            print('            - Temperature         : {0:6.2f} °C'.format(temp))
            print('            - Relative humidity   : {0:6.2f}  %'.format(humidity))
        else:
            print("        - SHT40 not found on address 44h")
        if 0x23 in int_i2c_dev:
            print("        - BH1750 found on address 23hh")
            print("        - initializing BH1750 ...        ",end = "")
            self.ALS = BH1750(self.SysI2C)
            ( AmbientLight ) = self.ALS.Measure()
            print('done')
            print('            - Ambient light       : {0:6.0f} lx'.format(AmbientLight))
        else:
            print("        - BH1750 not found on address 23h")
            
        print(" -> UART0 initialization ...             ", end = '')
        self.UART0 = UART(0, baudrate=9600, tx = self.__UART0_TX, rx = self.__UART0_RX, rxbuf=1024)
        print("done")
        #self.GSM = SIM800L(self.UART0,self.__GSM_RST, 0x00)
        self.Time = RTC() 
        self.Sensors = uasyncio.create_task(self.SensorService())
    
    def deinit(self):
        if self.GSM != None:
            print(" -> GSM deinitialization ...             ", end='')
            self.GSM.deinit()
            print("done")
        print(" -> Board deinitialization ...           ", end='')
        if self.Periodic != None:
            self.Periodic.cancel()
        if self.Sensors != None:
            self.Sensors.cancel()
        for i in range(self.NeoLEDs.n):
            self.NeoLEDs[i] = (0, 0, 0)
        self.NeoLEDs.write()
        if self.OLED != None:
            self.OLED.fill(0)
            self.OLED.show()
        print('done')
    
    ####################################################################################################
    # PROPERTIES                                                                                       #
    ####################################################################################################
    @property
    def BaseScreen(self):
        return self.__BaseScreen
    
    @BaseScreen.setter
    def BaseScreen(self, ScreenNumber):
        if self.__BaseScreen != ScreenNumber:
            self.__BaseScreen = ScreenNumber
    
    @property
    def CPUTemperature(self):
        return self.__CPU_Temperature
    
    def WiFi_STA(self, STA):
        self.__WiFiSTA = STA
    
    def WiFi_AP(self, AP):
        self.__WiFiAP = AP
    
