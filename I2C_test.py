from machine import Pin, I2C

print("Initializing I2C ...")
i2c_bus = I2C(1, scl=Pin(11), sda=Pin(10), freq=400000)  
print(i2c_bus)
print()
devices = i2c_bus.scan()  # scanning devices on bus
print(devices)