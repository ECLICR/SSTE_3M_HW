class NetworkSettings:
    __SSID = ""
    __Password = ""
    __IP = None
    __SM = None
    __DG = None
    __DNS = None
    
    def __init__(self, SSID, Password, IP = None, SM = None, DG = None, DNS = None):
        self.__SSID = SSID
        self.__Password = Password
        self.__IP = IP
        self.__SM = SM
        self.__DG = DG
        self.__DNS = DNS
    
    @property
    def SSID(self):
        return self.__SSID

    @property
    def Password(self):
        return self.__Password
    
    @property
    def IP(self):
        return self.__IP
    
    @property
    def SM(self):
        return self.__SM
    
    @property
    def DG(self):
        return self.__DG
    
    @property
    def DNS(self):
        return self.__DNS
    