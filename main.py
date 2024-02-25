import os
import re
import wget
import zipfile
import platform
import sqlite3
import json
import requests
import base64
import subprocess
import urllib3
from urllib import parse
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from colorama import Fore, Style

urllib3.disable_warnings()

# Define constants
DOMAIN = ""  # Use domain name if available
SUBPORT = ""  # Set a custom subPort if desired
MANUALLY_CONFIG = {
        "tls": True,
        "insecure": True,
        "early": True,
        "mux": True,
        "direct": True
    }

LOCALHOST = "127.0.0.1"
DB_ADDRESS = '/etc/x-ui/x-ui.db'
NGINX_SITES_AVAILABLE = '/etc/nginx/sites-available'
NGINX_SITES_ENABLED = '/etc/nginx/sites-enabled'
HTML_ROOT = '/var/www/html'
CHROME_VERSION = "114.0.5735.90"
CHROME_DRIVER_VERSION = "114.0.5735.90"

# Configure Selenium WebDriver
CHROMEDRIVER_PATH = '/usr/local/bin/chromedriver'
WINDOW_SIZE = "1920,1080"
GREEN= Fore.GREEN
RED = Fore.RED
PLAIN = Style.RESET_ALL

def get_architecture():
    # Get architecture
    architecture = platform.machine()
    architecture_mapping = {
        'x86_64': 'amd64',  # Map x86_64 architecture to amd64
        'aarch64': 'arm64',  # Map aarch64 architecture to arm64
    }
    return architecture_mapping.get(architecture, architecture)

def install_packages():
    def is_unzip_installed():
        return bool(subprocess.run(["which", "unzip"], capture_output=True, text=True).stdout)
    if not is_unzip_installed:
        # Install unzip package
        os.system("apt update && apt install -y unzip")
    

def download_and_install_chrome():
    def is_nginx_installed():
        return bool(subprocess.run(["which", "google-chrome-stable"], capture_output=True, text=True).stdout)
    if not is_nginx_installed:
        print(f"{Style.BRIGHT}{GREEN}Download and Install Google Chrome...{PLAIN}")
        # Download Google Chrome .deb package
        chrome_deb_url = f"https://dl.google.com/linux/chrome/deb/pool/main/g/google-chrome-stable/google-chrome-stable_{CHROME_VERSION}-1_{ARCHITECTURE}.deb"
        chrome_deb_file = f"google-chrome-stable_{CHROME_VERSION}-1_{ARCHITECTURE}.deb"
        wget.download(chrome_deb_url, out=chrome_deb_file)

        # Install Google Chrome .deb package
        subprocess.run(["apt", "install", "-y", f"./{chrome_deb_file}"], check=True)

def download_and_install_chrome_driver():
    if not os.path.isfile(CHROMEDRIVER_PATH):
        print(f"{Style.BRIGHT}{GREEN}Download Chrome Driver...{PLAIN}")
        # Download Chrome WebDriver zip file
        chrome_driver_url = "https://chromedriver.storage.googleapis.com/114.0.5735.90/chromedriver_linux64.zip"
        chrome_driver_zip_file = "chromedriver_linux64.zip"
        wget.download(chrome_driver_url, out=chrome_driver_zip_file)

        # Extract Chrome WebDriver zip file
        with zipfile.ZipFile(chrome_driver_zip_file, 'r') as zip_ref:
            zip_ref.extractall("/usr/local/bin")

        # Make chromedriver executable
        os.system(f"chmod +x /usr/local/bin/chromedriver")


def is_nginx_installed():
    return bool(subprocess.run(["which", "nginx"], capture_output=True, text=True).stdout)

def install_nginx():
    if not is_nginx_installed():
        print(f"{Style.BRIGHT}{GREEN}Install Nginx...{PLAIN}")
        os.system("apt update && apt install nginx -y")

def create_nginx_site_file(domain_name, port, subpath, cert_path='', key_path=''):
    # Check if HTTPS is used
    ssl_status = port in ['443', '8443', '2053', '2087', '2083', '2096']

    # Validate certificate and key paths
    if cert_path and not os.path.isfile(cert_path):
        raise ValueError("cert_path must be a valid file path")
    if key_path and not os.path.isfile(key_path):
        raise ValueError("key_path must be a valid file path")

    # Construct server configuration
    server_config = f"""
server {{
    listen {port}{' ssl' if ssl_status else ""};
    server_name {domain_name if domain_name else "_"};

    {''.join([f'''ssl_certificate {cert_path};
    ssl_certificate_key {key_path};''' if ssl_status else ""])}

    location {subpath} {{
        root {HTML_ROOT};
        index index.html index.htm;
    }}
}}
"""

    # Write server configuration to Nginx sites-available
    if not domain_name:
        site_filename = os.path.join(NGINX_SITES_AVAILABLE, 'default')
    else:
        site_filename = os.path.join(NGINX_SITES_AVAILABLE, domain_name)
    
    with open(site_filename, "w") as f:
        f.write(server_config)

    # Enable site by creating symbolic link in sites-enabled
    if domain_name and not os.path.exists(os.path.join(NGINX_SITES_ENABLED, domain_name)):
        os.symlink(site_filename, os.path.join(NGINX_SITES_ENABLED, domain_name))

    # Reload Nginx
    try:
        subprocess.run(["systemctl", "restart", "nginx"],check=True)
    except:
        print(f"{Style.BRIGHT}\n{Fore.RED}Please disable the subscription service in the panel settings\nand then restart nginx with {Style.RESET_ALL}{Style.BRIGHT}systemctl restart nginx{Fore.RED} command{Style.RESET_ALL}\n")
        exit()

def convert_to_fragment(files_directory):
    global MANUALLY_CONFIG

    try:
        regex_format = "^https://quickchart\.io/qr\?size=300x200&light=ffffff&text=(https.*)"
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--window-size=%s" % WINDOW_SIZE)
        chrome_options.add_argument('--no-sandbox')

        # Initialize Chrome WebDriver
        chrome_service = Service(CHROMEDRIVER_PATH)
        driver = webdriver.Chrome(service=chrome_service, options=chrome_options)

        # URL and configurations
        ircf_url = "https://ircfspace.github.io/fragment/"

        # Open IRCF website and set configurations
        driver.get(ircf_url)
        driver.maximize_window()
        driver.execute_script("window.alert = null;")
        
        setSwitch = False
        for filename in os.listdir(files_directory):
            filepath = os.path.join(files_directory, filename)
            if os.path.isfile(filepath):
                with open(filepath, 'r') as file:
                    data = file.read()

                driver.find_element(By.ID, 'defConfig').clear()
                driver.find_element(By.ID, 'defConfig').send_keys(data)
                config_check = driver.find_element(By.ID,"checkConf")
                config_check.click()
                
                switches = driver.find_elements(By.CLASS_NAME, "switch")
                if not setSwitch:
                    for switch in switches:
                        inputs_tag = switch.find_elements(By.TAG_NAME, "input")
                        for input_tag in inputs_tag:
                            if MANUALLY_CONFIG.get(input_tag.get_attribute('id')) != input_tag.is_selected():
                                switch.click()
                    setSwitch = True

                submit_button = driver.find_element(By.ID, "qrGen")
                submit_button.click()

                url_data = driver.find_element(By.ID, "copyJsonFromQR").find_element(By.TAG_NAME, 'img').get_attribute('src')
                driver.execute_script("document.querySelector('.close').click()")
                url_encode = re.findall(regex_format, url_data)[0]
                json_url = parse.unquote(url_encode)

                print(f"{Style.BRIGHT}{Fore.GREEN}Setting custom config on subID: {filename}{Style.RESET_ALL}")
                response = requests.get(json_url)

                with open(filepath, 'a') as file:
                    file.write(response.text)
    except Exception as e:
        print(f"An error occurred while converting to fragment: {e}")
    finally:
        if 'driver' in locals():
            driver.quit()
            print(f"{Style.BRIGHT}{GREEN}Conversion complete: Your configurations are now updated.{PLAIN}")

def main():
    try:
        global ARCHITECTURE,SUBPORT
        ARCHITECTURE = get_architecture()
        install_packages()
        download_and_install_chrome()
        download_and_install_chrome_driver()
        install_nginx()
        
        conn = sqlite3.connect(DB_ADDRESS)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("SELECT key,value FROM settings")
        settings_data = dict(cursor.fetchall())

        subPath, SubCertFile, SubkeyFile = settings_data.get('subPath', ''), settings_data.get('subCertFile', ''), settings_data.get('subKeyFile', '')
        panel_subPort = settings_data.get('subPort', '')
        if not SUBPORT:
            SUBPORT = panel_subPort

        https_status = 'http'
        if SubCertFile and SubkeyFile:
            https_status = 'https'

        create_nginx_site_file(DOMAIN, SUBPORT, subPath, SubCertFile, SubkeyFile)
        cursor.execute("SELECT settings FROM inbounds")
        rows = cursor.fetchall()

        html_subpath = os.path.join(HTML_ROOT, subPath[1:])
        os.makedirs(html_subpath, exist_ok=True)

        for client in json.loads(rows[0]['settings']).get('clients', []):
            sub_id = client.get('subId', '')
            email = client.get('email', '')
            response = requests.get(f"{https_status}://{LOCALHOST}:{panel_subPort}{subPath}{sub_id}", verify=False)
            if response.status_code == 200:
                vpn_account = response.text
                if vpn_account[0] != 'v':
                    vpn_account = base64.b64decode(vpn_account).decode('utf-8')

                with open(os.path.join(html_subpath, sub_id), 'w') as f:
                    f.write(vpn_account)
        
        convert_to_fragment(html_subpath)

    except Exception as e:
        print(f"An error occurred: {e}")
        # Log the error for debugging purposes

if __name__ == "__main__":
    main()
