FROM python:3.8.0

WORKDIR /app

ADD GraphQLWrap /app
ADD requirements.txt /app

RUN pip install -r requirements.txt

EXPOSE 8000

CMD ["gunicorn", "-k uvicorn.workers.UvicornWorker", "main:app"]

