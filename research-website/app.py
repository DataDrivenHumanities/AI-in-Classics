from flask import Flask, render_template, request, redirect, url_for
import pandas as pd

app = Flask(__name__)

#Load dataset
df = pd.read_csv('0-9999_edited.csv')

@app.route('/', methods=['GET', 'POST'])
def index():
    result = None
    if request.method == 'POST':
        user_input = request.form['serial']
        result = lookup_value(user_input)
        return render_template('display.html', result=result)
    return render_template('dashboard.html', result=result)

def lookup_value(user_input):
    result = df[df['serial'] == user_input]['aspect'].values[0]
    return result if len(result) > 0 else "Not found"

if __name__ == '__main__':
    app.run(debug=True)
