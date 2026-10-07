FROM python:3.11-slim

WORKDIR /svitlo-power-grid-reporter

# Version argument (injected at build time)
ARG VERSION=0000.00.00
RUN mkdir -p /app && echo "${VERSION}" > /app/VERSION

COPY grid-reporter/requirements.txt /svitlo-power-grid-reporter/
COPY shared/python /shared/python

RUN pip install --upgrade pip --root-user-action=ignore
RUN pip install --no-cache-dir -r requirements.txt --root-user-action=ignore

COPY grid-reporter/ /svitlo-power-grid-reporter/

CMD ["python", "/svitlo-power-grid-reporter/run.py"]