# AI Tutor: Skill Builder

AI Tutor: Skill Builder là một hệ thống trợ lý học tập cá nhân hoá dựa trên trí tuệ nhân tạo. Mục tiêu của dự án là hỗ trợ người dùng củng cố và mở rộng kỹ năng thông qua lộ trình học tập được thiết kế tự động, linh hoạt và phù hợp với quỹ thời gian cá nhân. Hệ thống thu thập và chuẩn hóa dữ liệu từ các nguồn học tập đáng tin cậy, xây dựng kho tri thức về kỹ năng và lộ trình, sau đó sử dụng mô hình ngôn ngữ lớn (LLM) để đề xuất danh mục kỹ năng và kế hoạch học tập cá nhân hóa.

Hệ thống được thiết kế theo kiến trúc đa tầng. Nó kết hợp giữa mô hình ngôn ngữ lớn và cơ sở tri thức ngoài để tạo ra phản hồi cho người dùng. Các thành phần chính bao gồm: (i) module thu thập dữ liệu (crawler) để khai thác và tiền xử lý tài liệu học tập; (ii) **vector store** lưu trữ embeddings của các đoạn văn bản chuẩn hóa, phục vụ tìm kiếm ngữ nghĩa; (iii) **mô hình ngôn ngữ lớn** (ví dụ: LLaMA hoặc các LLM tương đương) đóng vai trò trung tâm cho việc suy luận và sinh câu trả lời; và (iv) **API Backend** xây dựng bằng FastAPI để tiếp nhận yêu cầu từ người dùng và trả về kết quả dưới dạng JSON. Hệ thống sử dụng phương pháp **Retrieval-Augmented Generation (RAG)**, tức là mỗi khi có câu hỏi từ người dùng, hệ thống sẽ truy xuất các tài liệu liên quan từ vector store và đưa thông tin đó vào ngữ cảnh để LLM tổng hợp phản hồi. Toàn bộ hệ thống được đóng gói trong Docker, cho phép triển khai linh hoạt trên nhiều môi trường khác nhau.

-----

## Hướng dẫn cài đặt

**Yêu cầu hệ thống:** Máy chủ/PC có cài đặt Docker (phiên bản mới nhất), Python 3.8+ và Git. Docker được dùng để container hóa toàn bộ ứng dụng, bao gồm mã nguồn, mô hình và thư viện cần thiết.

### Thiết lập môi trường Python:

1.  Clone repository về máy:

    ```bash
    git clone https://github.com/<username>/ai-tutor-skill-builder.git
    cd ai-tutor-skill-builder
    ```

2.  Tạo và kích hoạt môi trường ảo Python:

    ```bash
    python3 -m venv .venv
    source .venv/bin/activate      # (Linux/macOS) hoặc .venv\Scripts\activate (Windows)
    ```

3.  Cài đặt các thư viện cần thiết:

    ```bash
    pip install --upgrade pip
    pip install -r requirements.txt
    ```

### Chạy ứng dụng với Docker:

1.  Build Docker image: (Ví dụ tên image là ai-tutor)

    ```bash
    docker build -t ai-tutor:latest .
    ```

2.  Chạy container: Mở cổng ứng dụng (giả sử API chạy trên port 8000):

    ```bash
    docker run -d -p 8000:8000 ai-tutor:latest
    ```

Sau khi chạy, API sẽ sẵn sàng lắng nghe các yêu cầu từ `http://localhost:8000`.

-----

## Hướng dẫn sử dụng API

Hệ thống cung cấp các endpoint chính dưới dạng dịch vụ RESTful. Dưới đây là danh sách các endpoint và ví dụ cấu trúc JSON:

  * **`POST /query`** – Xử lý truy vấn học tập của người dùng.

      * **Mô tả:** Nhận đầu vào là câu hỏi của người dùng và trả về danh sách kỹ năng cần học kèm lịch học.
      * **Ví dụ yêu cầu:**
        ```json
        {
          "query": "Tôi muốn trở thành nhà khoa học dữ liệu, cần học những kỹ năng gì và lộ trình thế nào trong 6 tháng?"
        }
        ```
      * **Ví dụ phản hồi:** (JSON bao gồm `skills` và `learning_path`)
        ```json
        {
          "skills": ["Python", "Thống kê cơ bản", "Machine Learning"],
          "learning_path": [
            {"week": 1, "objective": "Làm quen Python", "deadline": "2025-09-01"},
            {"week": 2, "objective": "Thống kê cơ bản", "deadline": "2025-09-08"},
            // ...
          ]
        }
        ```

  * **`GET /health`** – Kiểm tra tình trạng hoạt động của dịch vụ.

      * **Ví dụ phản hồi:**
        ```json
        {
          "status": "ok"
        }
        ```

**Lưu ý:** Các giá trị trong ví dụ trên chỉ mang tính minh họa. Đầu ra thực tế có thể khác tùy theo dữ liệu và mô hình sử dụng.

-----

## Ví dụ minh họa truy vấn

Dưới đây là một số ví dụ về truy vấn mẫu mà người dùng có thể gửi cho hệ thống:

  * **Ví dụ 1:** “Tôi muốn trở thành nhà khoa học dữ liệu, cần học những kỹ năng gì và lộ trình ra sao trong 6 tháng?”
  * **Ví dụ 2:** “Xin tư vấn lộ trình học Python và Machine Learning để trở thành lập trình viên data trong 3 tháng.”
  * **Ví dụ 3:** “Tôi đã biết C++ và toán cơ bản, hãy đề xuất các kỹ năng tiếp theo để phát triển web.”

Các truy vấn này cho phép hệ thống xác định mục tiêu học tập, tình trạng hiện tại của người dùng, và thời gian yêu cầu để sinh ra danh sách kỹ năng cùng lịch học phù hợp.
