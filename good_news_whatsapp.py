#!/usr/bin/env python3
"""
Sends 10 positive news headlines to your WhatsApp.
Schedule it for 7am with cron or GitHub Actions (see README notes in chat).

Install:  pip install feedparser requests

Environment variables (pick ONE sending method):

  Method A - CallMeBot (simplest, personal use):
    SENDER=callmebot
    WHATSAPP_PHONE=+92XXXXXXXXXX
    CALLMEBOT_APIKEY=your_key

  Method B - Twilio WhatsApp:
    SENDER=twilio
    WHATSAPP_PHONE=+92XXXXXXXXXX
    TWILIO_SID=ACxxxxxxxx
    TWILIO_TOKEN=xxxxxxxx
    TWILIO_FROM=+14155238886      # sandbox number or your approved sender
"""

import os
import sys
from datetime import date
from itertools import zip_longest

import feedparser
import requests

# Verify these URLs still work; swap in any other good-news feeds you like.
FEEDS = [
    "https://www.goodnewsnetwork.org/feed/",
    "https://www.positive.news/feed/",
    "https://reasonstobecheerful.world/feed/",
    "https://www.optimistdaily.com/feed/",
]

HOW_MANY = 10


def fetch_headlines():
    """Take items round-robin from each feed so the mix is varied."""
    per_feed = []
    for url in FEEDS:
        try:
            parsed = feedparser.parse(url)
            items = [(e.get("title", "").strip(), e.get("link", "")) for e in parsed.entries[:HOW_MANY]]
            per_feed.append([i for i in items if i[0] and i[1]])
        except Exception as exc:
            print(f"Could not read {url}: {exc}", file=sys.stderr)

    seen, picked = set(), []
    for group in zip_longest(*per_feed):
        for item in group:
            if item and item[1] not in seen:
                seen.add(item[1])
                picked.append(item)
                if len(picked) == HOW_MANY:
                    return picked
    return picked


def build_message(items):
    lines = [f"☀️ Good morning! Positive news for {date.today():%A, %d %B %Y}", ""]
    for n, (title, link) in enumerate(items, 1):
        lines.append(f"{n}. {title}\n{link}\n")
    lines.append("Have a wonderful day! 🌍")
    return "\n".join(lines)


def send_callmebot(text):
    r = requests.get(
        "https://api.callmebot.com/whatsapp.php",
        params={
            "phone": os.environ["WHATSAPP_PHONE"],
            "text": text,
            "apikey": os.environ["CALLMEBOT_APIKEY"],
        },
        timeout=30,
    )
    r.raise_for_status()


def send_greenapi(text):
    api_url = os.environ.get("GREENAPI_URL", "https://api.green-api.com").rstrip("/")
    idi = os.environ["GREENAPI_ID"]
    token = os.environ["GREENAPI_TOKEN"]
    digits = "".join(ch for ch in os.environ["WHATSAPP_PHONE"] if ch.isdigit())
    r = requests.post(
        f"{api_url}/waInstance{idi}/sendMessage/{token}",
        json={"chatId": f"{digits}@c.us", "message": text},
        timeout=30,
    )
    r.raise_for_status()


def send_twilio(text):
    sid = os.environ["TWILIO_SID"]
    r = requests.post(
        f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json",
        auth=(sid, os.environ["TWILIO_TOKEN"]),
        data={
            "From": f"whatsapp:{os.environ['TWILIO_FROM']}",
            "To": f"whatsapp:{os.environ['WHATSAPP_PHONE']}",
            "Body": text[:1500],  # Twilio caps WhatsApp bodies at 1600 chars
        },
        timeout=30,
    )
    r.raise_for_status()


def main():
    items = fetch_headlines()
    if not items:
        sys.exit("No headlines fetched; nothing sent.")

    message = build_message(items)
    sender = os.environ.get("SENDER", "callmebot").lower()

    if sender == "greenapi":
        send_greenapi(message)
    elif sender == "twilio":
        send_twilio(message)
    else:
        send_callmebot(message)

    print(f"Sent {len(items)} headlines via {sender}.")


if __name__ == "__main__":
    main()
