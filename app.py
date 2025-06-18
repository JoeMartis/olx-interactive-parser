from flask import Flask, request, send_file, redirect, url_for
import os
import tempfile
from olx_parser import InteractiveOLXParser

app = Flask(__name__)
UPLOAD_FOLDER = tempfile.gettempdir()

@app.route('/')
def index():
    return send_file('index.html')

@app.route('/upload', methods=['POST'])
def upload():
    file = request.files.get('olxfile')
    if not file:
        return "No file uploaded", 400

    # Save uploaded file to a temp location
    temp_path = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(temp_path)

    # Run the parser
    output_html = os.path.splitext(temp_path)[0] + '_structure.html'
    with InteractiveOLXParser(temp_path) as parser:
        structure = parser.parse_course_structure()
        parser.generate_interactive_html(structure, output_html)

    # Serve the generated HTML
    return send_file(output_html)

if __name__ == '__main__':
    app.run(debug=True) 