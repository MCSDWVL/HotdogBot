import os
import psycopg2

DATABASE_URL = os.environ['DATABASE_URL']

def execute_sql(sql, params):
    ret_val = None
    try:
        # connect to the PostgreSQL database
        conn = psycopg2.connect(DATABASE_URL, sslmode='require')
        # create a new cursor
        cur = conn.cursor()
        # execute the sql
        cur.execute(sql, params)
        # get the generated id back
        ret_val = cur.fetchone()[0]
        # commit the changes to the database
        conn.commit()
        # close communication with the database
        cur.close()
        return ret_val
    except (Exception, psycopg2.DatabaseError) as error:
        print(error)
    finally:
        if conn is not None:
            conn.close()

def new_user(user_id):
    """ insert a new user into the vendors table """
    sql = """INSERT INTO users(user_id) VALUES(%s) ON CONFLICT DO NOTHING RETURNING user_id;"""
    user_id = execute_sql(sql, (user_id,))
    if user_id is not None:
        sql = """INSERT INTO balances(user_id, balance) VALUES(%s,%s) ON CONFLICT DO NOTHING RETURNING balance;"""
        return execute_sql(sql, (user_id,100,))
    else:
        return None

def get_balance(user_id):
    sql = """SELECT balance FROM balances WHERE user_id=%s;"""
    return execute_sql(sql, (user_id,))

def update_balance(user_id, new_balance):
    sql = """UPDATE balances SET balance=%s WHERE user_id=%s RETURNING balance;"""
    return execute_sql(sql, (new_balance, user_id,))
    
def pay(payer_id, recipient_id, amount):
    if amount <= 0:
        return None
    curpayerbalance = get_balance(payer_id)
    if curpayerbalance is None or curpayerbalance < amount:
        return None
    # update each balance.
    currecipientbalance = get_balance(recipient_id)
    if currecipientbalance is None:
        return None

    update_balance(payer_id, curpayerbalance - amount)
    update_balance(recipient_id, currecipientbalance + amount)
    return (curpayerbalance - amount, currecipientbalance + amount)

