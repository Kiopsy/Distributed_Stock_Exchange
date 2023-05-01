import os
import requests
import urllib.parse

from flask import redirect, render_template, request, session
from functools import wraps
from cs50 import SQL
from datetime import date, timedelta
import re


def apology(message, code=400):
    """Render message as an apology to user."""
    def escape(s):
        """
        Escape special characters.

        https://github.com/jacebrowning/memegen#special-characters
        """
        for old, new in [("-", "--"), (" ", "-"), ("_", "__"), ("?", "~q"),
                         ("%", "~p"), ("#", "~h"), ("/", "~s"), ("\"", "''")]:
            s = s.replace(old, new)
        return s
    return render_template("apology.html", top=code, bottom=escape(message)), code


def login_required(f):
    """
    Decorate routes to require login.

    https://flask.palletsprojects.com/en/1.1.x/patterns/viewdecorators/
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function


def lookup(symbol):
    """Look up quote for symbol."""

    # Contact API
    try:
        api_key = os.environ.get("API_KEY")
        url = f"https://cloud.iexapis.com/stable/stock/{urllib.parse.quote_plus(symbol)}/quote?token={api_key}"
        response = requests.get(url)
        response.raise_for_status()
    except requests.RequestException:
        return None

    # Parse response
    try:
        quote = response.json()
        return {
            "name": quote["companyName"],
            "price": float(quote["latestPrice"]),
            "symbol": quote["symbol"]
        }
    except (KeyError, TypeError, ValueError):
        return None


def usd(value):
    """Format value as USD."""
    return f"${value:,.2f}"


def intraday_endpoints(symbol):
    """Get the intraday point values and market open for a symbol, so we may build a detailed chart.
       Modeled off the previous use of the API up above (lookup)"""
    try:
        api_key = os.environ.get("API_KEY")
        url = f"https://cloud-sse.iexapis.com/stable/stock/{urllib.parse.quote_plus(symbol)}/intraday-prices?token={api_key}"
        response = requests.get(url)
        response.raise_for_status()
    except requests.RequestException:
        return None

    try:
        endpoints = response.json()
        return [
            {
                "time": endpoint["label"],
                "value": endpoint["average"],
                "open": endpoint["open"]
            } for endpoint in endpoints
        ]

    except (KeyError, TypeError, ValueError):
        return None


def get_news(symbol):
    """Get the 10 most relevant stories surrounding a stock search term from the past week.
       Works very well with well-known stocks (AMZN, NFLX, TSLA, etc)
       With the less-known stocks/short name stocks (ie: Ford), not as much. But it works well enough.
       I could have restricted the search to certain sites (ie: Motley Fool, MarketWatch) but then the results become
       much more sparse in those situations. This is the best compromise, I think."""
    """NOTE: This uses an outside api, from newsapi.org, since IEX's stock news API function
       is less-than-ideal to say the least.
       I'm exposing my api key here for this to work -- not that I think you'll do anything wrong with it"""
    try:
        api_key = "96d608086f8242d0bdb3515140265e2c"
        today = date.today()
        last_week = today - timedelta(days=7)
        today = today.strftime("%Y-%m-%d")
        last_week = last_week.strftime("%Y-%m-%d")
        url = f"http://newsapi.org/v2/everything?q={urllib.parse.quote_plus(symbol)}%20stock&language=en&from={last_week}&to={today}&sortBy=relevancy&apiKey={api_key}"
        response = requests.get(url)
        response.raise_for_status()
    except request.RequestException:
        return None

    try:
        stories = response.json()['articles']
        return [
            {
                "headline": story['title'],
                "source": story['source']['name'],
                "url": story['url'],
                # Clean up any HTML tags, adapted from
                # https://stackoverflow.com/questions/9662346/python-code-to-remove-html-tags-from-a-string
                "summary": re.sub('<.*?>', '', story['description']),
                "date": story['publishedAt'].split('T')[0]
            } for story in stories[:10]
        ]

    except (KeyError, TypeError, ValueError):
        return None

# This is a helper function that gets the given users shares
# Basically just made so that I don't have to write the same exact thing three times over


def get_user_stocks(db, user_id):
    return db.execute("""SELECT symbol,
                        SUM(shares) AS shares
                        FROM transactions WHERE "user-id" = ?
                        GROUP BY symbol HAVING SUM(shares) > 0""", user_id)

