# HPDB

Current version: 4.0.6
## dbClass
### installation
python -m pip install hpdb

### usage

#### settings.ini
~~~~inifile
[database]
dbhost = myhost.mydomain.com
dbname = database_name
dbuser = database_user
dbpass = secret123
~~~~

#### Initializing from ini file
~~~~python
from hpdb import dbClass
db = dbClass.from_inifile('settings.ini')
~~~~

#### Initializing directly
~~~~python
db = dbClass(  host, dbname, user, passwd )
~~~~


#### SELECT
~~~~sql
db.select('users',{'isactive':1} )
~~~~

#### LOOKUP SPECIFIC VALUES
~~~~sql
db.lookup('users',{'id':15}, ['name', 'active] )
~~~~

#### INSERT
~~~~sql
db.insert('users', {'name':'john', 'isactive':1})
id = db.last_insert_id()
~~~~

#### UPDATE
~~~~sql
db.update( 'users', {'name':'john'}, {'active':0})
~~~~

#### DELETE
~~~~sql
db.delete( 'users', {'name':'john'})
~~~~

#### QUERY
~~~~sql
db.execute( 'SELECT * FROM users' )
~~~~


_Don't forget to commit when you have an innodb table_
~~~~sql
db.commit()
~~~~
