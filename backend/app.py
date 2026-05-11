from flask import Flask, render_template, request, jsonify
import uuid
import time

import x

from werkzeug.security import generate_password_hash
from werkzeug.security import check_password_hash

from flask_cors import CORS

from icecream import ic
ic.configureOutput(prefix=f"___ | ", includeContext=True)

from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from datetime import timedelta

app = Flask(__name__)
CORS(app)  # allows everything

app.config["JWT_SECRET_KEY"] = "your-secret-key"
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(minutes=15)
jwt = JWTManager(app)


##############################
@app.get("/login")
@x.no_cache
def show_login():
    return render_template("page_login.html")


##############################
@app.post("/api/login")
def login():
    try:
        data = request.get_json()
        email = x.validate_email(data.get("email", ""))
        password = x.validate_user_password(data.get("password", "")).strip()
        db, cursor = x.db()
        q = "SELECT * FROM users WHERE user_email = %s"
        cursor.execute(q, (email,))
        user = cursor.fetchone()
        if not user:
            error_message = "Email not found"
            return error_message, 400
        
        if not check_password_hash(user["user_password"], password):
            error_message = "Password is incorrect"
            return error_message, 400

        if user["user_verified_at"] == 0:
            return "Please verify your email first", 400
     

        access_token = create_access_token(identity=user["user_pk"])

        return jsonify(access_token=access_token), 200
    
    except Exception as ex:
        ic(ex)
        if "company_exception email" in str(ex):
            return "invalid email", 400

        if "company_exception user_password" in str(ex):
            return f"user password {x.USER_PASSWORD_MIN} to {x.USER_PASSWORD_MAX} characters", 400

        return "something went wrong", 500


    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()




##############################
@app.get("/api/profile")
@jwt_required()
def show_profile():
    try:
        user_pk = get_jwt_identity()
        db, cursor = x.db()
        q = "SELECT user_pk, user_name, user_email, user_verified_at FROM users WHERE user_pk = %s"
        cursor.execute(q, (user_pk,))
        user = cursor.fetchone()
        if not user:
            return "Bruger ikke fundet", 404
        return jsonify(user), 200
    except Exception as ex:
        ic(ex)
        return "Noget gik vidst galt", 500
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()


##############################
@app.delete("/api/users")
@jwt_required()
def delete_user():
    try:
        user_pk = get_jwt_identity()
        db, cursor = x.db()
        q = "DELETE FROM users WHERE user_pk = %s"
        cursor.execute(q, (user_pk,))
        db.commit()
        if cursor.rowcount == 0:
            return "Bruger ikke fundet", 400
        return jsonify({"message": "Bruger slettet"}), 200
    except Exception as ex:
        ic(ex)
        return "Ups.. Noget gik galt", 500
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()


##############################
@app.get("/")
def index():
    return jsonify({"status":"ok", "message":"Connected", "routes": "Up and running"})


##############################
@app.route("/people")
def get_people():
    return jsonify({
        "people": [
            {"first_name":"A", "last_name":"Aa", "cpr":"1"},
            {"first_name":"B", "last_name":"Bb", "cpr":"2"},
            {"first_name":"C", "last_name":"Cc", "cpr":"3"},
        ]
    })  

##############################
@app.get("/sign-up")
def show_sign_up():
    return render_template("page_sign_up.html")

##############################
@app.post("/api/sign-up")
def sign_up():
    try:
        user_first_name = x.validate_user_first_name()
        email = x.validate_email( request.form.get("email", "" ))
        password = x.validate_user_password( request.form.get("password", "") ).strip()
        confirm_password = request.form.get("confirm_password", "").strip()

        if password != confirm_password:
            return "Passwords do not match", 400

        hashed_password = generate_password_hash(password)

        user_pk = uuid.uuid4().hex
        verification_key = uuid.uuid4().hex
        ic(verification_key)
        
        user_reset_password_key = uuid.uuid4().hex + uuid.uuid4().hex
        ic(user_reset_password_key)        

        db, cursor = x.db()
        q = "INSERT INTO users  VALUES (%s, %s, %s, %s, %s, %s, %s)"
        cursor.execute(q, (user_pk, user_first_name, verification_key, 0, user_reset_password_key, email, hashed_password))
        db.commit()
       
        html = render_template("email_welcome.html", verification_key=verification_key)

        x.send_email("Activate your account", html)
        return "Please check your email maybe it arrived in the spam folder", 200
    except Exception as ex: 
        ic(ex)
        if "company_exception user_first_name" in str(ex):
            return f"user first name {x.USER_FIRST_NAME_MIN} to {x.USER_FIRST_NAME_MAX} characters", 400
        if "company_exception email" in str(ex):
            return "invalid email", 400
        if "company_exception user_password" in str(ex):
            return f"user password {x.USER_PASSWORD_MIN} to {x.USER_PASSWORD_MAX} characters", 400

        return str(ex), 500
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()


##############################
@app.get("/verify/<key>")
def verify_account(key):
    try:
        key = x.validate_uuid4(key)
        db, cursor = x.db()
        user_verified_at = int(time.time())
        q = """
            UPDATE users
            SET user_verified_at = %s
            WHERE user_verification_key = %s AND user_verified_at = 0
        """
        cursor.execute(q, (user_verified_at, key))
        db.commit()
        if cursor.rowcount == 0:
            return "user already verified"

        return f"Welcome to the system, you are verified"
    except Exception as ex: 
        ic(ex)
        if "company_exception uuid4 invalid" in str(ex):
            return "Invalid key", 400

        return str(ex), 500
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()    

##############################
@app.get("/forgot-password")
def show_forgot_password():
    return render_template("page_forgot_password.html")

##############################
@app.post("/api/forgot-password")
def forgot_password():
    try:
        email = x.validate_email( request.form.get("email", "") )
        db, cursor = x.db()
        q = "SELECT user_reset_password_key AS 'key' FROM users WHERE user_email = %s"
        cursor.execute(q, (email,))
        row = cursor.fetchone()
        
        if not row:
            return "Email not found", 400
        
        html = render_template("email_forgot_password.html", user_reset_password_key=row["key"])
        
        x.send_email("Reset Password", html)

        return "Check your email"

    except Exception as ex:
        ic(ex)

        if "company_exception email" in str(ex):
            return "invalid email", 400

        return str(ex), 500
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()


##############################
@app.get("/reset-password/<key>")
def show_reset_password(key):
    try:
        key = x.validate_uuid4_paranoia(key)
        db, cursor = x.db()
        q = """SELECT user_reset_password_key FROM users WHERE user_reset_password_key = %s"""

        cursor.execute(q, (key,))
        row = cursor.fetchone()
        
        if not row: return "ups...", 400

        return render_template("page_reset_password.html", key=key)
    except Exception as ex: 
        ic(ex)
        if "company_exception uuid4 invalid" in str(ex):
            return "Invalid key", 400

        return str(ex), 500
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()


##############################
@app.post("/reset-password")
def reset_password():
    try:
        password = x.validate_user_password( request.form.get("password", "")).strip()

        confirm_password = request.form.get("confirm_password", "").strip()

        if password != confirm_password:
            return "Passwords do not match", 400
        
        key = x.validate_uuid4_paranoia( request.form.get("key", ""))

        hashed_password = generate_password_hash(password)

        db, cursor = x.db()
        q = "UPDATE users SET user_password = %s WHERE user_reset_password_key = %s"
        cursor.execute(q, (hashed_password, key))
        db.commit()

        if cursor.rowcount == 0:
            return "Invalid key", 400

        return "password changed, please login"
    
    except Exception as ex:
        ic(ex)

        if "company_exception user_password" in str(ex):
            return f"Password {x.USER_PASSWORD_MIN} to {x.USER_PASSWORD_MAX} characters", 400
        
        if "company_exception paranoia" in str(ex):
            return "Invalid key", 400
        
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()



##############################
@app.get("/api/locations")
def get_locations():
    try:
        db, cursor = x.db()
        q = "SELECT * FROM locations"
        cursor.execute(q)
        locations = cursor.fetchall()
        return jsonify(locations), 200
    except Exception as ex:
        ic(ex)
        return "Noget gik galt", 500
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()

##############################
@app.post("/api/cars")
@jwt_required()
def add_car():
    try:
        user_pk = get_jwt_identity()
        data = request.get_json()
        car_brand = data.get("car_brand", "").strip()
        car_license_plate = data.get("car_license_plate", "").strip()

        if not car_brand or not car_license_plate:
            return "Brand and license plate are required", 400

        car_pk = uuid.uuid4().hex
        db, cursor = x.db()
        q = "INSERT INTO cars VALUES (%s, %s, %s, %s)"
        cursor.execute(q, (car_pk, user_pk, car_brand, car_license_plate))
        db.commit()
        return jsonify({"message": "Bil tilføjet"}), 201
    except Exception as ex:
        ic(ex)
        return "Noget gik galt", 500
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()


##############################
@app.get("/api/cars")
@jwt_required()
def get_cars():
    try:
        user_pk = get_jwt_identity()
        db, cursor = x.db()
        q = "SELECT * FROM cars WHERE car_user_fk = %s"
        cursor.execute(q, (user_pk,))
        cars = cursor.fetchall()
        return jsonify(cars), 200
    except Exception as ex:
        ic(ex)
        return "Noget gik galt", 500
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()


