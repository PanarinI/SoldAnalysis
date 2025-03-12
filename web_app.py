import dash
from dash import dcc, html
import pandas as pd
import plotly.graph_objects as go
from dash.dependencies import Input, Output
from sqlalchemy import create_engine

# Подключение к базе данных PostgreSQL
DB_URI = "postgresql+psycopg2://postgres:Pdjyjr2@localhost:5432/SoldAnalysis"
engine = create_engine(DB_URI)

# Ручное определение кластеров (ценовых диапазонов)
PRICE_CLUSTERS = {
    "0-25": (0, 25),
    "25-75": (25, 75),
    "75-400": (75, 400),
    "400+": (400, None),  # None для значений больше 400
    "all": (0, None)

}


def get_data(price_range):
    """Функция для получения данных из PostgreSQL с фильтром по ценовому диапазону"""
    min_price, max_price = price_range

    # Базовый запрос
    query = """
        SELECT 
            sale_date::DATE AS date, 
            COUNT(username) AS sales_count,
            AVG(price) AS average_price  -- Средняя цена
        FROM public.sold_usernames
        WHERE price >= %(min_price)s
          AND (%(max_price)s IS NULL OR price < %(max_price)s)
        GROUP BY date
        ORDER BY date;
    """

    # Параметры для запроса
    params = {"min_price": min_price, "max_price": max_price}

    # Выполняем запрос
    df = pd.read_sql(query, engine, params=params)
    return df

# Создаем приложение Dash
app = dash.Dash(__name__)

app.layout = html.Div([
    html.H1("Анализ проданных Telegram-имен", style={'textAlign': 'center'}),

    # Выбор периода (дата начала - дата окончания)
    dcc.DatePickerRange(
        id='date-picker',
        display_format='YYYY-MM-DD',
        start_date=pd.Timestamp.today().floor('D') - pd.Timedelta(days=7),  # Неделя назад
        end_date=pd.Timestamp.today().floor('D')
    ),

    # Выбор ценового диапазона (кластера)
    html.Label("Выберите ценовой диапазон:"),
    dcc.Dropdown(
        id='price-cluster-selector',
        options=[
            {'label': 'Любая цена', 'value': 'all'},  # Общий диапазон
            {'label': '0-25', 'value': '0-25'},
            {'label': '25-75', 'value': '25-75'},
            {'label': '75-400', 'value': '75-400'},
            {'label': '400+', 'value': '400+'}
        ],
        value='all',  # Начальное значение
        clearable=False
    ),

    # График с продажами по дням
    dcc.Graph(id="sales-chart")
])

@app.callback(
    Output("sales-chart", "figure"),
    Input("date-picker", "start_date"),
    Input("date-picker", "end_date"),
    Input("price-cluster-selector", "value")  # Новый Input для выбора ценового диапазона
)
def update_chart(start_date, end_date, price_cluster):
    # Получаем ценовой диапазон
    price_range = PRICE_CLUSTERS[price_cluster]

    # Загружаем данные с учетом выбранного ценового диапазона
    df = get_data(price_range)

    # Фильтруем по выбранному периоду
    df["date"] = pd.to_datetime(df["date"])  # Преобразуем в datetime
    df_filtered = df[(df["date"] >= start_date) & (df["date"] <= end_date)]

    # Создаем график с двумя осями Y
    fig = go.Figure()

    # Добавляем столбцы для количества продаж
    fig.add_trace(
        go.Bar(
            x=df_filtered["date"],
            y=df_filtered["sales_count"],
            name="Количество продаж",
            yaxis="y1"  # Левая ось Y
        )
    )

    # Добавляем линию для средней цены
    fig.add_trace(
        go.Scatter(
            x=df_filtered["date"],
            y=df_filtered["average_price"],
            name="Средняя цена",
            yaxis="y2",  # Правая ось Y
            line=dict(color="red")  # Красный цвет линии
        )
    )

    # Настраиваем оси
    fig.update_layout(
        title=f"Количество проданных имен и средняя цена по дням ({price_cluster})",
        xaxis=dict(title="Дата"),
        yaxis=dict(
            title="Количество продаж",
            side="left",  # Левая ось Y
            range=[0, df_filtered["sales_count"].max() * 1.1]  # Автомасштабирование
        ),
        yaxis2=dict(
            title="Средняя цена",
            overlaying="y",  # Наложение на ось Y
            side="right",    # Правая ось Y
            range=[0, df_filtered["average_price"].max() * 1.1]  # Автомасштабирование
        ),
        legend=dict(x=0.1, y=1.1)  # Позиция легенды
    )

    return fig

# Запускаем сервер
if __name__ == "__main__":
    app.run_server(debug=True)