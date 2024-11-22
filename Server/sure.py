from flask import Flask, request, render_template, redirect, url_for, flash, abort
from flask_sqlalchemy import SQLAlchemy
import os
import pymysql
from flask_migrate import Migrate
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SelectField, SubmitField
from wtforms.validators import DataRequired
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import face_recognition
import logging
from PIL import Image
import numpy as np


# Налаштування логування
logging.basicConfig(level=logging.DEBUG)

pymysql.install_as_MySQLdb()

# Ініціалізація Flask додатку з вказаним шляхом до шаблонів
app = Flask(__name__, template_folder='/home/vika/Курсова_робота/Server/templates', static_folder='/home/vika/Курсова_робота/Server/static')

# Налаштування папки для завантаження файлів
UPLOAD_FOLDER = os.path.join(os.getcwd(), 'uploads')
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)  # Створіть папку, якщо вона не існує

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


# Конфігурації
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://sikorska:tailcat12@localhost/client_authentication'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = 'your_secret_key'
UPLOAD_FOLDER = '/home/vika/Курсова_робота/Server/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['ALLOWED_EXTENSIONS'] = {'jpg', 'jpeg', 'png', 'mp3'}
app.config['MAX_CONTENT_LENGTH'] = 200 * 1024 * 1024  # 200 МБ

@app.errorhandler(413)
def request_entity_too_large(error):
    flash("Файл занадто великий. Завантажте файл меншого розміру.", "error")
    return redirect(request.url)  # Перенаправлення на ту саму сторінку


# Ініціалізація бази даних
db = SQLAlchemy(app)
migrate = Migrate(app, db)

def allowed_file(filename):
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def process_image(file):
    """Обробка зображення перед збереженням"""
    try:
        image = Image.open(file)
        image = image.convert('RGB')  # Перетворення на RGB формат
        image = image.resize((300, 300))  # Зміна розміру зображення на 300x300 пікселів
        return image
    except Exception as e:
        logging.error(f"Помилка при обробці зображення: {e}")
        return None

@app.route('/')
def home():
    return render_template('main.html')

class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    fullname = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    photo_received = db.Column(db.Boolean, default=False)
    voice_record_received = db.Column(db.Boolean, default=False)
    photo_filename = db.Column(db.String(255))
    voice_filename = db.Column(db.String(255))
    password = db.Column(db.String(255))
    auth_method = db.Column(db.String(50))
    photo = db.Column(db.LargeBinary)
    photo_encoding = db.Column(db.PickleType, nullable=True)


    def __init__(self, fullname, email, password, auth_method, photo, voice_record=None):
        self.fullname = fullname
        self.email = email
        self.password = password
        self.auth_method = auth_method
        self.photo = photo
        self.voice_record = voice_record

class SignupForm(FlaskForm):
    fullname = StringField('Full Name', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Register')
    auth_method = SelectField('Метод автентифікації', choices=[('photo', 'Фото'), ('voice', 'Голос')], coerce=str)

class LoginForm(FlaskForm):
    fullname = StringField('Full Name', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    auth_method = SelectField('Authentication Method', choices=[('photo', 'Photo'), ('voice', 'Voice')], validators=[DataRequired()])
    submit = SubmitField('Log In')
   

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    form = SignupForm()
    if form.validate_on_submit():
        fullname = form.fullname.data
        email = form.email.data
        password = form.password.data
        photo = request.files.get('photo')  # Отримуємо фото
        voice = request.files.get('voice')  # Отримуємо голосовий файл

        if not photo and not voice:
            flash('Будь ласка, завантажте фото або голос для реєстрації.', 'error')
            logging.debug("Neither photo nor voice uploaded")
            return redirect(url_for('signup'))
        
        photo_encoding = None  # Значення за замовчуванням для photo_encoding

        if photo:
            processed_image = process_image(photo)
            if processed_image:
                photo_array = np.array(processed_image)
                encodings = face_recognition.face_encodings(photo_array)
                if encodings:
                   photo_encoding = encodings[0]  # Використовуємо перший знайдений код
                else:
                    flash('Не вдалося розпізнати обличчя на фото.', 'error')
                    return redirect(url_for('signup'))
            else:
               flash('Помилка при обробці фото.', 'error')
               return redirect(url_for('signup'))
        
        if voice:
            if not allowed_file(voice.filename):
                flash('Будь ласка, завантажте правильний голосовий файл.', 'error')
                logging.debug("Invalid voice file format")
                return redirect(url_for('signup'))
            # Обробка голосового файлу, збереження або інша логіка
            voice_filename = secure_filename(voice.filename)
            voice_path = os.path.join(app.config['UPLOAD_FOLDER'], voice_filename)
            voice.save(voice_path)
            logging.debug(f"Voice file saved as {voice_filename}")
        else:
            voice_filename = None  # Якщо голос не був завантажений

        # Перевірка наявності користувача з таким email
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('Цей email вже зареєстровано! Використовуйте інший.', 'error')
            logging.debug(f"User with email {email} already exists")
            return redirect(url_for('signup'))

        # Створення нового користувача
        new_user = User(
           fullname=fullname,
           email=email,
           password=generate_password_hash(password),
           photo_received=True,
           photo_encoding=photo_encoding,
           voice_filename=voice_filename  # Додаємо ім'я голосового файлу
        )

        try:
            db.session.add(new_user)
            db.session.commit()
            logging.debug(f"New user {fullname} added to the database")
            flash('Користувача зареєстровано успішно!', 'success')
            return redirect('/login')
        except Exception as e:
            db.session.rollback()  # Відміна транзакції при помилці
            logging.error(f"Помилка при додаванні в базу даних: {str(e)}")
            flash('Сталася помилка під час реєстрації.', 'error')

    return render_template('sign_up.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data
        auth_method = form.auth_method.data

        # Пошук користувача за email
        user = User.query.filter_by(email=email).first()
        if user:
            # Перевірка пароля
            if not check_password_hash(user.password, password):
                flash("Невірний пароль.", "error")
                return redirect(url_for('login'))

            # Перевірка методу автентифікації
            if auth_method == 'photo' and not user.photo_received:
                flash("Для входу потрібно фото.", "error")
                return redirect(url_for('login'))

            # Якщо метод автентифікації фото
            if auth_method == 'photo' and user.photo_filename:
                photo = request.files.get('photo')  # Отримуємо фото з форми

                if not photo:
                    flash("Будь ласка, завантажте фото для автентифікації.", "error")
                    return redirect(url_for('login'))

                # Завантажуємо фото користувача
                user_image_path = os.path.join(app.config['UPLOAD_FOLDER'], user.photo_filename)
                user_image = face_recognition.load_image_file(user_image_path)
                user_encoding = face_recognition.face_encodings(user_image)

                uploaded_image = face_recognition.load_image_file(photo)
                uploaded_encoding = face_recognition.face_encodings(uploaded_image)

                if user_encoding and uploaded_encoding:
                    results = face_recognition.compare_faces(user_encoding, uploaded_encoding)
                    if results[0]:
                        flash('Вхід успішний!', 'success')
                        return redirect('/home')  # Перехід на головну сторінку
                    else:
                        flash('Не вдалося верифікувати ваше обличчя.', 'error')
                else:
                    flash('Не вдалося знайти обличчя на одному або обох зображеннях.', 'error')
            elif auth_method == 'voice' and not user.voice_filename:
                flash("Для входу потрібен голосовий запис.", "error")
                return redirect(url_for('login'))
            
            return redirect('/home')
        else:
            flash('Користувача з таким email не існує.', 'error')
            return redirect(url_for('login'))
    return render_template('login.html', form=form)


@app.route('/submit', methods=['GET', 'POST'])
def submit():
    fullname = request.form.get('fullname')
    email = request.form.get('email')
    password = request.form.get('password')
    auth_method = request.form.get('auth_method')
    photo = request.files.get('photo')
    voice_record = request.files.get('voice_record')

    # Check for required fields
    if not fullname or not email or not password or not auth_method:
        return "Please fill in all required fields", 400

    # Encrypt password (use default method: pbkdf2:sha256)
    hashed_password = generate_password_hash(password)

    # Prepare file paths
    photo_path = None
    voice_path = None

    # Save photo if provided
    if photo and allowed_file(photo.filename):
        photo_filename = 'photo_' + email + '.jpg'
        photo_path = os.path.join(app.config['UPLOAD_FOLDER'], photo_filename)
        photo.save(photo_path)

    # Save voice record if provided
    if voice_record and allowed_file(voice_record.filename):
        voice_filename = 'voice_' + email + '.wav'
        voice_path = os.path.join(app.config['UPLOAD_FOLDER'], voice_filename)
        voice_record.save(voice_path)

    # Create a new user and save to the database
    new_user = User(
        fullname=fullname,
        email=email,
        password=hashed_password,  # Store the hashed password
        auth_method=auth_method,
        photo=photo_path,  # Save the photo file path
        voice_record=voice_path  # Save the voice file path
    )

    db.session.add(new_user)
    db.session.commit()

    # Redirect to the login page after successful registration
    return redirect(url_for('login'))




if __name__ == '__main__':
   app.run(debug=True)



