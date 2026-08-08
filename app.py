from flask import Flask, render_template

from models import db

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'


@app.route('/')
def root():
   my_tasks = ["smile", "Your are the best!", "No one make you sad"] 
   return render_template('todo.html', all_tasks=my_tasks)

if __name__ == '__main__':
    with app.app_context():
        # db.init_app(app)
        db.create_all()