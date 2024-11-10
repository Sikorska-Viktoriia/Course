import os
from flask import Flask, request, render_template, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
import pymysql
from flask_migrate import Migrate
from flask import Flask, render_template, redirect, url_for, flash
from forms import LoginForm



pymysql.install_as_MySQLdb()


app = Flask(__name__)


app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://sikorska:tailcat12@localhost/client_authentication'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = 'your_secret_key'  


app.config['UPLOAD_FOLDER'] = 'uploads/'
app.config['ALLOWED_EXTENSIONS'] = {'jpg', 'jpeg', 'png', 'mp3'}


db = SQLAlchemy(app)
migrate = Migrate(app, db)



class User(db.Model):
    __tablename__ = 'users'  # Ensure this matches the table name in the database
    id = db.Column(db.Integer, primary_key=True)
    fullname = db.Column(db.String(255))
    email = db.Column(db.String(255), unique=True)
    photo_received = db.Column(db.Boolean)
    voice_record_received = db.Column(db.Boolean)
    photo_filename = db.Column(db.String(255))
    voice_filename = db.Column(db.String(255))


    def __repr__(self):
        return f'<User {self.email}>'


@app.route('/')
def index():
    return render_template('main.html')



@app.route('/submit', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':  # Перевіряємо метод POST для отримання даних з форми
        fullname = request.form['fullname']
        email = request.form['email']
        photo = request.files['photo']
        voice_record = request.files['voice_record']

        # Виводимо отримані дані
        print(f"Fullname: {fullname}, Email: {email}")

        # Перевірка наявності фото та голосового запису
        photo_received = bool(photo and photo.filename)
        voice_record_received = bool(voice_record and voice_record.filename)

        # Перевірка, чи вже існує користувач з таким email
        existing_user = User.query.filter_by(email=email).first()

        if existing_user:
            flash('Цей email вже зареєстровано!', 'error')
            return redirect(url_for('signup'))

        # Збереження файлів
        photo_filename = None
        voice_filename = None
        if photo_received:
            photo_filename = os.path.join(app.config['UPLOAD_FOLDER'], photo.filename)
            photo.save(photo_filename)
        if voice_record_received:
            voice_filename = os.path.join(app.config['UPLOAD_FOLDER'], voice_record.filename)
            voice_record.save(voice_filename)

        # Створення нового користувача та додавання в базу даних
        new_user = User(
            fullname=fullname,
            email=email,
            photo_received=photo_received,
            voice_record_received=voice_record_received,
            photo_filename=photo_filename,
            voice_filename=voice_filename
        )

        db.session.add(new_user)
        db.session.commit()

        print("User added successfully!")

        flash('Реєстрація успішна!', 'success')
        return redirect(url_for('login'))  # Перенаправлення на сторінку входу

    return render_template('sign_up.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()  # Створюємо екземпляр форми
    if form.validate_on_submit():  # Якщо форма була надіслана та успішно пройшла валідацію
        email = form.email.data
        password = form.password.data
        # Тут ви можете додати логіку для перевірки email і пароля
        flash('Login successful', 'success')  # Виводимо повідомлення про успіх
        return redirect(url_for('home'))  # Перехід на головну сторінку
    return render_template('log_in.html', form=form)  # Передаємо форму в шаблон


@app.route('/showSignUp')
def showSignUp():
    return render_template('sign_up.html')


if __name__ == '__main__':
   
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])
    
    app.run(debug=True)
