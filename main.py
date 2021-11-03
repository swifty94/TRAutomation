
import pandas as pd
import cx_Oracle as oracledb
import json, re, csv
from timeit import default_timer as timer
from os import path
from functools import cache
from datetime import datetime
import logging
import logging.config
_log_file_path = path.join(path.dirname(path.abspath(__file__)), 'logging.ini')
logging.config.fileConfig(_log_file_path)

class JsonParser(object):
    "Getter of JSON settings values for application runtime settings"
    @staticmethod
    def getVal(json_key):
        try:
            __json_file='settings.json'
            with open(__json_file) as f:
                data = json.load(f)       
            json_value = data[json_key]
            return json_value
        except Exception as e:
            logging.error(f'Exception: {e}', exc_info=1)

class AppSettings(object):
    """
    Setter of application entities based on JSON settings
    """
    def __init__(self) -> None:
        """
        Auto initialization of the settings.json properties and
        loading them into the Py object properties
        \n:args - None
        """
        super().__init__()
        n = __class__.__name__
        self.inputFile = JsonParser.getVal("inputXlsxPath")
        self.outputFile = JsonParser.getVal("outputCsvName")
        self.dbUser = JsonParser.getVal("DbUser")
        self.dbPass = JsonParser.getVal("DbPassword")
        self.dbDsn = JsonParser.getVal("DbDsn")
        logging.info(f'{n} initialization finished')
        for k,v in zip(self.__dict__.keys(), self.__dict__.values()):
            logging.info(f'{n} {k} : {v}')

class InputXlsx(object):
    def __init__(self, XlsxFile: str) -> None:
        """
        XLSX object with methods to get required data 
        \n:args 
            - str: path to the XLSX file
        """
        super().__init__()
        self.n = __class__.__name__
        self.XlsxFile = XlsxFile
        logging.info(f'{self.n} Received XLSX {self.XlsxFile} for processing')
        self.dataFrame = pd.read_excel(self.XlsxFile)

    @cache
    def getSerialList(self) -> list:
        try:
            snList = self.dataFrame["Serial"].tolist()
            if len(snList) > 0:
                logging.info(f'{self.n} getSerialList -> processed CPESerialList with length {len(snList)}')
                return snList
            else:
                logging.info(f'{self.n} getSerialList -> CPESerialList is empty! Check the log for the errors or validate your XLSX file')
                return None
        except Exception as e:
            logging.error(f'{self.n} Exception: {e}', exc_info=1)

    @cache
    def getMacList(self) -> list:
        try:
            macList = self.dataFrame["MAC Address"].tolist()
            if len(macList) > 0:
                logging.info(f'{self.n} getSerialList -> processed CPEMacAddrList with length {len(macList)}')
                return macList
            else:
                logging.info(f'{self.n} getSerialList -> CPEMacAddrList is empty! Check the log for the errors or validate your XLSX file')
                return None
        except Exception as e:
            logging.error(f'{self.n} Exception: {e}', exc_info=1)

    @cache
    def getManufacturerList(self) -> list:
        try:
            manufList = self.dataFrame["Manufacturer"].tolist()
            if len(manufList) > 0:
                logging.info(f'{self.n} getManufacturerList -> processed CPEManufacturerList with length {len(manufList)}')
                return manufList
            else:
                logging.info(f'{self.n} getManufacturerList -> CPEManufacturerList is empty! Check the log for the errors or validate your XLSX file')
                return None
        except Exception as e:
            logging.error(f'{self.n} Exception: {e}', exc_info=1)
    
    @cache
    def getModelList(self) -> list:
        try:
            modelList = self.dataFrame["Model name"].tolist()
            if len(modelList) > 0:
                logging.info(f'{self.n} getModelList -> processed CPEModelList with length {len(modelList)}')
                return modelList
            else:
                logging.info(f'{self.n} getModelList -> CPEModelList is empty! Check the log for the errors or validate your XLSX file')
                return None
        except Exception as e:
            logging.error(f'{self.n} Exception: {e}', exc_info=1)

class OracleDb(object):
    """
    Class of DB data processor using Oracle connector API
    """
    def __init__(self, dbUser, dbPass, dbDsn) -> None:
        super().__init__()
        """
        Init database properties
        \n:args 
            - dbUser: str
            - dbPass: str
            - dbDsn: str
        """
        self.n = __class__.__name__
        self.dbUser = dbUser
        self.dbPass = dbPass
        self.dbDsn = dbDsn        

    def init_connection(self) -> object:
        try:
            dbConnection = oracledb.connect(
                user=self.dbUser,
                password=self.dbPass,
                dsn=self.dbDsn
            )
            isValid = self.validate_connection(dbConnection)
            if isValid:
                return dbConnection
        except Exception as e:
            logging.error(f'{self.n} Exception: {e}', exc_info=1)

    def validate_connection(self, connection: object) -> bool:
        try:
            cursor = connection.cursor()
            cursor.execute("select 1 from dual")
            value = cursor.fetchall()
            match = [(1,)]
            if value != match:
                logging.exception(f'{self.n} Database connection validation FAILED!')
                return False
            return True
        except Exception as e:
            logging.error(f'{self.n} Exception: {e}', exc_info=1)

    def doSelect(self, sql) -> list:
        try:
            connection = self.init_connection()
            cursor = connection.cursor()
            cursor.execute(sql)
            value = cursor.fetchall()
            return value
        except Exception as e:
            logging.error(f'{self.n} Exception: {e}', exc_info=1)
            logging.error(f'{self.n} SQL used: {sql}')
        finally:
            cursor.close()
            if connection:
                connection.close()

class DataProcessor(object):
    """
    Class for getting data for final report
    """
    def __init__(self, db: OracleDb, inputXlsx: InputXlsx) -> None:
        """
        Loading OracleDb and InputXlsx as datasources with their methods
        and populating others with their methods\n
        :args
            - db: OracleDb object\n
            - inputXlsx: InputXlsx object
        """
        super().__init__()
        self.n = __class__.__name__
        self.db = db
        self.xlsx = inputXlsx
        self.cpeList = self.xlsx.getSerialList()
        self.macList = self.xlsx.getMacList()        
        self.ACTIVE_IP_SQL = """
select p.value
from  cpe_parameter p, cpe_parameter_name n
where p.name_id=n.id and
( n.name like 'Device.ManagementServer.UDPConnectionRequestAddress' OR
n.name like 'Device.ManagementServer.ConnectionRequestURL' OR
n.name like 'Device.IP.Interface.%.IPv%Address.%.IPAddress' OR
n.name like '%.ManagementServer.ConnectionRequestURL') and
        """
        self.ACTIVE_CONNECTION_OBJ_SQL = """
select n.name
from cpe_parameter p, cpe_parameter_name n
where p.name_id=n.id and      
        """
        self.WAN_CONNECTION_SQL = """
select p.value
from cpe_parameter p, cpe_parameter_name n
where p.name_id=n.id and
"""

    @cache
    def getCpeIdList(self) -> list:
        cpeIdList = [self.db.doSelect(f"select id from cpe where serial='{cpe}'") for cpe in self.cpeList]
        cpeIdList = [str(i).replace('(','').replace(')','').replace(',','').replace('[','').replace(']', '') for i in cpeIdList]
        cpeIdList = [int(i) for i in cpeIdList]
        return cpeIdList

    def getConnectionTypeParameterName(self, paramName: str) -> str:
        """
        Obtaining the name of full path of TR parameter for ConnectionType based on active WAN connection object path\n
        \nE.g., active connection was found in InternetGatewayDevice.WANDevice.1.WANConnectionDevice.2.WANIPConnection.1.ExternalIPAddress
        \n However, the ConnectionType needs to be obtained from WANPPPConnection node
        \n Thus, we'll need to replace ExternalIPAddress with ConnectionType + based on parent node substitute it (or not) with WANPPPConnection\n
        >>> param = r'InternetGatewayDevice.WANDevice.1.WANConnectionDevice.5.WANIPConnection.2.ExternalIPAddress'
        >>> connTypeParam = getConnectionTypeParameterName(param)
        >>> connTypeParam
        'InternetGatewayDevice.WANDevice.1.WANConnectionDevice.5.WANPPPConnection.2.ConnectionType'
        >>>
        """
        try:
            wanPppObject = r"WANPPPConnection"
            wanIpObject = r"WANIPConnection"
            if wanIpObject in paramName:
                connectionTypeParameter = re.sub(r"ExternalIPAddress", r"ConnectionType", paramName)
                connectionTypeParameter = re.sub(f"{wanIpObject}", f"{wanPppObject}", connectionTypeParameter)
            else:
                connectionTypeParameter = re.sub(r"ExternalIPAddress", r"ConnectionType", paramName)
            return connectionTypeParameter
        except Exception as e:
            logging.error(f'{self.n} Exception: {e}', exc_info=1)

    def getConnectionType(self):
        try:
            connectionTypeFinalList = []
            for cid in self.getCpeIdList():
                logging.info(f'{self.n} Started processing data for cpeId={cid}')
                activeIp = self.db.doSelect(self.ACTIVE_IP_SQL+f"p.cpe_id = {cid}")
                activeIp = str(activeIp)
                activeIp = re.search('[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}', activeIp)
                if activeIp != None:
                    activeIp = activeIp.group(0)
                    activeConnectionObject = self.db.doSelect(self.ACTIVE_CONNECTION_OBJ_SQL+f"p.value = '{activeIp}' and p.cpe_id = {cid}")
                    activeConnectionObject = str(activeConnectionObject)
                    activeConnectionObject = activeConnectionObject.replace('"','').replace('\'','').replace('[','').replace(']','').replace('(','').replace(')','').replace(',','')
                    if len(activeConnectionObject) <= 0:
                        logging.info(f'{self.n} CpeId = {cid}; activeConnectionObject not found!')
                        logging.info(f'{self.n}  %.WANIPConnection.%.ExternalIPAddress or %.WANPPPConnection.%.ExternalIPAddress was not found or empty')
                        logging.info(f'{self.n}  Algorithm of obtaining WAN object / connection type will not work on this CPE')
                        connectionTypeFinalList.append(None)
                        continue
                    else:                        
                        connectionTypeParam = self.getConnectionTypeParameterName(activeConnectionObject)
                        connectionTypeParamValue = self.db.doSelect(self.WAN_CONNECTION_SQL+f"n.name = '{connectionTypeParam}' and p.cpe_id = {cid}")
                        connectionTypeParamValue = str(connectionTypeParamValue).replace("[",'').replace("]",'').replace("(",'').replace(")",'').replace(",",'')
                        if len(connectionTypeParamValue) <= 0:
                            logging.info(f'{self.n} connectionTypeParameter=None or empty')
                            connectionTypeParamValue = None
                            connectionTypeFinalList.append(connectionTypeParamValue)
                        elif "L2TP" in connectionTypeParamValue:
                            connectionTypeFinalList.append(connectionTypeParamValue)
                    logging.info(f'{self.n} Finished processing data for cpeId={cid}')
                    logging.debug(f'\n{self.n} activeConnectionObject={activeConnectionObject};\n connectionTypeParam={connectionTypeParam};\n connectionTypeParamValue={connectionTypeParamValue}')
            return connectionTypeFinalList
        except Exception as e:
            logging.error(f'{self.n} Exception: {e}', exc_info=1)

class OutputCsv(object):
    """
    Class for creating final CSV report of filtered data
    """
    def __init__(self, outputFile, dataProcessor: DataProcessor, inputXlsx: InputXlsx) -> None:
        """
        
        """
        super().__init__()
        self.n = __class__.__name__
        self.csvF = outputFile
        self.dataProcessor = dataProcessor
        self.xlsx = inputXlsx
        self.serials = self.xlsx.getSerialList()
        self.manufacturer = self.xlsx.getManufacturerList()
        self.model = self.xlsx.getModelList()
        self.connectionType = self.dataProcessor.getConnectionType()
        self.columns = ['Serial', 'Manufacturer', 'Model name', 'Connection type']

    def createFinalReport(self):
        try:
            logging.info(f'{self.n} Started creating CSV report')
            __cnt = 0
            now = datetime.now()
            date = now.strftime("%m_%d_%H-%M-%S")
            csvfile = f"{self.csvF}_{date}.csv"            
            with open(csvfile, 'a', newline ='') as f:               
                writer = csv.DictWriter(f, delimiter=',', quoting=csv.QUOTE_NONNUMERIC, lineterminator='\n', fieldnames=self.columns)                
                writer.writeheader()                
                for sn, manuf, model, connT in zip(self.serials, self.manufacturer, self.model, self.connectionType):
                    __cnt += 1
                    __d = {
                        'Serial' : sn,
                        'Manufacturer' : manuf,
                        'Model name' : model,
                        'Connection type' : connT
                    }
                    logging.info(f'{self.n} dataToCsv: {__d}')
                    writer.writerow(__d)
                    logging.info(f'{self.n} writerow number: {__cnt}')
                logging.info(f'{self.n} Finished creating CSV report')
                return __cnt
        except Exception as e:
            logging.error(f'{self.n} Exception: {e}', exc_info=1)
            return 0


if __name__ == "__main__":
    try:
        print(__name__+"-"*30+" START "+"-"*30)
        __starttime = timer()
        logging.info("-"*30+" START "+"-"*30)
        
        app = AppSettings()
        xlsx = InputXlsx(app.inputFile)
        db = OracleDb(app.dbUser, app.dbPass, app.dbDsn)
        dataP = DataProcessor(db, xlsx)
        Csv = OutputCsv(app.outputFile, dataP, xlsx) 
        report = Csv.createFinalReport()
        print(f'Processed CPEs: {report}')
        __endtime = timer()
        __elapsed = round(__endtime - __starttime, 3)
        print(f'Elapsed time: {__elapsed} sec\n')
        if report:
            print(f'ResultOfReportCreation: Success')
            logging.info("-"*30+" FINISHED OK "+"-"*30)
            print(__name__+"-"*30+" FINISHED OK "+"-"*30)
            exit(0)
        else:
            print(f'ResultOfReportCreation: Fail')
            logging.info("-"*30+" FAILED "+"-"*30)
            print(__name__+"-"*30+" FAILED "+"-"*30)
            exit(1)
    except Exception as e:
        print(f'ResultOfReportCreation: Fail')
        print(f'Exception in the program entry point __main__:')
        print(f'Program finished with errors. Review the log for the details.')
        logging.info("-"*30+" FAILED "+"-"*30)
        print(__name__+"-"*30+" FAILED "+"-"*30)
        exit(2)