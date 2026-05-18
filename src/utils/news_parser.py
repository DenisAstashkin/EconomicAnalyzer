import requests
from bs4 import BeautifulSoup
import time
import random
from urllib.parse import urljoin

MIN_DELAY = 1.0
MAX_DELAY = 3.0

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
    'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
}

def get_article_text(article_url):
    """Загружает полный текст новости по ссылке."""
    try:
        time.sleep(random.uniform(MIN_DELAY, MAX_DELAY))
        response = requests.get(article_url, headers=HEADERS)
        if response.status_code != 200:
            return ""

        soup = BeautifulSoup(response.text, 'html.parser')

        # Основной контент
        article_body = soup.find('div', class_='content')
        if article_body:
            text = article_body.get_text(separator=' ', strip=True)
            if not text.startswith('Авторизация'):
                return text

        # Запасной вариант – внутри блока topic
        topic_div = soup.find('div', class_='topic')
        if topic_div:
            content = topic_div.find('div', class_='content')
            if content:
                return content.get_text(separator=' ', strip=True)

        # Мета-описание
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc and meta_desc.get('content'):
            return meta_desc['content']

        return ""
    except Exception:
        return ""

def get_latest_news(slug):
    url = f"https://smart-lab.ru/forum/news/{slug}/"
    time.sleep(random.uniform(MIN_DELAY, MAX_DELAY))
    response = requests.get(url, headers=HEADERS)
    if response.status_code != 200:
        return f"Не удалось загрузить страницу: {url}"

    soup = BeautifulSoup(response.text, 'html.parser')

    # Ищем первую ссылку с href = "/blog/anything.php" и атрибутом title (полный заголовок)
    news_a = None
    for a in soup.find_all('a', href=True):
        if '/blog/' in a['href'] and a['href'].endswith('.php') and a.has_attr('title'):
            news_a = a
            break

    if not news_a:
        return f"Новости для {slug} не найдены."

    # Собираем заголовок (приоритет – атрибут title)
    title = news_a.get('title', '').strip() or news_a.get_text(strip=True)
    news_link = urljoin(url, news_a['href'])

    # Ищем дату в той же строке таблицы, что и ссылка
    date = ""
    parent_tr = news_a.find_parent('tr')
    if parent_tr:
        date_cell = parent_tr.find('td', class_='date')  #класс date
        if not date_cell:
            date_cell = parent_tr.find('td', align='right')  # или просто выровненная вправо ячейка
        if date_cell:
            date = date_cell.get_text(strip=True)

    # Загружаем полный текст новости
    text = get_article_text(news_link)

    result = (
        f"Заголовок: {title}\n"
        f"Дата: {date}\n"
        f"Ссылка: {news_link}\n"
        f"Текст новости:\n{text if text else 'Текст не загружен'}"
    )
    return result

if __name__ == "__main__":
    slug = "SBER"
    print(get_latest_news(slug))