import os
import requests
from flask import Flask, request, render_template
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from openai import OpenAI

# Flask app setup
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = "downloaded_pdfs"
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Replace with your actual OpenAI API key
OPENAI_API_KEY = '<your-openai-api-key>'

client = OpenAI(api_key=OPENAI_API_KEY)


def scrape_and_get_pdfs(url):
    """Scrapes a webpage, extracts content, and uses OpenAI to find PDF links."""
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')
        text_content = soup.get_text(separator=" ", strip=True)
        links = [urljoin(url, link['href']) for link in soup.find_all('a', href=True)]

        # OpenAI prompt to extract PDFs
        prompt = f"""
        Analyze the following webpage content and extract all valid PDF file links:
        Links: {links}
        Return only a JSON list of valid PDF URLs.
        """

        response = client.chat.completions.create(
            model="gpt-4-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=300,
            temperature=0.3
        )

        pdf_links = response.choices[0].message.content.strip()

        if pdf_links.startswith("[") and pdf_links.endswith("]"):
            pdf_links = eval(pdf_links)  # Convert string JSON to Python list

        return pdf_links if isinstance(pdf_links, list) else []

    except requests.exceptions.RequestException as e:
        return f"Error fetching URL: {e}"


def download_pdfs(pdf_links):
    """Downloads PDFs from extracted links and saves them locally."""
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
            pdf_links = scrape_and_get_pdfs(url)
            if pdf_links:
                downloaded_files = download_pdfs(pdf_links)

    return render_template("index.html", pdf_links=pdf_links, downloaded_files=downloaded_files)


if __name__ == "__main__":
    app.run(debug=True)
