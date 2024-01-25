from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
db=SQLAlchemy()


class Book(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    title=db.Column(db.String(200),nullable=False)
    author=db.Column(db.String(200))
    isbn=db.Column(db.String(20))
    publisher=db.Column(db.String(100))
    page=db.Column(db.Integer,default=0)
    copies=db.Column(db.Integer)
    rented=db.Column(db.Integer)
    rents = db.relationship('rent', backref='book', lazy=True)
    
    
   



class student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    password = db.Column(db.String(50))

class fee(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    stu_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    book_id = db.Column(db.Integer, db.ForeignKey('book.id'), nullable=False)
    issue_date = db.Column(db.DateTime, nullable=False)
    return_date = db.Column(db.DateTime)
    rent_fee = db.Column(db.Float, default=0.0)

    

class rent(db.Model):
    rid=db.Column(db.Integer,primary_key=True)
    book_id=db.Column(db.Integer,db.ForeignKey('book.id'),nullable=False)
    borrowed_quantity=db.Column(db.Integer,default=0)
    stu_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    date = db.Column(db.DateTime)
    status=db.Column(db.String(20),default='Pending')

    student = relationship('student', foreign_keys=[stu_id], backref='rents')
    


class Request(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    book_id = db.Column(db.Integer, db.ForeignKey('book.id'), nullable=False)

    def __repr__(self):
        return f'<Request(user_id={self.user_id}, book_id={self.book_id})>'


