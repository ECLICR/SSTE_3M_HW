from Model import GlobalVars
import sys
import utime
import uasyncio
import gc
from machine import Pin
        
GV = None
RunRequest = True
    
def btnESC_LongPressed():
    global RunRequest
    RunRequest = False
        
print("=========  RPW APPLICATION STARTED  =========")
async def main():
    global GV, RunRequest
    gc.threshold((gc.mem_free() + gc.mem_alloc()) // 2)
    
    if Pin(22, Pin.IN, Pin.PULL_UP).value() == 0:
        return
    
    GV = GlobalVars()
    GV.Board.btnESC_LongPress(btnESC_LongPressed)
    ts = utime.time()
    STA_Activated = False
    STA_Fail_ts = None
    while RunRequest:
        if (utime.time()-ts) > 20:
            RunRequest = True
        if not STA_Activated and (utime.time()-ts) > 3 and STA_Fail_ts == None:
            await GV.Net.STA_Connect()
            STA_Activated = True
        if not STA_Activated and STA_Fail_ts != None and (utime.time()-STA_Fail_ts) > 10:
            await GV.Net.STA_Connect()
            STA_Activated = True
        if STA_Activated and GV.Net.STA.status() <= 0:
            STA_Fail_ts = utime.time()
            STA_Activated = False
            
        await uasyncio.sleep_ms(0)      
    print(' -> GUI shutdown requested')

async def shutdown():
    global GV
    if GV != None:
        GV.deinit()
        GV = None
        gc.collect()


if __name__ == '__main__':
    try:
        uasyncio.run(main())
    except KeyboardInterrupt:
        print(' -> REPL interrupt requested')
    except Exception as e:
        import sys
        print()
        print('====================ERROR====================') 
        sys.print_exception(e)
        print('---------------------------------------------')
        print()
    finally:
        uasyncio.run(shutdown())
        print("=========  RPW APPLICATION STOPPED  =========")
