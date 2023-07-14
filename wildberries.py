import datetime
import time

import requests
import json
import pandas as pd
#pip install openpyxl

"""
Парсер wildberries по ссылке на каталог (указывать без фильтров)

Рекомендую подписаться для того, чтобы быть в курсе последний обновлений:
https://vk.com/parsers_wildberries

Парсер не идеален, есть множество вариантов реализации, со своими идеями 
и предложениями обязательно пишите мне, либо в группу, ссылка ниже.

Подробное описание парсера Вайлдберриз можно почитать на сайте:
https://happypython.ru/2022/07/21/парсер-wildberries/

Ссылка на статью ВКонтакте: https://vk.com/@happython-parser-wildberries
По всем возникшим вопросам, можете писать в группу https://vk.com/happython

парсер wildberries по каталогам 2023, обновлен 18.05.2023 - на данное число работает исправно
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


def get_content(shard: str, query: str, low_price: int, top_price: int) -> list:
    """сбор данных со всех страниц выдачи (максимум Вайлдберис отдает 100 страниц) Ценовой диапазон для сужения выдачи"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/113.0",
        "Accept": "*/*",
        "Accept-Language": "ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3",
        "Accept-Encoding": "gzip, deflate, br",
        "Origin": "https://www.wildberries.ru",
        "Connection": "keep-alive",
        "Referer": "https://www.wildberries.ru/",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "cross-site"
    }
    data_list = []
    for page in range(1, 101):
        print(f'Сбор позиций со страницы {page} из 100')
        url = f'https://catalog.wb.ru/catalog/{shard}/catalog?curr=rub' \
              f'&dest=-1257786' \
              f'&locale=ru' \
              f'&page={page}' \
              f'&priceU={low_price * 100};{top_price * 100}' \
              f'&reg=0&sort=popular&spp=0' \
              f'&{query}'
        r = requests.get(url, headers=headers)
        if r.status_code != 200:
            print(f'Status code: {r.status_code} Timeout 10 sec')
            time.sleep(10)
            continue
        data = r.json()
        print(f'Добавлено позиций: {len(get_data_from_json(data))}')
        if len(get_data_from_json(data)) > 0:
            data_list.extend(get_data_from_json(data))
        else:
            print(f'Сбор данных завершен. Собрано: {len(data_list)} товаров.')
            break
    return data_list


def save_excel(data: list, filename: str):
    """сохранение результата в excel файл"""
    df = pd.DataFrame(data)
    writer = pd.ExcelWriter(f'{filename}.xlsx')
    df.to_excel(writer, 'data')
    writer.close()
    print(f'Все сохранено в {filename}.xlsx\n')


def parser(url: str, low_price: int, top_price: int):
    """основная функция"""
    # получаем данные по заданному каталогу
    catalog_data = get_data_category(get_catalogs_wb())
    try:
        # поиск введенной категории в общем каталоге
        category = search_category_in_catalog(url=url, catalog_list=catalog_data)
        # сбор данных в найденном каталоге
        data_list = get_content(shard=category['shard'],
                                query=category['query'],
                                low_price=low_price,
                                top_price=top_price)
        # сохранение найденных данных
        save_excel(data_list, f'{category["name"]}_from_{low_price}_to_{top_price}')
        print(f'Ссылка для проверки: {url}?priceU={low_price*100};{top_price*100}')
    except TypeError:
        print('Ошибка! Возможно не верно указан раздел. Удалите все доп фильтры с ссылки')
    except PermissionError:
        print('Ошибка! Вы забыли закрыть созданный ранее excel файл. Закройте и повторите попытку')


if __name__ == '__main__':
    """ссылку на каталог или подкаталог, указывать без фильтров (без ценовых, сортировки и тд.)"""
    # url = input('Введите ссылку на категорию для сбора: ')
    # low_price = int(input('Введите минимальную сумму товара: '))
    # top_price = int(input('Введите максимульную сумму товара: '))

    """данные для теста. собераем товар с раздела велосипеды в ценовой категории от 50тыс, до 100тыс"""
    url = 'https://www.wildberries.ru/catalog/sport/vidy-sporta/velosport/velosipedy'
    # url = 'https://www.wildberries.ru/catalog/elektronika/noutbuki-pereferiya/periferiynye-ustroystva/mfu'
    # url = 'https://www.wildberries.ru/catalog/dlya-doma/predmety-interera/dekorativnye-nakleyki'
    # url = 'https://www.wildberries.ru/catalog/dlya-doma/predmety-interera/boksy-dlya-salfetok'
    # url = 'https://www.wildberries.ru/catalog/dlya-doma/vse-dlya-prazdnika/otkrytki'

    # low_price = 1
    # top_price = 100000
    #
    # start = datetime.datetime.now()  # запишем время старта
    #
    # parser(url=url,
    #        low_price=low_price,
    #        top_price=top_price
    #        )
    #
    # end = datetime.datetime.now()  # запишем время завершения кода
    # total = end - start  # расчитаем время затраченное на выполнение кода
    # print("Затраченное время:" + str(total))


    """для exe приложения(чтобы сделать exe файл - pip install auto_py_to_exe для установки, для запуска auto-py-to-exe)"""
    while True:
        try:
            print('По вопросу парсинга Wildberries, отзывам и предложениям пишите в https://vk.com/happython')
            print('Заказать разработку парсера Вайлдберрис:  https://vk.com/atomnuclear'
                  '\nИли в группу ВК: https://vk.com/parsers_wildberries (рекомендую подписаться)\n')
            url = input('Введите ссылку на категорию без фильтров для сбора(или "q" для выхода):\n')
            if url == 'q':
                break
            low_price = int(input('Введите минимальную сумму товара: '))
            top_price = int(input('Введите максимульную сумму товара: '))
            parser(url=url, low_price=low_price, top_price=top_price)
        except:
            print('произошла ошибка данных при вводе, проверте правильность введенных данных,\n'
                  'Перезапуск...')
