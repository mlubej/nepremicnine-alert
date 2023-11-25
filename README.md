# Nepremicnine.net Alert Bot

Simple bot which sends an email when a new ad on is posted on [nepremicnine.net](https://www.nepremicnine.net/).

**The code is focused on buying flats. Might need some custom updates for querrying houses or looking for a place to rent.**

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

Sending via gmail will not work with your standard password, you have to generate an application-specific password in your account. More info [here](https://support.google.com/mail/answer/185833?hl=en).

## How to run

### Quick example

Run a similar example as below. The first run will trigger a database fill. All later runs check the new entries agains the existing ones and send an email if a new ad is posted.

```bash
$ python nepremicnine_alert.py \
    --url "https://www.nepremicnine.net/oglasi-prodaja/ljubljana-mesto/stanovanje/3-sobno/cena-od-200000-do-300000-eur,velikost-od-50-do-100-m2" \
    --out_path "./nepremicnine_entries.csv" \
    --recepient "recepient1@gmail.com" \
    --recepient "recepient2@gmail.com"
```

Works best run as a [cron job](https://en.wikipedia.org/wiki/Cron).

### More details

```
Options:
  -u, --url TEXT        Base URL with the search criteria.  [required]
  -o, --out_path TEXT   Name of the database file.
  -r, --recepient TEXT  Email of the recepient. Provide each recepient separately. [required]
  --help                Show this message and exit.
```

#### Specific querying

Simply include any search criteria of interest in the URL, e.g. "https://www.nepremicnine.net/oglasi-prodaja/ljubljana-mesto/stanovanje/3-sobno/cena-od-100000-do-300000-eur,velikost-od-50-do-100-m2/"
