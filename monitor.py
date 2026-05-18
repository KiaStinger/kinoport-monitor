"""
Основной скрипт мониторинга. Запускается GitHub Actions каждый час.
Читает куки из переменной окружения KINOPOISK_COOKIES,
загружает страницу Кинопорт, сравнивает сеансы с прошлым запуском,
отправляет уведомление в Telegram если появилось что-то новое.
"""

import asyncio
import json
import os
import requests
from playwright.async_api import async_playwright

TELEGRAM_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
KINOPOISK_COOKIES = json.loads(os.environ.get("KINOPOISK_COOKIES", "[]"))

URL = "https://www.kinopoisk.ru/special/kinoport/"
STATE_FILE = "state.json"


def send_telegram(text: str):
    api_url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    response = requests.post(api_url, json={
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": False,
    })
    if not response.ok:
        print(f"Telegram error: {response.text}")


def load_state() -> dict:
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {"sessions": [], "first_run": True}


def save_state(state: dict):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


async def fetch_sessions() -> list[dict]:
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        )

        if KINOPOISK_COOKIES:
            await context.add_cookies(KINOPOISK_COOKIES)

        page = await context.new_page()
        await page.goto(URL, wait_until="networkidle", timeout=30000)

        # Извлекаем данные о сеансах из страницы
        sessions = await page.evaluate("""
            () => {
                const results = [];
                const seen = new Set();

                // Ищем карточки с фильмами и сеансами по разным паттернам
                const selectors = [
                    '[class*="session"]',
                    '[class*="seance"]',
                    '[class*="schedule"]',
                    '[class*="screening"]',
                    '[class*="showtime"]',
                    '[class*="film-card"]',
                    '[class*="movie-card"]',
                    '[class*="event-card"]',
                    '[class*="kinoport"]',
                    'article',
                ];

                for (const selector of selectors) {
                    document.querySelectorAll(selector).forEach(el => {
                        const text = el.innerText.trim();
                        if (text.length > 10 && text.length < 500 && !seen.has(text)) {
                            seen.add(text);
                            const link = el.querySelector('a');
                            results.push({
                                text: text.substring(0, 300),
                                href: link ? link.href : null,
                            });
                        }
                    });
                }

                // Если ничего не нашли — берём весь основной контент страницы
                if (results.length === 0) {
                    const main = document.querySelector('main') || document.body;
                    results.push({
                        text: main.innerText.trim().substring(0, 1000),
                        href: null,
                    });
                }

                return results;
            }
        """)

        await browser.close()
        return sessions


def session_id(session: dict) -> str:
    return session.get("href") or session.get("text", "")[:100]


async def main():
    state = load_state()
    old_ids = set(state.get("sessions", []))
    is_first_run = state.get("first_run", False)

    print(f"Загружаю страницу {URL}...")
    try:
        sessions = await fetch_sessions()
    except Exception as e:
        print(f"Ошибка при загрузке страницы: {e}")
        send_telegram(f"⚠️ Кинопорт монитор: ошибка при проверке\n<code>{e}</code>")
        return

    print(f"Найдено {len(sessions)} элементов на странице.")

    current_ids = [session_id(s) for s in sessions]
    new_sessions = [s for s in sessions if session_id(s) not in old_ids]

    if is_first_run:
        # Первый запуск — просто сохраняем состояние, не шлём уведомления
        state["sessions"] = current_ids
        state["first_run"] = False
        save_state(state)
        print("Первый запуск — сохранили начальное состояние. Уведомления не отправляем.")
        send_telegram(f"✅ Кинопорт монитор запущен!\nОтслеживаю: {URL}\nТекущих элементов: {len(sessions)}")
        return

    if new_sessions:
        print(f"Новых элементов: {len(new_sessions)}")
        for session in new_sessions:
            text = session.get("text", "")
            href = session.get("href", "")
            link_part = f'\n🔗 <a href="{href}">Купить билет</a>' if href else ""
            msg = f"🎬 <b>Новый сеанс на Кинопорт!</b>\n\n{text}{link_part}\n\n<a href='{URL}'>Открыть страницу</a>"
            send_telegram(msg)

        state["sessions"] = current_ids
        save_state(state)
    else:
        print("Новых сеансов не найдено.")


asyncio.run(main())
