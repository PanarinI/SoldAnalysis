from sqlalchemy import create_engine
import pandas as pd

# Замените параметры подключения на свои
username = 'postgres'
password = 'Pdjyjr2'
host = 'localhost'
port = '5432'
database = 'SoldAnalysis'

# Создаем строку подключения
connection_string = f'postgresql+psycopg2://{username}:{password}@{host}:{port}/{database}'

# Создаем подключение
engine = create_engine(connection_string)