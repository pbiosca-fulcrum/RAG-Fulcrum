import os
import datetime
import sqlite3
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash

# We now import the USERS_DB constant from database_setup
from app.database_setup import USERS_DB

auth_bp = Blueprint('auth', __name__)

def get_user(username):
    with sqlite3.connect(USERS_DB) as conn:
        cur = conn.cursor()
        cur.execute("SELECT id, username, password FROM users WHERE username = ?", (username,))
        row = cur.fetchone()
        if row:
            return {"id": row[0], "username": row[1], "password": row[2]}
    return None

def register_user(username, password):
    hashed = generate_password_hash(password)
    with sqlite3.connect(USERS_DB) as conn:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO users (username, password, created_at) VALUES (?, ?, ?)",
            (username, hashed, datetime.datetime.utcnow().isoformat())
        )
        conn.commit()

@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username").strip()
        password = request.form.get("password").strip()
        if get_user(username):
            flash("Username already taken.", "error")
            return render_template("register.html")
        try:
            register_user(username, password)
            flash("Registration successful. Please log in.", "success")
            return redirect(url_for("auth.login"))
        except Exception as e:
            flash("Registration failed: " + str(e), "error")
            return render_template("register.html")
    return render_template("register.html")

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username").strip()
        password = request.form.get("password").strip()
        user = get_user(username)
        if user and check_password_hash(user["password"], password):
            session["user"] = username
            flash("Logged in successfully.", "success")
            return redirect(url_for("main.index"))
        else:
            flash("Invalid credentials.", "error")
            return render_template("login.html")
    return render_template("login.html")

@auth_bp.route("/logout")
def logout():
    session.pop("user", None)
    flash("Logged out.", "info")
    return redirect(url_for("auth.login"))
