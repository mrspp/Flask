from flask import Flask, render_template, flash, redirect, url_for, session, request, logging, Markup, jsonify
#from data import Articles
from flaskext.mysql import MySQL 
from wtforms import Form, StringField, TextAreaField, PasswordField, validators
from passlib.hash import sha256_crypt
from functools import wraps
from werkzeug.utils import secure_filename
import os

mysql = MySQL()
server = Flask(__name__,
            static_url_path='', 
            static_folder='templates',
            template_folder='templates')
server.config.from_object('config')
mysql.init_app(server)
#Articles = Articles()

@server.route('/')
def hello():
    return render_template('home.html')

@server.route('/about')
def about():
    return render_template('about.html')

@server.route('/articles')
def articles():
    cur=mysql.get_db().cursor()
    result = cur.execute('SELECT * FROM articles')
    articles = cur.fetchall()
    if result > 0:
        return render_template('articles.html', articles = articles)
    else:
        msg = 'No Article Found'
        return render_template('articles.html', msg = msg)
    cur.close()

@server.route('/article_test')
def article_test():
    cur = mysql.get_db().cursor()
    result = cur.execute('SELECT * FROM articles')
    articles = cur.fetchall()
    if result > 0:
        return render_template('article_test.html', articles=articles)
    else:
        msg = 'No Articles Found'
        return render_template('article_test.html', msg=msg)
    cur.close()

@server.route('/articles_test/<string:id>')
def articles_test(id):
    cur = mysql.get_db().cursor()
    result = cur.execute("SELECT * FROM articles WHERE id = %s", id)
    Article = cur.fetchone()
    form = ArticleForm(request.form)
    form.title.data = Article[1]
    form.body.data = Article[3]
    title = Article[1]
    body = Article[3]
    cur.close()
    if request.method == 'POST' and form.validate():
        title = request.form['title']
        body = request.form['body']
        author = session['username']
        cur = mysql.get_db().cursor()
        print(body)
        cur.execute("UPDATE articles SET body= %s WHERE id = %s", (body, id))
        mysql.get_db().commit()
        cur.close()
        flash('Article updated', 'success')
        return redirect(url_for('dashboard'))
    return render_template('view_test.html', form=form, body = body, title = title)

@server.route('/articles/<string:id>/')
def article(id):
    cur = mysql.get_db().cursor()
    result = cur.execute("SELECT * FROM articles WHERE id = %s", id)
    Article = cur.fetchone()
    form = ArticleForm(request.form)
    form.title.data = Article[1]
    form.body.data = Article[3]
    title = Article[1]
    body = Article[3]
    cur.close()
    return render_template('single.html', form=form, body = body, title = title)

class RegisterForm(Form):
    name = StringField('Name',[validators.Length(min=3, max=50)])
    username = StringField('Username',[validators.Length(min=3, max=25)])
    email = StringField('Email',[validators.Length(min=3, max=50)])
    password = PasswordField('Password', [
        validators.DataRequired(),
        validators.EqualTo('confirm', message='Password do not match')])
    confirm = PasswordField('Confirm Password')

@server.route('/register', methods = ['GET', 'POST'])
def register():
    form = RegisterForm(request.form)
    if request.method == 'POST' and form.validate():
        name = form.name.data
        email = form.email.data
        username = form.username.data
        password = sha256_crypt.hash(str(form.password.data))

        cur = mysql.get_db().cursor()
        cur.execute("INSERT INTO users(name, email, username, password) VALUES(%s, %s, %s, %s);", (name, email, username, password))
        mysql.get_db().commit()
        cur.close()
        flash ('You are now registered and can login !', 'success')
        return redirect(url_for('login'))
    return render_template('register.html',form = form)

@server.route('/login', methods= ['GET','POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password_candidate = request.form['password']
        cur = mysql.get_db().cursor()
        result = cur.execute('SELECT * FROM users WHERE username = %s',[username])
        if result > 0:
            data = cur.fetchone()
            password = data[4]
            if sha256_crypt.verify(password_candidate,password):
                session['logged_in'] = True
                session['username'] = username
                flash('You are now logged in !','success')
                return redirect(url_for('dashboard'))
            else:
                err = 'Invalid login'
                return render_template('login.html',err=err)
            cur.close()
        else:
            err = 'Username not found'
            return render_template('login.html',err=err)
    return render_template('login.html')

def is_logged_in(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'logged_in' in session:
            return f(*args, **kwargs)
        else:
            flash('Unthorized, please login', 'danger')
            return redirect(url_for('login'))
    return wrap

@server.route('/logout')
@is_logged_in
def logout():
    session.clear()
    flash('You are now logged out !','success')
    return redirect(url_for('login'))

@server.route('/dashboard')
@is_logged_in
def dashboard():
    cur = mysql.get_db().cursor()
    result = cur.execute('SELECT * FROM articles')
    articles = cur.fetchall()
    if result > 0:
        return render_template('dashboard.html', articles=articles)
    else:
        msg = 'No Articles Found'
        return render_template('dashboard.html', msg=msg)
    cur.close()

class ArticleForm(Form):
    title = StringField('title',[validators.Length(min=1, max=200)])
    body = TextAreaField('body',[validators.Length(min=30)])

@server.route('/add_article', methods=['GET','POST'])
@is_logged_in
def add_article():
    form = ArticleForm(request.form)
    if request.method == 'POST' and form.validate():
        title = form.title.data
        body =form.body.data
        author = session['username']
        cur = mysql.get_db().cursor()
        cur.execute("INSERT INTO articles(title,author,body) VALUES(%s,%s,%s);",(title, author, body))
        mysql.get_db().commit()
        cur.close()
        flash('Article created', 'success')
        return redirect(url_for('dashboard'))
    return render_template('add_article.html', form = form)

@server.route('/edit_article/<string:id>', methods=['GET','POST'])
@is_logged_in
def edit_article(id):
    cur = mysql.get_db().cursor()
    result = cur.execute("SELECT * FROM articles WHERE id = %s", id)
    Article = cur.fetchone()
    form = ArticleForm(request.form)
    form.title.data = Article[1]
    form.body.data = Article[3]
    cur.close()
    if request.method == 'POST' and form.validate():
        title = request.form['title']
        body = request.form['body']
        author = session['username']
        cur = mysql.get_db().cursor()
        print(body)
        cur.execute("UPDATE articles SET body= %s WHERE id = %s", (body, id))
        mysql.get_db().commit()
        cur.close()
        flash('Article updated', 'success')
        return redirect(url_for('dashboard'))
    return render_template('edit_article.html', form=form)

@server.route('/delete_article/<string:id>', methods=['POST', 'GET', 'DELETE'])
@is_logged_in
def delete_article(id):
    cur = mysql.get_db().cursor()
    cur.execute('DELETE FROM articles WHERE id = %s', [id])
    mysql.get_db().commit()
    cur.close()
    flash('Article Deleted', 'success')
    return redirect(url_for('dashboard'))

UPLOAD_FOLDER = 'uploads/img'
server.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

@server.route('/add_image', methods=['GET','POST'])
@is_logged_in
def add_img():
    if request.method == 'POST':
        f = request.files['file']
        p = os.path.join(server.config['UPLOAD_FOLDER'], secure_filename(f.filename))
        f.save(p)
        flash('Image uploaded')
        return render_template('add_image.html')
    return render_template('add_image.html')

@server.route('/api/posts', methods = ['GET'])
def posts():
    cur=mysql.get_db().cursor()
    result = cur.execute('SELECT * FROM articles')
    articles = cur.fetchall()
    if result > 0:
        return jsonify(articles)
    else:
        msg = 'No Article Found'
        return jsonify(articles)
    cur.close()



if __name__ == '__main__':
    server.run(debug=True)