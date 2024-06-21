import sys
import ubinascii
from AppSettings import *
from mqtt_as import MQTTClient, config
import ntptime
from machine import RTC, Pin, ADC
if sys.implementation._machine == 'Raspberry Pi Pico W with RP2040':
    import network
    import utime
    #from  Appsettings import *
    import gc
    #import _thread
    import uasyncio
    gc.collect()
    
    class PicoNet():
        #-------------------------------------
        #-- VARIABLE PREPARING --
        #-------------------------------------
       AP   = None
       STA = None
       
       __TimeZone = ' '
       __WiFi_nets = []
       
        
        
       def cettime(self):
            year = utime.localtime() [0]
            HHMarch = utime.mktime((year, 3 ,(31-(int(5*year/4+4))%7), 1,0,0,0,0,0))
            HHOctober = utime.mktime((year,10,(31-(int(5*year/4+1))%7),1,0,0,0,0,0))
            now = utime.time()
            if now < HHMarch :
                cet=utime.localtime(now+3600)
                self.__TimeZone = 'CET'
            elif now < HHOctober :
                cet.utime.localtime(now+7200)
                self.__TimeZone = 'CET'
            else:
                cet=utime.localtime(now+3600)
                self.__TimeZone = 'CET'
            return(cet)
        
       def __strSNetInfo(self, SNET_info):
           out = '{0: <40} {1} {2:>4} dBm, ch: {3:>2}, {4}' .format(
               SNET_info['SSID'], SNET_info['BSSID'], SNET_info['RSSI'],
               SNET_info['CH'], SNET_info['SECURITY'])
           return out
        
       def __parseScanResult(self, result):
            print(result)
            self.__WiFi_nets = []
            if len(result) !=0:
                for i in range(len(result)):
                    (SSID, MAC, t, RSSI, a, b) = result[i]
                    neti ={}
                    neti['SSID'] = SSID.decode('utf-8')
                    neti['BSSID'] = ubinascii.hexlify(MAC, ':').decode().upper()
                    neti['CH'] = t
                    neti['RSSI'] = RSSI
                    if a ==0:
                        neti['SECURITY'] = 'OPEN'
                    elif a ==1:
                        neti['SECURITY'] = 'WEP64'
                    elif a ==2:
                        neti['SECURITY'] = 'WEP128'
                    elif a ==3:
                        neti['SECURITY'] = 'WPA-PSK (TKIP)'
                    elif a ==4:
                        neti['SECURITY'] = 'WPA-PSK (AES)'
                    elif a ==5:
                        neti['SECURITY'] = 'WPA2-PSK (TKIP)'
                    elif a ==6:
                        neti['SECURITY'] = 'WPA2-PSK (AES)'
                    elif a ==7:
                        neti['SECURITY'] = 'WPA/WPA2-PSK (TKIP/AES)'
                    self.__WiFi_nets.append(neti)
                self.__WiFi_nets = sorted(self.__WiFi_nets, key=lambda x: x['RSSI'], reverse = True) #seřazení sítí podle RSSI reverse=sestupně :D
            
        
       def __init__(self):
            print(' NET  => INITIALIZING STARTED ')
            self.STA = network.WLAN(network.STA_IF)
            print(' NET  => activating STA')
            self.STA.active(True)
            self.STA.config(pm=0xA11140)
            print( 'NET  => {} activated' .format(self.STA))
            print(' NET  =>  STA MAC:  {}' .format(ubinascii.hexlify(self.STA.config('mac'), ':').decode().upper()))
            self.AP  = network.WLAN(network.AP_IF)
            gc.collect()
            print(' NET  => INITIALIZATION FINISHED')
        
        
       async def STA_Connect(self):
            print(' NET  => STA mode connection started')
            print(' NET  => WiFi scan started')
            # asyn.scan
        
            self.__parseScanResult(self.STA.scan())
            await  uasyncio.sleep_ms(0)
            print(' NET  => WiFi scan finished, ', end=' ')
            if len(self.__WiFi_nets) > 0:
                print('founded networks:')
                for i in range(len(self.__WiFi_nets)):
                    print('              {}'.format(self.__strSNetInfo(self.__WiFi_nets[i])))
            else:
                print(' NO NETWORKS FOUND')
                return
            KNi = None 
            for kn in range(len(KnownNetworks)):
                knSSID = KnownNetworks[kn] ['SSID']
                for en in range(len(self.__WiFi_nets)):
                    if self.__WiFi_nets[en]['SSID'] == knSSID:
                        KNi = kn
                        break
            #self.__NetScanning = False
            if KNi == None:
                print(' NET => NO KNOWN NETWORKS FOUND')
                return
            # await.uasyncio.sleep_ms(0)
            print(' NET => KNOWN WIFI {} FOUND, connecting...'.format(KnownNetworks[KNi] ['SSID']))
            self.STA.connect(KnownNetworks[KNi] ['SSID'], KnownNetworks [KNi] ['Password'])
            loops = 100
            while loops>0:
                aps = self.STA.status()
                if aps<0:
                    print( 'NET => connection failed ({:s})'.formatat(self.STA_status))
                    return
                elif aps>=3:
                    print( 'NET => sucessfully conected')
                    break
                #await uasyncio.sleep_ms(100)
                utime.sleep_ms(100)
                loops -= 1
                
            if self.STA.status() >=3:
                print(' NET => STA assigned IP : {}'.format(self.STA.ifconfig()[0]))
                print(' NET =>				   : {}'.format(self.STA.ifconfig()[1]))
                print(' NET =>				   : {}'.format(self.STA.ifconfig()[2]))
                #self.NTP_SetTime()
            else:
                print(' NET => connection timed out')
                
       def NTP_SetTime(self):
            print( 'NET => correct system time from ntp')
            ntptime.settime()
            cet = self.cettime()
            RTC().datetime((cet[0], cet[1], cet[2], cet[3], cet[4], cet[5], 0, 0))
    
MQTT_Connected = False

def MQTT_callback(topic, msg, retained):
    print(topic, msg, retained)
        
def MQTT_connect_callback(MQTT):
    global MQTT_Connected
    print('MQTT connected')
    MQTT_Connected = True
    #await uasyncio.sleep_ms(0)

if __name__ == '__main__':
    NET = PicoNet()
    HiveMQ = None
    uasyncio.run(NET.STA_Connect())
    
    if NET.STA.status() == 3:
        MQTTClient.DEBUG = True
        broker = MQTT_Url
        config['server'] = broker
        config['ssl'] = True
        config['ssl_params'] = {"server_hostname":broker}
        config['user'] = MQTT_User
        config['password'] = MQTT_Pwd
        config['subs_cb'] = MQTT_callback
        #config['connect_coro'] = MQTT_connect_callback
        HiveMQ = MQTTClient(config, NET.STA)
        uasyncio.run(HiveMQ.connect())
        
    tempS = ADC(4)
    lastTSm = utime.ticks_ms()
    while True:
        if utime.ticks_diff(utime.ticks_ms(), lastTSm) > 3000:
            lastTSm = utime.ticks_ms()
            adc_value = tempS.read_u16()
            volt = (3.3/65535) * adc_value
            temperature = 27 - (volt - 0.706)/0.001721
            print('{:.2f} °C'.format(temperature))
        
            