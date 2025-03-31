from flask import Flask, request, jsonify
import os
import requests
import tempfile
import gdown

app = Flask(__name__)

# Tải file từ Google Drive (link công khai)
def download_file_from_drive(share_url):
    try:
        output = tempfile.NamedTemporaryFile(delete=False).name
        gdown.download(url=share_url, output=output, quiet=False, fuzzy=True)
        return output
    except Exception as e:
        print("Error downloading:", e)
        return None

# Upload file lên transfer.sh và trả về link công khai
def upload_to_transfersh(file_path):
    try:
        filename = os.path.basename(file_path)
        with open(file_path, 'rb') as f:
            response = requests.put(f'https://transfer.sh/{filename}', data=f)
        if response.status_code == 200:
            return response.text.strip()
        else:
            print("Upload failed:", response.text)
            return None
    except Exception as e:
        print("Upload error:", e)
        return None

# Xử lý webhook POST
@app.route('/upload', methods=['POST'])
def handle_upload():
    data = request.get_json()
    drive_link = data.get('drive_link')

    if not drive_link:
        return jsonify({"error": "Missing drive_link"}), 400

    downloaded_file = download_file_from_drive(drive_link)

    if not downloaded_file:
        return jsonify({"error": "Failed to download file"}), 400

    public_url = upload_to_transfersh(downloaded_file)
    os.remove(downloaded_file)

    if public_url:
        return jsonify({"public_url": public_url})
    else:
        return jsonify({"error": "Failed to upload to transfer.sh"}), 500

# Khởi động server Flask
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
