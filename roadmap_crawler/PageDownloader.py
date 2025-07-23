from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
import time
import os
from utils.DownloadTools import login
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys


class PageDownloader:
    def __init__(self, driver, email=None, password=None):
        self.email = email
        self.password = password
        self.driver = driver

    def download_page(self, url, save_name, folder="roadmap"):
        self.driver.get(url)
        time.sleep(3)

        target = "Tôi muốn trở thành " + save_name

        input_box = WebDriverWait(self.driver, 3).until(
            EC.presence_of_element_located((By.ID, "«r8R0»"))
        )


        input_box.send_keys(target)
        input_box.send_keys(Keys.RETURN)
        time.sleep(6)


        save_dir = f"html_pages/{folder}/{save_name}"
        os.makedirs(save_dir, exist_ok=True)
        file_path = os.path.join(save_dir, f"{save_name}.html")

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(self.driver.page_source)
            print(f"✅ Đã lưu HTML vào: {file_path}")

        return file_path

if __name__ == "__main__":
    #login info
    EMAIL = "vuvantien_t67@hus.edu.vn"
    PASSWORD = "Anhyeuem2003"

    options = Options()
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--ignore-certificate-errors")
    options.add_argument("--allow-running-insecure-content")
    options.add_argument("--disable-web-security")
    options.add_argument("--ignore-ssl-errors")
    # options.add_argument("--headless")  # có thể bỏ nếu muốn xem trình duyệt

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)

    # Gọi login()
    login(driver, "https://roadmap.sh/login", EMAIL, PASSWORD)

    save_name = ["AI engineer", "Backend", "Frontend"]

    # Gọi PageDownloader
    bot = PageDownloader(driver, EMAIL, PASSWORD)
    print("_____________Start Download______________________")
    for name in save_name:
        bot.download_page("https://roadmap.sh/ai?format=roadmap", name)
