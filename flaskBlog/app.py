
#TODO: uuid for each post | a homepage with random posts | post actions

from flask import Flask
from flask import url_for
from flask import request
from flask import session
from flask import render_template
from flask import redirect
from flask import flash

import psycopg2
from hashlib import sha256
from uuid import uuid4
import datetime

SECRET_KEY = "veryverysecretkey"

def generate_hash(string : str) -> str: return sha256(string.encode()).hexdigest()
def generate_uuid() -> str: return uuid4().hex


class UsernameExists(Exception):...



class Database:
    def __init__(self):
        try:
            self.conn = psycopg2.connect("postgresql://postgres:1234@localhost:5432/test")
            print("connection successfull")
        except Exception as e:
            exit(e)

        self.cursor = self.conn.cursor()

    def fetch_password(self, username : str) -> str:
        self.cursor.execute(f"select password from login_data where username = '{username}' ;")
        return self.cursor.fetchone()[0]

    def add_user(self, username, password) -> None:
        if self.check_username_existence(username): raise UsernameExists
        else:
            hashed_password = generate_hash(password)
            self.cursor.execute(f"insert into login_data(username, password) values('{username.replace(" ","")}','{hashed_password}');")
            self.conn.commit()


    def check_username_existence(self, username_to_check) -> bool:
        query=f"""
        select exists(
            select 1 from login_data where username='{username_to_check}'
        );
              """
        self.cursor.execute(query)
        #true if username exists
        return self.cursor.fetchone()[0]

    def get_posts_by_author(self, username):
        self.cursor.execute(f"select * from posts where author ='{username.replace(' ','')}' ;")
        return self.cursor.fetchall()

    def create_post(self, author, title, content):
        self.cursor.execute("insert into posts(uuid,author, title, content) values(%s,%s,%s,%s);", (generate_uuid(),author, title, content))
        self.conn.commit()

    def get_posts_by_uuid(self,uuid : str) -> dict:
        self.cursor.execute(f"select * from posts where uuid='{uuid}';" )
        postdata = self.cursor.fetchall()[0]
        uuid = postdata[0]
        author = postdata[1]
        title = postdata[2]
        content = postdata[3]
        date_created : str = postdata[4].strftime("%d-%m-%y at %I:%M %p")
        date_modified : str = postdata[5].strftime("%d-%m-%y at %I:%M %p")

        return dict(zip( ("uuid", "author", "title", "content", "date_created", "date_modified"),(uuid, author, title, content, date_created, date_modified)))

    def delete_post_uuid(self, uuid : str):
        self.cursor.execute(f"delete from posts where uuid='{uuid}';")
        self.conn.commit()

    def update_post(self, uuid ,title, content, updated_date):
        self.cursor.execute(f"update posts set title=%s, content=%s, modified_date=%s where uuid=%s ;",(title, content, updated_date, uuid))
        self.conn.commit()



class App:
    def __init__(self):
        self.app = Flask(__name__, template_folder = "templates")
        self.app.secret_key = SECRET_KEY
        self.database = Database()

        self.filters()
        self.routes()

    def routes(self):
        @self.app.route("/")
        def main_menu():
            if "username" in session.keys(): #ie user is already logged in
                return redirect(url_for("content"))
            else: # user is not logged in
                return redirect(url_for("login"))

        @self.app.route("/login",methods=["GET","POST"])
        def login():
            if request.method == "GET":
                return render_template("login.html")
            elif request.method == "POST":
                if "username" in request.form.keys() and "password" in request.form.keys():
                    username = request.form.get("username")
                    password = request.form.get("password")

                    if self.database.check_username_existence(username):
                        if self.database.fetch_password(username) == generate_hash(password):
                            session["username"] = username
                            session["password"] = password
                            return redirect(url_for("content"))
                        else:
                            flash("Incorrect password")
                            return redirect(url_for("login"))

                    else:
                        flash("No such user exists")
                        return redirect(url_for("login"))



        @self.app.route("/content",methods=["GET"])
        def content():
            if "username" in session.keys():
                return render_template("content.html", posts=self.database.get_posts_by_author(session.get("username")))
            else:
                flash("You need to be logged in to view content")

        @self.app.route("/logout")
        def logout():
            session.pop("username",None)
            session.pop("password",None)
            return redirect(url_for("login"))

        @self.app.route("/createuser",methods=["POST","GET"])
        def create_user():
            if request.method == "GET": return render_template("create_user.html")
            elif request.method == "POST":
                if "username" in request.form.keys() and "password" in request.form.keys():
                    username = request.form.get("username")
                    password = request.form.get("password")
                    if self.database.check_username_existence(username):
                        flash("Username already exists")
                        return redirect(url_for("create_user"))
                    else:
                        self.database.add_user(username = username,password = password) #password hashing occurs in method definition inside the class
                        return  redirect(url_for("login"))
                else:
                    flash("Improper credentials")
                    return redirect(url_for("create_user"))

        @self.app.route("/createpost", methods=["POST","GET"])
        def createpost():
            if request.method == "GET":
                if "username" in session.keys(): #ie user is logged in
                    return render_template("create_post.html")
                else:
                    return redirect("/login")

            elif request.method == "POST":
                author = session.get("username")
                title = request.form.get("title")
                post_content = request.form.get("post_content")
                self.database.create_post(author=author,title=title,content=post_content)

                return redirect(url_for("content"))

        @self.app.route('/post/<string:uuid>')
        def go_to_post(uuid : str):
            return render_template("view_post.html",post=self.database.get_posts_by_uuid(uuid))

        @self.app.route("/post/delete/<string:uuid>")
        def delete_post(uuid : str):
            self.database.delete_post_uuid(uuid)
            return redirect(url_for("content"))

        @self.app.route("/post/edit/<string:uuid>", methods=["POST","GET"])
        def edit_post(uuid : str):
            if request.method == "GET":
                return render_template("edit_post.html",post=self.database.get_posts_by_uuid(uuid=uuid))

            elif request.method=="POST":
                new_title = request.form.get("title")
                new_content = request.form.get("post_content")
                updated_date = datetime.datetime.now()
                self.database.update_post(uuid=uuid,title=new_title, content=new_content, updated_date = updated_date)
                return redirect(url_for("content"))

    def filters(self):
        @self.app.template_filter('date_normalize')
        def date_normalize(date : datetime.datetime):
            return date.strftime("%d-%m-%y at %I:%M %p")
app = App().app
if __name__ == '__main__':
    app.run()