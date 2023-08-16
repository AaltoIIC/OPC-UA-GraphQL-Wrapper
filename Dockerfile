FROM python:3.8.0

WORKDIR /app

ADD GraphQLWrap /app
ADD requirements.txt /app

RUN pip install -r requirements.txt

CMD ["uvicorn", "main:app", "--workers", "4", "--host", "0.0.0.0", "--port", "8000"]

