from flask import Flask, render_template, request, session, g, redirect, url_for, abort, flash
from flask_mysqldb import MySQL

mysql = MySQL()

app = Flask(__name__)
app.config.from_object(__name__)


app.config.from_envvar('TOGGLTARTAN_SETTINGS') #silent=True)
mysql.init_app(app)


@app.route('/')
def main():
    cur = mysql.connection.cursor()
    cur.execute('''SELECT * FROM users''')
    rv = cur.fetchall()
    return render_template('index.html')
    #return 'Hello, World!'

@app.route('/hello/')
@app.route('/hello/<name>')
def hello(name=None):
    return render_template('hello.html', name=name)

if __name__ == "__main__":
    app.run(debug=True)