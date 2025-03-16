import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sqlalchemy import create_engine
from IPython.display import display
from ipywidgets import interact, FloatSlider, IntRangeSlider, widgets, interactive_output
import re
from ipywidgets import FloatSlider, IntRangeSlider, interactive_output, VBox, widgets
from datetime import datetime
import plotly.express as px


# Подключение к базе данных
DB_URI = "postgresql+psycopg2://postgres:Pdjyjr2@localhost:5432/SoldAnalysis"
engine = create_engine(DB_URI)

# Функция для загрузки данных
def get_price_distribution(start_date=None, end_date=None):
    query = """
        SELECT price
        FROM public.sold_usernames
        WHERE (%s IS NULL OR sale_date >= %s)
          AND (%s IS NULL OR sale_date <= %s)
    """
    params = (start_date, start_date, end_date, end_date)
    return pd.read_sql(query, engine, params=params)


# Виджеты для выбора дат
start_date_picker = widgets.DatePicker(description='Начальная дата:', value=datetime(2023, 1, 1))
end_date_picker = widgets.DatePicker(description='Конечная дата:', value=datetime.today())

# Слайдеры для выбора диапазона цен
min_slider = widgets.FloatSlider(min=0, max=5, step=0.1, value=0, description='Min (log10):')
max_slider = widgets.FloatSlider(min=0, max=5, step=0.1, value=3, description='Max (log10):')


# Функция обновления графика
def update_price_distribution(start_date, end_date, min_price_log, max_price_log):
    min_price = int(10 ** min_price_log)
    max_price = int(10 ** max_price_log)

    df = get_price_distribution(start_date, end_date)
    df['price'] = df['price'].round(0).astype(int)
    df_filtered = df[(df['price'] >= min_price) & (df['price'] <= max_price)]

    # Создание графика с Plotly
    fig = px.histogram(
        df_filtered,
        x='price',
        nbins=(max_price - min_price) // 10,  # Автоматическое определение бинов
        title=f"Распределение цен ({min_price}-{max_price})",
        labels={'price': 'Цена', 'count': 'Количество продаж'}
    )

    # Добавление метрик
    sample_size = len(df_filtered)
    mean_price = df_filtered['price'].mean()
    median_price = df_filtered['price'].median()
    std_price = df_filtered['price'].std()
    min_price_actual = df_filtered['price'].min()
    max_price_actual = df_filtered['price'].max()
    total_revenue = df_filtered['price'].sum()

    metrics_text = (
        f"Размер выборки: {sample_size}<br>"
        f"Минимальная цена: {min_price_actual:.2f}<br>"
        f"Максимальная цена: {max_price_actual:.2f}<br>"
        f"Средняя цена: {mean_price:.2f}<br>"
        f"Медианная цена: {median_price:.2f}<br>"
        f"Стандартное отклонение: {std_price:.2f}<br>"
        f"Объем продаж: {total_revenue:.2f}"
    )

    fig.add_annotation(
        text=metrics_text,
        align='left',
        xref='paper', yref='paper',
        x=1.1, y=0.5,
        showarrow=False,
        bgcolor='white',
        opacity=0.8
    )

    fig.show()


# Связывание виджетов с функцией обновления
output = interactive_output(update_price_distribution, {
    'start_date': start_date_picker,
    'end_date': end_date_picker,
    'min_price_log': min_slider,
    'max_price_log': max_slider
})

# Отображение виджетов и графика
display(widgets.VBox([start_date_picker, end_date_picker, min_slider, max_slider]), output)