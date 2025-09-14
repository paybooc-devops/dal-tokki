FROM python:3.12-slim

WORKDIR /app

COPY app app
COPY fal fal
COPY requirements.txt /app/

RUN pip install -r requirements.txt

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
