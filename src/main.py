import click
import os
import psycopg2
from tinkoff_voicekit_client import ClientSTT
import soundfile as sf
import logging
import uuid
import datetime
from config import API_KEY, SECRET_KEY


client = ClientSTT(API_KEY, SECRET_KEY)
audio_config = {
    "encoding": "LINEAR16",
    "sample_rate_hertz": 8000,
    "num_channels": 1
}


def calculating_file_length(path_file):
    """Метод для подсчёта длины аудиофайла в секундах"""
    f = sf.SoundFile(f'{path_file}')
    file_length = len(f) / f.samplerate
    return file_length


def conversation_handler_1(message):
    """Обработка сообщения, деление по слову Автоответчик"""
    if 'автоответчик' in message:
        return 0
    else:
        return 1


def conversation_handler_2(message):
    """Обработка сообщения, поиск негативных ответов. Если ключевые слова не были найдены, функция вернёт 1"""
    negative = ('нет', 'неудобно', 'сейчас занят', 'не могу', 'не хочу', 'до свидания', 'сейчас на работе')
    for elem in negative:
        if elem in message:
            return 0
    else:
        return 1


def logging_file(path_file, message, result, phone_number, save):
    """Запись в логи информации о разговоре"""
    file_length = calculating_file_length(path_file)
    logging.basicConfig(filename="fileslogs.log", level=logging.INFO)
    id = uuid.uuid1()
    date = datetime.date.today()
    time = datetime.datetime.now().time()
    logging.info(
        f'Дата: {date} |'
        f'Время: {time} |'
        f'ID: {id} |'
        f'Результат: {result} |'
        f'Номер телефона: {phone_number} |'
        f'Длительность разговора: {file_length} |'
        f'Результат распознования: {message} |'
    )
    # Запись данных в бд, при соответствующем флаге
    if save == 'Yes':
        write_database(date, time, message, result, phone_number, file_length)


def write_database(date, time, message, result, phone_number, file_length):
    """Запись в базу данных при соответствующем флаге"""
    con = None
    try:
        con = psycopg2.connect(
            dbname='postgres_db',
            user='postgres',
            password='tryexcept',
            host='127.0.0.1'
        )
        cursor = con.cursor()
        cursor.execute(
            f"""INSERT INTO calls (date, result, phone_number, duration, time, message)
            VALUES ('{date}', '{result}', {phone_number}, {file_length}, '{time}', '{message}')""")
        con.commit()
    except (Exception, psycopg2.DatabaseError) as error:
        with open("error.log", "w") as file:
            file.write(f'{error}')
    finally:
        if con is not None:
            con.close()


@click.command()
@click.option('-p', '--path-file', default=False, help='path to file')
@click.option(
    '-p', '--phone-number',
    default=88000000000,
    show_default=True,
    help='Phone number without space'
)
@click.option(
    '-w', '--save',
    type=click.Choice(['Yes', 'No'], case_sensitive=False),
    default='No',
    show_default=True,
    help='Writing data to the database'
)
@click.option(
    '-r', '--stage',
    type=click.Choice(['1', '2']),
    default='1',
    show_default=True,
    help='Recognition stage.'
)
def main(path_file, phone_number, save, stage):
    if path_file:
        response = client.recognize(path_file, audio_config)
        message = response[0]['alternatives'][0]['transcript']
        if stage == 1:
            answer = conversation_handler_1(message)
            if answer:
                result = 'человек'
            else:
                result = "автоответчик"
        else:
            answer = conversation_handler_2(message)
            if answer:
                result = 'положительно'
            else:
                result = 'отрицательно'
        logging_file(path_file, message, result, phone_number, save)
        os.remove(path_file)
    else:
        print('Введите путь до файла')


if __name__ == "__main__":
    main()
