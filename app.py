from flask import Flask, render_template
import requests
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET
from datetime import datetime
import pytz
import os
import time

app = Flask(__name__)

# Configuration
BASE_URL = "https://france-travel-website.onrender.com"  # Update after deploying
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
PLACES_URL = "https://en.wikipedia.org/wiki/Tourism_in_France"
DISHES_URL = "https://www.bbcgoodfood.com/recipes/collection/french-recipes"
RSS_FILE = "stable/rss_feed.xml"

# Predefined images for specific places and dishes (Unsplash royalty-free)
PLACE_IMAGES = {
    "Eiffel Tower": "https://images.unsplash.com/photo-1502602898657-3e91760cbb34",
    "Mont Saint-Michel": "https://images.unsplash.com/photo-1505205296326-2178af1b47bf",
    "Loire Valley": "https://images.unsplash.com/photo-1499856871958-5b9627545d1a",
    "Côte d’Azur": "https://images.unsplash.com/photo-1505761671935-60b3a7427bad",
    "Strasbourg": "https://images.unsplash.com/photo-1511739001486-6bfe10ce785f"
}

DISH_IMAGES = {
    "Croque Monsieur": "https://images.unsplash.com/photo-1627308594197-2843bd3b7bf3",
    "Crème Brûlée": "https://images.unsplash.com/photo-1574083249734-75983c23d0a6",
    "French Onion Soup": "https://images.unsplash.com/photo-1600354577269-e0a9e7b5c0ef",
    "Coq au Vin": "https://images.unsplash.com/photo-1603046893760-7bf0dabd95e8",
    "Ratatouille": "https://images.unsplash.com/photo-1598963603164-22202f2ae78f"
}

# Fallback image
DEFAULT_IMAGE = "https://images.unsplash.com/photo-1431274172761-fca41d930114"

def scrape_places():
    """Scrape famous places from Wikipedia."""
    headers = {"User-Agent": USER_AGENT}
    places = []
    try:
        response = requests.get(PLACES_URL, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        content = soup.find("div", class_="mw-parser-output")
        landmarks = ["Eiffel Tower", "Mont Saint-Michel", "Loire Valley", "Côte d’Azur", "Strasbourg"]
        for i, p in enumerate(content.find_all("p")):
            text = p.text.strip()
            for landmark in landmarks:
                if landmark.lower() in text.lower() and len(text) > 100:
                    title = landmark
                    description = text[:200] + "..." if len(text) > 200 else text
                    places.append({
                        "title": title,
                        "url": f"/places/{i}",
                        "image": PLACE_IMAGES.get(title, DEFAULT_IMAGE),
                        "description": description
                    })
                    break
            if len(places) >= 5:
                break
        return places
    except Exception as e:
        print(f"Error scraping places: {e}")
        return []

def scrape_dishes():
    """Scrape French dishes from BBC Good Food."""
    headers = {"User-Agent": USER_AGENT}
    dishes = []
    try:
        response = requests.get(DISHES_URL, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        cards = soup.find_all("div", class_="card__content")[:5]
        for i, card in enumerate(cards):
            title_tag = card.find("h2")
            title = title_tag.text.strip() if title_tag else f"French Dish {i+1}"
            description = card.find("p", class_="card__description")
            desc_text = description.text.strip() if description else "A classic French dish."
            image = next((DISH_IMAGES[k] for k in DISH_IMAGES if k.lower() in title.lower()), DEFAULT_IMAGE)
            dishes.append({
                "title": title,
                "url": f"/dishes/{i}",
                "image": image,
                "description": desc_text[:200] + "..." if len(desc_text) > 200 else desc_text
            })
        return dishes
    except Exception as e:
        print(f"Error scraping dishes: {e}")
        return []

def generate_rss_feed(places, dishes):
    """Generate RSS 2.0 feed for Pinterest."""
    rss = ET.Element("rss", version="2.0")
    channel = ET.SubElement(rss, "channel")
    ET.SubElement(channel, "title").text = "Travel France Auto-Pins"
    ET.SubElement(channel, "link").text = BASE_URL
    ET.SubElement(channel, "description").text = "Explore France's famous places and dishes"
    ET.SubElement(channel, "lastBuildDate").text = datetime.now(pytz.UTC).strftime("%a, %d %b %Y %H:%M:%S %z")

    for place in places:
        item = ET.SubElement(channel, "item")
        ET.SubElement(item, "title").text = place["title"]
        ET.SubElement(item, "link").text = f"{BASE_URL}{place['url']}"
        ET.SubElement(item, "description").text = place["description"]
        ET.SubElement(item, "media:content", url=place["image"], medium="image")
        ET.SubElement(item, "pubDate").text = datetime.now(pytz.UTC).strftime("%a, %d %b %Y %H:%M:%S %z")

    for dish in dishes:
        item = ET.SubElement(channel, "item")
        ET.SubElement(item, "title").text = dish["title"]
        ET.SubElement(item, "link").text = f"{BASE_URL}{dish['url']}"
        ET.SubElement(item, "description").text = dish["description"]
        ET.SubElement(item, "media:content", url=dish["image"], medium="image")
        ET.SubElement(item, "pubDate").TEXT = datetime.now(pytz.UTC).strftime("%a, %d %b %Y %H:%M:%S %z")

    os.makedirs("static", exist_ok=True)
    tree = ET.ElementTree(rss)
    tree.write(RSS_FILE, encoding="utf-8", xml_declaration=True)

@app.route("/")
def index():
    """Render the main page with scraped data."""
    places = scrape_places()
    dishes = scrape_dishes()
    if places or dishes:
        generate_rss_feed(places, dishes)
    return render_template("index.html", places=places, dishes=dishes)

@app.route("/rss_feed.xml")
def rss_feed():
    """Serve the RSS feed."""
    return app.send_static_file("rss_feed.xml")

if __name__ == "__main__":
    app.run(debug=True)