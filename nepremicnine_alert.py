from __future__ import annotations

import os
import re
import smtplib
from dataclasses import dataclass
from datetime import datetime
from email.mime.text import MIMEText
from time import sleep
from typing import Dict

import bs4
import click
import numpy as np
import pandas as pd
from dotenv import load_dotenv
from selenium import webdriver


load_dotenv(override=True)
_SORT_SUFFIX = "?s=16"
_ENTRY_IDENTIFIER = ["url", "title", "area_m2", "year", "room_type"]
_GMAIL_USERNAME = os.environ["GMAIL_USERNAME"]
_GMAIL_PASSWORD = os.environ["GMAIL_PASSWORD"]


@dataclass(frozen=True)
class EntryInfo:
    url: str
    title: str
    price: float
    area: float
    year: int
    floor: str | None
    category: str
    room_type: str
    date_found: str


def load_existing_database(database_path: str) -> pd.DataFrame:
    return pd.read_csv(database_path, index_col=0)


def save_database(database: pd.DataFrame, database_path: str) -> None:
    return database.to_csv(database_path)


def entry_parser(entry) -> EntryInfo:
    area_tag = entry.select_one("img[src*=velikost]")
    floor_tag = entry.select_one("img[src*=nadstropje]")

    entry_info = EntryInfo(
        url=entry.find("a", {"class": "url-title-d"})["href"],
        title=entry.find("a", {"class": "url-title-d"})["title"].lower(),
        price=float(entry.find("meta", {"itemprop": "price"})["content"]),
        area=float(re.search("[\d,]+", area_tag.parent.text).group().replace(",", ".")),
        year=int(entry.select_one("img[src*=leto]").parent.text),
        floor=floor_tag.parent.text if floor_tag is not None else "Ni podatka",
        date_found=datetime.now().date().isoformat(),
        category=re.search("Prodaja: (\w+)", str(entry)).group(1).lower(),
        room_type=re.search("[\d,]+-sobno", str(entry)).group(),
    )
    return entry_info


def get_entries_from_url(url: str) -> list[EntryInfo]:
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
    soup_entries = bs4.BeautifulSoup(driver.page_source, "lxml").find_all("div", {"class": "property-details"})
    return [entry_parser(entry) for entry in soup_entries if entry is not None]


def init_db(base_url: str, database_path: str) -> None:
    if os.path.exists(database_path):
        print("Loading database ...")
        return

    entries = []
    print("Initial fill of database")

    page_idx = 1
    while True:
        sleep(np.random.randint(10, 19) / 10)

        print(f"Parsing page: {page_idx}", end=" ... ")
        parsed = get_entries_from_url(f"{base_url}/{page_idx}/{_SORT_SUFFIX}")
        print(f"[Found {len(parsed)} ads]")

        entries.extend(parsed)
        page_idx += 1

        if len(parsed) == 0:
            print("  Search complete.")
            break

    entries_csv = pd.DataFrame(entries)
    save_database(entries_csv)


def get_new_entries(base_url: str, existing_database: pd.DataFrame) -> pd.DataFrame:
    entries_list = []
    database_indices = existing_database.set_index(_ENTRY_IDENTIFIER).index
    print("Searching for new entries")

    page_idx = 1
    while True:
        sleep(np.random.randint(10, 19) / 10)

        print(f"Parsing page: {page_idx}", end=" ... ")
        parsed_entries = get_entries_from_url(f"{base_url}/{page_idx}/{_SORT_SUFFIX}")

        parsed_indices = pd.DataFrame(parsed_entries).set_index(_ENTRY_IDENTIFIER).index
        parsed_entry_mask = parsed_indices.isin(database_indices)
        print(f"[Found {np.count_nonzero(~parsed_entry_mask)} NEW ads]")

        entries_list.extend(parsed_entries)
        page_idx += 1

        if parsed_entry_mask.any():
            print("  Search complete")
            break

    all_parsed_entries = pd.DataFrame(entries_list)
    all_parsed_entries_indices = all_parsed_entries.set_index(_ENTRY_IDENTIFIER).index
    new_entry_mask = ~all_parsed_entries_indices.isin(database_indices)
    return all_parsed_entries[new_entry_mask]


def send_email(entry: Dict[str, str | float], recepients: list[str]):
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
    msg["From"] = _GMAIL_USERNAME
    msg["To"] = ", ".join(recepients)
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp_server:
        smtp_server.login(_GMAIL_USERNAME, _GMAIL_PASSWORD)
        smtp_server.sendmail(_GMAIL_USERNAME, recepients, msg.as_string())


@click.command()
@click.option("--url", "-u", required=True, type=str, help="Base URL with the search criteria.")
@click.option("--out_path", "-o", type=str, default="./nepremicnine_entries.csv", help="Name of the database file.")
@click.option(
    "--recepient",
    "-r",
    required=True,
    multiple=True,
    help="Email of the recepient. Provide each recepient separately.",
)
def main(url: str, out_path: str, recepient: list[str]) -> None:
    if not os.path.exists(out_path):
        init_db(url, out_path)
        return

    database = load_existing_database(out_path)
    new_entries = get_new_entries(url, database)

    if len(new_entries) == 0:
        print("No new entries found")
        return

    print("Alerting for new entries")
    for _, entry in new_entries.iterrows():
        send_email(entry.to_dict())

    print("Updating database")
    updated_database = pd.concat([database, new_entries]).reset_index(drop=True)
    save_database(updated_database, out_path)


if __name__ == "__main__":
    main()
