from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium import webdriver
import time

def login(driver, url, email, password):
    driver.get(url)
    time.sleep(2)

    try:
        WebDriverWait(driver, 3).until(
            EC.presence_of_element_located((By.ID, "form:«r8R3»"))
        ).send_keys(email)
        driver.find_element(By.ID, "form:«r8R3H1»").send_keys(password + Keys.RETURN)
        time.sleep(3)
        return True
    except:
        return False


driver = webdriver.Chrome()

if login(driver, "https://roadmap.sh/login", "vuvantien_t67@hus.edu.vn", "Anhyeuem2003"):
    print("Đăng nhập thành công")
else:
    print("Đăng nhập thất bại")