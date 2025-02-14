#!/bin/bash
#python3 << END

import os
import re
import psycopg2
from bs4 import BeautifulSoup
from decimal import Decimal
from datetime import datetime
import pytz
import traceback
from pyppeteer import launch
from syncer import sync
import asyncio


executablePath = None #'/usr/bin/chromium-browser'
userAgent = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)'
             'Chrome/91.0.4472.124 Safari/537.36')

timezone_sp = pytz.timezone('America/Sao_Paulo')
url_base = "https://venda-imoveis.caixa.gov.br/sistema"

DB_CONFIG = {
    "dbname": "auction",
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASS"),
    "host": os.getenv("DB_HOST"),
    "port": "5432"
}

client_db = None
cursor_db = None
browser_instance = None

modality_key_caixa = 'CAIXA'
modality_key_db = 'DB'
modality_dict = {'LICITACAO': {modality_key_caixa: '21',
                               modality_key_db: 1},
                 'VENDA_DIRETA': {modality_key_caixa: '34',
                                  modality_key_db: 2},
                 'VENDA_ONLINE': {modality_key_caixa: '33',
                                  modality_key_db: 3}}


def init_conn():
    global client_db, cursor_db
    client_db = psycopg2.connect(**DB_CONFIG)
    cursor_db = client_db.cursor()

def close_conn():
    client_db.close()


def property_exists_db(property_id_to_verify):
    cursor_db.execute("SELECT 1 FROM property where external_id = %s", (property_id_to_verify,))
    results = cursor_db.fetchall()
    return bool(results)


def insert_log(external_id, status, log):
    sql_insert_query = """
        INSERT INTO log
        (external_id, status, created_at, log)
        VALUES(%s, %s, %s, %s);
    """
    data_to_insert = (external_id, status, datetime.now(timezone_sp), log)
    cursor_db.execute(sql_insert_query, data_to_insert)
    client_db.commit()


def delete_properties():
    data_to_delete = (datetime.now(timezone_sp).strftime('%Y%m%d'),)

    sql_delete_query = """
        DELETE FROM condition
        WHERE external_id IN (
            SELECT p.external_id 
            FROM property p 
            WHERE p.modality_id IN (2,3) OR p.auction_date < %s
        );
    """

    cursor_db.execute(sql_delete_query, data_to_delete)

    sql_delete_query = """
        DELETE FROM property p
        WHERE p.modality_id in (2,3) or p.auction_date < %s;
    """
    cursor_db.execute(sql_delete_query, data_to_delete)

    client_db.commit()


def insert_new_auction_property(auction_property_to_insert, modality):
    sql_insert_property_query = """
        INSERT INTO property
        (external_id, title, appraisal_value, value, situation, discount, type, registration, auction_date, 
         auction_notice, auction_item_number, address, cep, neighborhood, registration_link, auction_link, link, 
         created_at, modality_id)
        VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
    """
    sql_insert_condition_query = """
            INSERT INTO condition
            (external_id, description)
            VALUES(%s, %s);
    """

    data_to_insert = (auction_property_to_insert['id'],
                      auction_property_to_insert['title'],
                      auction_property_to_insert['appraisal_value'],
                      auction_property_to_insert['property_value'],
                      auction_property_to_insert['property_situation'],
                      auction_property_to_insert['property_discount'],
                      auction_property_to_insert['property_type'],
                      auction_property_to_insert['property_registration'],
                      auction_property_to_insert['auction_date'],
                      auction_property_to_insert['auction_notice'],
                      auction_property_to_insert['auction_item_number'],
                      auction_property_to_insert['property_address'],
                      auction_property_to_insert['property_cep'],
                      auction_property_to_insert['property_neighborhood'],
                      auction_property_to_insert['property_registration_link'],
                      auction_property_to_insert['auction_link'],
                      auction_property_to_insert['link'],
                      datetime.now(timezone_sp),
                      modality_dict.get(modality).get(modality_key_db))

    cursor_db.execute(sql_insert_property_query, data_to_insert)
    for description in auction_property_to_insert['descriptions']:
        cursor_db.execute(sql_insert_condition_query, (auction_property_to_insert['id'], description))

    client_db.commit()

    print(f"Auction property inserted: {auction_property_to_insert}")


async def init_browser_instance():
    global browser_instance
    if browser_instance is None:
        browser_instance = await launch(headless=True,
                                        executablePath=executablePath,
                                        args=['--no-sandbox', '--disable-setuid-sandbox'],
                                        timeout=60000)


@sync
async def browser_close():
    global browser_instance
    if browser_instance is not None:
        await browser_instance.close()


def has_security_errors(content):
    has_error = 'malicioso' in content.lower() or 'azion' in content.lower()
    if has_error:
        print(content)
    return has_error


@sync
async def get_property_ids(modality):
    page = await browser_instance.newPage()
    await page.setUserAgent(userAgent)

    wait_time = 10
    await page.goto(f"{url_base}/busca-imovel.asp?sltTipoBusca=imoveis")
    await page.waitForSelector('body')
    content = await page.content()
    if has_security_errors(content):
        return []

    await page.waitForSelector('#cmb_estado', {'visible': True})
    await page.select('#cmb_estado', 'MG')
    await asyncio.sleep(wait_time)
    await page.select('#cmb_cidade', '4105')  # Uberlândia
    await page.select('#cmb_modalidade', modality_dict.get(modality).get(modality_key_caixa))
    await asyncio.sleep(wait_time)
    await page.click('#btn_next0')
    await asyncio.sleep(wait_time)
    await page.click('#btn_next1')
    await asyncio.sleep(wait_time)
    decoded_string = await page.evaluate('''() => {
            const div = document.querySelector('#listaimoveis');
            return div ? div.innerHTML : '';
    }''')
    lines = decoded_string.splitlines()
    ids = []
    for line in lines:
        name_match = re.search(r'name="([^"]*)"', line)
        name = name_match.group(1) if name_match else None
        if name is not None and name.startswith("hdnImov"):
            value_match = re.search(r'value="([^"]*)"', line)
            value = value_match.group(1) if value_match else None
            if value is not None:
                ids.extend(value.split("||"))

    ids_mapped = []
    for p_id in ids:
        ids_mapped.append({'id': p_id,
                           'modality': modality})

    return ids_mapped


@sync
async def get_auction_property_by_id(property_id_to_find, modality):
    page = await browser_instance.newPage()
    await page.setUserAgent(userAgent)

    await page.goto(f"{url_base}/detalhe-imovel.asp?hdnimovel={property_id_to_find}")
    await page.waitForSelector('body')

    decoded_string = await page.content()
    if has_security_errors(decoded_string):
        raise ValueError('Security errors')

    soup = BeautifulSoup(decoded_string.replace("<!--", "<").replace("-->", ">"), 'lxml')
    form = soup.find('form', id='frm_detalhe')
    div_content = form.find('div', class_='content')
    div_related_box = form.find('div', class_='related-box')
    div_related_box_text = div_related_box.get_text().replace('\xa0', ' ')
    button_submit = form.find('button', class_='submit-orange')
    i_infos = div_related_box.findAll('i', class_='fa-info-circle')

    title = form.find('h5').get_text(strip=True).strip().replace("Imóvel em disputa", "")
    monetary_values = (div_content.find('p').get_text(strip=True).replace(' ', '')
                       .replace('\n', '').split("Valormínimodevenda:"))
    appraisal_value = monetary_values[0].split("R$")[1]
    value_and_discount = monetary_values[1].split("R$")[1]
    property_value = value_and_discount.split("(")[0].strip()
    property_discount = (value_and_discount.replace("Acompanheaquioslancesregistradosnessadisputa", "")
                         .split("(descontode")[1]
                         .replace(")", "").strip())
    property_type = re.search(r'Tipo de imóvel:\s*(\w+)', div_content.get_text()).group(1).strip()
    property_situation = re.search(r'Situação:\s*(\w+)', div_content.get_text()).group(1).strip()
    property_registration = re.search(r'Matrícula\(s\):\s*(\d+)', div_content.get_text()).group(1).strip()
    property_registration_link = (div_related_box.find('a', onclick=True)['onclick']
                                  .replace("javascript:ExibeDoc('", 'https://venda-imoveis.caixa.gov.br/')
                                  .replace("')", ""))

    auction_date = datetime.now(timezone_sp)
    auction_notice = None
    auction_item_number = None
    auction_link = property_registration_link

    if modality == 'LICITACAO':
        auction_date = datetime.strptime(re.search(r'Data da Licitação Aberta - ([\d/]+ - \d+h\d+)',
                                                   div_related_box_text).group(1).strip(), '%d/%m/%Y - %Hh%M')
        auction_notice = re.search(r'Licitação Aberta\s*(\d{4}/\d{4})', div_related_box_text).group(1).strip()
        auction_item_number = re.search(r'Número do item:\s*(\d+)', div_related_box_text).group(1).strip()
        auction_link = (re.search(r'SiteLeiloeiro\("([^"]+)"\)', button_submit['onclick']).group(1)
                        .replace('\xa0', ' ').strip())

    property_address = (re.search(r'Endereço:\s*(.*?),\s+[^,]*\s*-?\s*CEP:', div_related_box_text).group(1)
                        .strip())
    property_cep = re.search(r'CEP:\s*(\d{5}-\d{3})', div_related_box_text).group(1).strip()
    property_neighborhood = re.search(r',\s*([^,]+)\s*-\s*CEP:', div_related_box_text).group(1).strip()

    descriptions = []
    for i_info in i_infos:
        next_br = i_info.find_next_sibling('br')
        if next_br:
            description = i_info.find_next_sibling(string=True)
            if description:
                descriptions.append(' '.join(description.replace('\xa0', ' ').strip()
                                             .replace('\n', ' ').split()))

    return {
        'id': property_id_to_find,
        'title': title,
        'appraisal_value': Decimal(appraisal_value.replace('.', '').replace(',', '.')),
        'property_value': Decimal(property_value.replace('.', '').replace(',', '.')),
        'property_discount': property_discount,
        'property_type': property_type,
        'property_situation': property_situation,
        'property_registration': property_registration,
        'auction_date': auction_date,
        'auction_notice': auction_notice,
        'auction_item_number': auction_item_number,
        'property_address': property_address,
        'property_cep': property_cep,
        'property_neighborhood': property_neighborhood,
        'property_registration_link': property_registration_link,
        'auction_link': auction_link,
        'link': f'https://venda-imoveis.caixa.gov.br/sistema/detalhe-imovel.asp?hdnimovel={property_id_to_find}',
        'descriptions': descriptions
    }


if __name__ == '__main__':
    asyncio.get_event_loop().run_until_complete(init_browser_instance())
    init_conn()
    insert_log(None, "PROCESSING_STARTED", None)
    delete_properties()
    try:

        for type_str in ['LICITACAO', 'VENDA_DIRETA', 'VENDA_ONLINE']:

            auction_property_ids = get_property_ids(type_str)

            print(f"{len(auction_property_ids)} Properties found: {auction_property_ids}")
            if not auction_property_ids:
                insert_log(None, "FAIL_PROPERTIES_NOT_FOUND", None)

            for property_dict in auction_property_ids:

                property_id = property_dict['id']
                modality = property_dict['modality']

                if property_exists_db(property_id):
                    continue

                insert_log(property_id, "PROPERTY_STARTED", modality)
                try:

                    auction_property = get_auction_property_by_id(property_id, modality)
                    insert_new_auction_property(auction_property, modality)

                    insert_log(property_id, "PROPERTY_FINISHED", modality)
                except Exception as exception:
                    traceback.print_exc()
                    client_db.rollback()
                    log = f"{exception}"
                    insert_log(property_id, "PROPERTY_FINISHED_WITH_FAIL", log)

        insert_log(None, "PROCESSING_FINISHED", None)
    except Exception as exception:
        traceback.print_exc()
        log = f"{exception}"
        insert_log(None, "PROCESSING_FINISHED_WITH_FAIL", log)

    finally:
        browser_close()
        close_conn()

#END