from flask import Flask, render_template, request, redirect, url_for
import json
import yfinance as yf
from datetime import datetime
import pytz
from flask import session
import os
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3




app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret")
PORTFOLIO_FILE = "portfolio.json"

def get_db():
    return sqlite3.connect("database.db")


def create_user(username, password):
    db = get_db()
    c = db.cursor()

    hashed_password = generate_password_hash(password)

    c.execute(
        "INSERT INTO users (username, password, cash) VALUES (?, ?, ?)",
        (username, hashed_password, 10000)
    )

    db.commit()
    db.close()


def get_user(username):
    db = get_db()
    c = db.cursor()

    c.execute(
        "SELECT username, password, cash FROM users WHERE username = ?",
        (username,)
    )

    user = c.fetchone()
    db.close()
    return user


def get_portfolio(username):
    db = get_db()
    c = db.cursor()
    c.execute(
        "SELECT symbol, shares FROM portfolio WHERE username = ?",
        (username,)
    )
    data = dict(c.fetchall())
    db.close()
    return data


def update_cash(username, cash):
    db = get_db()
    c = db.cursor()
    c.execute(
        "UPDATE users SET cash = ? WHERE username = ?",
        (cash, username)
    )
    db.commit()
    db.close()


def update_stock(username, symbol, shares):
    db = get_db()
    c = db.cursor()

    if shares == 0:
        c.execute(
            "DELETE FROM portfolio WHERE username = ? AND symbol = ?",
            (username, symbol)
        )
    else:
        c.execute("""
        INSERT INTO portfolio (username, symbol, shares)
        VALUES (?, ?, ?)
        ON CONFLICT(username, symbol)
        DO UPDATE SET shares = excluded.shares
        """, (username, symbol, shares))

    db.commit()
    db.close()


# ------------------ MARKET DATA ------------------
def is_market_open():
    return True
def get_price(symbol):
    try:
        ticker = yf.Ticker(symbol)
        return float(ticker.fast_info["last_price"])
    except:
        return None

def get_market_prices(symbols):
    return {s: get_price(s) for s in symbols if get_price(s)}

def get_history(symbol, days=30):
    stock = yf.Ticker(symbol)
    data = stock.history(period=f"{days}d")
    return {
        "dates": data.index.strftime("%Y-%m-%d").tolist(),
        "prices": data["Close"].round(2).tolist()
    }
def calculate_portfolio_value(stocks):
    total_value = 0
    breakdown = {}

    for symbol, shares in stocks.items():
        price = get_price(symbol)
        if price:
            value = price * shares
            breakdown[symbol] = {
                "shares": shares,
                "price": round(price, 2),
                "value": round(value, 2)
            }
            total_value += value

    return round(total_value, 2), breakdown
def validate_order(action, symbol, shares, price, cash, stocks, market_open):
    if not market_open:
        return "Market is closed."

    if not symbol.isalpha():
        return "Invalid stock symbol."

    if shares <= 0:
        return "Shares must be greater than zero."

    if price is None:
        return "Stock symbol not found."

    if action == "buy":
        if price * shares > cash:
            return "Insufficient cash."

    if action == "sell":
        if stocks.get(symbol, 0) < shares:
            return "Insufficient shares to sell."

    return None
def get_stock_history(symbol, period):
    ticker = yf.Ticker(symbol)
    return ticker.history(period=period)


def get_stock_news(symbol):
    try:
        ticker = yf.Ticker(symbol)
        return ticker.news[:5]
    except:
        return []

# ------------------ ROUTES ------------------
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"].strip().lower()
        password = request.form["password"]

        user = get_user(username)

        if not user:
            return "Invalid username or password"

        stored_hash = user[1]

        if not check_password_hash(stored_hash, password):
            return "Invalid username or password"

        session["user"] = username
        return redirect(url_for("trade"))

    return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"].strip().lower()
        password = request.form["password"]

        if not username or not password:
            return "Missing username or password"

        if get_user(username):
            return "User already exists"

        create_user(username, password)
        session["user"] = username
        return redirect(url_for("trade"))

    return render_template("register.html")

@app.route("/market")

def market():
    symbols = [
        "AAPL", "MSFT", "NVDA", "TSLA", "AMZN",
        "META", "GOOGL", "AMD", "NFLX", "DIS"
    ]
    prices = get_market_prices(symbols)
    return render_template("market.html", prices=prices)

@app.route("/trade", methods=["GET", "POST"])
def trade():
    username = session["user"]
    cash = get_user(username)
    stocks = get_portfolio(username)

    market_open = is_market_open()
    error = None

    if request.method == "POST":
        symbol = request.form["symbol"].upper().strip()
        action = request.form["action"]

        try:
            shares = int(request.form["shares"])
        except:
            shares = 0

        price = get_price(symbol)
        error = validate_order(action, symbol, shares, price, cash, stocks, market_open)

        if not error:
            if action == "buy":
                cash -= price * shares
                stocks[symbol] = stocks.get(symbol, 0) + shares
            else:
                cash += price * shares
                stocks[symbol] -= shares
                if stocks[symbol] == 0:
                    del stocks[symbol]

            update_cash(username, cash)
            update_stock(username, symbol, stocks.get(symbol, 0))

            return redirect(url_for("trade"))

    portfolio = []
    portfolio_value = 0

    for symbol, shares in stocks.items():
        price = get_price(symbol)
        value = price * shares if price else 0
        portfolio_value += value
        portfolio.append({
            "symbol": symbol,
            "shares": shares,
            "price": round(price, 2),
            "value": round(value, 2)
        })

    total_value = round(cash + portfolio_value, 2)

    return render_template(
        "trade.html",
        cash=round(cash, 2),
        portfolio=portfolio,
        portfolio_value=round(portfolio_value, 2),
        total_value=total_value,
        market_open=market_open,
        error=error
    )



@app.route("/chart/<symbol>")
def chart(symbol):
    period = request.args.get("period", "1mo")
    ticker = yf.Ticker(symbol)
    data = ticker.history(period=period)
    news = get_stock_news(symbol)

    return render_template(
        "chart.html",
        symbol=symbol.upper(),
        dates=list(data.index.strftime("%Y-%m-%d")),
        prices=list(data["Close"]),
        period=period,
        news=news
    )
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

