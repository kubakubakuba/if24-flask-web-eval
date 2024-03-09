from flask import Flask, render_template, session, redirect, url_for
from markupsafe import escape

app = Flask(__name__)
app.secret_key = 'e4ed89f02f3aa07a4309dbfff'

@app.route("/")
def index():
    return render_template('index.html')

@app.route("/name/<name>")
def name(name):
	session['user'] = escape(name)
	return redirect(url_for('index'))

@app.route('/personal')
def personal():
	logged_in = session.get('logged_in', False)
	return render_template('personal.html', logged_in=logged_in)
	
@app.route("/login")
def login():
	session['logged_in'] = True
	return redirect(url_for('index'))

@app.route("/logout")
def logout():
	session.clear()
	return redirect(url_for('index'))