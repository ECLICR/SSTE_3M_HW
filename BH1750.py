import math
from micropython import const
import uasyncio
import utime

class BH1750:
    MEASUREMENT_MODE_CONTINUOUSLY       = const(1)
    MEASUREMENT_MODE_ONE_TIME           = const(2)
    
    RESOLUTION_HIGH                     = const(0)
    RESOLUTION_HIGH_2                   = const(1)
    RESOLUTION_LOW                      = const(2)
    
    MEASUREMENT_TIME_DEFAULT            = const(69)
    MEASUREMENT_TIME_MIN                = const(31)
    MEASUREMENT_TIME_MAX                = const(254)
    
    __AL = None 
    
    def __init__(self, I2C, address = False):
        if address:
            self._address = 0x5C
        else:
            self._address = 0x23
        self._i2c = I2C
        self._measurement_mode    = self.MEASUREMENT_MODE_ONE_TIME
        self._resolution          = self.RESOLUTION_HIGH
        self._measurement_time    = self.MEASUREMENT_TIME_DEFAULT
        self._write_measurement_time()
        self._write_measurement_mode()
        
    def configure(self, measurement_mode: int, resolution: int, measurement_time: int):
        """Configures the BH1750.
        Keyword arguments:
        measurement_mode -- measure either continuously or once
        resolution -- return measurements in either high, high2 or low resolution
        measurement_time -- the duration of a single measurement
        """
        if measurement_time not in range(BH1750.MEASUREMENT_TIME_MIN, BH1750.MEASUREMENT_TIME_MAX + 1):
            raise ValueError("measurement_time must be between {0} and {1}"
                             .format(BH1750.MEASUREMENT_TIME_MIN, BH1750.MEASUREMENT_TIME_MAX))
        
        self._measurement_mode = measurement_mode
        self._resolution = resolution
        self._measurement_time = measurement_time
        
        self._write_measurement_time()
        self._write_measurement_mode()
        sleep_ms(24 if self._measurement_time == self.RESOLUTION_LOW else 180)
    
    def _write_measurement_time(self):
        buffer = bytearray(1)        
        high_bit = 1 << 6 | self._measurement_time >> 5
        low_bit = 3 << 5 | (self._measurement_time << 3) >> 3                
        buffer[0] = high_bit
        self._i2c.writeto(self._address, buffer)        
        buffer[0] = low_bit
        self._i2c.writeto(self._address, buffer)
        
    def _write_measurement_mode(self):
        buffer = bytearray(1)                
        buffer[0] = self._measurement_mode << 4 | self._resolution
        self._i2c.writeto(self._address, buffer)
        
        
    def reset(self):
        """Clear the illuminance data register."""
        self._i2c.writeto(self._address, bytearray(b'\x07'))
    
    def power_on(self):
        """Powers on the BH1750."""
        self._i2c.writeto(self._address, bytearray(b'\x01'))

    def power_off(self):
        """Powers off the BH1750."""
        self._i2c.writeto(self._address, bytearray(b'\x00'))
        
    def Measure(self) -> float:
        """Returns the latest measurement."""
        if self._measurement_mode == BH1750.MEASUREMENT_MODE_ONE_TIME:
            self._write_measurement_mode()
            
        utime.sleep_ms(24 if self._measurement_time == self.RESOLUTION_LOW else 180)
        
        buffer = bytearray(2)
        self._i2c.readfrom_into(self._address, buffer)
        lux = (buffer[0] << 8 | buffer[1]) / (1.2 * (BH1750.MEASUREMENT_TIME_DEFAULT / self._measurement_time))
        
        if self._resolution == BH1750.RESOLUTION_HIGH_2:
            self.__AL = lux / 2
            return lux / 2
        else:
            self.__AL = lux
            return lux
    
    async def MeasureAsync(self) -> float:
        """Returns the latest measurement."""
        if self._measurement_mode == BH1750.MEASUREMENT_MODE_ONE_TIME:
            self._write_measurement_mode()
            
        await uasyncio.sleep_ms(24 if self._measurement_time == self.RESOLUTION_LOW else 180)
        
        buffer = bytearray(2)
        self._i2c.readfrom_into(self._address, buffer)
        lux = (buffer[0] << 8 | buffer[1]) / (1.2 * (BH1750.MEASUREMENT_TIME_DEFAULT / self._measurement_time))
        
        if self._resolution == BH1750.RESOLUTION_HIGH_2:
            self.__AL = lux / 2
            return lux / 2
        else:
            self.__AL = lux
            return lux
    
    @property
    def AmbientLight(self):
        return self.__AL