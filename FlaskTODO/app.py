from flask import Flask, render_template, url_for, redirect, request
import json
import os

tasks : list[dict] =  [
    {
        "name":"Some task",
        "status": "completed"
    },
    {
        "name":"Other task",
        "status" : "todo"
    }
]
# taskname : completion status

FILEPATH = "tasks.json"

def load_tasks():
    global tasks
    if os.path.exists(FILEPATH):
        with open(FILEPATH,"r") as file:
            tasks = json.load(file)
    else:
        open("FILEPATH").close()
        load_tasks()

def save_tasks():
    global tasks
    with open(FILEPATH,"w") as file:
        json.dump(tasks, file, indent = 4)

class App:
    def __init__(self):
        self.app = Flask(__name__, template_folder = "templates")
        load_tasks()
        save_tasks()

        self.routes()

    def routes(self):
        @self.app.route("/")
        @self.app.route("/todo")
        def load_todo():
            return render_template("todolist.html",tasks=tasks)

        @self.app.route("/completetask/<string:task_name>")
        def complete_task(task_name):
            for task in tasks:
                if task.get('name') == task_name:
                    task["status"] = "completed"

            save_tasks()
            load_tasks()
            return redirect(url_for("load_todo"))

        @self.app.route("/deletetask/<string:task_name>")
        def delete_task(task_name):
            for task in tasks:
                if task.get("name") == task_name:
                    tasks.remove(task)
            save_tasks()
            load_tasks()
            return redirect(url_for("load_todo"))

        @self.app.route("/addtask",methods=["POST","GET"])
        def add_task():
            if request.method == "GET": return render_template("newtask.html")
            elif request.method == "POST":
                task_name = request.form.get("task_name")
                tasks.append({"name":task_name,"status":"todo"})
            save_tasks()
            load_tasks()
            return redirect(url_for("load_todo"))


app = App().app
if __name__ == '__main__':
    app.run()