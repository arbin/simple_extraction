import json
import os
import pdfplumber
import openai
import lxml.etree as ET
import fitz  # PyMuPDF for PDF extraction
from flask import Flask, request, render_template, send_file, jsonify

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = "uploads"
app.config['XML_FOLDER'] = "xml_files"

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['XML_FOLDER'], exist_ok=True)

OPENAI_API_KEY = '<your-openai-api-key>'
client = openai.OpenAI(api_key=OPENAI_API_KEY)


def extract_text_from_pdf(pdf_path):
    """Extracts text from a given PDF file."""
    text = ""
    with fitz.open(pdf_path) as doc:
        for page in doc:
            text += page.get_text("text") + "\n"
    return text


def get_profile_information(text):
    """Extract structured profile information using OpenAI"""
    prompt = f"""
    Extract structured profile information (Name, Address, Phone Number) from the following text.
    Ensure that each name is correctly matched to its corresponding address and phone number.
    Format the output as a JSON list like this:

    [
        {{
            "name": "John Doe",
            "address": "123 Main St, City, Country",
            "phone_number": "+123456789"
        }},
        {{
            "name": "Jane Smith",
            "address": "456 Elm St, City, Country",
            "phone_number": "+987654321"
        }}
    ]

    --- Text Start ---
    {text}
    --- Text End ---
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=500,
            temperature=0.3
        )

        extracted_data = response.choices[0].message.content.strip()

        if not extracted_data:  # 🔹 Check if response is empty
            raise ValueError("OpenAI API returned an empty response.")

        # 🔹 Ensure OpenAI's response is valid JSON
        extracted_data = extracted_data.strip("```json").strip("```").strip()

        return json.loads(extracted_data)  # Convert JSON string to dict

    except json.JSONDecodeError as e:
        return {"error": f"JSON Decode Error: {e}. Response was: {extracted_data}"}
    except Exception as e:
        return {"error": f"OpenAI API Error: {e}"}


def structured_data_to_xml(data, xml_output_path):
    """Converts structured extracted data into XML format."""
    root = ET.Element("document")

    names_element = ET.SubElement(root, "names")
    for name in data["names"]:
        ET.SubElement(names_element, "name").text = name

    addresses_element = ET.SubElement(root, "addresses")
    for address in data["addresses"]:
        ET.SubElement(addresses_element, "address").text = address

    phones_element = ET.SubElement(root, "phone_numbers")
    for phone in data["phone_numbers"]:
        ET.SubElement(phones_element, "phone").text = phone

    tree = ET.ElementTree(root)
    tree.write(xml_output_path, pretty_print=True, xml_declaration=True, encoding="UTF-8")

    return xml_output_path


def labeled_info_to_xml(labeled_info, filename):
    """Converts labeled profile information to XML format."""
    root = ET.Element("Profiles")

    for person in labeled_info:
        profile = ET.SubElement(root, "Profile")

        name = ET.SubElement(profile, "Name")
        name.text = person.get("name", "Unknown")

        address = ET.SubElement(profile, "Address")
        address.text = person.get("address", "Unknown")

        phone = ET.SubElement(profile, "PhoneNumber")
        phone.text = person.get("phone_number", "Unknown")

    xml_filename = filename.replace(".pdf", ".xml")
    xml_path = os.path.join(app.config['XML_FOLDER'], xml_filename)

    tree = ET.ElementTree(root)
    tree.write(xml_path, pretty_print=True, xml_declaration=True, encoding="UTF-8")

    return xml_filename  # Return XML filename


@app.route("/", methods=["GET", "POST"])
def index():
    extracted_text = None
    labeled_info = None
    xml_filename = None

    if request.method == 'POST':
        if 'pdf_file' in request.files:
            pdf_file = request.files['pdf_file']
            if pdf_file.filename != '':
                pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], pdf_file.filename)
                pdf_file.save(pdf_path)

                # Extract text from PDF (Assumes `extract_text_from_pdf` function exists)
                extracted_text = extract_text_from_pdf(pdf_path)

                # Use OpenAI to label extracted information (Assumes `get_profile_information` exists)
                labeled_info = get_profile_information(extracted_text)

                # Convert extracted info to XML
                if labeled_info:
                    xml_filename = labeled_info_to_xml(labeled_info, pdf_file.filename)

    return render_template('index.html', extracted_text=extracted_text, labeled_info=labeled_info, xml_filename=xml_filename)

@app.route("/download/<filename>")
def download_file(filename):
    """Serve the XML file for download."""
    xml_path = os.path.join(app.config['XML_FOLDER'], filename)
    if os.path.exists(xml_path):
        return send_file(xml_path, as_attachment=True)
    return "File not found", 404


@app.route("/convert-to-xml", methods=["POST"])
def convert_to_xml():
    """Converts structured data to XML and provides download link."""
    data = request.json
    filename = data.get("filename")
    pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)

    if not os.path.exists(pdf_path):
        return jsonify({"error": "File not found"}), 404

    xml_filename = filename.replace(".pdf", ".xml")
    xml_path = os.path.join(app.config['XML_FOLDER'], xml_filename)

    structured_data_to_xml(data, xml_path)

    return jsonify({"xml_file": xml_filename})


if __name__ == "__main__":
    app.run(debug=True)
