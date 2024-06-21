from machine import Signal
from BSP import BSP
import sys
import gc
import ubinascii
from AppSettings import *
import uasyncio
import ustruct
import ntptime
import utime
from machine import RTC
from mqtt_as import MQTTClient, config
import math

if sys.implementation._machine == 'Raspberry Pi Pico W with RP2040':
    import network       # https://docs.micropython.org/en/latest/library/network.WLAN.html#network.WLAN.status
    STA = None
    AP = None
    
    class PicoNet():
        def cettime(self):
            year = utime.localtime()[0]       #get current year
            HHMarch   = utime.mktime((year,3 ,(31-(int(5*year/4+4))%7),1,0,0,0,0,0)) #Time of March change to CEST
            HHOctober = utime.mktime((year,10,(31-(int(5*year/4+1))%7),1,0,0,0,0,0)) #Time of October change to CET
            now=utime.time()
            if now < HHMarch :               # we are before last sunday of march
                cet=utime.localtime(now+3600) # CET:  UTC+1H
            elif now < HHOctober :           # we are before last sunday of october
                cet=utime.localtime(now+7200) # CEST: UTC+2H
            else:                            # we are after last sunday of october
                cet=utime.localtime(now+3600) # CET:  UTC+1H
            return(cet)
        
        
        def __init__(self):
            print(" -> Network initialization ...           ", end='')
            self.STA = network.WLAN(network.STA_IF)
            self.AP = network.WLAN(network.AP_IF)
            print('done')
       
        @property
        def AP_MAC(self):
            if self.AP.active():
                return ubinascii.hexlify(self.AP.config('mac'),':').decode().upper()
            else:
                return "inactive"
            
        @property
        def STA_MAC(self):
            if self.STA.active():
                return ubinascii.hexlify(self.STA.config('mac'),':').decode().upper()
            else:
                return "inactive"
        
        async def STA_Connect(self):
            print(" -> Network STA connection started.")
            print(" -> Activating STA ...                   ", end='')
            self.STA.active(True)
            self.STA.config(pm=0xA11140)
            print("done")
            print(" -> Scanning networks ...                ", end='')
            ANets = self.STA.scan()
            print("done")
            Nets_SSID = [] 
            for i in range(len(ANets)):
                (SSID, MAC, t, RSSI, a, b) = ANets[i]
                SSIDt = SSID.decode('utf-8').rstrip()
                Nets_SSID.append(SSIDt)
            
            KNi = None
            for kn in range(len(KnownNetworks)):
                knSSID = KnownNetworks[kn]['SSID']
                for en in range(len(Nets_SSID)):
                    if Nets_SSID[en] == knSSID:
                        KNi = kn
                        break
                if KNi != None:
                    break
            if KNi == None:
                print(" -> Known networks not found")
            else:
                print(' -> WiFi {} found'.format(KnownNetworks[KNi]['SSID']))
                print('       - connecting ...                  ', end='')
                self.STA.connect(KnownNetworks[KNi]['SSID'], KnownNetworks[KNi]['Password'])
                loops = 5000
                LSts = 50
                while loops > 0:
                    NSts = self.STA.status()
                    if NSts != LSts:
                        LSts = NSts
                    if self.STA.status() < 0:
                        print('fail')
                        break
                    elif self.STA.status() >= 3:
                        print('done')
                        break
                    await uasyncio.sleep_ms(1)
                    loops -= 1
                await uasyncio.sleep_ms(500)
                if self.STA.status() >= 3:
                    print(' -> WiFi STA assigned IP :    {0: >15s}'.format(self.STA.ifconfig()[0]))
                    print(" -> Setting RTC by NTP ...               ", end='')
                    ntptime.settime()
                    cet = self.cettime()
                    RTC().datetime((cet[0], cet[1], cet[2], cet[6] + 1, cet[3], cet[4], cet[5], 0))
                    print('done')
                else:
                    print('timed out')
        
class GlobalVars():
    Net = None
    Board = None
    MQTT = None
    MQTT_task = None
    MQTT_Connected = False
    LED = False
    LED_Brightness = 127
    
    def MQTT_callback(self, topic, msg, retained):
        print(' -> MQTT message received :')
        print('  - topic : {0:s}'.format(topic.decode('utf-8')))
        print('  - msg   : {0:s}'.format(msg.decode('utf-8')))
        print('  - retain: {0}'.format(retained))     
        if topic == 'SOUT_HW/LED':
            if msg == 'ON':
                a = self.LED_Brightness
                self.LED = True
            else:
                a = 0
                self.LED = False
            for i in range(2, self.Board.NeoLEDs.n):
                self.Board.NeoLEDs[i] = (a, a, a)
            self.Board.NeoLEDs.write()
        elif topic == 'SOUT_HW/LED_Brightness':
            b = msg.decode('utf-8').strip()
            l = int(int(b) * 2.55)
            self.LED_Brightness = l
            if self.LED:
                for i in range(2, self.Board.NeoLEDs.n):
                    self.Board.NeoLEDs[i] = (l, l, l)
                self.Board.NeoLEDs.write()
        
    async def MQTT_connect_callback(self, MQTT):
        print(' -> MQTT connected')
        self.MQTT_Connected = True
        await uasyncio.sleep_ms(0)
        
    async def MQTT_task_async(self):
        while self.Net.STA.status() < 3:
            await uasyncio.sleep_ms(300)
        
        await uasyncio.sleep_ms(1500)
        print(" -> MQTT connecting ...                  ")
        await self.MQTT.connect()
        while not self.MQTT.isconnected():
            await uasyncio.sleep_ms(10)
        await uasyncio.sleep_ms(1000)
        await self.MQTT.subscribe('SOUT_HW/LED', 1)
        await self.MQTT.subscribe('SOUT_HW/LED_Brightness', 1)
        Last_CPU_Temperature = None
        Last_CPU_Temperature_TS = utime.ticks_ms()
        Last_SHT_Temperature = None
        Last_SHT_Temperature_TS = utime.ticks_ms()
        Last_SHT_Humidity = None
        Last_SHT_Humidity_TS = None
        Last_AmbientLight = None
        Last_AmbientLight_TS = None
        FiveMin = False
        CPUTSended = False
        THSTempSended = False
        THSHumSended = False
        ALSLightSended = False
        while True:  
            if self.MQTT_Connected:
                bf = self.Board.CPUTemperature
                dt = RTC().datetime()
                TimeSend = False
                if dt[6] == 0 and (dt[5] % 5) == 0:
                    FiveMin = True
                else:
                    FiveMin = False
                if dt[6] != 0:
                    CPUTSended = False
                    THSTempSended = False
                    THSHumSended = False
                    ALSLightSended = False;
                if Last_CPU_Temperature == None or math.fabs(Last_CPU_Temperature - bf) > 1 or (dt[6] == 0 and not CPUTSended):
                    await self.MQTT.publish('SOUT_HW/CPU_Temperature', '{0:3.2f}'.format(bf), qos=0, retain = 0)
                    Last_CPU_Temperature = bf
                    Last_CPU_Temperature_TS = utime.ticks_ms()
                    CPUTSended = True
                if self.Board.THS != None:  
                    bf = self.Board.THS.Temperature
                    if Last_SHT_Temperature == None or math.fabs(Last_SHT_Temperature - bf) > 1 or (FiveMin and dt[6] == 0 and not THSTempSended):
                        await self.MQTT.publish('SOUT_HW/SHT_Temperature', '{0:3.2f}'.format(bf), qos=0, retain = 0)
                        Last_SHT_Temperature = bf
                        Last_SHT_Temperature_TS = utime.ticks_ms()
                        THSTempSended = True
                        print('Temperature update')
                    bf = self.Board.THS.RelativeHumidity
                    if Last_SHT_Humidity == None or math.fabs(Last_SHT_Humidity - bf) > 5 or (FiveMin and dt[6] == 0 and not THSHumSended):
                        await self.MQTT.publish('SOUT_HW/SHT_Humidity', '{0:3.2f}'.format(bf), qos=0, retain = 0)
                        Last_SHT_Humidity = bf
                        Last_SHT_Humidity_TS = utime.ticks_ms()
                        THSHumSended = True
                if self.Board.ALS != None:
                    bf = self.Board.ALS.AmbientLight
                    if Last_AmbientLight == None or math.fabs(Last_AmbientLight - bf) > 20 or (FiveMin and dt[6] == 0 and not ALSLightSended):
                        await self.MQTT.publish('SOUT_HW/AmbientLight', '{0:3.2f}'.format(bf), qos=0, retain = 1)
                        Last_AmbientLight = bf
                        Last_AmbientLight_TS = utime.ticks_ms()
                        ALSLightSended = True
                if FiveMin:
                    await uasyncio.sleep_ms(30) 
                if self.Net.STA.status() != 3:
                    print(" -> MQTT close due to network error")
                    self.MQTT.close()
                    self.MQTT_Connected = False
                    Last_CPU_Temperature = None
                    Last_SHT_Temperature = None
                    Last_SHT_Humidity = None
                    Last_AmbientLight = None
            else:
                if self.Net.STA.status() == 3:
                    print(" -> MQTT reconnecting ...")
                    self.MQTT.connect()
                    await uasyncio.sleep_ms(5000)
            
            await uasyncio.sleep_ms(100)
                    
    
    def __init__(self):
        self.Board = BSP()
        if sys.implementation._machine == 'Raspberry Pi Pico W with RP2040':
            self.Net = PicoNet()
            print(" -> Configuring MQTT client ...          ", end='')
            MQTTClient.DEBUG = True
            broker = MQTT_Url
            config['server'] = broker
            config['ssl'] = True
            config['ssl_params'] = {"server_hostname":broker}
            config['user'] = MQTT_User
            config['password'] = MQTT_Pwd
            config['subs_cb'] = self.MQTT_callback
            config['connect_coro'] = self.MQTT_connect_callback
            self.MQTT = MQTTClient(config, self.Net.STA)
            print('done')
            self.MQTT_task = uasyncio.create_task(self.MQTT_task_async())
                
        
        if self.Net != None and self.Board != None:
            self.Board.WiFi_STA(self.Net.STA)
            self.Board.WiFi_AP(self.Net.AP)
        
        
        
        
    def deinit(self):
        if self.Net != None:
            self.Net.AP.active(False)
            self.Net.STA.active(False)
            if self.Net.STA.status() != 0:
                self.Net.STA.disconnect()
            if self.MQTT_task != None:
                self.MQTT.close()
                self.MQTT_task.cancel()
        self.Board.deinit()
