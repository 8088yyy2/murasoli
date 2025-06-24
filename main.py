import requests
import os
import time
from datetime import datetime
from PyPDF2 import PdfMerger
from bs4 import BeautifulSoup

BASE_META_URL = "https://epaper.murasoli.in/Home/GetAllpages?editionid=1&editiondate="
DIR_URL_TEMPLATE = "https://mrsfsnew.avahan.net/mrs/{year}/{month}/{day}/CHN/5_{page:02d}/"
OUTPUT_PDF = "murasoli.pdf"
LOG_FILE = "log.txt"
RETRY_LIMIT = 3

def log(message):
    print(message)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(message + "\n")

with open(LOG_FILE, "w", encoding="utf-8") as f:
    f.write("=== Murasoli PDF Download Log ===\n")

def get_page_count(date_str):
    response = requests.get(BASE_META_URL + date_str)
    response.raise_for_status()
    data = response.json()
    return len(data)

def find_pdf_filename(directory_url, page_number):
    try:
        resp = requests.get(directory_url, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, 'html.parser')
        links = soup.find_all('a')
        for link in links:
            href = link.get('href')
            if href and href.endswith(f"_{page_number:02d}.pdf"):
                return href.split('/')[-1]
    except Exception as e:
        log(f"[ERROR] Reading {directory_url}: {e}")
    return None

def download_pdf(date, page_number):
    year = date.strftime("%Y")
    month = date.strftime("%m")
    day = date.strftime("%d")

    dir_url = DIR_URL_TEMPLATE.format(year=year, month=month, day=day, page=page_number)
    filename = find_pdf_filename(dir_url, page_number)

    if not filename:
        log(f"[WARN] No PDF found in: {dir_url}")
        return None

    pdf_url = dir_url + filename
    local_file = f"page_{page_number:02d}.pdf"

    for attempt in range(1, RETRY_LIMIT + 1):
        try:
            resp = requests.get(pdf_url, timeout=10)
            if resp.status_code == 200:
                with open(local_file, "wb") as f:
                    f.write(resp.content)
                log(f"[SUCCESS] Downloaded: {local_file} (Attempt {attempt})")
                return local_file
            else:
                log(f"[FAIL] Attempt {attempt}: Status {resp.status_code} for {pdf_url}")
        except Exception as e:
            log(f"[ERROR] Attempt {attempt} failed for {pdf_url}: {e}")
        time.sleep(2)
    log(f"[FAILED] Giving up on: {pdf_url}")
    return None

def merge_pdfs(pdf_files, output_file):
    merger = PdfMerger()
    for file in pdf_files:
        merger.append(file)
    merger.write(output_file)
    merger.close()
    log(f"[MERGED] All PDFs into: {output_file}")

def cleanup(files):
    for file in files:
        try:
            os.remove(file)
            log(f"[CLEANUP] Deleted: {file}")
        except Exception as e:
            log(f"[ERROR] Failed to delete {file}: {e}")

def main():
    today = datetime.today()
    date_str = today.strftime("%d/%m/%Y")

    log("[INFO] Fetching number of pages...")
    try:
        page_count = get_page_count(date_str)
        log(f"[INFO] Total pages: {page_count}")
    except Exception as e:
        log(f"[FATAL] Could not fetch page count: {e}")
        return

    downloaded = []
    for i in range(1, page_count + 1):
        pdf = download_pdf(today, i)
        if pdf:
            downloaded.append(pdf)

    if downloaded:
        merge_pdfs(downloaded, OUTPUT_PDF)
        cleanup(downloaded)
    else:
        log("[FATAL] No PDFs downloaded. Nothing to merge.")

if __name__ == "__main__":
    main()
