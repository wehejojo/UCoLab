from ucolab import db
from flask_login import UserMixin

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    college = db.Column(db.String(120))
    skills = db.Column(db.String(120))
    answers = db.relationship('Answer', backref='user', lazy=True)

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
