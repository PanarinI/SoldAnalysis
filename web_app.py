import dash
from dash import dcc, html
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from dash.dependencies import Input, Output
from sqlalchemy import create_engine
import re

# Подключение к базе данных
DB_URI = "postgresql+psycopg2://postgres:Pdjyjr2@localhost:5432/SoldAnalysis"
engine = create_engine(DB_URI)

# Конфигурация анализа
PRICE_CLUSTERS = {
    "0-25": (0, 25),
    "25-75": (25, 75),
    "75-400": (75, 400),
    "400+": (400, None),
    "all": (0, None)
}

CHARTS_CONFIG = {
    "sales": {
        "title": "Количество продаж и средняя цена",
        "metrics": [
            {"name": "sales_count", "type": "bar", "axis": "y1", "title": "Количество продаж"},
            {"name": "average_price", "type": "scatter", "axis": "y2", "title": "Средняя цена", "color": "red"}
        ],
        "yaxis": {"title": "Количество продаж", "side": "left"},
        "yaxis2": {"title": "Средняя цена", "overlaying": "y", "side": "right"}
    },
    "price_comparison": {
        "title": "Сравнение цен и доля чистых имен",
        "metrics": [
            {"name": "avg_price_clean", "type": "bar", "axis": "y1", "title": "Средняя цена (чистые)", "color": "blue"},
            {"name": "avg_price_not_clean", "type": "bar", "axis": "y1", "title": "Средняя цена (нечистые)", "color": "red"},
            {"name": "clean_ratio", "type": "scatter", "axis": "y2", "title": "Доля чистых имен", "color": "green"}
        ],
        "yaxis": {"title": "Средняя цена", "side": "left"},
        "yaxis2": {"title": "Доля чистых имен", "overlaying": "y", "side": "right", "range": [0, 1]}
    },
    "name_length": {
        "title": "Средняя длина имен",
        "metrics": [
            {"name": "avg_name_length", "type": "bar", "axis": "y1", "title": "Средняя длина имени", "color": "blue"}
        ],
        "yaxis": {"title": "Средняя длина", "side": "left"}
    }
}
def get_price_distribution(start_date=None, end_date=None):
    """Загрузка данных о ценах для гистограммы"""
    query = """
        SELECT price
        FROM public.sold_usernames
        WHERE (%s IS NULL OR sale_date >= %s)
          AND (%s IS NULL OR sale_date <= %s)
    """
    params = (start_date, start_date, end_date, end_date)
    return pd.read_sql(query, engine, params=params)

def get_data(price_range):
    """Загрузка данных с группировкой по дням и фильтрацией по цене"""
    min_price, max_price = price_range

    query = """
        SELECT 
            sale_date::DATE AS date,
            COUNT(username) AS sales_count,
            AVG(price) AS average_price,
            AVG(CASE WHEN username !~ '[0-9_]' THEN price END) AS avg_price_clean,
            AVG(CASE WHEN username ~ '[0-9_]' THEN price END) AS avg_price_not_clean,
            AVG(CASE WHEN username !~ '[0-9_]' THEN 1 ELSE 0 END) AS clean_ratio,
            AVG(LENGTH(username)) AS avg_name_length  -- Добавлено вычисление длины
        FROM public.sold_usernames
        WHERE price >= %s AND (%s IS NULL OR price < %s)
        GROUP BY date
        ORDER BY date;
    """
    params = (min_price, max_price, max_price)
    return pd.read_sql(query, engine, params=params)

def get_avg_length_by_cluster():
    """Новый запрос для средней длины по кластерам за всё время"""
    query = """
        WITH clusters AS (
            SELECT 
                CASE
                    WHEN price >= 0 AND price < 25 THEN '0-25'
                    WHEN price >= 25 AND price < 75 THEN '25-75'
                    WHEN price >= 75 AND price < 400 THEN '75-400'
                    WHEN price >= 400 THEN '400+'
                END AS price_cluster,
                LENGTH(username) as len
            FROM public.sold_usernames
        )
        SELECT 
            price_cluster,
            AVG(len) AS avg_length,
            COUNT(*) AS total_count
        FROM clusters
        WHERE price_cluster IS NOT NULL
        GROUP BY price_cluster
        ORDER BY price_cluster;
    """
    return pd.read_sql(query, engine)

app = dash.Dash(__name__)

app.layout = html.Div([
    html.H1("Анализ проданных Telegram-имен", style={'textAlign': 'center'}),

    # Новый график: гистограмма распределения цен
    html.Div([
        html.H3("Распределение цен", style={'marginTop': '20px'}),
        dcc.Graph(id="price-distribution-chart")
    ]),

    # Логарифмический слайдер для выбора диапазона цен
    html.Div([
        html.Label("Диапазон цен (логарифмический выбор):"),
        dcc.RangeSlider(
            id='price-range-slider',
            min=0,  # Минимальное значение (логарифм от 1)
            max=5,  # Максимальное значение (логарифм от 100000)
            step=0.1,  # Шаг
            value=[0, 3],  # Начальный диапазон (10^0 = 1, 10^3 = 1000)
            marks={i: f"10^{i}" for i in range(6)},  # Метки на слайдере
            tooltip={"placement": "bottom", "always_visible": True}
        )
    ]),

    # Остальные элементы макета
    dcc.DatePickerRange(
        id='date-picker',
        display_format='YYYY-MM-DD',
        start_date=pd.Timestamp.today() - pd.Timedelta(days=7),  # По умолчанию — последние 7 дней
        end_date=pd.Timestamp.today()
    ),

    html.Label("Ценовой диапазон:"),
    dcc.Dropdown(
        id='price-cluster-selector',
        options=[{'label': k, 'value': k} for k in PRICE_CLUSTERS],
        value='all',
        clearable=False
    ),

    html.Label("Тип графика:"),
    dcc.Dropdown(
        id='chart-type-selector',
        options=[
            {'label': 'Количество продаж и средняя цена', 'value': 'sales'},
            {'label': 'Сравнение цен и доля чистых имен', 'value': 'price_comparison'},
            {'label': 'Длина имен', 'value': 'name_length'}
        ],
        value='sales',
        clearable=False
    ),

    dcc.Graph(id="sales-chart"),

    # Раздел "Анализ за всё время"
    html.Div([
        html.H3("Анализ за всё время", style={'marginTop': '50px'}),
        dcc.Graph(id="cluster-length-chart")
    ]),
    # график: распределение продаж по часам
    html.Div([
        html.H3("Распределение продаж по часам", style={'marginTop': '20px'}),
        dcc.Dropdown(
            id='day-selector',
            options=[{'label': 'Все дни', 'value': 'all'}],  # Изначально только "Все дни"
            value='all',
            clearable=False
        ),
        dcc.Graph(id="sales-by-hour-chart")
    ]),
])

@app.callback(
    Output("sales-chart", "figure"),
    Input("date-picker", "start_date"),
    Input("date-picker", "end_date"),
    Input("price-cluster-selector", "value"),
    Input("chart-type-selector", "value")
)
def update_chart(start_date, end_date, price_cluster, chart_type):
    df = get_data(PRICE_CLUSTERS[price_cluster])
    df['date'] = pd.to_datetime(df['date'])
    filtered = df[(df['date'] >= start_date) & (df['date'] <= end_date)]

    fig = go.Figure()
    config = CHARTS_CONFIG[chart_type]

    for metric in config['metrics']:
        if metric['type'] == 'bar':
            fig.add_trace(go.Bar(
                x=filtered['date'],
                y=filtered[metric['name']],
                name=metric['title'],
                marker_color=metric.get('color'),
                yaxis=metric['axis']
            ))
        elif metric['type'] == 'scatter':
            fig.add_trace(go.Scatter(
                x=filtered['date'],
                y=filtered[metric['name']],
                name=metric['title'],
                yaxis=metric['axis'],
                line=dict(color=metric.get('color'))
            ))

    fig.update_layout(
        title=f"{config['title']} ({price_cluster})",
        xaxis=dict(title="Дата"),
        yaxis=config['yaxis'],
        yaxis2=config.get('yaxis2'),
        legend=dict(x=0.1, y=1.1),
        barmode='group'
    )

    return fig

@app.callback(
    Output("cluster-length-chart", "figure"),
    Input("price-cluster-selector", "value")  # Фиктивный триггер
)
def update_cluster_chart(_):
    df = get_avg_length_by_cluster()

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=df['price_cluster'],
        y=df['avg_length'],
        text=df['avg_length'].round(2),
        textposition='auto',
        marker_color='#4CAF50'
    ))

    fig.update_layout(
        title="Средняя длина имени по ценовым кластерам",
        xaxis_title="Ценовой кластер",
        yaxis_title="Средняя длина имени",
        hovermode="x unified",
        showlegend=False
    )

    return fig

@app.callback(
    Output("price-distribution-chart", "figure"),
    Input("date-picker", "start_date"),
    Input("date-picker", "end_date"),
    Input("price-range-slider", "value")
)
def update_price_distribution(start_date, end_date, price_range):
    # Преобразуем логарифмические значения слайдера в линейные
    min_price = 10 ** price_range[0]
    max_price = 10 ** price_range[1]

    # Загрузка данных
    df = get_price_distribution(start_date, end_date)

    # Фильтрация данных
    df_filtered = df[(df['price'] >= min_price) & (df['price'] <= max_price)]

    # Рассчитываем размер бина
    price_range_size = max_price - min_price
    bin_size = price_range_size / 100  # Фиксированное количество бинов

    # Создание гистограммы
    fig = go.Figure()
    fig.add_trace(go.Histogram(
        x=df_filtered['price'],
        xbins=dict(
            start=min_price,
            end=max_price,
            size=bin_size  # Теперь размер бина всегда точный
        ),
        marker_color='#1f77b4',
        opacity=0.75
    ))

    # Настройка оси X
    fig.update_xaxes(
        title="Цена",
        range=[min_price, max_price],
        tickformat=".1f"  # Формат для отображения дробных значений
    )

    # Настройка внешнего вида
    fig.update_layout(
        title=f"Распределение цен ({min_price:.1f}-{max_price:.1f}), Бин = {bin_size:.2f}",
        yaxis_title="Количество продаж",
        bargap=0.01
    )

    return fig


@app.callback(
    Output("day-selector", "options"),
    Input("date-picker", "start_date"),
    Input("date-picker", "end_date")
)
def update_day_selector(start_date, end_date):
    # Загружаем данные из базы данных
    query = """
        SELECT DISTINCT sale_date::DATE AS sale_date
        FROM public.sold_usernames
        WHERE (%s IS NULL OR sale_date >= %s)
          AND (%s IS NULL OR sale_date <= %s)
        ORDER BY sale_date;
    """
    params = (start_date, start_date, end_date, end_date)
    df = pd.read_sql(query, engine, params=params)

    # Формируем список опций для выпадающего списка
    options = [{'label': 'Все дни', 'value': 'all'}] + \
              [{'label': str(day), 'value': str(day)} for day in df['sale_date'].unique()]

    return options

@app.callback(
    Output("sales-by-hour-chart", "figure"),
    Input("day-selector", "value"),
    Input("date-picker", "start_date"),
    Input("date-picker", "end_date")
)
def update_sales_by_hour_chart(selected_day, start_date, end_date):
    # Загружаем данные из базы данных
    query = """
        SELECT 
            sale_date,
            EXTRACT(HOUR FROM sale_date) AS sale_hour, 
            COUNT(*) AS sales_count
        FROM public.sold_usernames
        WHERE (%s IS NULL OR sale_date >= %s)
          AND (%s IS NULL OR sale_date <= %s)
        GROUP BY sale_hour, sale_date
        ORDER BY sale_hour;
    """
    params = (start_date, start_date, end_date, end_date)
    df = pd.read_sql(query, engine, params=params)

    # Приводим даты к московскому времени
    df['sale_date'] = df['sale_date'].dt.tz_localize('UTC').dt.tz_convert('Europe/Moscow')
    df['sale_hour'] = df['sale_date'].dt.hour

    # Фильтруем данные, если выбран конкретный день
    if selected_day != 'all':
        selected_day = pd.to_datetime(selected_day).date()
        df = df[df['sale_date'].dt.date == selected_day]

    # Группируем данные по часам
    sales_by_hour = df.groupby('sale_hour')['sales_count'].sum()

    # Строим график
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=sales_by_hour.index,
        y=sales_by_hour.values,
        marker_color='#4CAF50'
    ))

    fig.update_layout(
        title="Распределение продаж по часам" + ("" if selected_day == 'all' else f" за {selected_day}"),
        xaxis_title="Часы суток",
        yaxis_title="Количество продаж",
        xaxis=dict(tickmode='linear', tick0=0, dtick=1),
        bargap=0.01
    )

    return fig


if __name__ == "__main__":
    app.run_server(debug=True)