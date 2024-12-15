'''
Main module to run the Flask application.
'''
from bokeh.embed import components
from flask import Flask, render_template
from scripts.plot import bokeh_general_layout


app = Flask(__name__)

@app.route('/')
def index():

    script, div = components(bokeh_general_layout)
    return render_template('index.html', script=script, div=div)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=7860, debug=True)
