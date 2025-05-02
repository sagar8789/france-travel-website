from flask import Flask, render_template
import requests
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET
from datetime import datetime
import pytz
import os
import logging

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASE_URL = "https://france-travel-website.onrender.com"  # Update to your Render URL after deployment
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
PLACES_URL = "https://en.wikipedia.org/wiki/Tourism_in_France"
DISHES_URL = "https://www.bbcgoodfood.com/recipes/collection/french-recipes"
DEFAULT_IMAGE = "https://images.unsplash.com/photo-1502602898657-3e91760cbb34"

PLACE_IMAGES = {
    "Eiffel Tower": "https://images.unsplash.com/photo-1502602898657-3e91760cbb34",
    "Mont Saint-Michel": "https://images.unsplash.com/photo-1517429171687-6f4c3f8e64e7",
    "Loire Valley": "https://images.unsplash.com/photo-1562183241-b937e1de65e4",
    "Côte d’Azur": "https://images.unsplash.com/photo-1498202763657-6b7b809d00d9",
    "Strasbourg": "https://images.unsplash.com/photo-1519689680058-323335c7a375"
}
DISH_IMAGES = {
    "Croque Monsieur": "https://images.unsplash.com/photo-1627308594197-2843bd3b7bf3",
    "Crème Brûlée": "https://images.unsplash.com/photo-1555972592-01bf139862b7",
    "French Onion Soup": "https://images.unsplash.com/photo-1579684453423-8c421b589815",
    "Coq au Vin": "https://images.unsplash.com/photo-1604901383881-c14e393316c2",
    "Ratatouille": "https://images.unsplash.com/photo-1598103605379-00d37f6b4a0b"
}

def scrape_places():
    headers = {"User-Agent": USER_AGENT}
    landmarks = ["Eiffel Tower", "Mont Saint-Michel", "Loire Valley", "Côte d’Azur", "Strasbourg"]
    places = []
    try:
        logger.info("Scraping places from %s", PLACES_URL)
        response = requests.get(PLACES_URL, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        content = soup.find("div", class_="mw-parser-output")
        if content:
            for i, landmark in enumerate(landmarks):
                paragraphs = content.find_all("p")
                description = "A famous landmark in France."
                for p in paragraphs:
                    if landmark.lower() in p.text.lower():
                        description = p.text.strip()
                        break
                places.append({
                    "title": landmark,
                    "url": f"/places/{i}",
                    "image": PLACE_IMAGES.get(landmark, DEFAULT_IMAGE),
                    "description": description[:200] + "..." if len(description) > 200 else description
                })
        else:
            logger.warning("No content found on Wikipedia page")
        return places
    except Exception as e:
        logger.error("Error scraping places: %s", e)
        return []

def scrape_dishes():
    headers = {"User-Agent": USER_AGENT}
    dishes = []
    try:
        logger.info("Scraping dishes from %s", DISHES_URL)
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
        logger.error("Error scraping dishes: %s", e)
        return []

def generate_rss_feed(places, dishes):
    try:
        logger.info("Generating RSS feed")
        rss = ET.Element("rss", version="2.0")
        channel = ET.SubElement(rss, "channel")
        ET.SubElement(channel, "title").text = "France Travel Guide"
        ET.SubElement(channel, "link").text = BASE_URL
        ET.SubElement(channel, "description").text = "Explore famous places and dishes in France"
        
        for item_data in places + dishes:
            item = ET.SubElement(channel, "item")
            ET.SubElement(item, "title").text = item_data["title"]
            ET.SubElement(item, "link").text = f"{BASE_URL}{item_data['url']}"
            ET.SubElement(item, "description").text = item_data["description"]
            ET.SubElement(item, "pubDate").text = datetime.now(pytz.UTC).strftime("%a, %d %b %Y %H:%M:%S %z")
            enclosure = ET.SubElement(item, "enclosure")
            enclosure.set("url", item_data["image"])
            enclosure.set("type", "image/jpeg")
        
        static_dir = os.path.join(os.getcwd(), "static")
        os.makedirs(static_dir, exist_ok=True)
        rss_path = os.path.join(static_dir, "rss_feed.xml")
        logger.info("Writing RSS feed to %s", rss_path)
        tree = ET.ElementTree(rss)
        tree.write(rss_path)
    except Exception as e:
        logger.error("Error generating RSS feed: %s", e)

@app.route("/")
def index():
    try:
        logger.info("Handling request for /")
        places = scrape_places()
        dishes = scrape_dishes()
        generate_rss_feed(places, dishes)
        return render_template("index.html", places=places, dishes=dishes)
    except Exception as e:
        logger.error("Error in index route: %s", e)
        return render_template("index.html", places=[], dishes=[], error="Failed to load content. Please try again later.")

@app.route("/rss_feed.xml")
def rss_feed():
    try:
        logger.info("Serving RSS feed")
        return app.send_static_file("rss_feed.xml")
    except Exception as e:
        logger.error("Error serving RSS feed: %s", e)
        return "RSS feed not available", 500

if __name__ == "__main__":
    app.run(debug=True)
