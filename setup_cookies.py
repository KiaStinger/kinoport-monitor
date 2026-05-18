"""
Запускается ОДИН РАЗ локально.
Открывает браузер — ты входишь в Яндекс вручную.
Скрипт сохраняет куки в cookies.json.
Содержимое cookies.json нужно добавить в GitHub Secrets как KINOPOISK_COOKIES.
"""

import asyncio
import json
from playwright.async_api import async_playwright

URL = "https://www.kinopoisk.ru/special/kinoport/"

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()

        print("Открываю Кинопоиск...")
        await page.goto(URL)

        print("\n→ Войди в аккаунт Яндекса в открывшемся браузере.")
        print("→ После входа убедись, что страница Кинопорт загрузилась.")
        print("→ Затем вернись сюда и нажми Enter.")
        input()

        cookies = await context.cookies()
        with open("cookies.json", "w", encoding="utf-8") as f:
            json.dump(cookies, f, ensure_ascii=False, indent=2)

        print(f"\n✓ Сохранено {len(cookies)} куки в cookies.json")
        print("Теперь скопируй содержимое cookies.json и добавь в GitHub Secrets как KINOPOISK_COOKIES")

        await browser.close()

asyncio.run(main())
