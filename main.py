from flask import Flask, request, jsonify
import requests
import os
import tempfile
import urllib.parse

app = Flask(__name__)

def download_file_from_drive(share_url):
    file_id = None
    if "id=" in share_url:
        file_id = share_url.split("id=")[-1]
    elif "file/d/" in share_url:
        file_id = share_url.split("file/d/")[1].split("/")[0]

    if not file_id:
        return None

    download_url = f"https://drive.google.com/uc?export=download&id={file_id}"
    response = requests.get(download_url, stream=True)
    if response.status_code != 200:
        return None

    temp_file = tempfile.NamedTemporaryFile(delete=False)
    for chunk in response.iter_content(chunk_size=8192):
        temp_file.write(chunk)
    temp_file.close()
    return temp_file.name

def upload_to_transfersh(file_path):
    filename = os.path.basename(file_path)
    with open(file_path, 'rb') as f:
        r = requests.put(f"https://transfer.sh/{filename}", data=f)
        if r.status_code == 200:
            return r.text
    return None

@app.route("/upload", methods=["POST"])
def handle_upload():
    data = request.get_json()
    drive_link = data.get("drive_link")

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

if __name__ == "__main__":
    app.run()
