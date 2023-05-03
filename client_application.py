import os
from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session, jsonify
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash
from client import BrokerClient
import constants as c
import grpc
import exchange_pb2

from client_helpers import apology, login_required, lookup, usd, intraday_endpoints, get_user_stocks, get_news

# Configure application
app = Flask(__name__)
app.secret_key = 'mysecretkey'

channel = grpc.insecure_channel(c.BROKER_IP[1] + ':' + str(c.BROKER_IP[0]))
broker_client = BrokerClient(channel)

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
os.environ["API_KEY"] = "sk_1463654bf81f469798bf7cf5a57c270c"
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")

@app.route("/get_fill_order")
@login_required
def get_fill_order():
    uid = session["user_id"]
    print("user id is ", uid)
    fill = broker_client.stub.OrderFill(exchange_pb2.UserInfo(uid=session["user_id"]))

    if not fill or fill.oid == -1:
        return jsonify({})
    
    balance = broker_client.GetBalance(session["user_id"])
    db.execute("UPDATE users SET cash = ? WHERE id = ?", balance, session["user_id"])
    
    if fill.order_type == exchange_pb2.OrderType.ASK:
        profit = fill.amount_filled * fill.execution_price
        db.execute("INSERT INTO transactions (\"user-id\", symbol, shares, price) VALUES(?, ?, ?, ?)",
                   session["user_id"], fill.ticker, fill.amount_filled, fill.execution_price)
    else:
        db.execute("INSERT INTO transactions (\"user-id\", symbol, shares, price) VALUES(?, ?, ?, ?)",
                   session["user_id"], fill.ticker, fill.amount_filled, 0)
    return jsonify({"order": (fill.oid, fill.amount_filled, fill.execution_price, fill.order_type)})


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
    balance = broker_client.GetBalance(session["user_id"])
    db.execute("UPDATE users SET cash = ? WHERE id = ?", balance, session["user_id"])
    user = db.execute("SELECT * FROM users WHERE id = ?", session["user_id"])

    if user:
        username = user[0]['username']
        balance = usd(user[0]['cash'])

    try:
        msg, success, owned_stocks = broker_client.GetStocks(session["user_id"])
    except:
        return apology("server is down", 400)
    
    if not success:
        return apology(msg, 400)

    stocks = []
    for ticker, shares in owned_stocks.items():
        stocks.append({"symbol": ticker, "shares": shares, "value": 1})

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
    if request.method == "POST":

        ticker = request.form.get("symbol")

        if not ticker or ticker not in c.TICKERS:
            return apology("please enter a valid ticker symbol", 400)

        shares = request.form.get("shares")

        if not shares:
            return apology("please enter # of shares", 400)

        if not shares.isdigit():
            return apology("please enter a *number* of shares", 400)

        if "." in shares:
            return apology("cannot buy fractional shares", 400)

        if int(shares) < 1:
            return apology("please enter a valid amount of shares", 400)
        
        shares = int(shares)

        price = request.form.get("price")

        if not price:
            return apology("please enter # of price", 400)

        if not price.isdigit():
            return apology("please enter a *number* of price", 400)

        if "." in price:
            return apology("cannot buy fractional price", 400)

        if int(price) < 1:
            return apology("please enter a valid amount of price", 400)
        
        price = int(price)

        cash = db.execute("SELECT cash FROM users WHERE id = ?", session["user_id"])

        if cash:
            cash = float(cash[0]["cash"])
        else:
            return apology("something went wrong on our end and we could not process the transaction.", 501)

        if cash < round(int(shares) * price, 2):
            return apology("not enough balance in account for transaction", 400)
        
        try:
            msg, success = broker_client.SendOrder(exchange_pb2.OrderType.BID, ticker, shares, price, session["user_id"])
        except:
            return apology("server is down", 400)
        
        if success:

            cash = round(cash - int(shares) * price - c.BROKER_FEE, 2) 

            db.execute("UPDATE users SET cash = ? WHERE id = ?", cash, session["user_id"])

            total = usd(int(shares) * price)

            flash(f"Success! You placed an order for {shares} share(s) of {ticker} at {str(usd(price))} per share.",
                "success")
        else:
            flash(msg, "error")

        return redirect("/")

    else:
        return render_template("buy.html")

@app.route("/ask", methods=["GET", "POST"])
@login_required
def ask():
    if request.method == "POST":

        ticker = request.form.get("symbol")

        if not ticker or ticker not in c.TICKERS:
            return apology("please enter a valid ticker symbol", 400)

        shares = request.form.get("shares")

        if not shares:
            return apology("please enter # of shares", 400)

        if not shares.isdigit():
            return apology("please enter a *number* of shares", 400)

        if "." in shares:
            return apology("cannot buy fractional shares", 400)

        if int(shares) < 1:
            return apology("please enter a valid amount of shares", 400)
        
        shares = int(shares)

        price = request.form.get("price")

        if not price:
            return apology("please enter # of price", 400)

        if not price.isdigit():
            return apology("please enter a *number* of price", 400)

        if "." in price:
            return apology("cannot buy fractional price", 400)

        if int(price) < 1:
            return apology("please enter a valid amount of price", 400)
        
        price = int(price)

        cash = db.execute("SELECT cash FROM users WHERE id = ?", session["user_id"])

        if cash:
            cash = float(cash[0]["cash"])
        else:
            return apology("something went wrong on our end and we could not process the transaction.", 501)

        if cash < round(int(shares) * price, 2):
            return apology("not enough balance in account for transaction", 400)
        
        try:
            msg, success = broker_client.SendOrder(exchange_pb2.OrderType.ASK, ticker, shares, price, session["user_id"])
        except:
            return apology("server is down", 400)
        
        if success:
            flash(f"Success! You placed an order to sell {shares} share(s) of {ticker} at {str(usd(price))} per share.",
                "success")
        else:
            flash(msg, "error")

        return redirect("/")

    else:
        return render_template("ask.html")

@app.route("/deposit", methods=["GET", "POST"])
@login_required
def deposit():
    """Deposit cash into amount"""

    if request.method == "POST":

        amount = request.form.get("amount")

        if not amount:
            return apology("please enter an amount to deposit", 400)

        if not amount.isdigit():
            return apology("please enter a numerical value", 400)

        if float(amount) <= 0:
            return apology("please enter an amount >= 0", 400)

        cash = db.execute("SELECT cash FROM users WHERE id = ?", session["user_id"])

        if cash:
            cash = float(cash[0]["cash"])
        else:
            return apology("something went wrong on our end and we could not process the transaction.", 501)


        cash += float(amount)

        amount = int(amount)

        try:
            broker_client.DepositCash(session["user_id"], amount)
        except:
            return apology("sever is down", 400)
        
        db.execute("UPDATE users SET cash = ? WHERE id = ?", cash, session["user_id"])


        flash(f"Success! Deposited ${amount}", "success")

        return redirect("/")

    else:
        return render_template("deposit.html")

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
        session["user_id"] = int(rows[0]["id"])

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

        session["user_id"] = int(rows[0]["id"])

        try:
            broker_client.Register(int(session["user_id"]))
        except:
            return apology("server is down")
        
        flash("Registration successful!", "success")

        flash("Welcome to Gouda Exchange!", 'welcome')

        return redirect("/")

    else:
        return render_template("register.html")


def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)

if __name__ == "__main__":
    db.execute("""CREATE TABLE IF NOT EXISTS 'transactions' ('id' integer PRIMARY KEY AUTOINCREMENT NOT NULL, 'user-id' integer NOT NULL, 'symbol' text NOT NULL, 'shares' integer NOT NULL, 'price' double precision NOT NULL, 'time' datetime DEFAULT CURRENT_TIMESTAMP);""")
    # db.execute("""CREATE UNIQUE INDEX 'ids' ON "transactions" ("id" ASC);""")
    db.execute("""CREATE TABLE IF NOT EXISTS 'users' ('id' INTEGER, 'username' TEXT NOT NULL UNIQUE, 'hash' TEXT NOT NULL, 'cash' NUMERIC NOT NULL DEFAULT 0.00, PRIMARY KEY(id));""")
    #db.execute("""CREATE UNIQUE INDEX username ON users (username);""")
    app.run(debug=True, host = "0.0.0.0", port = 8080)