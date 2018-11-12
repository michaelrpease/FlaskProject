import os
import json
import requests
from flask import Flask, session, render_template, request, jsonify
from flask_session import Session
from sqlalchemy import create_engine, exc
from sqlalchemy.orm import scoped_session, sessionmaker

app = Flask(__name__)

# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))


@app.route("/")
def index():
    return render_template("index.html")
    
@app.route("/register", methods=["POST"])
def register():

	email = request.form.get("registerEmail")
	password = request.form.get("registerPassword")
		
	try:
		db.execute("INSERT INTO users (email, password) VALUES (:email, :password)",
			{"email": email, "password": password})
		db.commit()
		return render_template("login.html", message="Successfully Registered!")
	except exc.IntegrityError as e:
		db.rollback()
		return render_template("login.html", message="Error: Already Registered!")
		
		
@app.route("/login")
def login():

	return render_template("login.html")

	
@app.route("/search", methods=["POST"])
def search():

	email = request.form.get("loginEmail")
	password = request.form.get("loginPassword")
	
	currentUser, storedPassword = db.execute("SELECT id, password FROM users WHERE email = :email",
		{"email": email}).first()

	if password != storedPassword:
		return render_template("login.html", message="Error: Incorrect email or password!")
	else:
		session["user_id"] = currentUser
		return render_template("search.html")
		
	
@app.route("/results", methods=["POST"])
def results():
	
	filter = "%"+request.form.get("searchInput")+"%"
	results = db.execute("SELECT * FROM books WHERE isbn LIKE :filter OR title LIKE :filter OR author LIKE :filter",
		{"filter": filter}).fetchall()
		
	print(results)
		
	if results == []:
		message = "Sorry, no results found."
		return render_template("search.html", message=message)

	return render_template("search.html", results=results)


@app.route("/results/<isbn>", methods=["POST", "GET"])
def result(isbn):

	details = db.execute("SELECT * FROM books WHERE isbn = :isbn", {"isbn": isbn}).fetchall()
	reviews = db.execute("SELECT * FROM reviews JOIN users ON reviews.user_id=users.id").fetchall()
	user_id = session["user_id"]
	res = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": "pjM8I6hMgmjx16QHJQGaQ", "isbns": isbn}).json()
	work_ratings_count = res['books'][0]['work_ratings_count']
	average_rating = res['books'][0]['average_rating']
	
	if request.method == "POST":
	
		flag = db.execute("SELECT * FROM reviews WHERE isbn = :isbn AND user_id = :user_id",
			{"isbn": isbn, "user_id": user_id}).fetchall()
		review = request.form.get("review")
		rating = request.form.get("rating")
		
		if flag == []:
			db.execute("INSERT INTO reviews (isbn, user_id, rating, review) VALUES (:isbn, :user_id, :rating, :review)",
				{"isbn": isbn, "user_id": user_id, "rating": rating, "review": review})
			db.commit()
			reviews = db.execute("SELECT * FROM reviews JOIN users ON reviews.user_id=users.id").fetchall()
			return render_template("details.html", details=details, reviews=reviews, work_ratings_count=work_ratings_count, average_rating=average_rating)
			
		else:
			message = "Sorry, you've already reviewed this title."
			return render_template("details.html", details=details, message=message, reviews=reviews, work_ratings_count=work_ratings_count, average_rating=average_rating)
	
	return render_template("details.html", details=details, reviews=reviews, work_ratings_count=work_ratings_count, average_rating=average_rating)
	

@app.route("/api/<isbn>", methods=["GET"])
def api(isbn):

	details = db.execute("SELECT * FROM books WHERE isbn = :isbn", {"isbn": isbn}).fetchall()
	
	if details == []:
	
		return jsonify({'Error': 'Invalid ISBN'}), 404
	
	res = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": "pjM8I6hMgmjx16QHJQGaQ", "isbns": isbn}).json()
	title = details[0].title
	author = details[0].author
	year = details[0].year
	isbn = details[0].isbn
	work_reviews_count = res['books'][0]['work_reviews_count']
	average_rating = res['books'][0]['average_rating']
	
	data = {'title':title, 
			'author':author,
			'year':year,
			'isbn':isbn,
			'review_count':work_reviews_count,
			'average_score':average_rating}
	data = jsonify(data)

	return(data)