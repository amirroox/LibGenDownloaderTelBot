# Create a connection DB
from contextlib import contextmanager

import mysql.connector
from mysql.connector.abstracts import MySQLConnectionAbstract
from mysql.connector.pooling import PooledMySQLConnection

from static import config
from typing import Union

connection_pool = mysql.connector.pooling.MySQLConnectionPool(
    pool_name="mypool",
    pool_size=5,
    host="localhost",
    user=config.DATABASE_USERNAME,
    password=config.DATABASE_PASSWORD,
    database=config.DATABASE_NAME,
    autocommit=True,
    charset="utf8mb4",
    collation="utf8mb4_general_ci"
)


# Create a connection DB
@contextmanager
def create_connection() -> Union[PooledMySQLConnection, MySQLConnectionAbstract]:
    connection = None
    try:
        connection = connection_pool.get_connection()
        yield connection
    except mysql.connector.Error as err:
        print(f"Error in DB: {err}")
        raise
    finally:
        if connection:
            connection.close()
