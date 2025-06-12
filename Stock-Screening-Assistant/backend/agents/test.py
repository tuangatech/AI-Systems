import yfinance as yf

def print_stock_info(ticker_symbol: str):
    # Get the stock data
    stock = yf.Ticker(ticker_symbol)

    # print(f"Stock info {stock.info}\n")
    
    # Print basic info
    print(f"\n=== {ticker_symbol.upper()} Stock Information ===")
    print(f"Company Name: {stock.info.get('longName', 'N/A')}")
    print(f"Current Price: {stock.info.get('currentPrice', 'N/A')}")
    print(f"Market Cap: {stock.info.get('marketCap', 'N/A'):,}")
    print(f"Dividend Yield: {stock.info.get('dividendYield', 'N/A')}%")
    print(f"PE Ratio: {stock.info.get('trailingPE', 'N/A')}")
    print(f"Free Cash Flow: {stock.info.get('freeCashflow', 'N/A')}")
    
    # Print recent news headlines
    print("\nRecent News Headlines:")
    # print(stock.news[:2])
    for news in stock.news[:3]:  # Show top 3 news items
        print(f"- {news['content']['title']} ({news['content']['provider']['displayName']})")

# Example usage
print_stock_info("AAPL")  # Apple Inc.
# print_stock_info("MSFT")  # Microsoft