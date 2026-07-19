"""
CarBikeUpdateBot — Telegram bot
Commands: /latestcar, /latestbike
Fetches the newest article (title + image) from car/bike news RSS feeds
and sends it to the user via Telegram's sendPhoto.

Install requirements:
    pip install -r requirements.txt

Run locally:
    export BOT_TOKEN=your_token_here
    python car_bike_bot.py
"""

import logging
import os
import re
import feedparser
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

logging.basicConfig(level=logging.INFO)

# ---- CONFIG ----
BOT_TOKEN = os.environ["BOT_TOKEN"]  # set this in Railway's Variables tab, never hardcode it

# You can swap/add any RSS feed that includes images
CAR_FEEDS = [
    "https://www.motor1.com/rss/news/",
    "https://www.carscoops.com/feed/",
]

BIKE_FEEDS = [
    "https://www.rideapart.com/rss/articles/all/",
    "https://www.rideapart.com/rss/news/all/",
]


def get_latest_entry(feed_urls):
    """Loop through feeds, return (title, link, image_url, summary) of newest entry with an image."""
    for url in feed_urls:
        try:
            feed = feedparser.parse(url)
        except Exception as e:
            logging.warning(f"Failed to parse {url}: {e}")
            continue

        if not feed.entries:
            continue

        entry = feed.entries[0]  # newest item
        image_url = extract_image(entry)

        if image_url:
            title = entry.get("title", "Latest update")
            link = entry.get("link", "")
            summary = clean_text(entry.get("summary", ""))[:300]
            return title, link, image_url, summary

    return None


def clean_text(raw_html):
    """Strip HTML tags and decode entities so the text is safe to send as a Telegram caption."""
    import html
    text = re.sub(r"<[^>]+>", "", raw_html)  # remove tags like <div>, <img>, <a>
    text = html.unescape(text)  # convert &amp; -> & etc.
    return text.strip()


def extract_image(entry):
    """Try common RSS image locations: media_content, enclosures, or an <img> tag in the summary HTML."""
    if hasattr(entry, "media_content") and entry.media_content:
        return entry.media_content[0].get("url")

    if hasattr(entry, "media_thumbnail") and entry.media_thumbnail:
        return entry.media_thumbnail[0].get("url")

    if hasattr(entry, "enclosures") and entry.enclosures:
        for enc in entry.enclosures:
            if "image" in enc.get("type", ""):
                return enc.get("href") or enc.get("url")

    summary_html = entry.get("summary", "")
    if "<img" in summary_html:
        match = re.search(r'<img[^>]+src="([^"]+)"', summary_html)
        if match:
            return match.group(1)

    return None


async def send_latest(update: Update, context: ContextTypes.DEFAULT_TYPE, feeds, label):
    result = get_latest_entry(feeds)

    if not result:
        await update.message.reply_text(f"Couldn't find a recent {label} update right now, try again shortly.")
        return

    title, link, image_url, summary = result
    icon = "🚗" if label == "car" else "🏍️"
    safe_title = clean_text(title)
    caption = f"{icon} <b>{safe_title}</b>\n\n{summary}\n\n🔗 {link}"

    try:
        await update.message.reply_photo(photo=image_url, caption=caption, parse_mode="HTML")
    except Exception as e:
        logging.warning(f"Failed to send photo, falling back to text: {e}")
        await update.message.reply_text(f"{title}\n{link}")


async def latest_car(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_latest(update, context, CAR_FEEDS, "car")


async def latest_bike(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_latest(update, context, BIKE_FEEDS, "bike")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Hi! I'm CarBikeUpdateBot.\n\n"
        "Use /latestcar for the newest car news\n"
        "Use /latestbike for the newest bike news"
    )


def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("latestcar", latest_car))
    app.add_handler(CommandHandler("latestbike", latest_bike))

    print("CarBikeUpdateBot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()
