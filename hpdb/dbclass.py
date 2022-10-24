import decimal
import time
from datetime import datetime
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import OperationalError
import sqlparse

class dbClass(object):

    def __init__(self, host, dbname, user, passwd, database_type='mysql+pymysql', port=''):
        # database_type could also be postgresql
        if port:
            port = ':' + port
        self.engine = create_engine(f"{database_type}://{user}:{passwd}@{host}{port}/{dbname}")
        self.database_type = database_type
        self.escape_char = '"' if database_type == 'postgresql' else '`'
        self.quote = "'" if database_type == 'postgresql' else '"'
        self.engine.connect()
        self.session = sessionmaker(bind=self.engine)()

        self.attempts = 3
        self.retry_timeout = 1
        self.test = 0
        self.debug = 0


    @classmethod  # Inititate like this: db = dbClass.from_inifile( 'db.ini' )
    def from_inifile(cls, inifilename, section='database'):
        from configparser import ConfigParser, NoOptionError
        inifile = ConfigParser()
        inifile.read(inifilename)
        params = tuple(inifile.get(section, param) for param in ['dbhost', 'dbname', 'dbuser', 'dbpass'])
        for param in ['dbtype', 'dbport']:
            try:
                value = inifile.get(section, param)
            except NoOptionError:
                continue
            params = params + (value,)

        return cls(*params)


    def first(self, sql: str):
        return next(self.query(sql))

    def query(self, sql: str) -> Generator:
        if self.debug:
            print(sql)
        if not sql.strip().lower().startswith('select'):
            print( 'Warning: dbClass.query sql parameter should start with SELECT. Use .execute instead\n', sql)
        resultset = self.execute_with_retries(sql)
        for row_mapping in resultset.mappings().all():
            yield(dict(row_mapping))
        else:
            yield from () # Interesting construction to make sure query always returns a generator

    def execute(self, sql, *params):
        if sql.strip().lower().startswith('select'):
            print( 'Warning: dbClass.execute sql parameter should not start with SELECT. Use .query instead\n', sql)
        if params:
            print( 'PARAMS', params)
            sql = sql % tuple([str(s).replace('\\', '\\\\').replace("'", r"\'").replace('"', r'\"') for s in params])
        return self.execute_multiple(sql)

    def execute_multiple(self, sql):
        if self.debug:
            print(sql)
        for statement in sqlparse.split(sql):
            if statement:
                self.execute_with_retries(statement)

    def execute_with_retries(self, sql):
        for attempt in range(self.attempts):
            try:
                return self.engine.execute(sql.replace('%', '%%'), params=None)
            except (TimeoutError, OperationalError) as err:
                if attempt < self.attempts - 1:
                    time.sleep(self.retry_timeout)
                    continue # Try again
                raise err  # Attempts ran out

    def lookup(self, table, conditions, outfields):
        whereclause = ''
        for key in conditions.keys():
            if not whereclause:
                whereclause = f'WHERE {self.escape_char}{key}{self.escape_char}={self.quote}{conditions[key]}{self.quote} '
            else:
                whereclause += f'AND {self.escape_char}{key}{self.escape_char}={self.quote}{conditions[key]}{self.quote} '
        if type(outfields) == type(''):
            what = outfields
        elif type(outfields) == type([]):
            what = ','.join(outfields)

        try:
            res = self.first(f'SELECT {what} FROM {table} {whereclause}')
        except StopIteration:
            return None
        if type(outfields) == type(''):
            return res[outfields]
        else:
            return tuple([res[outf] for outf in outfields])

    def select(self, table, conditions=None) -> Generator[int, None, None]:
        whereclause = ''
        if conditions:
            for key in conditions.keys():
                if not whereclause:
                    whereclause = f'WHERE {self.escape_char}{key}{self.escape_char}={self.quote}{conditions[key]}{self.quote} '
                else:
                    whereclause += f'AND {self.escape_char}{key}{self.escape_char}={self.quote}{conditions[key]}{self.quote} '

        yield from self.query('SELECT * FROM %s %s' % (table, whereclause))

    def insert(self, table, dict, ignore=False, returnfield=None):
        keys = ','.join(['%s' % key for key in dict.keys()])
        values = ','.join([self.formatval(val) for val in dict.values()])
        ignore_string = ignore and ' IGNORE' or ''
        sql = f'INSERT{ignore_string} INTO {table} ({keys}) VALUES ({values})'
        if self.test:
            if not self.debug:
                print(sql)
        else:
            if self.database_type == 'postgresql':
                if returnfield:
                    sql += f' RETURNING {returnfield}'
                    return self.query(sql)
                else:
                    return self.execute(sql)
            else:
                self.execute(sql)
                return self.last_insert_id()

    def last_insert_id(self):
        if self.database_type == 'postgresql':
            return self.first('SELECT lastval()')
        return self.first('SELECT LAST_INSERT_ID() as id')['id']

    def update(self, table, wheredict, valuedict, ignore=False):
        valueclause = ','.join([f'{self.escape_char}{key}{self.escape_char}={self.formatval(valuedict[key])}' for key in valuedict.keys()])
        whereclause = ' AND '.join([f'{self.escape_char}{key}{self.escape_char}={self.quote}{wheredict[key]}{self.quote}' for key in wheredict.keys()])
        ignore_keyword = 'IGNORE ' if ignore else ''

        sql = f'UPDATE {ignore_keyword} {table} SET {valueclause} WHERE {whereclause}'

        if self.test:
            if not self.debug:
                print(sql)
        else:
            self.execute(sql)

    def updateinsert(self, table, lookupdict, insertdict, returnfield=None):
        lookupfield = list(lookupdict.keys())[0]
        id = self.lookup(table, lookupdict, lookupfield)
        if not id:
            id = self.insert(table, insertdict, returnfield=returnfield)
        else:
            self.update(table, lookupdict, insertdict)
        return id

    def delete(self, table, wheredict):
        whereclause = ' AND '.join([f'{self.escape_char}{key}{self.escape_char}={self.quote}{wheredict[key]}{self.quote}' for key in wheredict.keys()])
        sql = f'DELETE FROM {table} WHERE {whereclause}'
        if self.test:
            if not self.debug:
                print(sql)
        else:
            self.execute(sql)

    def commit(self):
        self.session.commit()

    def formatval(self, val):
        if val == None:
            return 'NULL'
        if isinstance(val, (int, float, decimal.Decimal)):
            return str(val)
        if isinstance(val, datetime):
            return val.strftime('%Y-%m-%d %H:%M:%S')

        if self.database_type== 'postgresql':
            return "'%s'" % str(val).replace("'", '"')
        else:
            return '"%s"' % str(val).replace('"', "'")


    def dataframe(self, query:str):
        import pandas as pd
        return pd.read_sql_query(query.replace('%', '%%'), self.engine)
