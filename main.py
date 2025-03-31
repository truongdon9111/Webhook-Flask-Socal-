# Auto Upload Server: Tải video từ Google Drive và đẩy link về Make.com

from flask import Flask, request, jsonify
import requests
import io
import threading
import os
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

app = Flask(__name__)

# ==== CONFIG ==== #
SECRET_KEY = "YOUR_SECRET_KEY"  # Để xác thực khi nhận request
SERVICE_ACCOUNT_FILE = "service-account.json"  # File key của Google Service Account
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
PORT = int(os.environ.get("PORT", 5000))

# ==== INIT GOOGLE DRIVE API ==== #
creds = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE,
    scopes=SCOPES
)
drive_service = build('drive', 'v3', credentials=creds)

# ==== DOWNLOAD FILE FROM GOOGLE DRIVE ==== #
def download_file_from_drive(file_id):
    request = drive_service.files().get_media(fileId=file_id)
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request, chunksize=10 * 1024 * 1024)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    fh.seek(0)
    return fh

# ==== UPLOAD FILE TO TRANSFER.SH ==== #
def upload_to_transfersh(file_stream, filename):
    files = {'file': (filename, file_stream)}
    response = requests.post(f'https://transfer.sh/{filename}', files=files)
    return response.text.strip()

# ==== BACKGROUND JOB ==== #
def process_download(file_id, filename, callback_url):
    try:
        file_stream = download_file_from_drive(file_id)
        public_url = upload_to_transfersh(file_stream, filename)
        result = {"file_id": file_id, "public_url": public_url}
        requests.post(callback_url, json=result)
    except Exception as e:
        error_result = {"file_id": file_id, "error": str(e)}
        requests.post(callback_url, json=error_result)

# ==== API ENDPOINT ==== #
@app.route('/download', methods=['POST'])
def download():
    data = request.get_json()
    file_id = data.get('file_id')
    callback_url = data.get('callback_url')
    secret = data.get('secret')
    filename = data.get('filename', f"{file_id}.mp4")

    if secret != SECRET_KEY:
        return jsonify({"error": "Unauthorized"}), 401
    if not file_id or not callback_url:
        return jsonify({"error": "Missing file_id or callback_url"}), 400

    threading.Thread(target=process_download, args=(file_id, filename, callback_url)).start()
    return jsonify({"status": "processing"}), 202

# ==== START SERVER ==== #
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=PORT)
