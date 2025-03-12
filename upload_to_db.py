import requests
from bs4 import BeautifulSoup
import asyncio
import asyncpg
from datetime import datetime
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# URL страницы с проданными юзернеймами
url = "https://fragment.com/?sort=ending&filter=sold"

# Заголовки для запроса
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
}

# Функция для парсинга данных
def parse_data():
    logging.info("Начало парсинга данных.")
    # Отправляем запрос к странице
    response = requests.get(url, headers=headers)

    # Проверяем успешность запроса
    if response.status_code != 200:
        logging.error(f"Ошибка при загрузке страницы: {response.status_code}")
        exit()

    # Разбираем HTML с помощью BeautifulSoup
    soup = BeautifulSoup(response.content, "html.parser")

    # Списки для хранения данных
    usernames = []
    prices = []
    datetimes = []

    # Находим все строки таблицы с данными
    rows = soup.find_all("tr", class_="tm-row-selectable")

    for row in rows:
        # Извлекаем юзернейм
        username_element = row.find("div", class_="table-cell-value tm-value")
        if username_element:
            username = username_element.text.strip()
        else:
            username = None
            logging.warning("Юзернейм не найден в строке.")

        # Извлекаем цену
        price_element = row.find("div", class_="table-cell-value tm-value icon-before icon-ton")
        if price_element:
            price = price_element.text.strip()
        else:
            price = None
            logging.warning("Цена не найдена в строке.")

        # Извлекаем дату и время
        time_element = row.find("time")
        if time_element and time_element.has_attr("datetime"):
            datetime_str = time_element["datetime"]
            # Преобразуем строку в объект datetime
            try:
                datetime_obj = datetime.fromisoformat(datetime_str)
                # Удаляем информацию о временной зоне (делаем timezone-naive)
                datetime_obj = datetime_obj.replace(tzinfo=None)
            except ValueError:
                logging.error(f"Невозможно преобразовать дату: {datetime_str}")
                datetime_obj = None
        else:
            datetime_obj = None
            logging.warning("Дата и время не найдены в строке.")

        # Добавляем данные в списки, если все элементы найдены
        if username and price and datetime_obj:
            usernames.append(username)
            prices.append(price)
            datetimes.append(datetime_obj)
        else:
            logging.warning("Пропущена строка из-за отсутствия данных.")

    logging.info(f"Парсинг завершен. Найдено {len(usernames)} записей.")
    return usernames, prices, datetimes

def clean_price(price):
    try:
        # Удаляем запятые (разделители тысяч)
        cleaned_price = price.replace(',', '')
        # Преобразуем в float
        return round(float(cleaned_price), 2)
    except ValueError:
        logging.warning(f"Некорректное значение цены: {price}")
        return None  # Возвращаем None для некорректных значений

# Асинхронная функция для вставки данных в PostgreSQL
async def insert_data(usernames, prices, datetimes):
    pool = None
    try:
        pool = await asyncpg.create_pool(
            user="postgres",
            password="Pdjyjr2",
            database="SoldAnalysis",
            host="localhost",
            port="5432",
            min_size=1,
            max_size=10
        )
        async with pool.acquire() as conn:
            logging.info("Подключение к базе данных успешно установлено.")

            max_id = await conn.fetchval("SELECT COALESCE(MAX(id), 0) FROM sold_usernames")

            for username, price, datetime_obj in zip(usernames, prices, datetimes):
                max_id += 1
                # Очищаем цену и преобразуем в число
                cleaned_price = clean_price(price)  # Используем функцию clean_price
                if cleaned_price is None:
                    continue  # Пропустить некорректные значения

                await conn.execute(
                    """
                    INSERT INTO sold_usernames (id, username, price, sale_date)
                    VALUES ($1, $2, $3, $4)
                    ON CONFLICT (username, sale_date) DO NOTHING
                    """,
                    max_id, username, cleaned_price, datetime_obj
                )

            logging.info("Данные успешно добавлены в базу данных.")

    except Exception as e:
        logging.error(f"Ошибка при работе с базой данных: {e}")
    finally:
        if pool:
            await pool.close()
            logging.info("Пул соединений закрыт.")


# Основная асинхронная функция
async def main():
    logging.info("Запуск программы.")
    # Парсим данные
    usernames, prices, datetimes = parse_data()

    # Вставляем данные в базу данных
    await insert_data(usernames, prices, datetimes)
    logging.info("Программа завершена.")

# Запуск асинхронного кода
if __name__ == "__main__":
    asyncio.run(main())