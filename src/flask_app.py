from bokeh.embed import components
from flask import Flask, render_template
from scripts.bokeh_plot import bokeh_layout


app = Flask(__name__)

@app.route('/')
def index():

  
    # Embed components
    script, div = components(bokeh_layout)
    return render_template('index.html', script=script, div=div)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=7860, debug=True)
