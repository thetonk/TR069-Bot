import paramiko, re, hashlib, requests, traceback, config
from bs4 import BeautifulSoup
from datetime import datetime

class Modem():

    def __init__(self):
        self.attainableUP = 0
        self.attainableDOWN = 0
        self.syncUP = 0
        self.syncDOWN = 0
        self.snrUP = 0
        self.snrDOWN = 0
        self.attenuationUP = 0
        self.attenuationDOWN = 0
        self.powerUP = 0
        self.powerDOWN = 0
        self.crcUP = 0
        self.crcDOWN = 0
        self.fecUP = 0
        self.fecDOWN = 0
        self.isOnline = True
    
    def fetchNums(self,string, integer):
        #if integer:
        #    outlist = [int(s) for s in re.findall("\d+",string)]
        #else:
        #    outlist = [float(s) for s in re.findall("[+-]?[0-9]+\.[0-9]+",string)]
        #    if len(outlist) == 0:
        #        self.fetchNums(string, True) #no match, so number is an integer
        return [float(s) for s in re.findall("[+-]?[0-9]+\.?[0-9]*",string)]
    
    def connect(self):
        pass
    
    def disconnect(self):
        pass
    
    def updateStats(self):
        raise NotImplementedError
    
    def showStats(self):
        print(self.fecUP, self.fecDOWN)
        print("ATTAINABLE UP %d ATTAINABLE DOWN %d" %(self.attainableUP, self.attainableDOWN))
        print("SYNC UP: %d SYNC DOWN %d" % (self.syncUP, self.syncDOWN))
        print("SNRS %f %f\nATT %f %f\nPOWER %f %f" % (self.snrUP, self.snrDOWN, self.attenuationUP, self.attenuationDOWN, self.powerUP, self.powerDOWN))
    
    

class TechnicolorModem(Modem):
    def __init__(self, HOST, USERNAME, PASSWORD):
        super().__init__()
        self.HOST = HOST
        self.USERNAME = USERNAME
        self.PASSWORD = PASSWORD
        self.COMMANDS = {
            "dsl_status":"sys.class.xdsl.@line0.Status",
            "dsl_type":"sys.class.xdsl.@line0.ModulationType",
            "dsl_linerate_up":"sys.class.xdsl.@line0.UpstreamCurrRate",
            "dsl_linerate_down":"sys.class.xdsl.@line0.DownstreamCurrRate",
            "dsl_linerate_up_max":"sys.class.xdsl.@line0.UpstreamMaxRate",
            "dsl_linerate_down_max":"sys.class.xdsl.@line0.DownstreamMaxRate",
            "dsl_uptime":"sys.class.xdsl.@line0.ShowtimeStart",
            "dsl_power_up":"sys.class.xdsl.@line0.UpstreamPower",
            "dsl_power_down":"sys.class.xdsl.@line0.DownstreamPower",
            "dsl_attenuation_up":"sys.class.xdsl.@line0.UpstreamAttenuation",
            "dsl_attenuation_down":"sys.class.xdsl.@line0.DownstreamAttenuation",
            "dsl_margin_up":"sys.class.xdsl.@line0.UpstreamNoiseMargin",
            "dsl_margin_down":"sys.class.xdsl.@line0.DownstreamNoiseMargin",
            "dsl_fec_up":"sys.class.xdsl.@line0.UpstreamFECTotal",
            "dsl_fec_down":"sys.class.xdsl.@line0.DownstreamFECTotal",
            "dsl_crc_up":"sys.class.xdsl.@line0.UpstreamCRCTotal",
            "dsl_crc_down":"sys.class.xdsl.@line0.DownstreamCRCTotal",
        }
    
    def connect(self):
        print("SSH CONNECTING " + self.HOST)
        self.client = paramiko.SSHClient()
        try:
            self.client.load_host_keys("host_key.txt")
            self.client.connect(self.HOST,username=self.USERNAME, password=self.PASSWORD)
        except FileNotFoundError:
            print("Key file not found, saving current")
            with open("host_key.txt", "w") as f:
                pass
            self.client.set_missing_host_key_policy(paramiko.client.AutoAddPolicy())
            self.client.connect(self.HOST,username=self.USERNAME, password=self.PASSWORD)
            self.client.save_host_keys("host_key.txt")
    
    def disconnect(self):
        if self.client is not None:
            self.client.close()
    def getStats(self, cmd):
        if self.client is not None:
            stdin, stdout, stderr = self.client.exec_command("transformer-cli get " + self.COMMANDS[cmd])
            return stdout.readline().split("=")[1].strip()

    def updateStats(self):
        if self.getStats("dsl_status") == "Up":
            self.isOnline = True
        else:
            self.isOnline = False
        try:
            self.attainableUP = self.fetchNums(self.getStats("dsl_linerate_up_max"), True)[0]
            self.attainableDOWN = self.fetchNums(self.getStats("dsl_linerate_down_max"), True)[0]
            self.syncUP = self.fetchNums(self.getStats("dsl_linerate_up"), True)[0]
            self.syncDOWN = self.fetchNums(self.getStats("dsl_linerate_down"), True)[0]
            self.snrUP = self.fetchNums(self.getStats("dsl_margin_up"), False)[0]
            self.snrDOWN = self.fetchNums(self.getStats("dsl_margin_down"), False)[0]
            self.attenuationUP = self.fetchNums(self.getStats("dsl_attenuation_up"), False)[0]
            self.attenuationDOWN = self.fetchNums(self.getStats("dsl_attenuation_down"), False)[0]
            self.powerUP = self.fetchNums(self.getStats("dsl_power_up"), False)[0]
            self.powerDOWN = self.fetchNums(self.getStats("dsl_power_down"), False)[0]
            self.crcUP = self.fetchNums(self.getStats("dsl_crc_up"), True)[0]
            self.crcDOWN = self.fetchNums(self.getStats("dsl_crc_down"), True)[0]
            self.fecUP = self.fetchNums(self.getStats("dsl_fec_up"), True)[0]
            self.fecDOWN = self.fetchNums(self.getStats("dsl_fec_down"), True)[0]
        except IndexError as i:
            print("ERROR: ", i)
            timestr = datetime.now().strftime("%m-%d-%Y_%H.%M.%S")
            with open(timestr+".txt", "a") as file:
                file.write(traceback.format_exc()+"\n")
                print("==============================DATA=================================")
                file.write("==============================DATA=================================\n")
                values = self.COMMANDS.keys()
                for value in values:
                    print(value, self.getStats(value))
                    file.write(value+"\t"+self.getStats(value)+"\n")
                print("==============================END DATA=============================")
                file.write("==============================END DATA============================="+"\n")

    def updateLineState(self):
        if self.getStats("dsl_status") == "Up":
            self.isOnline = True
        else:
            self.isOnline = False
            
    def reboot(self):
        if self.client is not None:
            self.client.exec_command("reboot")
    
    def disconnectLine(self):
        if self.client is not None:
            self.client.exec_command("xdslctl connection --down")

    def connectLine(self):
        if self.client is not None:
            self.client.exec_command("xdslctl connection --up")

    def showStats(self):
        super().showStats() 

class ZTEModem(Modem):
    def __init__(self, HOST, USERNAME, PASSWORD):
        super().__init__()
        self.IPAddress = ""
        self.HOST = HOST
        self.USERNAME = USERNAME
        self.PASSWORD = PASSWORD

    def parseData(self, source):
        #print("--------------------------------------------------------------------------------------------------------")
        #soup = BeautifulSoup(source, "lxml")
        labels = source.find_all("paraname")
        values = source.find_all("paravalue")
        #This implementation is bad, I know
        for i in range(len(labels)):
            #print(labels[i].text, values[i].text)
            label = labels[i].text
            if label == "IPAddress":
                self.IPAddress = values[i].text
                continue

            if label == "Fec_errors":
                self.stats[0][0] = int(values[i].text)
                continue

            if label == "Atuc_fec_errors":
                self.stats[0][1] = int(values[i].text)
                continue

            if label == "Upstream_max_rate":
                self.attainableUP = int(values[i].text)
                continue

            if label == "Downstream_max_rate":
                self.attainableDOWN = int(values[i].text)
                continue

            if label == "Upstream_current_rate":
                self.syncUP = int(values[i].text)
                continue

            if label == "Downstream_current_rate":
                self.syncDOWN = int(values[i].text)
                continue

            if label == "UpCrc_errors":
                self.stats[1][1] = int(values[i].text)
                continue

            if label == "DownCrc_errors":
                self.stats[1][0] = int(values[i].text)
                continue

            if label == "Upstream_attenuation":
                self.attenuationUP = float(values[i].text)/10
                continue

            if label == "Downstream_attenuation":
                self.attenuationDOWN = float(values[i].text)/10
                continue

            if label == "Upstream_power":
                self.powerUP = float(values[i].text)/10
                continue

            if label == "Downstream_power":
                self.powerDOWN = float(values[i].text)/10
                continue

            if label == "Upstream_noise_margin":
                self.snrUP = float(values[i].text)/10
                continue
            
            if label == "Downstream_noise_margin":
                self.snrDOWN = float(values[i].text)/10
                continue
    
    def updateStats(self):
        h = hashlib.new("sha256")
        session = requests.Session()
        session.get("http://{}".format(self.HOST))
        randomnumber = session.get("http://{}/function_module/login_module/login_page/logintoken_lua.lua".format(self.HOST))
        soup = BeautifulSoup(randomnumber.content, "lxml")
        passnumber = soup.find("ajax_response_xml_root").text
        #print(randomnumber.content)
        h.update((("{}"+passnumber).format(self.PASSWORD)).encode())
        password = h.hexdigest()
        #print(password)
        payload={"Username":"admin", "Password":password, "action":"login"}
        r = session.post("http://{}".format(self.HOST), data=payload, allow_redirects=False)
        r = session.get("http://{}".format(self.HOST))
        print(r.status_code)
        session.get("http://{}/getpage.lua?pid=1002&nextpage=Internet_AdminInternetStatus_DSL_t.lp".format(self.HOST))
        dataXML = session.get("http://{}/common_page/internet_dsl_interface_lua.lua".format(self.HOST))
        internetSoup = BeautifulSoup(dataXML.content, "lxml")
        self.parseData(internetSoup.find("instance"))
        dataXML = session.get("http://{}/common_page/Internet_Internet_lua.lua?TypeUplink=1&pageType=1".format(self.HOST))
        IPSoup = BeautifulSoup(dataXML.content, "lxml")
        self.parseData(IPSoup.find_all("instance")[4])
    
    def showStats(self):
        super().showStats()
        print("IP ADDRESS: ", self.IPAddress)

def getRouter():
    router = None
    brand = config.ROUTER_BRAND.lower()
    if brand.__contains__("zte"):
        router = ZTEModem(config.HOST, config.USERNAME, config.PASSWORD)
    elif brand.__contains__("technicolor"):
        router = TechnicolorModem(config.HOST, config.USERNAME, config.PASSWORD)
    return router
