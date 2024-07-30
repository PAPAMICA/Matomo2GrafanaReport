<p align="center">
  <a href="https://mickaelasseline.com">
    <img src="https://zupimages.net/up/20/04/7vtd.png" width="140px" alt="PAPAMICA" />
  </a>
</p>

<p align="center">
  <a href="#"><img src="https://readme-typing-svg.herokuapp.com?center=true&vCenter=true&lines=Matomo+2+Grafana+Report;"></a>
</p>

<p align="center">
    <a href="https://matomo.org/"><img src="https://img.shields.io/badge/matomo-%233152A0.svg?style=for-the-badge&logo=matomo&logoColor=white"> </a>
    <a href="https://grafana.com/"><img src="https://img.shields.io/badge/grafana-%23F46800.svg?style=for-the-badge&logo=grafana&logoColor=white"> </a>
    <a href="https://www.python.org"><img src="https://img.shields.io/badge/python-%233776AB.svg?style=for-the-badge&logo=python&logoColor=white"> </a>
    <br />
</p>

[TOC]

## 🎯 Objective

Matomo2GrafanaReport is a Python script that generates a Grafana dashboard with a specified time range and variables, exports it to a PDF, and sends it via email with an attached PNG image. It automates the process of creating and sharing Grafana dashboards for different websites.

## 🚀 Functioning

The script uses the `pyppeteer` library to interact with Grafana, `requests` to handle API requests, and `smtplib` to send emails. The main steps are:

1. Parse input arguments and load configurations from `config.ini` and `sites.ini`.
2. Load the template JSON file and modify it with new variables and time range.
3. Get or create a folder ID in Grafana.
4. Delete the existing dashboard if it exists in the specified folder.
5. Create a new dashboard with the modified template.
6. Print the dashboard to PDF and convert it to PNG.
7. Upload the PNG image to Jirafeau and get a public link.
8. Send an HTML email with the image link and the PDF file attached.

## 🚀 Prerequisites

- Python 3.x
- `pyppeteer` library
- `requests` library
- `smtplib` library
- `pdf2image` library (for converting PDF to PNG)
- Access to a Grafana instance with a Matomo datasource
- A Grafana API key with necessary permissions
- An SMTP server for sending emails
- A Jirafeau instance for uploading PNG images (optional)

## 🦾 Usage

1. Clone the repository: `git clone https://github.com/your_username/Matomo2GrafanaReport.git`
2. Install required packages: `pip install -r requirements.txt`
3. Update the `config.ini` and `sites.ini` files with your specific configurations.
4. Run the script with the desired month and year: `python3 report_generator.py --month MM-YYYY`

## ⚙️ Configuration

The script uses two configuration files:

### `config.ini`:
```ini
[Grafana]
url = 
api_key = 
user = 
password = 

[Paths]
template_json = template.json

[Settings]
timezone = Europe/Paris

[Jirafeau]
url = 

[SMTP]
server = mail.infomaniak.com
port = 587
login = 
password = 
from = 

[Email]
subject_template = 
```

### `sites.ini`:

```ini
[Site1]
name = example1.com
email = example1@example.com

[Site2]
name = example2.com
email = example2@example.com
```

## 🚧 Troubleshoots

### Grafana API errors

- Ensure the provided API key has necessary permissions.
- Check Grafana URL and version for compatibility.

### Datasource not found

- Add Matomo datasource with name `MATOMO` with this configuration :
    - Datasource type : `JSON API`
    - URL : `https://<your_matomo_url>/index.php`
    - Query string : `token_auth=<your_matomo_api_key>&module=API&format=json`

### PDF conversion errors

- Ensure `pdf2image` library is installed and updated.
- Adjust viewport size and waiting time in `print_to_pdf` function.

### Email sending errors

- Verify SMTP server, port, login, and password.
- Check email format and attachment for validity.

### Jirafeau upload errors

- Ensure the provided Jirafeau URL is correct and accessible.
- Adjust the upload function to handle different file formats or sizes.

## 🔥 Result
![Report](https://send.genevois-informatique.com/f.php?h=39HRhMNq&p=1)