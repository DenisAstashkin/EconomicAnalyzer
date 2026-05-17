FROM python:3.11.9
WORKDIR /app
COPY . /app
RUN pip install --no-cache-dir --upgrade -r /app/requarement.txt
CMD ["python", "-m", "uvicorn", "src.server:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]