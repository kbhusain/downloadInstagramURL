import os
import tempfile
from flask import Flask, request, send_file, render_template_string, jsonify, after_this_request
import yt_dlp

app = Flask(__name__)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Instagram MP4 Downloader</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background-color: #fafafa;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            margin: 0;
        }
        .container {
            background: #ffffff;
            padding: 2rem;
            border-radius: 12px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
            width: 100%;
            max-width: 450px;
            text-align: center;
        }
        h2 {
            margin-top: 0;
            color: #262626;
        }
        input[type="url"] {
            width: 100%;
            padding: 12px;
            margin: 12px 0;
            border: 1px solid #dbdbdb;
            border-radius: 6px;
            box-sizing: border-box;
            font-size: 14px;
        }
        button {
            width: 100%;
            padding: 12px;
            background-color: #0095f6;
            color: white;
            border: none;
            border-radius: 6px;
            font-size: 14px;
            font-weight: 600;
            cursor: pointer;
            transition: background-color 0.2s;
        }
        button:hover {
            background-color: #1877f2;
        }
        button:disabled {
            background-color: #b2dffc;
            cursor: not-allowed;
        }
        .status {
            margin-top: 15px;
            font-size: 13px;
            color: #8e8e8e;
        }
        .error {
            color: #ed4956;
        }
    </style>
</head>
<body>
    <div class="container">
        <h2>Instagram Video Downloader</h2>
        <form id="downloadForm">
            <input type="url" id="postUrl" placeholder="Paste Instagram Post or Reel URL..." required>
            <button type="submit" id="submitBtn">Download MP4</button>
        </form>
        <div id="status" class="status"></div>
    </div>

    <script>
        const form = document.getElementById('downloadForm');
        const statusDiv = document.getElementById('status');
        const submitBtn = document.getElementById('submitBtn');

        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            const url = document.getElementById('postUrl').value.trim();
            
            submitBtn.disabled = true;
            statusDiv.className = 'status';
            statusDiv.textContent = 'Fetching video... This may take a few seconds.';

            try {
                const response = await fetch('/download', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ url })
                });

                if (!response.ok) {
                    const errData = await response.json();
                    throw new Error(errData.error || 'Failed to download video.');
                }

                // Convert response to blob and trigger browser download
                const blob = await response.blob();
                const downloadUrl = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = downloadUrl;
                a.download = 'instagram_clip.mp4';
                document.body.appendChild(a);
                a.click();
                a.remove();
                window.URL.revokeObjectURL(downloadUrl);

                statusDiv.textContent = 'Download complete!';
            } catch (err) {
                statusDiv.className = 'status error';
                statusDiv.textContent = err.message;
            } finally {
                submitBtn.disabled = false;
            }
        });
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/download', methods=['POST'])
def download():
    data = request.get_json()
    url = data.get('url', '').strip()

    if not url or 'instagram.com' not in url:
        return jsonify({'error': 'Please provide a valid Instagram URL.'}), 400

    # Create a temporary directory to store the downloaded file safely
    temp_dir = tempfile.mkdtemp()
    output_template = os.path.join(temp_dir, '%(id)s.%(ext)s')

    ydl_opts = {
        'format': 'best[ext=mp4]/best',
        'outtmpl': output_template,
        'quiet': True,
        'no_warnings': True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)

        if not os.path.exists(filename):
            return jsonify({'error': 'No downloadable video found at this URL.'}), 404

        # Clean up the temporary file after the response is sent
        @after_this_request
        def cleanup(response):
            try:
                os.remove(filename)
                os.rmdir(temp_dir)
            except (OSError, FileNotFoundError):
                pass
            return response

        return send_file(
            filename,
            as_attachment=True,
            download_name=f"{info.get('id', 'instagram_clip')}.mp4",
            mimetype='video/mp4'
        )

    except Exception as e:
        return jsonify({'error': 'Could not extract video. Ensure the post is public and contains a video.'}), 500

if __name__ == '__main__':
    app.run(debug=False, port=5000)
