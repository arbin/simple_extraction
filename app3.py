import os
import requests
from flask import Flask, request, render_template
from bs4 import BeautifulSoup
from urllib.parse import urljoin

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = "downloaded_pdfs"
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)


def scrape_pdfs(url):
    """Scrapes a webpage and extracts direct PDF links."""
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')

        # Extract PDF links directly
        pdf_links = [urljoin(url, link['href']) for link in soup.find_all('a', href=True) if
                     link['href'].endswith('.pdf')]

        return pdf_links
    except requests.exceptions.RequestException as e:
        return f"Error fetching URL: {e}"


def download_pdfs(pdf_links):
    """Downloads PDFs and saves them locally."""
    downloaded_files = []

    for pdf_url in pdf_links:
        try:
            pdf_filename = pdf_url.split("/")[-1]
            pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], pdf_filename)

            response = requests.get(pdf_url, stream=True, timeout=10)
            response.raise_for_status()

            with open(pdf_path, "wb") as pdf_file:
                for chunk in response.iter_content(chunk_size=8192):
                    pdf_file.write(chunk)

            downloaded_files.append(pdf_filename)

        except requests.exceptions.RequestException:
            pass  # Ignore failed downloads

    return downloaded_files


@app.route("/", methods=["GET", "POST"])
def index():
    pdf_links = []
    downloaded_files = []

    if request.method == "POST":
        url = request.form.get("url")
        if url:
            pdf_links = scrape_pdfs(url)
            if pdf_links:
                downloaded_files = download_pdfs(pdf_links)

    return render_template("index.html", pdf_links=pdf_links, downloaded_files=downloaded_files)


if __name__ == "__main__":
    app.run(debug=True)


# https://file-examples.com/index.php/sample-documents-download/sample-pdf-download/