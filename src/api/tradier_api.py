import requests
import pandas as pd
from concurrent.futures import ThreadPoolExecutor
import time
from typing import Optional, List, Literal
import logging

logger = logging.getLogger('gex_collector')

BASE_URL = 'https://api.tradier.com/'


class TradierAPI:
    """Production-ready Tradier API client with error handling and logging"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.headers = {
            'Accept': 'application/json',
            'Authorization': f'Bearer {api_key}',
        }
    
    def _fetch_url(self, url: str, params: Optional[dict] = None, max_retries: int = 3, sleep: float = 2):
        """Fetch URL with retry logic and error handling"""
        attempts = 0
        while attempts < max_retries:
            try:
                response = requests.get(url, params=params, headers=self.headers, timeout=30)
                response.raise_for_status()
                return response
            except requests.RequestException as e:
                attempts += 1
                logger.warning(f"Request attempt {attempts} failed: {str(e)}")
                if attempts < max_retries:
                    logger.info(f"Retrying in {sleep} seconds...")
                    time.sleep(sleep)
                else:
                    logger.error(f"Max retries ({max_retries}) exceeded for {url}")
                    raise
    
    def _handle_api_response(self, response, symbol: str, data_type: str):
        """Handle API response and log rate limit information"""
        if response.status_code != 200:
            logger.error(f"{symbol} {data_type} not received - Status: {response.status_code}")
            logger.error(f"Response: {response.text}")
            
            # Log rate limit info if available
            rate_limit_available = response.headers.get('X-Ratelimit-Available')
            rate_limit_expiry = response.headers.get('X-Ratelimit-Expiry')
            
            if rate_limit_available:
                logger.warning(f"Rate limit available: {rate_limit_available}")
            if rate_limit_expiry:
                reset_time = int(rate_limit_expiry) / 1000 - int(time.time())
                logger.warning(f"Rate limit resets in: {reset_time:.0f}s")
        
        return response
    
    def get_intraday_data(self, symbol: str, interval: str = '30min', days_back: int = 5) -> pd.DataFrame:
        """Get intraday data for a symbol (15min, 30min, 1hour intervals)"""
        endpoint = 'v1/markets/timesales'
        
        # Calculate start time (days_back from now)
        from datetime import datetime, timedelta
        end_time = datetime.now()
        start_time = end_time - timedelta(days=days_back)
        
        params = {
            'symbol': symbol.upper(),
            'interval': interval,
            'start': start_time.strftime('%Y-%m-%d %H:%M'),
            'end': end_time.strftime('%Y-%m-%d %H:%M'),
            'session_filter': 'open'  # Only trading hours
        }
        
        try:
            response = self._fetch_url(BASE_URL + endpoint, params)
            self._handle_api_response(response, symbol, f'intraday {interval} data')
            
            if response.status_code == 200:
                json_response = response.json()
                data = json_response.get('series', {})
                data = data if data is not None else {}
                data = data.get('data', [])
                
                if len(data) > 0:
                    df = pd.DataFrame(data)
                    # Convert timestamp to datetime
                    df['time'] = pd.to_datetime(df['time'])
                    df['symbol'] = symbol.upper()
                    
                    # Rename columns to match standard OHLCV format
                    column_mapping = {
                        'time': 'datetime',
                        'open': 'open',
                        'high': 'high', 
                        'low': 'low',
                        'close': 'close',
                        'volume': 'volume'
                    }
                    
                    df = df.rename(columns=column_mapping)
                    df = df.sort_values('datetime').reset_index(drop=True)
                    
                    logger.info(f"Retrieved {len(df)} {interval} bars for {symbol}")
                    return df
        
        except Exception as e:
            logger.error(f"Error fetching intraday data for {symbol}: {str(e)}")
        
        return pd.DataFrame()
    
    def get_historical_quote(self, symbol: str, start_date: str, end_date: str, 
                           resolution: Literal['daily', 'weekly', 'monthly'] = 'daily') -> pd.DataFrame:
        """Get historical quotes for a symbol"""
        endpoint = 'v1/markets/history'
        symbol = symbol.upper()
        columns = ['date', 'symbol', 'open', 'high', 'low', 'close', 'volume']

        params = {
            'symbol': symbol,
            'interval': resolution,
            'start': start_date,
            'end': end_date,
            'session_filter': 'all',
        }
        
        try:
            response = self._fetch_url(BASE_URL + endpoint, params)
            self._handle_api_response(response, symbol, 'historical data')
            
            if response.status_code == 200:
                json_response = response.json()
                history = json_response.get('history', {})
                history = history if history is not None else {}
                data = history.get('day', [])
                data = data if isinstance(data, list) else [data]
                
                if len(data) > 0:
                    df = pd.DataFrame(data)
                    df['date'] = pd.to_datetime(df['date']).dt.date
                    df['symbol'] = symbol
                    logger.info(f"Retrieved {len(df)} historical records for {symbol}")
                    return df[columns]
        
        except Exception as e:
            logger.error(f"Error fetching historical data for {symbol}: {str(e)}")
        
        return pd.DataFrame(columns=columns)

    def get_historical_quotes(self, symbols: List[str], start_date: str, end_date: str, 
                            resolution: Literal['daily', 'weekly', 'monthly'] = 'daily') -> pd.DataFrame:
        """Get historical quotes for multiple symbols using threading"""
        logger.info(f"Fetching historical data for {len(symbols)} symbols")
        
        with ThreadPoolExecutor(max_workers=5) as executor:
            results = list(executor.map(
                lambda symbol: self.get_historical_quote(symbol, start_date, end_date, resolution), 
                symbols
            ))
        
        results = [df for df in results if not df.empty]
        if results:
            df = pd.concat(results, ignore_index=True)
            logger.info(f"Combined {len(df)} total historical records")
            return df.sort_values(by=['symbol', 'date']).reset_index(drop=True)
        
        return pd.DataFrame()

    def get_current_quote(self, symbol: str) -> pd.DataFrame:
        """Get current quote for a single symbol (optimized for SPX)"""
        return self.get_latest_quotes([symbol], greeks=False)
    
    def get_latest_quotes(self, symbols: List[str], greeks: bool = False) -> pd.DataFrame:
        """Get latest quotes for symbols"""
        endpoint = 'v1/markets/quotes'
        columns = ['symbol', 'description', 'exch', 'type', 'last', 'change', 'volume', 
                  'open', 'high', 'low', 'close', 'bid', 'ask', 'change_percentage', 
                  'average_volume', 'last_volume', 'trade_date', 'prevclose', 
                  'week_52_high', 'week_52_low', 'bidsize', 'bidexch', 'bid_date', 
                  'asksize', 'askexch', 'ask_date', 'root_symbols']
        
        if greeks:
            columns += ['greeks.delta', 'greeks.gamma', 'greeks.theta', 'greeks.vega', 
                       'greeks.rho', 'greeks.phi', 'greeks.bid_iv', 'greeks.mid_iv', 
                       'greeks.ask_iv', 'greeks.smv_vol', 'greeks.updated_at']
        
        syms = ','.join([s.upper() for s in symbols])
        params = {
            'symbols': syms,
            'greeks': greeks,
        }
        
        try:
            response = self._fetch_url(BASE_URL + endpoint, params)
            self._handle_api_response(response, syms, 'quotes')
            
            if response.status_code == 200:
                json_response = response.json()
                quotes = json_response.get('quotes', {})
                quotes = quotes if quotes is not None else {}
                data = quotes.get('quote', [])
                data = data if isinstance(data, list) else [data]
                
                if len(data) > 0:
                    df = pd.json_normalize(data)
                    df['trade_date'] = pd.to_datetime(df['trade_date'], unit='ms')
                    df['bid_date'] = pd.to_datetime(df['bid_date'], unit='ms')
                    df['ask_date'] = pd.to_datetime(df['ask_date'], unit='ms')
                    logger.info(f"Retrieved quotes for {len(df)} symbols")
                    return df[columns]
        
        except Exception as e:
            logger.error(f"Error fetching quotes for {syms}: {str(e)}")
        
        return pd.DataFrame(columns=columns)

    def get_chains(self, symbol: str, expiration: str, greeks: bool = True) -> pd.DataFrame:
        """Get option chain for a symbol and expiration date"""
        endpoint = 'v1/markets/options/chains'
        params = {
            'symbol': symbol.upper(),
            'expiration': expiration,
            'greeks': greeks,
        }
        
        try:
            response = self._fetch_url(BASE_URL + endpoint, params)
            self._handle_api_response(response, symbol, f'option chain for {expiration}')
            
            if response.status_code == 200:
                json_response = response.json()
                chains = json_response.get('options', {})
                chains = chains if chains is not None else {}
                data = chains.get('option', [])
                data = data if isinstance(data, list) else [data]
                
                if len(data) > 0:
                    df = pd.json_normalize(data)
                    df['trade_date'] = pd.to_datetime(df['trade_date'], unit='ms')
                    df['bid_date'] = pd.to_datetime(df['bid_date'], unit='ms')
                    df['ask_date'] = pd.to_datetime(df['ask_date'], unit='ms')
                    df['greeks.updated_at'] = pd.to_datetime(df['greeks.updated_at'])
                    logger.info(f"Retrieved {len(df)} option contracts for {symbol} {expiration}")
                    return df
        
        except Exception as e:
            logger.error(f"Error fetching option chain for {symbol} {expiration}: {str(e)}")
        
        # Return empty DataFrame with expected columns
        columns = ['symbol', 'description', 'exch', 'type', 'last', 'change', 'volume', 
                  'open', 'high', 'low', 'close', 'bid', 'ask', 'underlying', 'strike', 
                  'change_percentage', 'average_volume', 'last_volume', 'trade_date', 
                  'prevclose', 'week_52_high', 'week_52_low', 'bidsize', 'bidexch', 
                  'bid_date', 'asksize', 'askexch', 'ask_date', 'open_interest', 
                  'contract_size', 'expiration_date', 'expiration_type', 'option_type', 
                  'root_symbol', 'greeks.delta', 'greeks.gamma', 'greeks.theta', 
                  'greeks.vega', 'greeks.rho', 'greeks.phi', 'greeks.bid_iv', 
                  'greeks.mid_iv', 'greeks.ask_iv', 'greeks.smv_vol', 'greeks.updated_at']
        
        return pd.DataFrame(columns=columns)

    def get_strikes(self, symbol: str, expiration: str) -> List[float]:
        """Get available strikes for a symbol and expiration date"""
        endpoint = 'v1/markets/options/strikes'
        params = {
            'symbol': symbol.upper(),
            'expiration': expiration,
        }
        
        try:
            response = self._fetch_url(BASE_URL + endpoint, params)
            self._handle_api_response(response, symbol, f'strikes for {expiration}')
            
            if response.status_code == 200:
                json_response = response.json()
                data = json_response.get('strikes', {})
                data = data if data is not None else {}
                data = data.get('strike', [])
                data = data if isinstance(data, list) else [data]
                
                if len(data) > 0:
                    logger.info(f"Retrieved {len(data)} strikes for {symbol} {expiration}")
                    return data
        
        except Exception as e:
            logger.error(f"Error fetching strikes for {symbol} {expiration}: {str(e)}")
        
        return []