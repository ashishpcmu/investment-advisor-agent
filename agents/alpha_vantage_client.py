"""
Alpha Vantage API Client for Investment Strategy Advisor
This module provides a client to interact with the Alpha Vantage API 
for retrieving real-time stock data and market insights
"""

import os
import json
import requests
from datetime import datetime, timedelta
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AlphaVantageClient:
    """Client for Alpha Vantage API to fetch stock data for investment decisions."""
    
    def __init__(self):
        self.api_key = os.getenv("STOCK_API_KEY")
        if not self.api_key:
            logger.warning("STOCK_API_KEY environment variable not set. Alpha Vantage API will not work.")
        self.base_url = "https://www.alphavantage.co/query"
        self.cache = {}  # Simple cache to avoid repeated API calls
        
    def get_stock_price(self, symbol):
        """Get the latest price for a stock symbol."""
        if not self.api_key:
            return {"error": "API key not set"}
            
        # Check cache first
        cache_key = f"price_{symbol}"
        if cache_key in self.cache:
            # Only use cache if it's less than 1 hour old
            if datetime.now() - self.cache[cache_key]["timestamp"] < timedelta(hours=1):
                return self.cache[cache_key]["data"]
        
        params = {
            "function": "GLOBAL_QUOTE",
            "symbol": symbol,
            "apikey": self.api_key
        }
        
        try:
            response = requests.get(self.base_url, params=params)
            data = response.json()
            
            if "Global Quote" not in data or not data["Global Quote"]:
                return {"error": f"No data found for symbol {symbol}"}
                
            result = {
                "symbol": symbol,
                "price": float(data["Global Quote"]["05. price"]),
                "change_percent": data["Global Quote"]["10. change percent"],
                "volume": int(data["Global Quote"]["06. volume"]),
                "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            # Update cache
            self.cache[cache_key] = {
                "timestamp": datetime.now(),
                "data": result
            }
            
            return result
        except Exception as e:
            logger.error(f"Error fetching stock price for {symbol}: {e}")
            return {"error": str(e)}
    
    def get_performance_metrics(self, symbol):
        """Get performance metrics for a stock symbol (1mo, 3mo, 6mo, 1yr returns)."""
        if not self.api_key:
            return {"error": "API key not set"}
            
        # Check cache first
        cache_key = f"metrics_{symbol}"
        if cache_key in self.cache:
            # Only use cache if it's less than 6 hours old
            if datetime.now() - self.cache[cache_key]["timestamp"] < timedelta(hours=6):
                return self.cache[cache_key]["data"]
        
        params = {
            "function": "TIME_SERIES_DAILY",
            "symbol": symbol,
            "outputsize": "full",
            "apikey": self.api_key
        }
        
        try:
            response = requests.get(self.base_url, params=params)
            data = response.json()
            
            if "Time Series (Daily)" not in data or not data["Time Series (Daily)"]:
                return {"error": f"No data found for symbol {symbol}"}
            
            time_series = data["Time Series (Daily)"]
            dates = sorted(time_series.keys(), reverse=True)
            
            # Get current price
            current_price = float(time_series[dates[0]]["4. close"])
            
            # Calculate performance for different time periods
            metrics = {
                "symbol": symbol,
                "current_price": current_price,
                "performance": {}
            }
            
            # Define time periods to calculate
            periods = {
                "1mo": 30,
                "3mo": 90,
                "6mo": 180,
                "1yr": 365
            }
            
            for period_name, days in periods.items():
                # Find the closest date to our target period
                target_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
                closest_date = min(dates, key=lambda x: abs((datetime.strptime(x, "%Y-%m-%d") - datetime.strptime(target_date, "%Y-%m-%d")).days))
                
                # Only use if it's within 7 days of our target
                if abs((datetime.strptime(closest_date, "%Y-%m-%d") - datetime.strptime(target_date, "%Y-%m-%d")).days) <= 7:
                    past_price = float(time_series[closest_date]["4. close"])
                    percent_change = ((current_price - past_price) / past_price) * 100
                    metrics["performance"][period_name] = {
                        "price_change_percent": round(percent_change, 2),
                        "reference_date": closest_date
                    }
                else:
                    metrics["performance"][period_name] = {
                        "error": f"No data available within 7 days of target date"
                    }
            
            # Update cache
            self.cache[cache_key] = {
                "timestamp": datetime.now(),
                "data": metrics
            }
            
            return metrics
        except Exception as e:
            logger.error(f"Error fetching performance metrics for {symbol}: {e}")
            return {"error": str(e)}
    
    def get_etf_overview(self, symbol):
        """Get overview information for an ETF."""
        if not self.api_key:
            return {"error": "API key not set"}
            
        # Check cache first
        cache_key = f"overview_{symbol}"
        if cache_key in self.cache:
            # Use cache if it's less than 24 hours old since this data doesn't change often
            if datetime.now() - self.cache[cache_key]["timestamp"] < timedelta(hours=24):
                return self.cache[cache_key]["data"]
        
        params = {
            "function": "OVERVIEW",
            "symbol": symbol,
            "apikey": self.api_key
        }
        
        try:
            response = requests.get(self.base_url, params=params)
            data = response.json()
            
            if not data or "Error Message" in data:
                return {"error": f"No overview data found for symbol {symbol}"}
                
            # Extract relevant fields for ETFs
            result = {
                "symbol": symbol,
                "name": data.get("Name", "Unknown"),
                "description": data.get("Description", "No description available"),
                "sector": data.get("Sector", "Various"),
                "pe_ratio": data.get("PERatio", "N/A"),
                "dividend_yield": data.get("DividendYield", "N/A"),
                "market_cap": data.get("MarketCapitalization", "N/A"),
                "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            # Update cache
            self.cache[cache_key] = {
                "timestamp": datetime.now(),
                "data": result
            }
            
            return result
        except Exception as e:
            logger.error(f"Error fetching ETF overview for {symbol}: {e}")
            return {"error": str(e)}
    
    def get_sector_performance(self):
        """Get performance of major market sectors."""
        if not self.api_key:
            return {"error": "API key not set"}
            
        # Check cache first
        cache_key = "sector_performance"
        if cache_key in self.cache:
            # Only use cache if it's less than 6 hours old
            if datetime.now() - self.cache[cache_key]["timestamp"] < timedelta(hours=6):
                return self.cache[cache_key]["data"]
        
        params = {
            "function": "SECTOR",
            "apikey": self.api_key
        }
        
        try:
            response = requests.get(self.base_url, params=params)
            data = response.json()
            
            if "Rank A: Real-Time Performance" not in data:
                return {"error": "No sector performance data available"}
                
            # Extract real-time sector performance
            sectors = data["Rank A: Real-Time Performance"]
            result = {
                "sectors": sectors,
                "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            # Update cache
            self.cache[cache_key] = {
                "timestamp": datetime.now(),
                "data": result
            }
            
            return result
        except Exception as e:
            logger.error(f"Error fetching sector performance: {e}")
            return {"error": str(e)}
    
    def analyze_etf_for_investment(self, symbol, risk_tolerance):
        """
        Analyze an ETF for investment suitability based on performance and risk tolerance.
        
        Args:
            symbol: The ETF symbol
            risk_tolerance: "low", "medium", or "high"
            
        Returns:
            Analysis dict with risk score, performance metrics, and recommendation
        """
        # Get performance data
        metrics = self.get_performance_metrics(symbol)
        price_data = self.get_stock_price(symbol)
        
        if "error" in metrics or "error" in price_data:
            return {
                "symbol": symbol,
                "error": metrics.get("error") or price_data.get("error")
            }
        
        # Calculate volatility (simple measure based on max performance swing)
        performances = [v["price_change_percent"] for k, v in metrics["performance"].items() 
                        if "price_change_percent" in v]
        
        if not performances:
            return {
                "symbol": symbol,
                "error": "Insufficient performance data"
            }
        
        volatility = max(performances) - min(performances)
        
        # Assign risk score (1-10)
        risk_score = min(10, max(1, round(volatility / 5)))
        
        # Determine if ETF matches risk tolerance
        risk_match = False
        if risk_tolerance == "low" and risk_score <= 4:
            risk_match = True
        elif risk_tolerance == "medium" and risk_score > 3 and risk_score <= 7:
            risk_match = True
        elif risk_tolerance == "high" and risk_score > 6:
            risk_match = True
        
        # Create analysis
        analysis = {
            "symbol": symbol,
            "current_price": price_data["price"],
            "performance": metrics["performance"],
            "risk_score": risk_score,
            "volatility": round(volatility, 2),
            "risk_match": risk_match,
            "recommendation": "hold"
        }
        
        # Add simple recommendation
        yearly_performance = metrics["performance"].get("1yr", {}).get("price_change_percent")
        if yearly_performance:
            if yearly_performance > 15 and risk_match:
                analysis["recommendation"] = "buy"
            elif yearly_performance < -10:
                analysis["recommendation"] = "avoid"
        
        return analysis