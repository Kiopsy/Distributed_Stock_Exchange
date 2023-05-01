import os
from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd, intraday_endpoints, get_user_stocks, get_news

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")

@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""

    username = "there!"
    balance = "N/A"
    user = db.execute("SELECT * FROM users WHERE id = ?", session["user_id"])

    if user:
        username = user[0]['username']
        balance = usd(user[0]['cash'])

    stocks = get_user_stocks(db, session["user_id"])

    for stock in stocks:
        info = lookup(stock["symbol"])
        if not info:
            stock["value"] = "N/A"
            continue
        stock["value"] = usd(round(info["price"] * stock["shares"], 2))

    return render_template("index.html", username=username, stocks=stocks, balance=balance)


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""

    if request.method == "POST":

        stock = lookup(request.form.get("symbol"))

        if not stock:
            return apology("please enter a valid stock symbol", 400)

        shares = request.form.get("shares")

        if not shares:
            return apology("please enter # of shares", 400)

        if not shares.isdigit():
            return apology("please enter a *number* of shares", 400)

        if "." in shares:
            return apology("cannot buy fractional shares", 400)

        if int(shares) < 1:
            return apology("please enter a valid amount of shares", 400)

        cash = db.execute("SELECT cash FROM users WHERE id = ?", session["user_id"])

        if cash:
            cash = float(cash[0]["cash"])
        else:
            return apology("something went wrong on our end and we could not process the transaction.", 501)

        if cash < round(int(shares) * stock["price"], 2):
            return apology("not enough balance in account for transaction", 400)

        db.execute("INSERT INTO transactions (\"user-id\", symbol, shares, price) VALUES(?, ?, ?, ?)",
                   session["user_id"], stock["symbol"], int(shares), stock["price"])

        cash = round(cash - int(shares) * stock["price"], 2)

        db.execute("UPDATE users SET cash = ? WHERE id = ?", cash, session["user_id"])

        total = usd(int(shares) * stock["price"])

        flash("Success! Bought " + shares + " share(s) of " + stock['symbol'] + " for " + total + " at " + str(usd(stock['price'])) + " per share.",
              "notification")

        return redirect("/")

    else:
        return render_template("buy.html")


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    transactions = db.execute("SELECT * FROM transactions WHERE \"user-id\" = ?", session["user_id"])

    return render_template("history.html", transactions=transactions)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page

        flash("Welcome back, " + request.form.get("username") + "! Ready to make some money today?",
              "welcome")

        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""

    if request.method == "POST":

        stock = lookup(request.form.get("symbol"))

        if not stock:
            return apology("please enter a valid stock symbol", 400)

        display = {}

        # Green color default, triangle pointing up unicode
        display['color'] = "32, 166, 32"
        display['tick'] = "&#9652"
        display['change'] = "N/A"

        endpoint_data = intraday_endpoints(stock["symbol"])

        # If getting the chart data messes up for some reason, return without the chart
        if not endpoint_data:
            stock['price'] = usd(stock['price'])
            return render_template("quoted.html", stock=stock, endpoint=False, news=None, display=display)

        labels = []

        values = []

        # Get the x and y axis, where labels (x) is the time, and value (y) is the price
        # Additionally, get the first valid point and the open time
        for endpoint in endpoint_data:
            if endpoint['value']:
                labels.append(endpoint['time'])
                values.append(endpoint['value'])

        # In case the user opens the quote right as the market starts, before
        # average data is available
        if len(values) == 0:
            values.append(stock['price'])
            labels.append("9:30 AM")

        # If the stock lost money through the day, set to a dark red color and triangle pointing down
        if stock['price'] < values[0]:
            display['color'] = "255, 25, 25"
            display['tick'] = "&#9662"

        # Percent change from first minute (not exact! I could have used the open/close API data, but
        # I did not want to use up more of my API message limit, so this is an in-house method)
        # (I also could have used the first open, but this breaks on stocks whose first value is not at 9:30 AM
        #  without some messy coding, so this will do OK. Also, the first intraday open is not accurate without
        #  using the market data, which is premium only, so either way it won't be 100% correct.)
        display['change'] = round(((stock['price'] - values[0])/values[0]) * 100, 2)

        news = get_news(stock["symbol"])

        stock['price'] = usd(stock['price'])

        return render_template("quoted.html", stock=stock, labels=labels, values=values, endpoint=True,
                               news=news, display=display)

    else:
        return render_template("quote.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    session.clear()

    if request.method == "POST":

        username = request.form.get("username")

        password = request.form.get("password")

        confirm = request.form.get("confirmation")

        if not username:
            return apology("must enter a username to register", 400)

        elif db.execute("SELECT * FROM users WHERE username = ?", username):
            return apology("a user with that username already exists", 400)

        elif not password:
            return apology("must enter a password to register", 400)

        elif not password == confirm:
            return apology("password field is empty or does not match", 400)

        db.execute("INSERT INTO users (username, hash) VALUES(?, ?)", username,
                   generate_password_hash(password))

        rows = db.execute("SELECT * FROM users WHERE username = ?", username)

        if not rows or not rows[0]:
            return redirect("/")

        session["user_id"] = rows[0]["id"]

        flash("Registration successful!", "notification")

        flash("Welcome to C$50 finance!", 'welcome')

        return redirect("/")

    else:
        return render_template("register.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    if request.method == "POST":
        stock = lookup(request.form.get("symbol"))

        if not stock:
            return apology("please enter a valid stock symbol", 400)

        share_request = request.form.get("shares")

        if not share_request:
            return apology("please enter number of shares", 400)

        if not share_request.isdigit():
            return apology("please enter a *number* of shares", 400)

        if "." in share_request:
            return apology("cannot sell fractional shares", 400)

        shares_owned = get_user_stocks(db, session["user_id"])

        if not shares_owned:
            return apology("something went wrong on our end", 501)

        for shares in shares_owned:
            if shares['symbol'] == stock['symbol']:
                shares_owned = shares['shares']
                break

        if not isinstance(shares_owned, int):
            return apology("we're not sure how you got here, but please enter a valid stock symbol", 400)

        if int(share_request) < 1 or shares_owned < int(share_request):
            return apology("please enter a valid amount of shares", 400)

        sale_value = round(stock["price"] * int(share_request), 2)

        db.execute("INSERT INTO transactions (\"user-id\", symbol, shares, price) VALUES(?, ?, ?, ?)",
                   session["user_id"], stock["symbol"], -int(share_request), stock["price"])

        db.execute("UPDATE users SET cash = cash + ? WHERE id = ?", sale_value, session["user_id"])

        cash = db.execute("SELECT cash FROM users WHERE id = ?", session["user_id"])

        if cash:
            cash = usd(round(cash[0]['cash'], 2))
        else:
            cash = "N/A"

        total = usd(stock["price"] * int(share_request))

        flash("Success! Sold " + share_request + " share(s) for " + total + ", at " + usd(stock['price']) + " per share.",
              "notification")

        return redirect("/")

    else:
        stocks = get_user_stocks(db, session["user_id"])
        return render_template("sell.html", symbols=[stock["symbol"] for stock in stocks])


def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
