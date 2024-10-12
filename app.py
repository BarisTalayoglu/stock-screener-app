from flask import Flask, render_template, request, jsonify, redirect, url_for, send_file
from screener import StockScreener
from technicalAnalysis import create_stock_chart, create_rsi_chart, create_macd_chart, fetch_and_plot_stock_charts
import base64
from technicalAnalysis import fetch_technical_indicators
import yfinance as yf
from datetime import datetime

# API key
stock_screener = StockScreener(api_key='ADD_YOUR_NEWS_API_KEY')

app = Flask(__name__)


@app.route('/')
def stock_search():
    return render_template('stock_search.html')

@app.route('/stock-screener')
def index():
    return render_template('stock_screener.html')


@app.route('/run_screener', methods=['POST'])
def run_screener():
    try:
        # Fetch weights from the form
        relative_volume = float(request.form.get('relative_volume', 0))
        news_event = float(request.form.get('news_event', 0))
        price_movement = float(request.form.get('price_movement', 0))
        historical_volatility = float(request.form.get('historical_volatility', 0))
        available_shares = float(request.form.get('available_shares', 0))
        stock_universe = request.form['stock_universe']

        print(f"Inputs: {relative_volume}, {news_event}, {price_movement}, {historical_volatility}, {available_shares}, {stock_universe}")

        stock_screener.indicators = {
            'relative_volume': relative_volume / 100,
            'market_sentiment': news_event / 100,
            'historical_volatility': historical_volatility / 100,
            'price_movement': price_movement / 100,
            'available_shares': available_shares / 100,
        }

        # Fetch tickers from the file
        if stock_universe == "sp500":
            tickers = stock_screener.fetch_tickers_from_file('stock_data/sp500_all_tickers.txt')  # Load S&P 500 tickers
        else:
            tickers = stock_screener.fetch_tickers_from_file('stock_data/all_tickers.txt')  # Load all U.S. tickers

        stock_data = stock_screener.fetch_stock_data(tickers)

        ranked_stocks = stock_screener.rank_stocks(stock_data)

        results_with_sentiment = []

        for ticker, score in ranked_stocks[:10]:  # Get top 10 stocks (ticker, score)
            market_sentiment = stock_screener.get_market_sentiment(ticker)
            results_with_sentiment.append([ticker, score, market_sentiment])

        return render_template('stock_screener_results.html', stocks=results_with_sentiment)

    except Exception as e:
        print(f"Error in run_screener: {e}")
        return jsonify({"error": "An error occurred during stock screening. Please try again."}), 500


@app.route('/stock/<ticker>')
def stock_details(ticker):
    # Fetch the charts images in memory
    price_chart_image, rsi_chart_image, macd_chart_image, fibonacci_chart_image = fetch_and_plot_stock_charts(ticker)

    # Encode the images to base64
    price_chart_base64 = base64.b64encode(price_chart_image.getvalue()).decode('utf-8')
    rsi_chart_base64 = base64.b64encode(rsi_chart_image.getvalue()).decode('utf-8')
    macd_chart_base64 = base64.b64encode(macd_chart_image.getvalue()).decode('utf-8')
    fibonacci_chart_base64 = base64.b64encode(fibonacci_chart_image.getvalue()).decode('utf-8')

    technical_indicators, stock_details = fetch_technical_indicators(ticker)

    # Fetch additional stock metrics using yfinance
    stock_info = yf.Ticker(ticker)

    today = datetime.now().weekday()
    period = '5d' if today >= 5 else '1d'

    # Fetch historical data
    try:
        historical_data = stock_info.history(period=period)
        if historical_data.empty:
            current_price = "N/A"
            previous_close = "N/A"
            change_percent = "N/A"
        else:
            current_price = historical_data['Close'].iloc[-1]

            # Calculate previous close and change percent safely
            if len(historical_data) >= 2:
                previous_close = historical_data['Close'].iloc[-2]
                change_percent = ((current_price - previous_close) / previous_close) * 100
            else:
                previous_close = "N/A"
                change_percent = "N/A"
    except Exception as e:
        print(f"Error fetching historical data for {ticker}: {e}")
        current_price = "N/A"
        previous_close = "N/A"
        change_percent = "N/A"

    market_cap = stock_info.info.get('marketCap', 'N/A')
    pe_ratio = stock_info.info.get('trailingPE', 'N/A')
    dividend_yield = stock_info.info.get('dividendYield', 'N/A')
    volume = historical_data['Volume'].iloc[-1] if not historical_data.empty else "N/A"

    full_name = stock_details.get('full_name', "N/A")
    industry = stock_details.get('industry', "N/A")
    sector = stock_details.get('sector', "N/A")

    if technical_indicators is not None and not technical_indicators.empty:
        ichimoku_values = technical_indicators.iloc[-1]
        ichimoku_tenkan = ichimoku_values.get('tenkan_sen', "N/A")
        ichimoku_kijun = ichimoku_values.get('kijun_sen', "N/A")
        ichimoku_span_a = ichimoku_values.get('senkou_span_a', "N/A")
        ichimoku_span_b = ichimoku_values.get('senkou_span_b', "N/A")
        ichimoku_chikou = ichimoku_values.get('chikou_span', "N/A")
    else:
        ichimoku_tenkan = ichimoku_kijun = ichimoku_span_a = ichimoku_span_b = ichimoku_chikou = "N/A"

    daily_return = (current_price - technical_indicators['SMA'].iloc[-1]) / technical_indicators['SMA'].iloc[
        -1] * 100 if 'SMA' in technical_indicators.columns else "N/A"
    fifty_two_week_high = stock_info.info.get('fiftyTwoWeekHigh', 'N/A')
    fifty_two_week_low = stock_info.info.get('fiftyTwoWeekLow', 'N/A')
    beta = stock_info.info.get('beta', 'N/A')
    analyst_rating = stock_info.info.get('recommendationKey', 'N/A')

    if dividend_yield in ["N/A", ""]:
        dividend_yield = 0.0
    else:
        try:
            dividend_yield = float(dividend_yield)
        except ValueError:
            dividend_yield = 0.0

    return render_template(
        'stock_details.html',
        ticker=ticker,
        price_chart_image=price_chart_base64,
        rsi_chart_image=rsi_chart_base64,
        macd_chart_image=macd_chart_base64,
        fibonacci_chart_image=fibonacci_chart_base64,
        technical_indicators=technical_indicators,
        current_price=current_price,
        market_cap=market_cap,
        pe_ratio=pe_ratio,
        dividend_yield=dividend_yield,
        volume=volume,
        change_percent=change_percent,
        ichimoku_tenkan=ichimoku_tenkan,
        ichimoku_kijun=ichimoku_kijun,
        ichimoku_span_a=ichimoku_span_a,
        ichimoku_span_b=ichimoku_span_b,
        ichimoku_chikou=ichimoku_chikou,
        daily_return=daily_return,
        fifty_two_week_high=fifty_two_week_high,
        fifty_two_week_low=fifty_two_week_low,
        beta=beta,
        analyst_rating=analyst_rating,
        full_name=full_name,
        industry=industry,
        sector=sector
    )


if __name__ == '__main__':
    app.run(debug=True)
