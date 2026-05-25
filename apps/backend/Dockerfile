FROM python:3.11-slim

WORKDIR /app

# System dependencies for PyMuPDF
RUN apt-get update && apt-get install -y \
    libmupdf-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

RUN chmod +x start.sh && sed -i 's/\r$//' start.sh
ENTRYPOINT ["bash", "./start.sh"]
