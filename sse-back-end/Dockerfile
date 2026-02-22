FROM python:latest

WORKDIR /svitlo-power-sse-api

# set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DEBUG True

COPY sse-back-end/requirements.txt /svitlo-power-sse-api/
COPY shared/python /shared/python

# install python dependencies
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

COPY sse-back-end/ /svitlo-power-sse-api/

CMD ["uvicorn", "run:app", "--host", "0.0.0.0", "--port", "5005", "--workers", "5"]
