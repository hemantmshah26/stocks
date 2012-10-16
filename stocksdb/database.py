#!/usr/bin/env python

import ystockquote as quotes
import config
from sys import argv
from datetime import date, timedelta
from models  import Symbol, Quote
from sqlalchemy import create_engine, desc
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import and_, or_, not_
from sqlalchemy.ext.declarative import declarative_base


class Database(object):

    def __init__(self):
        """
        Set up database access
        """
        self.Base = declarative_base()
        if config.sql_password == '':
            engine_config = 'mysql://%s@%s/%s' % (config.SQL_USER, config.SQL_HOSTNAME, config.SQL_DATABASE)
        else:
            engine_config = 'mysql://%s:%s@%s/%s' % (config.SQL_USER, config.SQL_PASSWORD, config.SQL_HOSTNAME, config.SQL_DATABASE)
        self.Engine = create_engine(engine_config)
        self.Session = sessionmaker()
        self.Session.configure(bind=self.Engine)


class StockDBManager(object):
    """
    Stock database management class
    """

    def __init__(self):
        """
        Get access to database
        """
        self.db = Database()
    

    def create_database(self):
        """
        Create stock database tables if they do not exist already
        """
        self.db.Base.metadata.create_all(Engine)


    def add_stock(self, ticker, name=None, exchange=None, sector=None, industry=None):
        """
        Add a stock to the stock database
        """
        ticker = ticker.lower()
        if name is None:
            name = quotes.get_name(ticker) 
        if exchange is None:
            exchange = quotes.get_stock_exchange(ticker)
        if sector is None:
            sector = quotes.get_sector(ticker)
        if industry is None:
            industry = quotes.get_industry(ticker)
        stock = Symbol(ticker, name, exchange, sector, industry)
        session = self.db.Session()
        
        if self.check_stock_exists(ticker,session):
            print "Stock %s already exists!" % (ticker.upper())
        else:
            print "Adding %s to database" % (ticker.upper())
            session.add(stock)
            session.add_all(self.download_quotes(ticker, date(1900,01,01), date.today()))
        
        session.commit()
        session.close()

    def download_quotes(self, ticker, start_date, end_date):
        """
        Get quotes from Yahoo Finance
        """
        ticker = ticker.lower()
        if start_date == end_date:
            return 
        start = start_date
        end = end_date
        data = quotes.get_historical_prices(ticker, start, end)
        data = data[len(data)-1:0:-1]
        if len(data):
            return [Quote(ticker,val[0],val[1],val[2],val[3],val[4],val[5],val[6]) for val in data]
        else:
            return

    def update_quotes(self, ticker):
        """
        Get all missing quotes through current day for the given stock
        """
        ticker = ticker.lower()
        quotes = None
        session = self.db.Session()
        last = session.query(Quote).filter_by(Ticker=ticker).order_by(desc(Quote.Date)).first().Date
        start_date = last + timedelta(days=1)
        end_date = date.today()
        if end_date > start_date:
            quotes = self.download_quotes(ticker, start_date, end_date)
        if quotes is not None:
            session.add_all(quotes)
        session.commit()
        session.close()

    def sync_quotes(self):
        """
        Updates quotes for all stocks through current day.
        """
        session = self.db.Session()
        for symbol in session.query(Symbol).all():
            self.update_quotes(symbol.Ticker)
            print 'Updated quotes for %s' % symbol.Ticker
        session.close()        
    
    def check_stock_exists(self,ticker,session=None):
        """
        Return true if stock is already in database
        """
        if session is None:
            session = self.db.Session()
        exists = bool(session.query(Symbol).filter_by(Ticker=ticker.lower()).count())
        if session is None:
            session.close()
        return exists
 
    def check_quote_exists(self,ticker,date,session=None):
        """
        Return true if a quote for the given symbol and date exists in the database
        """
        if session is None:
            session = self.db.Session()
        exists = bool(session.query(Symbol).filter_by(Ticker=ticker.lower(),
                        Date=date).count())
        if session is None:
            session.close()
        return exists
        
    def get_quotes(self, ticker, quote_date, end_date=None):
        """
        Return a list of quotes between the start date and (optional) end date.
        if no end date is specified, return a list containing the quote for the start date
        """
        ticker = ticker.lower()
        session = self.db.Session()
        if end_date is not None:
            query = session.query(Quote).filter(and_(Quote.Ticker == ticker, 
                            Quote.Date >= quote_date, 
                            Quote.Date <= end_date)).order_by(Quote.Date)
        else:
            query = session.query(Quote).filter(and_(Quote.Ticker == ticker, 
                            Quote.Date == quote_date))    
        session.close()
        return [quote for quote in query.all()]
    


    
if __name__ == '__main__':
    db = StockDBManager()
    if str(argv[1]) == 'sync':
        db.sync_quotes()   
    
    
