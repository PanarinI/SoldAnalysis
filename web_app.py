import dash
from dash import dcc, html
import pandas as pd
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

    dcc.DatePickerRange(
        id='date-picker',
        display_format='YYYY-MM-DD',
        start_date=pd.Timestamp.today() - pd.Timedelta(days=7),
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
            {'label': 'Длина имен', 'value': 'name_length'}  # Новая опция
        ],
        value='sales',
        clearable=False
    ),

    dcc.Graph(id="sales-chart"),

    # Новый раздел
    html.Div([
        html.H3("Анализ за всё время", style={'marginTop': '50px'}),
        dcc.Graph(id="cluster-length-chart")
    ])
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

if __name__ == "__main__":
    app.run_server(debug=True)