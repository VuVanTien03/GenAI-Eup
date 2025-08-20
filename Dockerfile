# =========================
# Stage 1: Base environment
# =========================
FROM python:3.11-slim AS base

# Cài đặt các gói cần thiết cho hệ thống
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Tạo thư mục làm việc
WORKDIR /app

# =========================
# Stage 2: Install dependencies
# =========================
FROM base AS builder

# Copy requirements trước (để cache dependencies)
COPY requirements.txt .

# Cài đặt dependencies (nếu dùng requirements.lock thì càng ổn định)
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# =========================
# Stage 3: Runtime
# =========================
FROM base AS runtime

# Copy lại môi trường từ builder
COPY --from=builder /usr/local /usr/local

# Copy code của ứng dụng
COPY . .

# Expose cổng FastAPI chạy
EXPOSE 8000

# Thiết lập biến môi trường
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Chạy ứng dụng
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
