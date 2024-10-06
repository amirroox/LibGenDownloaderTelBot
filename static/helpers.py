# Create a connection DB
import mysql.connector
from mysql.connector.abstracts import MySQLConnectionAbstract
from mysql.connector.pooling import PooledMySQLConnection

from typing import Union

from static import config

connection_pool = mysql.connector.pooling.MySQLConnectionPool(
    pool_name="mypool",
    pool_size=10,
    host="localhost",
    user=config.DATABASE_USERNAME,
    password=config.DATABASE_PASSWORD,
    database=config.DATABASE_NAME
)


# Create a connection DB
def create_connection() -> Union[PooledMySQLConnection, MySQLConnectionAbstract]:
    try:
        return connection_pool.get_connection()
    except mysql.connector.Error as err:
        print(f"Error in DB: {err}")
        exit()
