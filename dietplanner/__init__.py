import pymysql

# 1. Tell Django to use pymysql
pymysql.install_as_MySQLdb()

# 2. TRICK Django into thinking the version is new enough
try:
    import MySQLdb
    if MySQLdb.version_info < (2, 2, 1):
        MySQLdb.version_info = (2, 2, 1, 'final', 0)
except ImportError:
    pass