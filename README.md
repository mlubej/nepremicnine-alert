# Nepremicnine.net Alert Bot

Simple bot which sends an email when a new ad on is posted on [nepremicnine.net](https://www.nepremicnine.net/).

## Prerequisites

### chromedriver

Install [chromedriver](https://chromedriver.chromium.org/) on your system. Firefox driver is currently not supported. PRs welcome.

### Requirements

Install requirements

```bash
pip install -r requirements.txt
```

### Set up env

This package uses the `.env` file to read the gmail username and password. Set them there in the form of

```
GMAIL_USERNAME=name.surname@gmail.com
GMAIL_PASSWORD=<your-app-password-here>
```

## How to run

```
Options:
  -u, --url TEXT        Base URL with the search criteria.  [required]
  -o, --out_path TEXT   Name of the database file.
  -r, --recepient TEXT  Email of the recepient. Provide each recepient separately. [required]
  --help                Show this message and exit.
```

When everything is installed, simply run the `nepremicnine_alert.py` script with the appropriate arguments.

### Specific querying

Simply include any search criteria of interest in the URL, e.g. "https://www.nepremicnine.net/oglasi-prodaja/ljubljana-mesto/stanovanje/3-sobno/cena-od-100000-do-300000-eur,velikost-od-50-do-100-m2/"

The first run will trigger a database fill. All later runs check the new entries agains the existing ones and send an email if a new ad is posted.

Works best run as a [cron job](https://en.wikipedia.org/wiki/Cron).
