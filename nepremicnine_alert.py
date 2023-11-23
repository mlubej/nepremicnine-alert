from __future__ import annotations

import os
import re
import smtplib
from datetime import datetime
from email.mime.text import MIMEText
from time import sleep
from typing import Dict

import numpy as np
import pandas as pd
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from selenium import webdriver

SORT_SUFFIX = "?s=16"
ENTRY_IDENTIFIER = ["url", "title", "area_m2", "year", "room_type"]
CSV_DATABASE_FILE = "./nepremicnine_entries.csv"
NEPREMICNINE_URL = "https://www.nepremicnine.net/oglasi-prodaja/ljubljana-mesto/stanovanje/2.5-sobno,3-sobno,3.5-sobno,4-sobno/cena-od-220000-do-300000-eur,velikost-od-55-do-120-m2"
GMAIL_RECEPIENTS = ["lubej.matic@gmail.com", "neza.arambasic@gmail.com"]
DATE_COLUMN = "date"

load_dotenv(override=True)
GMAIL_SENDER = os.environ["GMAIL_SENDER"]
GMAIL_PASSWORD = os.environ["GMAIL_PASSWORD"]


def load_existing_database() -> pd.DataFrame:
    return pd.read_csv(CSV_DATABASE_FILE)


def save_database(database: pd.DataFrame) -> None:
    return database.sort_values(DATE_COLUMN, ascending=False).to_csv(CSV_DATABASE_FILE, index=False)


def entry_parser(entry) -> Dict[str, str | float]:
    meta_info = dict(
        url=entry.find("a", {"class": "url-title-d"})["href"],
        title=entry.find("a", {"class": "url-title-d"})["title"].lower(),
        price=float(entry.find("meta", {"itemprop": "price"})["content"]),
        **dict(zip(["area_m2", "year", "floor"], [item.text for item in entry.find_all("li")])),
        category=re.search("Prodaja: (\w+)", str(entry)).group(1).lower(),
        room_type=re.search("[\d,]+-sobno", str(entry)).group(),
    )
    meta_info[DATE_COLUMN] = datetime.now().date().isoformat()
    meta_info["area_m2"] = float(re.search("[\d,]+", meta_info["area_m2"]).group().replace(",", "."))
    meta_info["year"] = int(re.search("[\d]+", meta_info["year"]).group())
    return meta_info


def get_entries_from_url(url: str) -> None:
    # set a headless driver
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument("--headless")

    # set the user-agent back to chrome.
    user_agent = (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.50 Safari/537.36"
    )
    chrome_options.add_argument(f"user-agent={user_agent}")

    driver = webdriver.Chrome(options=chrome_options)
    driver.set_window_size(1080, 800)  # set the size of the window

    # get page content
    driver.get(url)

    # parse ads
    soup_entries = BeautifulSoup(driver.page_source, "lxml").find_all("div", {"class": "property-details"})
    return [entry_parser(entry) for entry in soup_entries]


def init_db() -> None:
    if os.path.exists(CSV_DATABASE_FILE):
        print("Loading database ...")
        return

    entries = []
    print("Initial fill of database")

    page_idx = 1
    while True:
        sleep(np.random.randint(10, 19) / 10)

        print(f"Parsing page: {page_idx}", end=" ... ")
        parsed = get_entries_from_url(f"{NEPREMICNINE_URL}/{page_idx}/{SORT_SUFFIX}")
        print(f"[Found {len(parsed)} ads]")

        entries.extend(parsed)
        page_idx += 1

        if len(parsed) == 0:
            print("  Search complete.")
            break

    entries_csv = pd.DataFrame(entries)
    save_database(entries_csv)


def get_new_entries(existing_database: pd.DataFrame) -> pd.DataFrame:
    entries_list = []
    database_indices = existing_database.set_index(ENTRY_IDENTIFIER).index
    print("Searching for new entries")

    page_idx = 1
    while True:
        sleep(np.random.randint(10, 19) / 10)

        print(f"Parsing page: {page_idx}", end=" ... ")
        parsed_entries = get_entries_from_url(f"{NEPREMICNINE_URL}/{page_idx}/{SORT_SUFFIX}")

        parsed_indices = pd.DataFrame(parsed_entries).set_index(ENTRY_IDENTIFIER).index
        parsed_entry_mask = parsed_indices.isin(database_indices)
        print(f"[Found {np.count_nonzero(~parsed_entry_mask)} NEW ads]")

        entries_list.extend(parsed_entries)
        page_idx += 1

        if parsed_entry_mask.any():
            print("  Search complete")
            break

    all_parsed_entries = pd.DataFrame(entries_list)
    all_parsed_entries_indices = all_parsed_entries.set_index(ENTRY_IDENTIFIER).index
    new_entry_mask = ~all_parsed_entries_indices.isin(database_indices)
    return all_parsed_entries[new_entry_mask]


def send_email(entry: Dict):
    subject = f'Nova nepremičnina: {entry["category"]}, {entry["room_type"]}: {entry["title"]}, {entry["area_m2"]} m2'

    content = [
        f'Naslov oglasa: {entry["title"]}',
        f'Cena nepremičnine: {int(entry["price"])} EUR',
        f'Površina: {entry["area_m2"]} m2',
        f'Število sob: {entry["room_type"]}',
        f'Leto: {entry["year"]}',
        f'Nadstropje: {entry["floor"]}',
        f'Povezava: {entry["url"]}',
    ]
    body = "\n".join(content)

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = GMAIL_SENDER
    msg["To"] = ", ".join(GMAIL_RECEPIENTS)
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp_server:
        smtp_server.login(GMAIL_SENDER, GMAIL_PASSWORD)
        smtp_server.sendmail(GMAIL_SENDER, GMAIL_RECEPIENTS, msg.as_string())


def append_and_alert_for_new_entries() -> None:
    database = load_existing_database()
    new_entries = get_new_entries(database)

    if len(new_entries) == 0:
        print("No new entries found")
        return

    print("Alerting for new entries")
    for _, entry in new_entries.iterrows():
        send_email(entry.to_dict())

    print("Updating database")
    save_database(pd.concat([database, new_entries]).reset_index(drop=True))


if __name__ == "__main__":
    init_db()
    append_and_alert_for_new_entries()
