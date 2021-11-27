import os
import psycopg2

DATABASE_URL = os.environ['DATABASE_URL']

def create_tables():
    """ create tables in the PostgreSQL database"""
    commands = (
        """
        DROP TABLE users CASCADE
        """,
        """
        DROP TABLE balances CASCADE
        """,
        """
        CREATE TABLE IF NOT EXISTS users (
            user_id VARCHAR(50) PRIMARY KEY UNIQUE NOT NULL
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS  balances (
                user_id VARCHAR(50) PRIMARY KEY,
                balance INTEGER NOT NULL,
                FOREIGN KEY (user_id)
                REFERENCES users (user_id)
                ON UPDATE CASCADE ON DELETE CASCADE
        )
        """)
    conn = None
    try:
        # connect to the PostgreSQL server
        conn = psycopg2.connect(DATABASE_URL, sslmode='require')
        cur = conn.cursor()
        # create table one by one
        for command in commands:
            cur.execute(command)
        # close communication with the PostgreSQL database server
        cur.close()
        # commit the changes
        conn.commit()
    except (Exception, psycopg2.DatabaseError) as error:
        print(error)
    finally:
        if conn is not None:
            conn.close()

if __name__ == '__main__':
    create_tables()
