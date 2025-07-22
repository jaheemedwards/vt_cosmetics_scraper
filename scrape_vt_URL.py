import os
import re
import shutil
import gradio as gr
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from urllib.request import urlretrieve

# === CONFIG ===
HEADERS = {"User-Agent": "Mozilla/5.0"}
BASE_URL = "https://globalvt-cosmetics.com"
ROOT_FOLDER = "vt_products"
os.makedirs(ROOT_FOLDER, exist_ok=True)

def sanitize_filename(name):
    return re.sub(r'[^a-zA-Z0-9_-]', '_', name.strip().lower())

def get_soup(url):
    response = requests.get(url, headers=HEADERS)
    if response.status_code != 200:
        raise Exception(f"Failed to fetch URL: {url} (Status code: {response.status_code})")
    return BeautifulSoup(response.text, "html.parser")

def scrape_product(product_url):
    soup = get_soup(product_url)

    # Get product title
    title_tag = soup.select_one("h2.h1")
    if not title_tag:
        raise Exception("⚠️ Title not found.")

    title = title_tag.get_text(strip=True)
    folder_name = sanitize_filename(title)
    folder_path = os.path.join(ROOT_FOLDER, folder_name)
    os.makedirs(folder_path, exist_ok=True)

    # Save description
    desc_tag = soup.select_one(".product__description")
    description = desc_tag.get_text("\n", strip=True) if desc_tag else "No description available"
    with open(os.path.join(folder_path, "description.txt"), "w", encoding="utf-8") as f:
        f.write(description)

    # Collect image URLs
    image_urls = set()

    # 1. Thumbnail images
    img_tags = soup.select("ul.thumbnail-list img")
    for img in img_tags:
        src = img.get("src")
        if src:
            if src.startswith("//"):
                src = "https:" + src
            elif src.startswith("/"):
                src = urljoin(BASE_URL, src)
            image_urls.add(src)

    # 2. Main product image
    main_img_tag = soup.select_one("div.product__media.media--transparent img")
    if main_img_tag:
        main_src = main_img_tag.get("src")
        if main_src:
            if main_src.startswith("//"):
                main_src = "https:" + main_src
            elif main_src.startswith("/"):
                main_src = urljoin(BASE_URL, main_src)
            image_urls.add(main_src)

    # Download images
    for i, img_url in enumerate(image_urls, 1):
        ext = os.path.splitext(img_url.split("?")[0])[-1]
        filename = f"{folder_name}_{i}{ext}"
        file_path = os.path.join(folder_path, filename)
        try:
            urlretrieve(img_url, file_path)
        except Exception as e:
            print(f"⚠️ Failed to download {img_url}: {e}")

    # Zip folder
    zip_path = f"{folder_path}.zip"
    shutil.make_archive(folder_path, 'zip', folder_path)
    return zip_path

# === Gradio Interface ===
def gradio_scraper(url_input):
    try:
        if not url_input.startswith("http"):
            url_input = urljoin(BASE_URL, url_input)
        zip_file = scrape_product(url_input)
        return zip_file
    except Exception as e:
        return f"❌ Error: {e}"

gr.Interface(
    fn=gradio_scraper,
    inputs=gr.Textbox(label="Paste VT Cosmetics Product URL"),
    outputs=gr.File(label="Download Product Folder (.zip)"),
    title="VT Cosmetics Product Scraper",
    description="Paste a product link and download its images and description."
).launch()
