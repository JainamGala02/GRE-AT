import random

from app import app
from flask import render_template, request, redirect, url_for, session, g, flash
from werkzeug.urls import url_parse
from app.forms import LoginForm, RegistrationForm, QuestionForm
from app.models import User, Questions
from app import db
import sqlite3
from sqlalchemy import text, func
import pickle
import numpy as np
import io
import base64
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
import matplotlib.pyplot as plt
import seaborn as sns
import csv
import pandas as pd  # (version 1.0.0)
import plotly  # (version 4.5.4) #pip install plotly==4.5.4
import plotly.express as px
import json

# con = sqlite3.connect("app.db")
# cur = con.cursor()

model = pickle.load(open('model.pkl', 'rb'))
id_rand = []


@app.before_request
def before_request():
    g.user = None

    if 'user_id' in session:
        user = User.query.filter_by(id=session['user_id']).first()
        g.user = user

@app.route('/')
def home():
    return render_template('homepage.html', title='Home')

@app.route('/quiz')
def quiz():
    global id_rand
    id_rand = np.random.randint(low=1, high=80, size=5).tolist()
    id_rand.append(0)
    session['marks'] = 0
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            return redirect(url_for('login'))
        session['user_id'] = user.id
        session['marks'] = 0
        next_page = request.args.get('next')
        if not next_page or url_parse(next_page).netloc != '':
            next_page = url_for('quiz')
        return redirect(next_page)
        return redirect(url_for('quiz'))
    if g.user:
        return redirect(url_for('quiz'))
    return render_template('login.html', form=form, title='Login')

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.password.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        session['user_id'] = user.id
        session['marks'] = 0
        return redirect(url_for('quiz'))
    if g.user:
        return redirect(url_for('quiz'))
    return render_template('register.html', title='Register', form=form)



@app.route('/question/<int:id>/<int:new>', methods=['GET', 'POST'])
def question(id, new):
    global id_rand
    new = new
    form = QuestionForm()
    q = Questions.query.filter_by(q_id=id).first()
    # q = Questions.query.from_statement(text(f"SELECT * from questions where type = 'Quantitative' and q_id = {id}  limit 3"))
    # verbal = random.randint(1, 25)
    # quantitative = random.randint(26, 50)
    # total = random.choice([verbal, quantitative])
    print(q)
    # q = cur.execute(f"SELECT * from questions where type = 'Verbal' and q_id = {id} limit 20")
    if not q:
        return redirect(url_for('score'))
    if not g.user:
        return redirect(url_for('login'))
    if request.method == 'POST':
        option = request.form['options']
        if option == q.ans:
            session['marks'] += 1






        return redirect(url_for('question', id=(id_rand[new]), new=new+1))


    form.options.choices = [(q.a, q.a), (q.b, q.b), (q.c, q.c), (q.d, q.d)]
    return render_template('question.html', form=form, q=q, title='Question {}'.format(id))


@app.route('/score')
def score():
    if not g.user:
        return redirect(url_for('login'))
    g.user.marks = session['marks']
    # db.session.commit()
    return render_template('score.html', title='Final Score')

@app.route('/logout')
def logout():
    if not g.user:
        return redirect(url_for('login'))
    session.pop('user_id', None)
    session.pop('marks', None)
    return redirect(url_for('quiz'))

@app.route("/admission")
def pred_chances():
    return render_template("pred.html")

@app.route("/predict", methods=["GET", "POST"])
def predator():
    int_features = [float(x) for x in request.form.values()]
    # print(request.form.values())
    # print(int_features[2])
    predicted_values = []
    perc_predicted_values = []
    for i in range(1, 6):
        int_features[2] = i
        final = [np.array(int_features)]
        prediction = model.predict(final)
        int_prediction = float(prediction)
        predicted_values.append(int_prediction)
        print(predicted_values)
    for val in predicted_values:
        percentage = val*100
        print(percentage)
        formatted_percentage = round(percentage, 2)
        print(formatted_percentage)
        perc_predicted_values.append(formatted_percentage)

    with open('uni.csv', 'w', newline='') as f:
        thewriter = csv.writer(f)
        thewriter.writerow(['University', 'Chance of Admit'])
        thewriter.writerow([1, perc_predicted_values[0]])
        thewriter.writerow([2, perc_predicted_values[1]])
        thewriter.writerow([3, perc_predicted_values[2]])
        thewriter.writerow([4, perc_predicted_values[3]])
        thewriter.writerow([5, perc_predicted_values[4]])

    if perc_predicted_values[0] >= 85:
        start = 0
        end = 25
    elif perc_predicted_values[0] >= 70:
        start = 26
        end = 70
    elif perc_predicted_values[0] >= 60:
        start = 71
        end = 200
    else:
        start = 201
        end = 354


    # return render_template("pred.html", pred=predicted_values)
    return redirect(url_for('university'))


@app.route("/visualize")
def visualize():
    df = pd.read_csv("uni.csv")
    barchart = px.bar(
        data_frame=df,
        x="University",
        y="Chance of Admit",
        labels={"University" : "Current University Rating (Rating of the university you performed your undergraduation from)", "Chance of Admit" : "Chance of Admit (percent)"},
        barmode='relative',
        title='Chance of Admission according to university ranking',  # figure title
        width=1400,  # figure width in pixels
        height=720,  # figure height in pixels
        template='gridon',
    )
    barchart.update_layout(yaxis_range=[50, 100])
    # plotly.offline.plot(barchart, filename='templates/positives.html', config={'displayModeBar': False})
    # barchart.write_html("app/templates/positives.html")
    fig = json.dumps(barchart, cls=plotly.utils.PlotlyJSONEncoder)
    return render_template("vis.html", barchart=fig)


@app.route("/uni")
def university():
    data = pd.read_csv("na_uni_rankings.csv")
    uni_srs = data["institution"]
    uni_rank = data["Rank"]
    uni_location = data["location"]
    return render_template("test.html", uni_srs=uni_srs, uni_rank=uni_rank, uni_location=uni_location)


@app.route("/test")
def test():
    return render_template("test.html")

