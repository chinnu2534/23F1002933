from flask import Flask,render_template,request,redirect,flash,url_for,jsonify
from flask_migrate import Migrate
from models import db,Book,student,rent,fee
from datetime import datetime,timedelta
import requests 
from sqlalchemy import desc
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func
from collections import defaultdict

from sqlalchemy.orm.exc import NoResultFound

import random




app=Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI']='sqlite:///library.db'
app.config['SECRET_KEY']='af9d4e10d142994285d0c1f861a70925'
db.init_app(app)
migrate=Migrate(app,db)

@app.route('/')
def index():
    

    borrowed_books = db.session.query(rent).filter(rent.status == "Approved").count()
    total_books = Book.query.count()
    total_members = student.query.count()
    total_rent_current_month = round(db.session.query(func.sum(fee.rent_fee)).scalar() or 0, 2)
    recent_transactions  =  db.session.query(rent,Book).join(Book).order_by(rent.date.desc()).limit(5).all()

    return render_template('index.html', borrowed_books=borrowed_books, total_books=total_books,total_members=total_members,recent_transactions=recent_transactions,total_rent_current_month=total_rent_current_month)

def calculate_total_rent_current_month():
    current_month = datetime.datetime.now().month
    current_year = datetime.datetime.now().year
    start_date = datetime.datetime(current_year, current_month, 1)
    end_date = datetime.datetime(current_year, current_month + 1, 1) - datetime.timedelta(days=1)

    total_rent = db.session.query(db.func.sum(rent.rent_fee)).filter(rent.issue_date >= start_date,rent.issue_date <= end_date).scalar()

    return total_rent if total_rent else 0

@app.route('/add_book',methods=['GET','POST'])
def add_book():
    if request.method == 'POST':
        title = request.form.get('title')
        author = request.form.get('author')
        isbn = request.form.get('isbn')
        publisher = request.form.get('publisher')
        page = request.form.get('page')
        copies = request.form.get('stock')
        new_book = Book(title=title, author=author, isbn=isbn, publisher=publisher, page=page,copies=copies,rented=0)
        db.session.add(new_book)
        db.session.flush()
        db.session.commit()
        flash('Book added successfully!', 'success')
        return redirect(url_for('index'))

    return render_template('add_book.html')


@app.route('/add_member', methods=['GET', 'POST'])
def add_member():
    if request.method == 'POST':
        name = request.form.get('name')
        id = request.form.get('id')
        password = request.form.get('password')

        try:
            new_member = student(name=name, id=id, password=password)
            db.session.add(new_member)
            db.session.commit()
            flash('Member added successfully!', 'success')
            return redirect(url_for('add_member'))
        except IntegrityError as e:
            db.session.rollback()
            flash('Error adding member. ID may already exist.', 'danger')
            app.logger.error(f"Error adding member: {str(e)}")
    return render_template('add_member.html')


@app.route('/view_books', methods=['GET', 'POST'])
def book_list():
    if request.method == 'POST':
        if 'searcht'and 'searcha' in request.form:
            title = request.form.get('searcht')
            author=request.form.get('searcha')
            books = db.session.query(Book).filter((Book.title.like(f'%{title}%')),(Book.author.like(f'%{author}%'))).all()
        elif 'searcht' in request.form:
             title=request.form.get('searcht')
             books = db.session.query(Book).filter(Book.title.like(f'%{title}%')).all()
        elif 'searcha' in request.form:
             author=request.form.get('searcha')
             books = db.session.query(Book).filter(Book.author.like(f'%{author}%')).all()
    else:
        books= db.session.query(Book).all()

    return render_template('view_books.html', books=books)

@app.route('/view_members', methods=['GET','POST'])
def member_list():
    if request.method == 'POST':
        search = request.form.get('search')
        member = db.session.query(student).filter(student.name.like(f'%{search}%')).all()
        return render_template('view_members.html', member=member)

    else:
        member=db.session.query(student).all()
        print([ i.name for i in member])
        return render_template('view_members.html', member=member)

@app.route('/edit_book/<int:id1>',methods=['GET','POST'])
def edit_book(id1):
    print(id1)
    book=Book.query.get(id1)
   
    try:
        if request.method == 'POST':
            rented=book.rented
            to_be_updated=int(request.form.get('stock'))-rented
            if to_be_updated<0:
                flash("Quantity decrease failed!books are on rent",'error')
            else:
                book.title = request.form.get('title')
                book.author = request.form.get('author')
                book.isbn = request.form.get('isbn')
                book.publisher = request.form.get('publisher')
                book.page = request.form.get('page')
                book.copies=request.form.get('stock')
                db.session.commit()
                flash("Updated Sucessfully",'success')
    except Exception as e:
        db.session.rollback()
        flash(f"An error ocuured \n{e}",'error')
    return render_template('edit_book.html',book=book)

@app.route('/edit_member/<int:id>', methods=['GET', 'POST'])
def edit_member(id):
    member = student.query.get(id)
    try:
        if request.method == "POST":
            member.name = request.form['name']
            member.password = request.form['phone']
            db.session.commit()
            flash("Updated Successfully", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"An error occurred \n{e}", 'error') 
    return render_template('edit_member.html', member=member)

@app.route('/delete_member/<int:id>', methods=['GET', 'POST'])
def delete_member(id):
    try:
        # Remove the member from the Rent table first
        rent_entries = rent.query.filter_by(stu_id=id).all()
        for rent_entry in rent_entries:
            db.session.delete(rent_entry)

        # Now, remove the member from the student table
        member = student.query.get(id)
        db.session.delete(member)

        # Commit the changes
        db.session.commit()

        flash("Member removed successfully", "success")
    except Exception as e:
        flash(f"An error occurred \n{e}", 'error')

    return redirect('/view_members')

@app.route('/delete_book/<int:id>', methods=['GET', 'POST'])
def delete_book(id):
    try:
        # Check if there are any rental records for the book
        rentals = rent.query.filter_by(book_id=id).all()

        # Delete associated rental records
        for rental in rentals:
            db.session.delete(rental)

        # Delete the book itself
        book = Book.query.get(id)
        db.session.delete(book)

        db.session.commit()
        flash("Book removed successfully", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"An error occurred \n{e}", 'error')

    return redirect('/view_books')
@app.route('/view_book/<int:id>')
def view_book(id):
    book = Book.query.get(id)
    transactions = rent.query.filter_by(book_id=id).all()
    return render_template('view_book.html', book=book, trans=transactions)


@app.route('/view_member/<int:id>')
def view_member(id):
    member = student.query.get(id)
    transactions = rent.query.filter_by(stu_id=id).all()
    outstanding_debt = db.session.query(func.sum(fee.rent_fee)).filter_by(stu_id=id).scalar() or 0.0
    return render_template('view_member.html', member=member, transactions=transactions,debt=outstanding_debt)






@app.route('/transactions', methods=['GET', 'POST'])
def view_borrowings():
    # Query the necessary columns from rent and aggregated fee tables
    subquery = db.session.query(
        fee.stu_id.label('stu_id'),
        fee.book_id.label('book_id'),
        func.max(fee.issue_date).label('max_issue_date'),
        func.max(fee.return_date).label('max_return_date'),
        func.sum(fee.rent_fee).label('total_rent_fee')
    ).group_by(fee.stu_id, fee.book_id).subquery()

    transactions = db.session.query(
        rent.rid.label('Transaction Id'),
        Book.title.label('Book Title'),
        student.name.label('Student Name'),
        rent.date.label('Issue Date'),
        subquery.c.max_return_date.label('Return Date'),
        subquery.c.total_rent_fee.label('Rent Fee'),
    ).join(student, rent.stu_id == student.id).join(Book, rent.book_id == Book.id).outerjoin(subquery, (subquery.c.stu_id == rent.stu_id) & (subquery.c.book_id == rent.book_id)).order_by(desc(rent.date)).all()

    if request.method == "POST":
        search = request.form['search']
        
        transactions_by_name = db.session.query(
            rent.rid.label('Transaction Id'),
            Book.title.label('Book Title'),
            student.name.label('Student Name'),
            rent.date.label('Issue Date'),
            subquery.c.max_return_date.label('Return Date'),
            subquery.c.total_rent_fee.label('Rent Fee'),
        ).join(student, rent.stu_id == student.id).join(Book, rent.book_id == Book.id).outerjoin(subquery, (subquery.c.stu_id == rent.stu_id) & (subquery.c.book_id == rent.book_id)).filter(student.name.ilike(f'%{search}%')).order_by(desc(rent.date)).all()
        
        transaction_by_id = db.session.query(
            rent.rid.label('Transaction Id'),
            Book.title.label('Book Title'),
            student.name.label('Student Name'),
            rent.date.label('Issue Date'),
            subquery.c.max_return_date.label('Return Date'),
            subquery.c.total_rent_fee.label('Rent Fee'),
        ).join(student, rent.stu_id == student.id).join(Book, rent.book_id == Book.id).outerjoin(subquery, (subquery.c.stu_id == rent.stu_id) & (subquery.c.book_id == rent.book_id)).filter(rent.rid == search).order_by(desc(rent.date)).all()
        
        if transactions_by_name:
            transactions = transactions_by_name
        elif transaction_by_id:
            transactions = transaction_by_id
        else:
            transactions = []

    return render_template('transactions.html', fees=transactions)




#def calculate_rent(transaction):
#    charge=Charges.query.first()
#    rent=(datetime.date.today() - transaction.Transaction.issue_date.date() ).days * charge.rentfee
#    return rent

#API_BASE_URL = "https://frappe.io/api/method/frappe-library"







@app.route('/userlogin')
def login():
    return render_template('userlogin.html')


@app.route('/logout', methods=['POST'])
def logout():
    # Add any necessary logout logic here, such as clearing session data
    flash('You have been successfully logged out', 'success')
    return jsonify({'redirect': url_for('login')})


@app.route('/dashboard', methods=['POST'])
def dashboard():
    username = request.form['username']
    password = request.form['password']

    if username == '1234' and password == '1234':
        return redirect('http://127.0.0.1:5000/')  # Redirect to the specified URL

    # Rest of your existing code for normal login
    try:
        user = student.query.filter_by(id=username, password=password).one()
    except:
        user = None

    if user:
        # Fetch user's name
        user_name = user.name

        # Example dictionary mapping book titles to links
        title_to_link = {
            'IITM CSE JAVA': 'https://drive.google.com/file/d/1O3pSFNscduWrMRIaBUawLwivsShujKJ0/view?usp=sharing',
            'IITM CSE PYTHON': 'https://drive.google.com/file/d/1ech-FKS2DI21BT9t5jSVqixH4McV-igg/view?usp=sharing',
            'IITM CSE ENGLISH': 'https://drive.google.com/file/d/1ieQLQArRBDWWldF3joZUsFgTQ6R1JG4P/view?usp=sharing',
            'IITM CSE MATHEMATICS':'https://drive.google.com/file/d/1KrtEmvoOBV45TqDGjUMSioi_Yi7-FUQh/view?usp=sharing',
            'IITM CSE DBMS':'https://drive.google.com/file/d/1OR1mQ_PgKVE6HvpRFFySsu4l0RtMibR2/view?usp=sharing',
            'IITM CSE C PROG':'https://drive.google.com/file/d/1qc6ojmq7M1jkqdWdnMK4uP9_pCyOFRkS/view?usp=sharing'
            # Add more titles and links as needed
        }

        books = Book.query.all()

        approved_books = rent.query.join(Book, rent.book_id == Book.id).\
                         filter(rent.stu_id == username, rent.status == 'Approved').\
                         with_entities(rent.rid, Book.title, Book.author).all()

        # Pass 'user_id' and the title_to_link dictionary to the template
        return render_template('dashboard.html', username=user_name, user_id=str(username), approved_books=approved_books,books=books, title_to_link=title_to_link)
    else:
        flash('Invalid username or password', 'error')
        return redirect(url_for('dashboard'))


    
@app.route('/request', methods=['POST'])
def request_book():
    user_id = request.form.get('user_id')
    book_id = request.form.get('book_id')

    # Check if the user has already requested 5 books
    current_requests = rent.query.filter_by(stu_id=user_id, status='Pending').count()

    if current_requests >= 5:
        flash_message = 'You have reached the maximum limit of 5 book requests. Please wait for some requests to be processed.'
        return jsonify({'status': 'error', 'message': flash_message})

    # Generate a random RID (4 digits)
    rid = str(random.randint(1000, 9999))

    # Fetch book and student information
    book = Book.query.get(book_id)
    student_info = student.query.get(user_id)

    # Add entry to Rent table
    new_rent = rent(rid=rid, book_id=book_id, borrowed_quantity=1, stu_id=user_id,
                    date=datetime.utcnow(), status='Pending')

    try:
        db.session.add(new_rent)
        db.session.commit()
        flash_message = 'Book request submitted successfully!'
    except IntegrityError:
        db.session.rollback()
        flash_message = 'Error submitting request. Please try again.'

    return jsonify({'status': 'success', 'message': flash_message})


@app.route('/approve_requests')
def approve_requests():
    # Fetch rent objects from the database using SQLAlchemy
    rent_objects = db.session.query(rent, student, Book).\
        join(student).join(Book).order_by(desc(rent.date)).all()

    return render_template('approve_requests.html', rent_objects=rent_objects)


@app.route('/rents_page')
def rents_page():
    # Assuming rents is a list of rent objects fetched from the database
    rents = rent.query.all()  # You may need to adjust this query based on your actual data
    return render_template('rents_page.html', rents=rents)


@app.route('/approve_request/<int:rid>', methods=['GET', 'POST'])
def approve_request(rid):
    if request.method == 'POST':
        # Fetch the rent object by RID
        rent_object = rent.query.get(rid)

        if rent_object:
            # Check if the book is available
            if rent_object.status == 'Pending':
                # Fetch the corresponding book
                book = Book.query.get(rent_object.book_id)

                # Check if there are available copies to approve the request
                if book.copies - book.rented > 0:
                    # Update the status to 'Approved'
                    rent_object.status = 'Approved'

                    # Update the book's rented and copies columns
                    book.rented += 1
                    

                    try:
                        db.session.commit()
                        flash('Request approved successfully!', 'success')
                    except IntegrityError:
                        db.session.rollback()
                        flash('Error approving request. Please try again.', 'error')
                else:
                    flash('No available copies to approve the request.', 'warning')
            else:
                flash('This request has already been approved.', 'warning')
        else:
            flash('Request not found.', 'error')

        return redirect(url_for('approve_requests'))
    else:
        # Handle GET request (if needed)
        return render_template('approve_request.html', rid=rid)
    

@app.route('/returnbook')
def return_book():
    # Fetch data from the 'rent' table
    data = rent.query.order_by(desc(rent.date)).all()

    return render_template('returnbook.html', data=data)

@app.route('/process_return', methods=['POST'])
def process_return():
    rent_id = request.form.get('rent_id')
    rent_record = rent.query.get(rent_id)

    if rent_record:
        # Update the status to "Returned"
        rent_record.status = 'Returned'

        # Fetch the corresponding book
        book = Book.query.get(rent_record.book_id)

        # Increase the "copies" column for the returned book
        book.copies += 1

        try:
            db.session.commit()

            # Assuming rent_record.date is already a datetime object
            issue_date = rent_record.date

            # Create a new entry in the fee table
            fee_entry = fee(
                stu_id=rent_record.stu_id,
                book_id=rent_record.book_id,
                issue_date=issue_date,
                return_date=datetime.now(),  # Current date and time
                rent_fee=calculate_rent_fee(issue_date)  # Calculate rent fee
            )
            db.session.add(fee_entry)
            db.session.commit()

            flash('Book returned successfully!', 'success')
        except IntegrityError:
            db.session.rollback()
            flash('Error processing return. Please try again.', 'error')

    return redirect(url_for('return_book'))

def calculate_rent_fee(issue_date):
    # Assuming issue_date is a datetime object
    return_date = datetime.now()
    time_difference = return_date - issue_date
    hours_difference = time_difference.total_seconds() / 3600  # Convert seconds to hours

    # Assuming rent_fee is 2 rupees per hour
    return max(0, hours_difference) * 2.0  # Minimum rent_fee is 0


def calculate_total_rent_current_month():
    # Get the current month and year
    current_month = datetime.now().month
    current_year = datetime.now().year

    # Calculate the sum of rent_fee for the current month
    total_rent_current_month = db.session.query(func.sum(fee.rent_fee)).\
        filter(func.strftime("%m", fee.return_date) == str(current_month)).\
        filter(func.strftime("%Y", fee.return_date) == str(current_year)).scalar()

    # If there are no entries for the current month, set total_rent_current_month to 0
    total_rent_current_month = total_rent_current_month or 0

    return total_rent_current_month


@app.route('/books', methods=['GET', 'POST'])
def books():
    # Assuming you have fetched all books from the database
    all_books = Book.query.all()

    # Group books by author using defaultdict
    books_by_author = defaultdict(list)
    for book in all_books:
        books_by_author[book.author].append(book)

    # Pass the grouped data to the template
    return render_template('books.html', books_by_author=books_by_author)


@app.route('/register', methods=['POST'])
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        register_name = request.form['register_name']
        register_id = request.form['register_id']
        register_password = request.form['register_password']

        # Check if the user with the given ID already exists
        existing_user = student.query.filter_by(id=register_id).first()
        if existing_user:
            flash('User with this ID already exists', 'error')
            return redirect(url_for('index'))

        # If the user doesn't exist, create a new user and add it to the database
        new_user = student(id=register_id, name=register_name, password=register_password)
        db.session.add(new_user)
        db.session.commit()

        flash('Registration successful! You can now log in.', 'success')

        # Add the registration success message to the JavaScript popup
        return render_template('userlogin.html', register_success=True)

    return render_template('register.html', flashes=flash.get_messages(with_categories=True))




@app.route('/readbook', methods=['POST'])
def read_book():
    book_title = request.form['book_title']
    title_to_link = {
        'IITM CSE JAVA': 'https://drive.google.com/file/d/1J-S42V46LJ9pZozYwKrSrgwJn1sSVXz2/view?usp=sharing',
        # Add more titles and links as needed
    }
    link = title_to_link.get(book_title, '#')  # Use '#' as a fallback link if the title is not found
    return redirect(link)


@app.route('/top_books')
def top_books():
    # Query to get the top 3 most requested books
    top_books = (
        db.session.query(Book.title, func.count(rent.book_id).label('total_requests'))
        .join(rent)
        .group_by(Book.id)
        .order_by(func.count(rent.book_id).desc())
        .limit(3)
        .all()
    )

    return render_template('top_books.html', top_books=top_books)

@app.route('/issue_book', methods=['GET', 'POST'])
def issue_book():
    if request.method == 'POST':
        stu_id = request.form.get('stu_id')
        book_id = request.form.get('book_id')

        try:
            student_obj = student.query.filter_by(id=stu_id).one()
            book_obj = Book.query.filter_by(id=book_id).one()

            # Generate a random RID (between 10000 and 99999)
            rid = random.randint(10000, 99999)

            # Update rent table
            new_rent = rent(rid=rid, book_id=book_id, borrowed_quantity=1, stu_id=stu_id, date=datetime.utcnow(), status='Approved')

            db.session.add(new_rent)
            db.session.commit()

            flash('Book issued successfully! ', 'success')
        except NoResultFound:
            flash('Student or book not found. Please check the IDs and try again.', 'error')
        except IntegrityError:
            db.session.rollback()
            flash('Error issuing book. Please try again.', 'error')

    return render_template('issue_book.html')

@app.route('/profile/<int:user_id>')
def profile(user_id):
    # Query the student table to get the user's details
    user_details = student.query.filter_by(id=user_id).first()

    # Render the profile template with user details
    return render_template('profile.html', user_details=user_details)

if __name__ == '__main__':
    app.run(debug=True)