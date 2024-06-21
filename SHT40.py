

import struct
import uasyncio
import utime
import ubinascii

_SHT4X_DEFAULT_ADDR         = const(0x44)  # SHT4X I2C Address

# Commands
SHT4X_READSERIAL           = const(0x89)  # Read Out of Serial Register
SHT4X_SOFTRESET            = const(0x94)  # Soft Reset
SHT4X_Meas_HighP_NoHeat    = const(0xFD)  # Measure with high precision without heat
SHT4X_Meas_MidP_NoHeat     = const(0xF6)  # Measure with middle precision without heat
SHT4X_Meas_LowP_NoHeat     = const(0xE0)  # Measure with low precision without heat
SHT4X_Meas_HighP_HeatHL    = const(0x39)  # Measure with high precision with 200mW 1s heating
SHT4X_Meas_HighP_HeatHS    = const(0x32)  # Measure with high precision with 200mW 0.1s heating
SHT4X_Meas_HighP_HeatML    = const(0x2F)  # Measure with high precision with 110mW 1s heating
SHT4X_Meas_HighP_HeatMS    = const(0x24)  # Measure with high precision with 110mW 0.1s heating
SHT4X_Meas_HighP_HeatLL    = const(0x1E)  # Measure with high precision with 20mW 1s heating
SHT4X_Meas_HighP_HeatLS    = const(0x15)  # Measure with high precision with 20mW 0.1s heating

class SHT40:
    __LastTemp = None
    __LastRH = None 
    __SNo = None
    
    def __init__(self, I2C):
        self.i2c = I2C
        self.__sendCmd(SHT4X_READSERIAL)
        utime.sleep_ms(10)
        buffer = bytearray(6)
        buffer = self.i2c.readfrom(_SHT4X_DEFAULT_ADDR, 6, True)
        word1 = struct.unpack_from(">H",buffer[0:2])[0]
        word2 = struct.unpack_from(">H",buffer[3:5])[0]
        self.__SNo = (word1 << 16) + word2
        

    def __sendCmd(self, cmd):
        buffer = bytearray(1)
        buffer[0] = cmd
        self.i2c.writeto(_SHT4X_DEFAULT_ADDR, buffer)
        
    def __readTH(self) -> (float, float):
        buffer = bytearray(6)
        buffer = self.i2c.readfrom(_SHT4X_DEFAULT_ADDR, 6, True)
        temp_data = buffer[0:2]
        temp_crc = buffer[2]
        humidity_data = buffer[3:5]
        humidity_crc = buffer[5]

        temperature = struct.unpack_from(">H", temp_data)[0]
        temperature = -45.0 + 175.0 * temperature / 65535.0
        temperature_f = (temperature * 9/5) +32

        # repeat above steps for humidity data
        humidity = struct.unpack_from(">H", humidity_data)[0]
        humidity = -6.0 + 125.0 * humidity / 65535.0
        humidity = max(min(humidity, 100), 0)
        return (humidity, temperature)
        print(temperature)
    
    def Measure(self, MeasureType) -> (float, float):
        self.__sendCmd(MeasureType)
        if MeasureType == SHT4X_Meas_HighP_NoHeat:
            utime.sleep_ms(10)
        elif MeasureType == SHT4X_Meas_MiddleP_NoHeat:
            utime.sleep_ms(5)
        elif MeasureType == SHT4X_Meas_LowP_NoHeat:
            utime.sleep_ms(2)
        elif MeasureType == SHT4X_Meas_HighP_HeatHL or MeasureType == SHT4X_Meas_HighP_HeatML or MeasureType == SHT4X_Meas_HighP_HeatHL:
            utime.sleep_ms(1010)
        elif MeasureType == SHT4X_Meas_HighP_HeatHS or MeasureType == SHT4X_Meas_HighP_HeatMS or MeasureType == SHT4X_Meas_HighP_HeatHS:
            utime.sleep_ms(110)
        (self.__LastRH, self.__LastTemp) = self.__readTH()         
        return (self.__LastRH, self.__LastTemp)
    
    async def MeasureAsync(self, MeasureType) -> (float, float):
        self.__sendCmd(MeasureType)
        if MeasureType == SHT4X_Meas_HighP_NoHeat:
            await uasyncio.sleep_ms(10)
        elif MeasureType == SHT4X_Meas_MiddleP_NoHeat:
            await uasyncio.sleep_ms(5)
        elif MeasureType == SHT4X_Meas_LowP_NoHeat:
            await uasyncio.sleep_ms(2)
        elif MeasureType == SHT4X_Meas_HighP_HeatHL or MeasureType == SHT4X_Meas_HighP_HeatML or MeasureType == SHT4X_Meas_HighP_HeatHL:
            await uasyncio.sleep_ms(1010)
        elif MeasureType == SHT4X_Meas_HighP_HeatHS or MeasureType == SHT4X_Meas_HighP_HeatMS or MeasureType == SHT4X_Meas_HighP_HeatHS:
            await uasyncio.sleep_ms(110)
        (self.__LastRH, self.__LastTemp) = self.__readTH()          
        return (self.__LastRH, self.__LastTemp)
    
    @property
    def SerialNumber(self):
        return self.__SNo
    
    @property
    def Temperature(self):
        return self.__LastTemp

    @property
    def RelativeHumidity(self):
        return self.__LastRH
