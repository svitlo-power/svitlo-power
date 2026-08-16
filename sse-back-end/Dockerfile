FROM python:latest

WORKDIR /svitlo-power-sse-api

# set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBUG=True

COPY sse-back-end/requirements.txt /svitlo-power-sse-api/
COPY shared/python /shared/python

# install python dependencies
RUN pip install --upgrade pip --root-user-action=ignore
RUN pip install --no-cache-dir -r requirements.txt --root-user-action=ignore

COPY sse-back-end/ /svitlo-power-sse-api/

CMD ["uvicorn", "run:app", "--host", "0.0.0.0", "--port", "5005", "--workers", "5"]
