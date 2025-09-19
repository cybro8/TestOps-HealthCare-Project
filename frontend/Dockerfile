FROM python:3.11

WORKDIR /app
COPY . .
RUN pip install --no-cache-dir -r requirements.txt
ENV API_URL=http://web:8000
EXPOSE 8501
CMD ["streamlit", "run", "app.py", "--server.port", "8501", "--server.address", "0.0.0.0"]