#TR-069 Data processing automation

Design:
---
- first data source (DS1) is the XLSX with the list of CPEs
- second data source (DS2) is FTL RDMS, Oracle in this case
- we need to take the router from DS1 (e.g., serial number) > search for it in DS2 > find the connection type of active WAN interface
- if the connection type is L2TP > save it to the CSV output (third data source)

NOTE: in order to find an active connection WAN object, we need to find the match of the router IP address somewhere in the WANDevice object
e.g., %.WANIPConnection.%.ExternalIPAddress or %.WANPPPConnection.%.ExternalIPAddress

NOTE2: once we found an instance of active connection we need to find the value for the connection type parameter within the same instance
E.g., based on router IP address, the active connection object is

InternetGatewayDevice.WANDevice.3.WANConnectionDevice.3.WANIPConnection.1.ExternalIPAddress

thus, the connection type should be searched in

InternetGatewayDevice.WANDevice.3.WANConnectionDevice.3.WANPPPConnection.1.ConnectionType

NOTE3: if the router does not have such parameter or its value is empty it will be reflected in the app.log. E.g.,

<pre>
[2021-02-11 10:46:45] [INFO] [main] [DataProcessor Started processing data for cpeId=16090] [getConnectionType]
[2021-02-11 10:46:47] [INFO] [main] [DataProcessor connectionTypeParameter=None or empty] [getConnectionType]
</pre>

Requirements:
---

- Python 3.X MUST be installed on the machine where the program is being executed
https://www.python.org/downloads/

- Oracle client (instant or full) MUST be installed on the machine where the program is being executed
https://www.oracle.com/database/technologies/instant-client.html

Installation:
---    
- If there is access to the Internet
<pre>
    Linux:
        - open terminal
        - cd to the folder of the project
        - python3 -m venv venv
        - ./venv/Scripts/activate
        - pip3 install -r dependecies.txt
       
    Windows:
        - open CMD
        - cd to the folder of the project
        - py -m venv venv
        - ./venv/Scripts/activate.bat
        - pip3 install -r dependecies.txt
        
</pre>

- TODO: - dependencies installation without Internet

Usage:
---

- Put the relevant details in the settings.json file. Explanation:

<pre>
{
    "inputXlsxPath": "path/to/your/input.xlsx",      // NOTE: on Windows you might need to use the unix-like style of paths e.g.,
                                                    C:/mydir

    "outputCsvName": "NameOfReportFile",             // NOTE: do NOT put file extension here. The report will be saved as
                                                    "NameOfReportFile_MM_DD_HH-MM-SS.csv"

    "DbUser": "ftacs",                               // Database user

    "DbPassword": "ftacs",                           // Database password

    "DbDsn": "10.0.0.1/FTACS"    // Connection string for Oracle must be in format "IP_OR_HOSTNAME/ORACLE_SID"
}
</pre>

- Open CMD/terminal in the folder of the project

- Run: python3 main.py. Example of the successful program execution:

<pre>
(venv) C:\Users\Documents\TR_Automation>python main.py
__main__------------------------------ START ------------------------------
Processed CPEs: 9
Elapsed time: 18.187 sec

ResultOfReportCreation: Success
__main__------------------------------ FINISHED OK ------------------------------

(venv) C:\Users\Documents\TR_Automation>
</pre>
