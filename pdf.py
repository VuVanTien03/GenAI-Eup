from google.oauth2 import service_account
import google.generativeai as genai

# Load credentials từ file JSON
credentials = service_account.Credentials.from_service_account_file(
    'path/to/your-service-account.json',
    scopes=['https://www.googleapis.com/auth/cloud-platform']
)

# Cấu hình Gemini với credentials
genai.configure(credentials=credentials)

# Sử dụng model
model = genai.GenerativeModel('gemini-pro')
response = model.generate_content("Xin chào")
print(response.text)