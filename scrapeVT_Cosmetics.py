import os
import re
import requests
import pandas as pd
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from urllib.request import urlretrieve
from fuzzywuzzy import fuzz

# === CONFIG ===
CSV_PATH = "Reedle Pricing for Innnovation Lab Revised Price Listing(TRADE).csv"  # <-- change to your CSV path
COLUMN_NAME = "ITEM DESCRIPTION TO ENTER ON VAI"
MATCH_THRESHOLD = 85
BASE_URL = "https://globalvt-cosmetics.com"
COLLECTION_URL = f"{BASE_URL}/collections/all"
HEADERS = {"User-Agent": "Mozilla/5.0"}

# === Create Root Folder ===
image_root_folder = "vt_products"
os.makedirs(image_root_folder, exist_ok=True)

def sanitize_filename(name):
    return re.sub(r'[^a-zA-Z0-9_-]', '_', name.strip().lower())

def get_soup(url):
    response = requests.get(url, headers=HEADERS)
    return BeautifulSoup(response.text, "html.parser")

def load_target_names():
    df = pd.read_csv(CSV_PATH)
    return df[COLUMN_NAME].dropna().str.strip().tolist()

def is_match(scraped_title, targets):
    scraped_title_clean = scraped_title.lower()
    for target in targets:
        score = fuzz.partial_ratio(scraped_title_clean, target.lower())
        if score >= MATCH_THRESHOLD:
            return True, target
    return False, None

def scrape_product(product_url, targets):
    soup = get_soup(product_url)

    title_tag = soup.select_one("h2.h1")
    if not title_tag:
        print(f"⚠️ Title not found for {product_url}")
        return

    title = title_tag.get_text(strip=True)
    match, matched_name = is_match(title, targets)
    if not match:
        print(f"❌ Skipping: {title}")
        return

    print(f"\n🛍️ Matched and scraping: {title}  →  ({matched_name})")
    folder_name = sanitize_filename(title)
    folder_path = os.path.join(image_root_folder, folder_name)
    os.makedirs(folder_path, exist_ok=True)

    # Save description
    desc_tag = soup.select_one(".product__description")
    description = desc_tag.get_text("\n", strip=True) if desc_tag else "No description available"
    with open(os.path.join(folder_path, "description.txt"), "w", encoding="utf-8") as f:
        f.write(description)

    # Get image URLs
    thumbnail_list = soup.select("ul.thumbnail-list img")
    image_urls = []
    for img in thumbnail_list:
        src = img.get("src")
        if src:
            if src.startswith("//"):
                src = "https:" + src
            elif src.startswith("/"):
                src = urljoin(BASE_URL, src)
            image_urls.append(src)

    # Download images
    for i, img_url in enumerate(image_urls, start=1):
        ext = os.path.splitext(img_url.split("?")[0])[-1]
        filename = f"{folder_name}_{i}{ext}"
        file_path = os.path.join(folder_path, filename)

        try:
            urlretrieve(img_url, file_path)
            print(f"📸 Saved image: {file_path}")
        except Exception as e:
            print(f"⚠️ Failed to download {img_url}: {e}")

def main():
    targets = load_target_names()
    print(f"📦 Loaded {len(targets)} product names from CSV.")

    soup = get_soup(COLLECTION_URL)
    product_cards = soup.select("a.full-unstyled-link")

    product_urls = []
    for card in product_cards:
        href = card.get("href")
        if href and "/products/" in href:
            full_url = urljoin(BASE_URL, href)
            if full_url not in product_urls:
                product_urls.append(full_url)

    print(f"\n🔗 Found {len(product_urls)} products on site")

    for product_url in product_urls:
        scrape_product(product_url, targets)

if __name__ == "__main__":
    main()
