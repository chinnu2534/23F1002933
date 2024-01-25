from celery import Celery
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import IntegrityError
from datetime import datetime, timedelta
from app import app, db, rent, Book, fee, calculate_rent_fee

celery = Celery(app.name, broker=app.config['CELERY_BROKER_URL'])
celery.conf.update(app.config)

@celery.task
def auto_return_books():
    # Fetch overdue rent records
    overdue_records = rent.query.filter(
        rent.status == 'Pending',
        rent.date <= datetime.now() - timedelta(minutes=1)
    ).all()

    for record in overdue_records:
        # Update status to "Returned"
        record.status = 'Returned'

        # Fetch corresponding book
        book = Book.query.get(record.book_id)

        # Increase the "copies" column for the returned book
        book.copies += 1

        try:
            db.session.commit()

            # Create a new entry in the fee table
            issue_date = record.date
            fee_entry = fee(
                stu_id=record.stu_id,
                book_id=record.book_id,
                issue_date=issue_date,
                return_date=datetime.now(),  # Current date and time
                rent_fee=calculate_rent_fee(issue_date)  # Calculate rent fee
            )
            db.session.add(fee_entry)
            db.session.commit()

            print(f'Auto-returned book with rent ID {record.rid} successfully!')
        except IntegrityError:
            db.session.rollback()
            print(f'Error auto-returning book with rent ID {record.rid}. Please try again.')
