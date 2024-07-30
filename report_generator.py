import os
import json
import configparser
import requests
import uuid
import argparse
from datetime import datetime, timedelta
import pytz
import asyncio
from pyppeteer import launch
from pdf2image import convert_from_path
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from rich.console import Console
import locale

# Initialize the console for rich output
console = Console()

# Load configuration from config.ini
config = configparser.ConfigParser()
config.read('config.ini')

# General configuration
grafana_url = config['Grafana']['url']
api_key = config['Grafana']['api_key']
grafana_user = config['Grafana']['user']
grafana_password = config['Grafana']['password']
template_json_path = config['Paths']['template_json']
timezone = config['Settings']['timezone']
jirafeau_url = config['Jirafeau']['url']
smtp_server = config['SMTP']['server']
smtp_port = config['SMTP']['port']
login = config['SMTP']['login']
password = config['SMTP']['password']
from_email = config['SMTP']['from']

# Load sites configuration from sites.ini
sites_config = configparser.ConfigParser()
sites_config.read('sites.ini')

# Function to load sites information
def load_sites(sites_config):
    sites = []
    for section in sites_config.sections():
        site_info = {
            'site': sites_config[section]['site'],
            'email': sites_config[section]['email']
        }
        sites.append(site_info)
    return sites

# List of sites
sites = load_sites(sites_config)

# Function to upload a file to Jirafeau
def upload_to_jirafeau(file_path, jirafeau_url):
    try:
        with console.status(f"[bold purple]Uploading {file_path} to Jirafeau..."):
            files = {'file': open(file_path, 'rb')}
            data = {'time': 'none'}
            response = requests.post(jirafeau_url, files=files, data=data)
            response.raise_for_status()
            response_text = response.text.strip().split('\n')
            if response_text and len(response_text) > 1:
                file_id = response_text[0]
                download_url = f"{jirafeau_url.replace('/script.php', '')}/f.php?h={file_id}&p=1"
                return download_url
            else:
                console.log("[bold red]Unexpected response:", response_text)
                return None
    except requests.RequestException as e:
        console.log(f"[bold red]Request error: {e}")
        return None

# Function to send an HTML email with an attachment
def send_html_email(smtp_server, smtp_port, login, password, to_email, subject, html_content, pdf_file):
    with console.status(f"[bold purple]Sending email to {to_email}..."):
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = login
        msg['To'] = to_email

        html_part = MIMEText(html_content, 'html')
        msg.attach(html_part)

        attachment = MIMEBase('application', 'octet-stream')
        attachment.set_payload(open(pdf_file, 'rb').read())
        encoders.encode_base64(attachment)
        attachment.add_header('Content-Disposition', 'attachment', filename=pdf_file)
        msg.attach(attachment)

        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(login, password)
            server.sendmail(login, to_email, msg.as_string())
        console.log(f"[bold green]Email sent to [bold blue]{to_email}")

# Function to load the template JSON file
def load_template(template_path):
    with console.status(f"[bold purple]Loading template from {template_path}..."):
        with open(template_path, 'r') as file:
            return json.load(file)

# Function to modify the template with new variables and time range
def modify_template(template, new_variables, time_range):
    console.log("Modifying template with new variables and time range...")
    for variable in template['templating']['list']:
        if variable['name'] in new_variables:
            variable['current']['text'] = new_variables[variable['name']]
            variable['current']['value'] = new_variables[variable['name']]
            variable['query'] = new_variables[variable['name']]
    
    template['time'] = {
        "from": time_range['from'],
        "to": time_range['to']
    }
    template['uid'] = str(uuid.uuid4())

    return template

# Function to get or create a folder ID in Grafana
def get_or_create_folder_id(folder_title):
    with console.status(f"[bold purple]Getting or creating folder ID for {folder_title}..."):
        url = f"{grafana_url}/api/folders"
        headers = {
            'Authorization': f"Bearer {api_key}",
            'Content-Type': 'application/json'
        }
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        folders = response.json()

        for folder in folders:
            if folder['title'] == folder_title:
                return folder['id']
        
        payload = {
            "title": folder_title,
            "uid": str(uuid.uuid4())
        }
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        response.raise_for_status()
        return response.json()['id']

# Function to delete a dashboard by UID
def delete_dashboard_by_uid(dashboard_uid):
    with console.status(f"[bold purple]Deleting dashboard with UID {dashboard_uid}..."):
        url = f"{grafana_url}/api/dashboards/uid/{dashboard_uid}"
        headers = {
            'Authorization': f"Bearer {api_key}",
            'Content-Type': 'application/json'
        }
        response = requests.delete(url, headers=headers)
        try:
            console.log("Dashboard deleted!")
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            console.log("[bold red]Error deleting dashboard:", response.json())
            raise e

# Function to check if a dashboard exists in a specific folder
def dashboard_exists(dashboard_title, folder_id):
    with console.status(f"[bold purple]Checking if dashboard {dashboard_title} exists in folder {folder_id}..."):
        url = f"{grafana_url}/api/search?query={dashboard_title}&folderIds={folder_id}"
        headers = {
            'Authorization': f"Bearer {api_key}",
            'Content-Type': 'application/json'
        }
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        dashboards = response.json()
        for dashboard in dashboards:
            if dashboard['title'] == dashboard_title:
                console.log("Dashboard already exists!")
                return dashboard['uid']
        return None

# Function to create a new dashboard
def create_dashboard(new_dashboard, title, folder_id):
    with console.status(f"[bold purple]Creating new dashboard with title {title}..."):
        url = f"{grafana_url}/api/dashboards/db"
        headers = {
            'Authorization': f"Bearer {api_key}",
            'Content-Type': 'application/json'
        }
        new_dashboard['title'] = title
        new_dashboard['id'] = None
        new_dashboard['version'] = 1
        payload = {
            "dashboard": new_dashboard,
            "overwrite": False,
            "message": "Dashboard created",
            "folderId": folder_id
        }
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            console.log("[bold red]Error creating dashboard:", response.json())
            raise e
        return response.json()

# Function to convert a PDF to PNG
def convert_pdf_to_png(pdf_file, output_file):
    with console.status(f"[bold purple]Converting {pdf_file} to PNG..."):
        images = convert_from_path(pdf_file)
        for image in images:
            image.save(output_file, 'PNG')

# Function to calculate the time range for a given month and year
def get_time_range_for_month(month_year):
    console.log(f"Calculating time range for {month_year}...")
    tz = pytz.timezone(timezone)
    month, year = map(int, month_year.split('-'))
    first_day = tz.localize(datetime(year, month, 1, 0, 0, 0)).isoformat()
    last_day = (tz.localize(datetime(year, month + 1, 1, 0, 0, 0)) - timedelta(seconds=1)).isoformat() if month < 12 else (tz.localize(datetime(year + 1, 1, 1, 0, 0, 0)) - timedelta(seconds=1)).isoformat()
    return {"from": first_day, "to": last_day}

# Function to get the period and dates for a given month and year
def get_period_and_dates(month_year):
    # Set locale to French
    locale.setlocale(locale.LC_TIME, 'fr_FR.UTF-8')
    
    tz = pytz.timezone(timezone)
    month, year = map(int, month_year.split('-'))
    
    # First and last day of the current month
    first_day_of_month = datetime(year, month, 1)
    last_day_of_month = (first_day_of_month + timedelta(days=32)).replace(day=1) - timedelta(days=1)
    
    # First day of the previous month
    first_day_of_previous_month = (first_day_of_month - timedelta(days=1)).replace(day=1)
    
    periode = f"1er {first_day_of_month.strftime('%B %Y')} → {last_day_of_month.strftime('%d %B %Y')}"
    date_from = first_day_of_previous_month.strftime('%Y-%m-%d')
    date_to = last_day_of_month.strftime('%Y-%m-%d')
    
    return periode, date_from, date_to

# Asynchronous function to print a dashboard to PDF
async def print_to_pdf(dashboard_url, output_file, username, password):
    with console.status(f"[bold purple]Printing dashboard to PDF from {dashboard_url}..."):
        browser = await launch(headless=True, args=['--no-sandbox'])
        page = await browser.newPage()
        await page.setViewport({"width": 1920, "height": 1080})

        await page.goto(f"{grafana_url}/login")
        await page.type('input[name="user"]', username)
        await page.type('input[name="password"]', password)
        await page.keyboard.press('Enter')
        await page.waitForNavigation()

        await page.goto(dashboard_url)

        height = await page.evaluate('document.body.scrollHeight')
        await page.setViewport({"width": 1392, "height": 3800})
        await asyncio.sleep(30)

        pdf_options = {
            'path': output_file,
            'printBackground': True,
            'width': '1392px',
            'height': f'3800px'
        }
        await page.pdf(pdf_options)
        await browser.close()

# Function to create a directory for a site if it doesn't exist
def create_site_directory(site):
    directory = os.path.join(os.getcwd(), site)
    if not os.path.exists(directory):
        os.makedirs(directory)
    return directory

# Main function to parse arguments and execute the script
def main():
    parser = argparse.ArgumentParser(description='Duplicate a Grafana dashboard with new variables and a time range.')
    parser.add_argument('--month', required=True, help='Month and year to change the dashboard time range (format: MM-YYYY)')
    
    args = parser.parse_args()
    
    periode, date_from, date_to = get_period_and_dates(args.month)
    subject_template = config['Email']['subject_template']
    
    for site_info in sites:
        site = site_info['site']
        to_email = site_info['email']

        new_variables = {
            'SITE': site,
            'Periode': periode,
            'DATE_FROM': date_from,
            'DATE_TO': date_to,
        }

        subject = subject_template.format(site=site, periode=periode)
    
        time_range = get_time_range_for_month(args.month)
        year, month = args.month.split('-')
        new_title = f"{site} - {year}-{month}"

        dashboard_template = load_template(template_json_path)
        modified_dashboard = modify_template(dashboard_template, new_variables, time_range)
    
        folder_id = get_or_create_folder_id(site)
    
        existing_dashboard_uid = dashboard_exists(new_title, folder_id)
        if (existing_dashboard_uid):
            delete_dashboard_by_uid(existing_dashboard_uid)
    
        created_dashboard_response = create_dashboard(modified_dashboard, new_title, folder_id)
        dashboard_uid_new = created_dashboard_response['uid']
        dashboard_url = f"{grafana_url}{created_dashboard_response['url']}?kiosk"

        console.log(f"[bold green]Dashboard created: [bold blue]{dashboard_url}")

        site_directory = create_site_directory(site)
    
        pdf_file = os.path.join(site_directory, f"{new_title}.pdf")
    
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(print_to_pdf(dashboard_url, pdf_file, grafana_user, grafana_password))
    
        console.log(f"[bold green]PDF saved: [bold blue]{pdf_file}")

        png_file = os.path.join(site_directory, f"{new_title}.png")
        convert_pdf_to_png(pdf_file, png_file)
    
        console.log(f"[bold green]PNG saved: [bold blue]{png_file}")

        image_url = upload_to_jirafeau(png_file, jirafeau_url)
        console.log(f"[bold green]PNG hosted: [bold blue]{image_url}")
        if image_url:
            html_content = f"""
            <html>
            <body>
                <img src="{image_url}" alt="Image">
            </body>
            </html>
            """
            send_html_email(smtp_server, smtp_port, login, password, to_email, subject, html_content, pdf_file)
        else:
            console.log("[bold red]Failed to upload image.")

if __name__ == "__main__":
    main()
