from ucolab import db
from flask_login import UserMixin
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, PasswordField, SelectField
from wtforms.validators import InputRequired, Length, ValidationError, Email

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), nullable=False, unique=True)
    password = db.Column(db.String(120), nullable=False)
    college = db.Column(db.String(120))
    skills = db.Column(db.String(120))
    answers = db.relationship('Answer', backref='user', lazy=True)
    is_admin = db.Column(db.Boolean, default=False)

    def __repr__(self):
        return f"Name: {self.name}, College: {self.college}, Skills: {self.skills}{', Answers: {self.answers}' if self.answers else ''}"

class Answer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    question_id = db.Column(db.String(10), nullable=False)
    answer = db.Column(db.String(120), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    def __repr__(self):
        return f"User ID: {self.user_id}, Question: {self.question_id}, Answer: {self.answer}"

class Group(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50))
    users = db.relationship('User', secondary='group_membership')

    def __repr__(self):
        return f"Group ID: {self.id}, Group Name: {self.name}, Members: {self.users}"

class GroupMembership(db.Model):
    group_id = db.Column(db.Integer, db.ForeignKey('group.id'), primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)

class Document(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey('group.id'), unique=True, nullable=False)
    text = db.Column(db.Text, default="")
    revision = db.Column(db.Integer, default=0)
    group = db.relationship('Group', backref=db.backref('document', uselist=False))

    def __repr__(self):
        return f"<Document group={self.group.name}, revision={self.revision}>"

class RegisterForm(FlaskForm):
    name = StringField(
        validators = [
            InputRequired(),
            Length(min=4, max=20)
        ], render_kw = { "placeholder" : "Name" }
    )
    email = StringField(
        validators = [
            InputRequired(),
            Email(message="Invalid Email"),
        ], render_kw = { "placeholder" : "Email" }
    )
    password = PasswordField(
        validators = [
            InputRequired(),
            Length(min=8, max=20)
        ], render_kw = { "placeholder" : "Password" }
    )
    college = SelectField(
        'College',
        choices = [
            ('CITCS', 'College of Information Technology and Computer Science'),
            ('CON', 'College of Nursing'),
            ('CEA', 'College of Engineering and Architecture'),
            ('CBA', 'College of Business Administration'),
            ('CAS', 'College of Art and Sciences'),
            ('COA', 'College of Accountancy'),
            ('CHTM', 'College of Hospitality Tourism Management'),
            ('CCJE', 'College of Criminal Justice Education'),
            ('CTE', 'College of Teacher Education')
        ],
        validators=[InputRequired()]
    )
    skills = StringField(
        validators = [InputRequired()],
        render_kw = { "placeholder" : "Please keep it short"}
    )
    submit = SubmitField("Register")

    def validate_email(self, email):
        existing = User.query.filter_by(email=email.data).first()

        if existing:
            raise ValidationError(f"{existing} already exists bozo.")

class LoginForm(FlaskForm):
    email = StringField(
        validators = [
            InputRequired(),
            Email(message="Invalid Email"),
        ], render_kw = { "placeholder" : "Email" }
    )
    password = PasswordField(
        validators = [
            InputRequired(),
            Length(min=8, max=20)
        ], render_kw = { "placeholder" : "Password" }
    )
    submit = SubmitField("Login")