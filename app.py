from flask import Flask, request, send_file, render_template_string
import psycopg2
import qrcode
import io
import uuid

app = Flask(__name__)

# --- Neon DB Connection ---
conn = psycopg2.connect(
    host="ep-red-wind-adchaz2b-pooler.c-2.us-east-1.aws.neon.tech",
    dbname="neondb",
    user="neondb_owner",
    password="npg_AVsJD9Kg2Cej",
    sslmode="require"
)

# --- HTML Template ---
HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>QR File Generator</title>
    <style>
        body { font-family: Arial; text-align: center; background: #f7f7f7; }
        form { margin-top: 40px; background: white; display: inline-block; padding: 30px; border-radius: 10px; box-shadow: 0 0 10px #ccc; }
        input[type=file], button { margin: 10px; padding: 10px; }
        img { margin-top: 20px; border: 2px solid #333; border-radius: 10px; }
    </style>
</head>
<body>
    <h2>📁 Upload File & Generate QR</h2>
    <form action="/" method="post" enctype="multipart/form-data">
        <input type="file" name="file" required>
        <br>
        <button type="submit">Generate QR</button>
    </form>

    {% if qr_data %}
        <h3>Scan to Download:</h3>
        <img src="data:image/png;base64,{{ qr_data }}" width="250">
        <p><a href="{{ file_url }}" target="_blank">{{ file_url }}</a></p>
    {% endif %}
</body>
</html>
"""

# --- Home route (upload + generate QR) ---
@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        uploaded = request.files["file"]
        if not uploaded:
            return "No file uploaded", 400

        # Generate unique file ID
        file_id = str(uuid.uuid4())

        # Save to Neon DB
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO qr_files (file_id, filename, filedata) VALUES (%s, %s, %s)",
            (file_id, uploaded.filename, psycopg2.Binary(uploaded.read()))
        )
        conn.commit()
        cur.close()

        # Generate QR for download link
        download_url = request.host_url + "download/" + file_id
        qr = qrcode.make(download_url)
        buf = io.BytesIO()
        qr.save(buf, format="PNG")
        qr_data = io.BytesIO(buf.getvalue()).getvalue()

        import base64
        encoded = base64.b64encode(qr_data).decode('utf-8')

        return render_template_string(HTML, qr_data=encoded, file_url=download_url)

    return render_template_string(HTML)


# --- File download route ---
@app.route("/download/<file_id>")
def download(file_id):
    cur = conn.cursor()
    cur.execute("SELECT filename, filedata FROM qr_files WHERE file_id = %s", (file_id,))
    result = cur.fetchone()
    cur.close()

    if not result:
        return "❌ File not found", 404

    filename, filedata = result
    return send_file(io.BytesIO(filedata), as_attachment=True, download_name=filename)


if __name__ == "__main__":
    app.run(debug=True)
