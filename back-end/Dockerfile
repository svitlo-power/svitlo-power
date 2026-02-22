FROM python:latest

WORKDIR /svitlo-power-api

# set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DEBUG True

COPY back-end/requirements.txt /svitlo-power-api/
COPY shared/python /shared/python
COPY shared/i18n /shared/i18n

# install python dependencies
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

COPY back-end/ /svitlo-power-api/

# gunicorn
CMD ["uvicorn", "run:app", "--host", "0.0.0.0", "--port", "5005"]