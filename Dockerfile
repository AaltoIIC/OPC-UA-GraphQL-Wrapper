FROM python:3.8.0

WORKDIR /app

ADD GraphQLWrap /app
ADD requirements.txt /app

RUN pip install -r requirements.txt

CMD ["gunicorn", "-w 3", "-k uvicorn.workers.UvicornH11Worker", "-b :8000", "main:app"]

