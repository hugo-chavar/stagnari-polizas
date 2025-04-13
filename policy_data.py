import pandas as pd
from io import StringIO

 # TODO: replace accents
csv = """Matricula,Referencia,Cliente,Marca,Modelo,Año
SDB4050,8585536,\"GOLDARACENA CANTONI, EDUARDO\",SUZUKI,ALTO 800 GL,2017
B590070,9604283,DISTRAVI SA,MITSUBISHI,L200 3.5 GLS 4X4,2010
SDD6542,9176866,\"BERMUDEZ MATTIAS, CARLOS ADOLFO\",TRAILER,,2014
AAQ4798,9627417,\"DE LUCA RODRIGUEZ, VERONICA GABRIELA\",VOLKSWAGEN,UP! TAKE 1.0,2017
ABF9639,AR115368,\"SOÑORA FERNANDEZ, JUAN ANDRES\",HAVAL,JOLION 1.5 HEV,2024
ANE302,8895018,\"BELLO LARROCA, JORGE LUIS\",HONDA,1500 GOLD WING,1995
SCY9936,8944590,\"FRANZINI FROS, CESAR RAUL\",JAC,1035 HFC K 2.8 ABS CON CAJA,2022
AAW1102,8995376,\"LERMA SCHNECK, FLORENCIA Victoria\",TOYOTA,RAV4 2.5 LIMITED HYBRID 4X4 AUT.,2020
SBN4905,1914467,\"NUÑEZ PEREIRA, JOAQUIN\",VOLKSWAGEN,GOL 1.6 COMPORTLINE VI A/A SEDAN,2013
SDC7023,9080794,\"LINARES PEREZ, JORGE PABLO\",BYD,E2 GS 70 KW EXTRA FULL AUT.,2024
SCT1246,9096163,\"LINARES PEREZ, RICHARD ALEJANDRO\",BYD,E2 GL 300 EXTRA FULL AUT.,2022"""

df = None

def load_csv_data():
    # df = pd.read_csv("seguros_autos.csv")
    global df
    df = pd.read_csv(StringIO(csv))

def apply_filter(query_string, columns):
    result = df.query(query_string, engine='python')[columns]
    csv_string = result.to_csv(index=False, lineterminator ='\n')
    return csv_string
