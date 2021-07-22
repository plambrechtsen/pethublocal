'''
    Create Pet Hub Local test database

    This script imports the base schema from pethublocal.sql and then imports test data.
    It is used by all tests so needs to be run in init, and the database needs to be created before pethubpacket gets imported otherwise the library
    expects the pethublocal.db main database to exist. That is why this is in the init.
'''

import sqlite3
pethubdb = "pethubtest.db"
connection = sqlite3.connect(pethubdb)
cursor = connection.cursor()
pethubtest_file = open("../source/pethublocal.sql")
cursor.executescript(pethubtest_file.read())
pethubtest_file = open("pethubtest.sql")
cursor.executescript(pethubtest_file.read())
connection.close()
