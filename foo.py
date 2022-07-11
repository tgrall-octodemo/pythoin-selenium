from PIL import Image
from io import BytesIO
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


from google.cloud import storage

import logging
import os
import time



# Set default download folder for ChromeDriver
working_dir = r"."
if not os.path.exists(working_dir):
    os.makedirs(working_dir)
prefs = {"download.default_directory": working_dir}

def publish_image(address, user_id, session_id):
    # SELENIUM SETUP
    global_session_id = session_id;
    global_user_id = user_id;
    logging.getLogger('WDM').setLevel(logging.WARNING)  # just to hide not so rilevant webdriver-manager messages
    chrome_options = Options()
    chrome_options.headless = True
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_prefs = {}
    chrome_prefs["profile.default_content_settings"] = {"images": 2}    
    chrome_prefs["download.default_directory"] = working_dir    
    chrome_options.add_experimental_option("prefs", chrome_prefs)
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    driver.maximize_window()
    image_url = address + "/traces/" + session_id + "/image";
    driver.get(image_url)
    driver.set_window_size(800, 800)  # to set the screenshot width
    img_url = save_screenshot(driver,user_id, session_id)
    driver.quit()
    return img_url;

def save_screenshot(driver, user_id, session_id):
    file_name = session_id + '.png'.format(working_dir)
    height, width = scroll_down(driver)
    driver.set_window_size(width, height)
    img_binary = driver.get_screenshot_as_png()
    img = Image.open(BytesIO(img_binary))
    img.save(file_name)
    return save_to_google_cloud(user_id, file_name);

def save_to_google_cloud(user_id, file_name):
    storage_client = storage.Client.from_service_account_json('service_account.json');
    bucket = storage_client.get_bucket('windsurf-app-bucket')
    blob = bucket.blob("sessions/"+ user_id +"/"+ file_name)
    blob.upload_from_filename(file_name)
    
    print('File {} uploaded to Google Cloud!'.format(blob.public_url))
    os.remove(file_name)
    print('File {} removed!'.format(file_name))
    return blob.public_url;

def scroll_down(driver):
    total_width = driver.execute_script("return document.body.offsetWidth")
    total_height = driver.execute_script("return document.body.parentNode.scrollHeight")
    viewport_width = driver.execute_script("return document.body.clientWidth")
    viewport_height = driver.execute_script("return window.innerHeight")

    rectangles = []

    i = 0
    while i < total_height:
        ii = 0
        top_height = i + viewport_height

        if top_height > total_height:
            top_height = total_height

        while ii < total_width:
            top_width = ii + viewport_width

            if top_width > total_width:
                top_width = total_width

            rectangles.append((ii, i, top_width, top_height))

            ii = ii + viewport_width

        i = i + viewport_height

    previous = None
    part = 0

    for rectangle in rectangles:
        if not previous is None:
            driver.execute_script("window.scrollTo({0}, {1})".format(rectangle[0], rectangle[1]))
            time.sleep(0.5)
        # time.sleep(0.2)

        if rectangle[1] + viewport_height > total_height:
            offset = (rectangle[0], total_height - viewport_height)
        else:
            offset = (rectangle[0], rectangle[1])

        previous = rectangle

    return total_height, total_width

