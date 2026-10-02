FROM python:latest

WORKDIR /svitlo-power-back-end

# set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBUG=True

# Version argument (injected at build time)
ARG VERSION=0000.00.00
RUN mkdir -p /app && echo "${VERSION}" > /app/VERSION

COPY back-end/requirements.txt /svitlo-power-back-end/
COPY shared/python /shared/python
COPY shared/i18n /shared/i18n

# install python dependencies
RUN pip install --upgrade pip --root-user-action=ignore
RUN pip install --no-cache-dir -r requirements.txt --root-user-action=ignore

COPY back-end/ /svitlo-power-back-end/

# gunicorn
CMD ["uvicorn", "run:app", "--host", "0.0.0.0", "--port", "5005"]