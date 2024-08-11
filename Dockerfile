FROM python:3.10-alpine

WORKDIR /pydog

COPY *.py ./
COPY ./static/ ./static/
COPY ./templates/ ./templates/

RUN pip config set global.index-url https://mirrors.cloud.tencent.com/pypi/simple/
RUN pip install -r requirements.txt

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--timeout-keep-alive", "60", "--workers", "4"]