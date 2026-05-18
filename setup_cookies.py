"""
Запускается ОДИН РАЗ локально в Terminal.app (не через ! в Claude Code).
Открывает страницу входа Яндекса — ты логинишься вручную.
Скрипт ждёт пока ты войдёшь и автоматически сохраняет куки в cookies.json.
"""

import asyncio
import json
from playwright.async_api import async_playwright

LOGIN_URL = "https://passport.yandex.ru/auth?retpath=https%3A%2F%2Fwww.kinopoisk.ru%2Fspecial%2Fkinoport%2F"
KINOPORT_URL = "https://www.kinopoisk.ru/special/kinoport/"

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()

        print("Открываю страницу входа Яндекса...")
        await page.goto(LOGIN_URL)

        print("\n→ Войди в аккаунт Яндекса в открывшемся браузере.")
        print("→ Скрипт автоматически продолжит после входа (ждёт до 3 минут).")

        # Ждём пока страница переключится на Кинопоиск — значит вход выполнен
        await page.wait_for_url(f"{KINOPORT_URL}**", timeout=180000)

        print("\n✓ Вход выполнен! Сохраняю куки...")
        cookies = await context.cookies()
        with open("cookies.json", "w", encoding="utf-8") as f:
            json.dump(cookies, f, ensure_ascii=False, indent=2)

        print(f"✓ Сохранено {len(cookies)} куки в cookies.json")
        print("\nТеперь скопируй содержимое cookies.json и добавь в GitHub Secrets как KINOPOISK_COOKIES")

        await browser.close()

asyncio.run(main())
