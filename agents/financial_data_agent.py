"""
Financial Data Agent for Investment Strategy Advisor
This module provides an agent that utilizes the Alpha Vantage API
to evaluate company performance and find missing financial data
when choosing the final portfolio composition.
"""

import os
import json
import logging
import requests
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import autogen
from autogen import AssistantAgent, UserProxyAgent

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


class FinancialDataTool:
    """Tools for financial data retrieval and analysis using Alpha Vantage API."""
    
    def __init__(self):
        self.client = AlphaVantageClient()
        
    def get_stock_price(self, symbol: str) -> Dict[str, Any]:
        """Get current stock price for a symbol."""
        return self.client.get_stock_price(symbol)
    
    def get_performance_metrics(self, symbol: str) -> Dict[str, Any]:
        """Get performance metrics for a symbol over multiple time periods."""
        return self.client.get_performance_metrics(symbol)
    
    def get_etf_overview(self, symbol: str) -> Dict[str, Any]:
        """Get overview information for an ETF."""
        return self.client.get_etf_overview(symbol)
    
    def get_sector_performance(self) -> Dict[str, Any]:
        """Get performance of major market sectors."""
        return self.client.get_sector_performance()
    
    def analyze_etf_for_investment(self, symbol: str, risk_tolerance: str) -> Dict[str, Any]:
        """Analyze an ETF for investment suitability based on performance and risk tolerance."""
        return self.client.analyze_etf_for_investment(symbol, risk_tolerance)
    
    def evaluate_portfolio_symbols(self, symbols: List[str], risk_tolerance: str) -> Dict[str, Any]:
        """
        Evaluate a list of investment symbols for inclusion in a portfolio.
        
        Args:
            symbols: List of stock/ETF symbols to evaluate
            risk_tolerance: "low", "medium", or "high"
            
        Returns:
            Dict with evaluations for each symbol and overall portfolio metrics
        """
        results = {}
        valid_symbols = []
        total_volatility = 0
        matched_risk_count = 0
        
        # Analyze each symbol
        for symbol in symbols:
            analysis = self.analyze_etf_for_investment(symbol, risk_tolerance)
            results[symbol] = analysis
            
            # Track statistics for valid symbols
            if "error" not in analysis:
                valid_symbols.append(symbol)
                total_volatility += analysis.get("volatility", 0)
                if analysis.get("risk_match", False):
                    matched_risk_count += 1
        
        # Calculate overall portfolio metrics
        portfolio_metrics = {
            "total_symbols": len(symbols),
            "valid_symbols": len(valid_symbols),
            "avg_volatility": round(total_volatility / len(valid_symbols), 2) if valid_symbols else 0,
            "risk_match_percentage": round((matched_risk_count / len(valid_symbols)) * 100, 2) if valid_symbols else 0,
            "diversification_score": min(10, len(valid_symbols)) if valid_symbols else 0
        }
        
        return {
            "symbol_evaluations": results,
            "portfolio_metrics": portfolio_metrics
        }
    
    def find_alternative_investments(self, 
                                    symbol: str, 
                                    risk_tolerance: str, 
                                    count: int = 3) -> List[Dict[str, Any]]:
        """
        Find alternative investments similar to the given symbol but better matching risk tolerance.
        
        This is a simplified implementation that would normally use more sophisticated
        matching algorithms and a larger database of alternatives.
        
        Args:
            symbol: The reference symbol to find alternatives for
            risk_tolerance: "low", "medium", or "high"
            count: Number of alternatives to return
            
        Returns:
            List of alternative investment options
        """
        # Map of alternative ETFs to consider based on risk tolerance
        # In a real implementation, this would use a database or API call
        alternatives_map = {
            "low": ["BND", "VTIP", "VGSH", "VMBS", "MUB"],
            "medium": ["VTI", "VOO", "VIG", "IJH", "VXUS"],
            "high": ["VGT", "VB", "VWO", "ARKK", "QQQ"]
        }
        
        # Get alternatives based on risk tolerance
        possible_alternatives = alternatives_map.get(risk_tolerance, ["VTI", "BND", "VXUS"])
        
        # Remove the reference symbol if it's in the list
        if symbol in possible_alternatives:
            possible_alternatives.remove(symbol)
        
        results = []
        
        # Analyze each alternative
        for alt_symbol in possible_alternatives[:count]:
            analysis = self.analyze_etf_for_investment(alt_symbol, risk_tolerance)
            if "error" not in analysis:
                results.append({
                    "symbol": alt_symbol,
                    "analysis": analysis
                })
            
            # Stop when we have enough alternatives
            if len(results) >= count:
                break
                
        return results
    
    def get_portfolio_diversification_recommendations(self, 
                                                     symbols: List[str], 
                                                     risk_tolerance: str) -> Dict[str, Any]:
        """
        Provide recommendations to improve portfolio diversification.
        
        Args:
            symbols: Current portfolio symbols
            risk_tolerance: "low", "medium", or "high"
            
        Returns:
            Recommendations for improving diversification
        """
        # Get sector performance to help with diversification recommendations
        sector_data = self.get_sector_performance()
        
        # Evaluate current portfolio
        portfolio_eval = self.evaluate_portfolio_symbols(symbols, risk_tolerance)
        
        # Map symbols to sectors (simplified implementation)
        # In a real implementation, this would use actual ETF holdings data
        sector_mapping = {
            "VTI": "US Stocks",
            "VOO": "US Stocks",
            "VGT": "Technology",
            "VHT": "Healthcare",
            "VFH": "Financials",
            "VNQ": "Real Estate",
            "BND": "US Bonds",
            "VXUS": "International Stocks",
            "VWO": "Emerging Markets",
            "BNDX": "International Bonds"
        }
        
        # Count sectors in portfolio
        sectors = {}
        missing_sectors = []
        for symbol in symbols:
            sector = sector_mapping.get(symbol, "Unknown")
            sectors[sector] = sectors.get(sector, 0) + 1
        
        # Identify missing or underrepresented sectors
        key_sectors = ["US Stocks", "International Stocks", "US Bonds", "Real Estate"]
        for sector in key_sectors:
            if sector not in sectors:
                missing_sectors.append(sector)
        
        # Generate recommendations based on missing sectors and risk tolerance
        recommendations = {
            "missing_sectors": missing_sectors,
            "sector_allocation": sectors,
            "suggested_additions": []
        }
        
        # Simplified recommendations based on risk tolerance and missing sectors
        # In a real implementation, this would be more sophisticated
        for sector in missing_sectors:
            if sector == "US Stocks":
                recommendations["suggested_additions"].append({
                    "sector": sector,
                    "symbol": "VTI" if risk_tolerance != "low" else "VIG",
                    "rationale": "Provides broad US market exposure"
                })
            elif sector == "International Stocks":
                recommendations["suggested_additions"].append({
                    "sector": sector,
                    "symbol": "VXUS",
                    "rationale": "Adds international diversification"
                })
            elif sector == "US Bonds":
                recommendations["suggested_additions"].append({
                    "sector": sector,
                    "symbol": "BND",
                    "rationale": "Adds stability and income"
                })
            elif sector == "Real Estate":
                recommendations["suggested_additions"].append({
                    "sector": sector,
                    "symbol": "VNQ",
                    "rationale": "Provides exposure to real estate sector"
                })
        
        # Add information from sector performance if available
        if "sectors" in sector_data and not isinstance(sector_data["sectors"], str):
            top_sectors = []
            for sector, performance in sector_data["sectors"].items():
                # Extract percentage value from string like "+1.45%"
                try:
                    perf_value = float(performance.strip("%").strip("+"))
                    top_sectors.append((sector, perf_value))
                except:
                    continue
            
            # Sort by performance (descending)
            top_sectors.sort(key=lambda x: x[1], reverse=True)
            
            # Add top performing sectors to recommendations
            recommendations["top_performing_sectors"] = [
                {"sector": sector, "performance": f"{perf}%"} 
                for sector, perf in top_sectors[:3]
            ]
        
        return recommendations


def get_financial_data_agent(config_list):
    """Create a financial data agent that uses Alpha Vantage API."""
    
    # Create the financial data tools
    financial_tools = FinancialDataTool()
    
    # Create the financial data agent
    financial_agent = AssistantAgent(
        name="FinancialDataAgent",
        llm_config={
            "config_list": config_list,
            "temperature": 0.1
        },
        system_message="""You are a financial data specialist responsible for evaluating investments and providing 
        market data analysis. You have access to real-time financial data through the Alpha Vantage API.
        
        Your responsibilities include:
        1. Retrieving and analyzing current market data
        2. Evaluating investment options based on performance metrics
        3. Finding alternative investments that better match risk profiles
        4. Providing recommendations for portfolio diversification
        5. Filling in missing financial data for investment recommendations
        
        When evaluating investment options:
        - Consider performance over multiple time periods (1mo, 3mo, 6mo, 1yr)
        - Assess volatility and risk scores
        - Compare against sector performance
        - Evaluate alignment with user's risk tolerance
        
        Provide your analysis in a clear, structured format with specific data points to support your recommendations.
        Format your response as a JSON object when appropriate to ensure it can be easily processed by other agents.
        """
    )
    
    # Create a user proxy agent that will execute the financial tool functions
    user_proxy = UserProxyAgent(
        name="FinancialToolsExecutor",
        human_input_mode="NEVER",
        code_execution_config={"use_docker": False},
        function_map={
            "get_stock_price": financial_tools.get_stock_price,
            "get_performance_metrics": financial_tools.get_performance_metrics,
            "get_etf_overview": financial_tools.get_etf_overview,
            "get_sector_performance": financial_tools.get_sector_performance,
            "analyze_etf_for_investment": financial_tools.analyze_etf_for_investment,
            "evaluate_portfolio_symbols": financial_tools.evaluate_portfolio_symbols,
            "find_alternative_investments": financial_tools.find_alternative_investments,
            "get_portfolio_diversification_recommendations": financial_tools.get_portfolio_diversification_recommendations
        }
    )
    
    return financial_agent, user_proxy


# Function to simulate financial data since Alpha Vantage API key might not be available
def get_simulated_financial_data():
    """Get simulated financial data for testing purposes."""
    return {
        "sector_performance": {
            "technology": {
                "1mo_return": 0.05,
                "3mo_return": 0.12,
                "6mo_return": 0.20,
                "1yr_return": 0.30
            },
            "healthcare": {
                "1mo_return": 0.03,
                "3mo_return": 0.08,
                "6mo_return": 0.15,
                "1yr_return": 0.25
            },
            "consumer_discretionary": {
                "1mo_return": 0.02,
                "3mo_return": 0.06,
                "6mo_return": 0.18,
                "1yr_return": 0.28
            }
        },
        "symbol_data": {
            "VTI": {
                "1mo_return": 0.03,
                "3mo_return": 0.09,
                "6mo_return": 0.17,
                "1yr_return": 0.27,
                "volatility": 0.12,
                "risk_score": 3
            },
            "VXUS": {
                "1mo_return": 0.01,
                "3mo_return": 0.05,
                "6mo_return": 0.12,
                "1yr_return": 0.22,
                "volatility": 0.15,
                "risk_score": 4
            },
            "BND": {
                "1mo_return": 0.02,
                "3mo_return": 0.04,
                "6mo_return": 0.08,
                "1yr_return": 0.15,
                "volatility": 0.05,
                "risk_score": 2
            }
        },
        "market_insights": {
            "VTI": {
                "alignment_with_goal": "Good",
                "alignment_with_risk_tolerance": "Good",
                "recommendation": "Consider for long-term retirement portfolio due to consistent performance and moderate risk."
            },
            "VXUS": {
                "alignment_with_goal": "Fair",
                "alignment_with_risk_tolerance": "Fair",
                "recommendation": "May be suitable for diversification in a long-term portfolio, but higher volatility may require monitoring."
            },
            "BND": {
                "alignment_with_goal": "Fair",
                "alignment_with_risk_tolerance": "Excellent",
                "recommendation": "Consider for stability and lower risk exposure in a retirement portfolio."
            }
        }
    }


def analyze_investment_options(config_list, symbols, risk_tolerance):
    """
    Analyze investment options using the financial data agent.
    
    Args:
        config_list: Configuration for the LLM
        symbols: List of investment symbols to analyze
        risk_tolerance: Risk tolerance level ("low", "medium", "high")
        
    Returns:
        Analysis results
    """
    # Check if API key is available, if not use simulated data
    if not os.getenv("STOCK_API_KEY"):
        logger.info("STOCK_API_KEY not set. Using simulated data.")
        simulated_data = get_simulated_financial_data()
        return {
            "analysis": """Based on the simulated data, VTI (Vanguard Total Stock Market ETF) has a 1-year return of 27%
            with moderate volatility, making it suitable for medium risk tolerance. VXUS (Vanguard Total International
            Stock ETF) has a 1-year return of 22% with higher volatility, requiring more monitoring. BND (Vanguard
            Total Bond ETF) offers stability with a 1-year return of 15% and low volatility, suitable for lower risk
            exposure in a diversified portfolio.""",
            "simulated_data": simulated_data
        }
    
    financial_agent, tools_executor = get_financial_data_agent(config_list)
    
    # Initialize chat with a clear termination condition
    message = f"""Please analyze the following investment symbols: {', '.join(symbols)}
    
    The user's risk tolerance is: {risk_tolerance}
    
    Please:
    1. Evaluate each symbol individually
    2. Provide an overall assessment of the portfolio
    3. Suggest improvements for diversification
    4. Find alternatives for any investments that don't align with the risk profile
    
    Use the financial tools available to perform this analysis.
    
    IMPORTANT: Provide your complete analysis in a single response and then stop.
    """
    
    # Set up a conversation with a single response expected
    tools_executor.initiate_chat(
        financial_agent,
        message=message,
        max_turns=2  # Limit to a single turn to prevent infinite loop
    )
    
    # Extract the analysis from the last message
    analysis_message = financial_agent.last_message()["content"]
    
    # Extract any JSON content from the message
    try:
        json_start = analysis_message.find('{')
        json_end = analysis_message.rfind('}') + 1
        
        if json_start >= 0 and json_end > json_start:
            analysis = json.loads(analysis_message[json_start:json_end])
            return analysis
        else:
            # Return the full message if no JSON was found
            return {"analysis": analysis_message}
    except Exception as e:
        logger.error(f"Error extracting analysis: {e}")
        return {"analysis": analysis_message, "error": str(e)}


def get_market_data_for_strategy(config_list, structured_goal):
    """
    Retrieve relevant market data for investment strategy based on user goals.
    
    Args:
        config_list: Configuration for the LLM
        structured_goal: Structured goal from the GoalCreatorAgent
        
    Returns:
        Market data relevant to the strategy
    """
    # Check if API key is available, if not use simulated data
    if not os.getenv("STOCK_API_KEY"):
        logger.info("STOCK_API_KEY not set. Using simulated data.")
        simulated_data = get_simulated_financial_data()
        # Format the simulated data into a readable string
        analysis = f"""
        Based on simulated data, the market shows technology sector leading with 30% annual return,
        followed by consumer discretionary (28%) and healthcare (25%).
        
        For a {structured_goal.get('risk_tolerance', 'medium')} risk profile with
        a {structured_goal.get('investment_horizon', 'medium-term')} horizon aiming for 
        {structured_goal.get('goal_type', 'general investing')}, the following ETFs are analyzed:
        
        - VTI: 27% 1-yr return, risk score 3/10, good alignment with medium risk tolerance
        - VXUS: 22% 1-yr return, risk score 4/10, fair alignment with medium risk tolerance, requires monitoring
        - BND: 15% 1-yr return, risk score 2/10, excellent for stability in a portfolio
        """
        
        # Return the simulated data as market data
        return {
            "analysis": analysis,
            "symbols_analyzed": ["VTI", "VXUS", "BND"],
            "risk_tolerance": structured_goal.get('risk_tolerance', 'medium'),
            "simulated_data": True
        }
    
    financial_agent, tools_executor = get_financial_data_agent(config_list)
    
    risk_tolerance = structured_goal.get("risk_tolerance", "medium")
    investment_preferences = structured_goal.get("investment_preferences", [])
    
    # Convert investment preferences to symbols if needed
    symbols = []
    for pref in investment_preferences:
        if pref in ["ETF", "stocks", "bonds"]:
            # Add default symbols for each preference
            if pref == "ETF":
                symbols.extend(["VTI", "VXUS", "VGT"])
            elif pref == "stocks":
                symbols.extend(["VOO", "QQQ", "SPY"])
            elif pref == "bonds":
                symbols.extend(["BND", "BNDX", "AGG"])
        elif pref in ["VTI", "BND", "VXUS", "VOO", "VGT", "VYM"]:
            # Add specific ETFs mentioned
            symbols.append(pref)
    
    # Ensure we have at least some symbols to analyze
    if not symbols:
        symbols = ["VTI", "BND", "VXUS"]  # Default balanced portfolio
    
    # Deduplicate symbols
    symbols = list(set(symbols))
    
    # Initialize chat with a clear message and termination condition
    message = f"""Please provide current market data relevant to the user's investment strategy:
    
    User's goal type: {structured_goal.get('goal_type', 'general investing')}
    Investment horizon: {structured_goal.get('investment_horizon', 'medium-term')}
    Risk tolerance: {risk_tolerance}
    
    Specifically:
    1. Get current sector performance
    2. Analyze the following symbols relevant to their preferences: {', '.join(symbols)}
    3. Provide market insights relevant to their goal and risk tolerance
    
    Use the financial tools available to perform this analysis.
    
    IMPORTANT: Provide your complete analysis in a single response and then stop.
    """
    
    # Set up a conversation with a single response expected
    tools_executor.initiate_chat(
        financial_agent,
        message=message,
        max_turns=2  # Limit to a single turn to prevent infinite loop
    )
    
    # Return the market data
    market_data = {
        "analysis": financial_agent.last_message()["content"],
        "symbols_analyzed": symbols,
        "risk_tolerance": risk_tolerance
    }
    
    return market_data


def enhance_investment_recommendations(config_list, strategy, structured_goal):
    """
    Enhance investment recommendations with real-time financial data.
    
    Args:
        config_list: Configuration for the LLM
        strategy: The investment strategy from the VotingCoordinator
        structured_goal: The user's structured investment goal
        
    Returns:
        Enhanced strategy with current financial data
    """
    # Check if API key is available, if not use simulated data
    if not os.getenv("STOCK_API_KEY"):
        logger.info("STOCK_API_KEY not set. Using simulated data.")
        # Add simulated market data to the strategy
        enhanced_strategy = {**strategy}
        
        # Add current prices and performance to products
        if "products" in enhanced_strategy:
            for product in enhanced_strategy["products"]:
                symbol = product.get("name", "").split(" ")[0].strip() if "(" in product.get("name", "") else ""
                if symbol in ["VTI", "VXUS", "BND"]:
                    product["current_price"] = {
                        "VTI": "$257.83",
                        "VXUS": "$62.41",
                        "BND": "$74.56"
                    }.get(symbol)
                    product["performance"] = {
                        "VTI": "+18.2% (1yr)",
                        "VXUS": "+9.8% (1yr)",
                        "BND": "+1.2% (1yr)"
                    }.get(symbol)
        
        # Add market analysis
        enhanced_strategy["market_analysis"] = """
        Based on simulated market data, the technology sector is currently showing strong performance (+2.1% today),
        which supports allocations to broad market ETFs like VTI which have significant tech exposure.
        The current market environment aligns well with the recommended asset allocation.
        """
        
        return enhanced_strategy
    
    financial_agent, tools_executor = get_financial_data_agent(config_list)
    
    # Extract products from strategy
    products = strategy.get("products", [])
    
    # Extract symbols from products
    symbols = []
    for product in products:
        name = product.get("name", "")
        # Extract symbol from name, assuming format like "VTI (Vanguard Total Market)"
        if "(" in name:
            symbol = name.split("(")[0].strip()
            if len(symbol) <= 5:  # Most stock symbols are 5 or fewer characters
                symbols.append(symbol)
    
    # Fallback if no symbols found
    if not symbols:
        symbols = ["VTI", "BND", "VXUS"]
    
    risk_tolerance = structured_goal.get("risk_tolerance", "medium")
    
    # Initialize chat with a clear message and termination condition
    message = f"""Please enhance the following investment strategy with current financial data:
    
    Strategy: {json.dumps(strategy)}
    
    Specifically:
    1. Add current price and performance data for each product
    2. Evaluate if the allocation aligns with current market conditions
    3. Check if the products match the user's risk tolerance: {risk_tolerance}
    4. Suggest any specific adjustments based on current market data
    
    Use the financial tools available to perform this analysis.
    Return an enhanced version of the strategy JSON.
    
    IMPORTANT: Provide your complete analysis in a single response and then stop.
    """
    
    # Set up a conversation with a single response expected
    tools_executor.initiate_chat(
        financial_agent,
        message=message,
        max_turns=2  # Limit to a single turn to prevent infinite loop
    )
    
    # Extract the enhanced strategy from the last message
    enhanced_message = financial_agent.last_message()["content"]
    
    # Extract any JSON content from the message
    try:
        json_start = enhanced_message.find('{')
        json_end = enhanced_message.rfind('}') + 1
        
        if json_start >= 0 and json_end > json_start:
            enhanced_strategy = json.loads(enhanced_message[json_start:json_end])
            return enhanced_strategy
        else:
            # If no JSON found, return original strategy with the analysis
            return {
                **strategy,
                "financial_analysis": enhanced_message
            }
    except Exception as e:
        logger.error(f"Error extracting enhanced strategy: {e}")
        return {
            **strategy,
            "financial_analysis": enhanced_message,
            "error": str(e)
        }