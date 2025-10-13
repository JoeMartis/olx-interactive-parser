from flask import Flask, request, send_from_directory, abort, redirect, url_for
import os
import tempfile
from olx_parser import InteractiveOLXParser

app = Flask(__name__, static_folder='static')
UPLOAD_FOLDER = tempfile.gettempdir()
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024

@app.route('/')
def index():
    # Serve index.html from static/html/
    return send_from_directory('static/html', 'index.html')

@app.route('/upload', methods=['POST'])
def upload():
    file = request.files.get('olxfile')
    if not file:
        return "No file uploaded", 400

    # Get course ID and construct Studio URL
    course_id = request.form.get('course_id', '').strip()
    studio_base_url = request.form.get('studio_base_url', '').strip() or 'https://studio.courses.rc.learn.mit.edu'
    
    course_url = None
    if course_id:
        # Construct full Studio URL: {base}/container/block-v1:{course_id}
        course_url = f'{studio_base_url.rstrip("/")}/container/block-v1:{course_id}'

    # Save uploaded file to a temp location
    temp_path = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(temp_path)

    # Run the parser
    output_html = os.path.splitext(temp_path)[0] + '_structure.html'
    with InteractiveOLXParser(temp_path) as parser:
        structure = parser.parse_course_structure()
        parser.generate_interactive_html(structure, output_html, course_url)

    # Serve the generated HTML
    return send_from_directory(os.path.dirname(output_html), os.path.basename(output_html))

@app.errorhandler(413)
def too_large(e):
    return "File is too large (max 5MB).", 413

@app.errorhandler(405)
def method_not_allowed(e):
    # Redirect to home page for Method Not Allowed
    return redirect(url_for('index'))

@app.errorhandler(404)
def page_not_found(e):
    # Redirect to home page for Not Found
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True) 