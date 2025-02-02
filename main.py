# pylint: disable=E1136

from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.select import Select

import requests
from bs4 import BeautifulSoup as bs 
import time
from assets import USER_AGENTS
import random
from icecream import ic
import html2text
import json
import re
import csv
import os

HIENTHITHEO = '50'
SLEEP_TIME_FOR_HIENTHITHEO = 2

def chrome_driver():
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--headless') # Comment this line to see the browser
    chrome_options.add_argument(f'user-agent={random.choice(USER_AGENTS)}')
    return webdriver.Chrome(options=chrome_options)

def scrape_category_data():
    url = 'https://lamthaocosmetics.vn/collections/'
    driver = chrome_driver()
    driver.get(url)
    print('Start scraping category data')
    try:
        element = WebDriverWait(driver, 50).until(
            EC.presence_of_element_located(
                (By.CLASS_NAME, "listmenu1")
                )
        )
        driver.implicitly_wait(1)
        html = driver.page_source
        soup = bs(html, 'html.parser')
        listmenu = soup.find('div', class_ = 'listmenu1').find_all('div', class_ = re.compile(r'listmenu1link1'))

        category_links = []
        for category in listmenu:
            link = 'https://lamthaocosmetics.vn' + category.find('a').get('href')
            if link not in category_links:
                category_links.append(link)
    finally:
        driver.quit()

    return category_links

def scrape_product_pagination_data(urls):
    product_listing = []
    for url in urls:
        driver = chrome_driver()
        driver.get(url)
        print('Start scraping product pagination data of ', url)
        item_per_page = Select(driver.find_element(By.ID, 'hienthitheo'))
        item_per_page.select_by_value(HIENTHITHEO)
        time.sleep(SLEEP_TIME_FOR_HIENTHITHEO)
        try:
            element = WebDriverWait(driver, 50).until(
                EC.presence_of_element_located(
                    (By.CLASS_NAME, 'templatecolreal')
                    )
            )
            driver.implicitly_wait(1)
            html = driver.page_source
            soup = bs(html, 'html.parser')

            multi_page = soup.find(id = 'pagination').find('ul', class_ = 'pagination')
            max_pagination = 1
            if multi_page is not None:
                paginations = multi_page.find_all('li')
                for pagination in paginations:
                    try:
                        if int(pagination.find('a').text) > max_pagination:
                            max_pagination = int(pagination.find('a').text)
                    except:
                        pass

            for i in range(max_pagination):
                product_listing.append(url + '?page=' + str(i+1))
        
        finally:
            driver.quit()

    return product_listing

def scrape_product_listing_data(urls):
    product_links = []
    for url in urls:
        driver = chrome_driver()
        driver.get(url)
        print('Start scraping product listing data of ', url)
        item_per_page = Select(driver.find_element(By.ID, 'hienthitheo'))
        item_per_page.select_by_value(HIENTHITHEO)
        time.sleep(SLEEP_TIME_FOR_HIENTHITHEO)
        try:
            element = WebDriverWait(driver, 50).until(
                EC.presence_of_element_located(
                    (By.CLASS_NAME, 'templatecolreal')
                    )
            )
            driver.implicitly_wait(1)
            html = driver.page_source
            soup = bs(html, 'html.parser')

            product_listing = soup.find_all('div', attrs={'datagia': True, 'class': re.compile(r'col-lg- col-md- col- product-loop')}) 

            for product in product_listing:
                link = 'https://lamthaocosmetics.vn' + product.find('div', class_ = re.compile(r'lazy-imgnew')).find('a').get('href')
                if link not in product_links:
                    product_links.append(link)

        finally:
            driver.quit()

    return product_links

def scrape_product_detail_data(urls):
    k = 1
    for url in urls:
        driver = chrome_driver()
        driver.get(url)
        print('Start scraping product detail data of ',url)
        try:
            element = WebDriverWait(driver, 50).until(
                EC.presence_of_element_located(
                    (By.CLASS_NAME, "producttemplatenew2")
                    )
            )
            driver.implicitly_wait(1)
            html = driver.page_source
            soup = bs(html, 'html.parser')

            script_tag = soup.find('script', string = re.compile(r'window.f1langdingpage1_variable.quickview'))
            script_content = json.loads(script_tag.string.strip().removeprefix('window.f1langdingpage1_variable.quickview = ')) if script_tag else None

            # print(script_content)

            sub_soup_2 = soup.find('div', class_ ='producttemplatenew2')

            for i in range(len(script_content['variants'])):
                product_info = {
                    'no': k,
                    'url': url,
                    'product_id': script_content['id'],
                    'name': script_content['title'],
                    'brand': script_content['vendor'],
                    'category': script_content['type'],
                    'sold': int(sub_soup_2.find('div', class_='gridlfextag3').text.strip("\n\tĐã bán ")),
                    'featured_image': script_content['featured_image'],
                    'description': script_content['metadescription'],
                    'published_at': script_content['published_at'],
                    'created_at': script_content['created_at'],
                    'variant_by': script_content['options'],
                    'variant_id': script_content['variants'][i]['id'],
                    'title': script_content['variants'][i]['title'],
                    'barcode': script_content['variants'][i]['barcode'],
                    'price': script_content['variants'][i]['price']/100,
                    'variant_image': script_content['variants'][i]['featured_image']['src'] if script_content['variants'][i]['featured_image'] else None,
                    'available': script_content['variants'][i]['available'],
                    'inventory_quantity': script_content['variants'][i]['inventory_quantity'],
                }
                extract_product_info([product_info])
                k += 1
        finally:
            driver.quit()

def extract_product_info(content):
    file_exists = os.path.isfile('scrape_data_lamthaocosmetics.csv')
    
    with open('scrape_data_lamthaocosmetics.csv', 'a' if file_exists else 'w', encoding="utf-8", newline='') as csvfile:
        fieldnames = ['no', 'url', 'product_id', 'name', 'brand', 'category', 'sold', 'featured_image', 'description', 'published_at', 'created_at', 'variant_by', 'variant_id', 'title', 'barcode', 'price', 'variant_image', 'available', 'inventory_quantity']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        if not file_exists:
            writer.writeheader()
        
        writer.writerows(content)
    
def main():
    scrape_product_detail_data(scrape_product_listing_data(scrape_product_pagination_data(scrape_category_data())))

if __name__ == '__main__':
    main()