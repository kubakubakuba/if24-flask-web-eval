from flask import Flask
from flask import render_template
from flask import request

app = Flask(__name__)
app.secret_key = 'e4ed89f02f3aa07a4309dbfff'

@app.route("/")
def index():
    return render_template('index.html')

@app.route("/register", methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        return "Registered with username: " + \
            request.form['username'] + " and password: " + \
            request.form['password']
    return render_template('register.html')
