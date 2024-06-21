from machine import Pin, I2C
import neopixel

print("Initializing I2C ...")
i2c_bus = I2C(1, scl=Pin(11), sda=Pin(10), freq=400000)  
print(i2c_bus)
print()
devices = i2c_bus.scan()  # scanning devices on bus
print(devices)

print(" -> NeoPixel LED initialization ...      ", end='')
NeoLEDs = neopixel.NeoPixel(Pin(6, Pin.OUT), 2)
for i in range(NeoLEDs.n):
    NeoLEDs[i] = (127, 127, 127)
NeoLEDs.write()

