from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

class PageDownloader:
    def __init__(self, driver, email, password):
        self.email = email
        self.password = password
        self.driver = driver