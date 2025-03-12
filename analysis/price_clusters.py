import pandas as pd
import numpy as np
from sklearn.cluster import DBSCAN
import matplotlib
matplotlib.use('Agg')  # Используем неинтерактивный бэкенд
import matplotlib.pyplot as plt
from sqlalchemy import create_engine

# Подключение к базе данных PostgreSQL
DB_URI = "postgresql+psycopg2://postgres:Pdjyjr2@localhost:5432/SoldAnalysis"
engine = create_engine(DB_URI)

# Загрузка данных
prices = pd.read_sql("SELECT price FROM public.sold_usernames", engine)

# Преобразуем данные в двумерный массив
X = prices['price'].values.reshape(-1, 1)

# Применяем DBSCAN
dbscan = DBSCAN(eps=1000, min_samples=5)  # Подберите eps и min_samples под ваши данные
labels = dbscan.fit_predict(X)

# Выводим результаты
print("Метки кластеров:", labels)

# Количество кластеров (исключая шум, который помечен как -1)
n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
print("Количество кластеров:", n_clusters)

# Количество выбросов (шум)
n_noise = list(labels).count(-1)
print("Количество выбросов (шум):", n_noise)

# Визуализация
plt.scatter(prices['price'], np.zeros_like(prices['price']), c=labels, cmap='viridis', label='Data points')
plt.xlabel('Price')
plt.title('Price Clusters with DBSCAN')
plt.legend()

# Сохраняем график в файл
plt.savefig('price_clusters_dbscan.png')
print("График сохранен в файл 'price_clusters_dbscan.png'")







