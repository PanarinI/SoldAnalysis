import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')  # Используем неинтерактивный бэкенд
import matplotlib.pyplot as plt
import seaborn as sns
from scipy.stats import gaussian_kde
from scipy.signal import find_peaks
from sqlalchemy import create_engine

# Подключение к базе данных PostgreSQL
DB_URI = "postgresql+psycopg2://postgres:Pdjyjr2@localhost:5432/SoldAnalysis"
engine = create_engine(DB_URI)

# Загрузка данных
prices = pd.read_sql("SELECT price FROM public.sold_usernames", engine)

# Фильтрация: убираем значения выше 10000
prices_filtered = prices[prices['price'] <= 1000]

# Расчет медианы по всей выборке (без фильтрации)
median_price_all = prices['price'].median()

# Проверим минимальное и максимальное значения
print(f"Минимальная цена: {prices['price'].min()}")
print(f"Максимальная цена: {prices['price'].max()}")
print(f"Медиана цены по всей выборке: {median_price_all}")



# Построим гистограмму для отфильтрованных данных
sns.histplot(prices_filtered['price'], bins=20, kde=True)
plt.title('Распределение цен (до 1000)')
plt.xlabel('Цена')
plt.ylabel('Частота')

# Сохраняем график в файл
plt.savefig('filtered_price_distribution.png')  # Сохранение в PNG
# Закрываем график, чтобы освободить память
plt.close()

# Сохраняем график в файл
plt.savefig('price_distribution.png')  # Сохранение в PNG
# Закрываем график, чтобы освободить память
plt.close()
# Вычисляем KDE
density = gaussian_kde(prices_filtered['price'])
x_values = np.linspace(prices_filtered['price'].min(), prices_filtered['price'].max(), 1000)
y_values = density(x_values)

# Находим локальные максимумы (моды)
peaks, _ = find_peaks(y_values, height=0.00001)  # height задает минимальную высоту пика
modes = x_values[peaks]  # Значения x, соответствующие пикам

# Проверяем, что найдено хотя бы две моды
if len(modes) < 2:
    raise ValueError("Недостаточно мод для поиска минимальной плотности между ними.")

# Выбираем первую и вторую моду
first_mode = modes[0]
second_mode = modes[1]

# Находим минимальную плотность между первой и второй модами
mask = (x_values >= first_mode) & (x_values <= second_mode)
x_between_modes = x_values[mask]
y_between_modes = y_values[mask]

min_density_index = np.argmin(y_between_modes)
min_density_x = x_between_modes[min_density_index]
min_density_y = y_between_modes[min_density_index]

# Построение графика плотности
plt.figure(figsize=(10, 6))
sns.kdeplot(prices_filtered['price'], fill=True, color='blue', label='Плотность цен (до 10000)', clip=(0, None))

# Добавляем вертикальные пунктирные линии для мод
plt.axvline(x=first_mode, color='red', linestyle='--', label=f'Мода 1: {first_mode:.2f}')
plt.axvline(x=second_mode, color='green', linestyle='--', label=f'Мода 2: {second_mode:.2f}')

# Добавляем вертикальную линию для минимальной плотности
plt.axvline(x=min_density_x, color='purple', linestyle='--', label=f'Минимальная плотность: {min_density_x:.2f}')

# Подписываем значения на оси X
plt.text(first_mode, density(first_mode) * 0.9, f'{first_mode:.2f}', color='red', fontsize=12, ha='center')
plt.text(second_mode, density(second_mode) * 0.9, f'{second_mode:.2f}', color='green', fontsize=12, ha='center')
plt.text(min_density_x, min_density_y * 0.9, f'{min_density_x:.2f}', color='purple', fontsize=12, ha='center')

# Настройка графика
plt.xlabel('Цена')
plt.ylabel('Плотность')
plt.title('Минимальная плотность между модами')
plt.legend()

# Сохраняем график в файл
plt.savefig('price_density_min_between_modes_plot.png')
print("График плотности с минимальной плотностью между модами сохранен в файл 'price_density_min_between_modes_plot.png'")