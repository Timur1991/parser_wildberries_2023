import datetime

import requests
import json
import pandas as pd
from retry import retry
# pip install openpyxl


"""
ОБНОВЛЕН: 28.08.2023

https://vk.com/parsers_wildberries  # группа ВК парсера ВБ
https://vk.com/happython  # группа ВК где можете заказывать парсеры и скрипты
https://happypython.ru/2022/07/21/парсер-wildberries/  # ссылка на обучающую статью парсинга WB

Парсер wildberries по ссылке на каталог (указывать без фильтров)
Данные которые собирает парсер:
    -наименование
    -id
    -скидка
    -цена
    -цена со скидкой
    -бренд
    -отзывы
    -рейтинг
    -ссылка

Возможные фильтра: 
    -нижняя цена
    -верхняя цена
    -скидка (%)
"""


def get_catalogs_wb() -> dict:
    """получаем полный каталог Wildberries"""
    url = 'https://www.wildberries.ru/webapi/menu/main-menu-ru-ru.json'
    headers = {'Accept': '*/*', 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    # with open('wb_goods_list.json', 'w', encoding='UTF-8') as file:
    #     json.dump(requests.get(url, headers=headers).json(), file, indent=4, ensure_ascii=False)
    return requests.get(url, headers=headers).json()


def get_data_category(catalogs_wb: dict) -> list:
    """сбор данных категорий из каталога Wildberries"""
    catalog_data = []
    if isinstance(catalogs_wb, dict) and 'childs' not in catalogs_wb:
        catalog_data.append({
            'name': f"{catalogs_wb['name']}",
            'shard': catalogs_wb.get('shard', None),
            'url': catalogs_wb['url'],
            'query': catalogs_wb.get('query', None)
        })
    elif isinstance(catalogs_wb, dict):
        catalog_data.extend(get_data_category(catalogs_wb['childs']))
    else:
        for child in catalogs_wb:
            catalog_data.extend(get_data_category(child))
    return catalog_data


def search_category_in_catalog(url: str, catalog_list: list) -> dict:
    """проверка пользовательской ссылки на наличии в каталоге"""
    for catalog in catalog_list:
        if catalog['url'] == url.split('https://www.wildberries.ru')[-1]:
            print(f'найдено совпадение: {catalog["name"]}')
            return catalog


def get_data_from_json(json_file: dict) -> list:
    """извлекаем из json данные"""
    data_list = []
    for data in json_file['data']['products']:
        data_list.append({
            'Наименование': data['name'],
            'id': data['id'],
            'Скидка': data['sale'],
            'Цена': int(data["priceU"] / 100),
            'Цена со скидкой': int(data["salePriceU"] / 100),
            'Бренд': data['brand'],
            'feedbacks': data['feedbacks'],
            'rating': data['rating'],
            'Ссылка': f'https://www.wildberries.ru/catalog/{data["id"]}/detail.aspx?targetUrl=BP'
        })
    return data_list


@retry(Exception, tries=-1, delay=0)
def scrap_page(page: int, shard: str, query: str, low_price: int, top_price: int, discount: int = None) -> dict:
    """Сбор данных со страниц"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/113.0",
        "Accept": "*/*",
        "Accept-Language": "ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3",
        "Accept-Encoding": "gzip, deflate, br",
        "Origin": "https://www.wildberries.ru",
        'Content-Type': 'application/json; charset=utf-8',
        'Transfer-Encoding': 'chunked',
        "Connection": "keep-alive",
        'Vary': 'Accept-Encoding',
        'Content-Encoding': 'gzip',
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "cross-site"
    }
    url = f'https://catalog.wb.ru/catalog/{shard}/catalog?appType=1&curr=rub' \
          f'&dest=-1257786' \
          f'&locale=ru' \
          f'&page={page}' \
          f'&priceU={low_price * 100};{top_price * 100}' \
          f'&sort=popular&spp=0' \
          f'&{query}' \
          f'&discount={discount}'
    r = requests.get(url, headers=headers)
    print(f'Статус: {r.status_code} Страница {page} Идет сбор...')
    return r.json()


def save_excel(data: list, filename: str):
    """сохранение результата в excel файл"""
    df = pd.DataFrame(data)
    writer = pd.ExcelWriter(f'{filename}.xlsx')
    df.to_excel(writer, 'data')
    writer.close()
    print(f'Все сохранено в {filename}.xlsx\n')


def parser(url: str, low_price: int = 1, top_price: int = 1000000, discount: int = 0):
    """основная функция"""
    # получаем данные по заданному каталогу
    catalog_data = get_data_category(get_catalogs_wb())
    try:
        # поиск введенной категории в общем каталоге
        category = search_category_in_catalog(url=url, catalog_list=catalog_data)
        data_list = []
        for page in range(1, 51):  # вб отдает 50 страниц товара (раньше было 100)
            data = scrap_page(
                page=page,
                shard=category['shard'],
                query=category['query'],
                low_price=low_price,
                top_price=top_price,
                discount=discount)
            print(f'Добавлено позиций: {len(get_data_from_json(data))}')
            if len(get_data_from_json(data)) > 0:
                data_list.extend(get_data_from_json(data))
            else:
                break
        print(f'Сбор данных завершен. Собрано: {len(data_list)} товаров.')
        # сохранение найденных данных
        save_excel(data_list, f'{category["name"]}_from_{low_price}_to_{top_price}')
        print(f'Ссылка для проверки: {url}?priceU={low_price * 100};{top_price * 100}&discount={discount}')
    except TypeError:
        print('Ошибка! Возможно не верно указан раздел. Удалите все доп фильтры с ссылки')
    except PermissionError:
        print('Ошибка! Вы забыли закрыть созданный ранее excel файл. Закройте и повторите попытку')


if __name__ == '__main__':
    """данные для теста. собераем товар с раздела велосипеды в ценовой категории от 1тыс, до 100тыс, со скидкой 10%"""
    url = 'https://www.wildberries.ru/catalog/sport/vidy-sporta/velosport/velosipedy'
    low_price = 1  # нижний порог цены
    top_price = 1000000  # верхний порог цены
    discount = 10  # скидка в %
    start = datetime.datetime.now()  # запишем время старта

    parser(url=url, low_price=low_price, top_price=top_price, discount=discount)

    end = datetime.datetime.now()  # запишем время завершения кода
    total = end - start  # расчитаем время затраченное на выполнение кода
    print("Затраченное время:" + str(total))

    # """для exe приложения(чтобы сделать exe файл - pip install auto_py_to_exe для установки, для запуска auto-py-to-exe)"""
    # while True:
    #     try:
    #         print('По вопросу парсинга Wildberries, отзывам и предложениям пишите в https://vk.com/happython')
    #         print('Заказать разработку парсера Вайлдберрис:  https://vk.com/atomnuclear'
    #               '\nИли в группу ВК: https://vk.com/parsers_wildberries (рекомендую подписаться)\n')
    #         url = input('Введите ссылку на категорию без фильтров для сбора(или "q" для выхода):\n')
    #         if url == 'q':
    #             break
    #         low_price = int(input('Введите минимальную сумму товара: '))
    #         top_price = int(input('Введите максимульную сумму товара: '))
    #         discount = int(input('Введите минимальную скидку(введите 0 если без скидки): '))
    #         parser(url=url, low_price=low_price, top_price=top_price, discount=discount)
    #     except:
    #         print('произошла ошибка данных при вводе, проверте правильность введенных данных,\n'
    #               'Перезапуск...')
