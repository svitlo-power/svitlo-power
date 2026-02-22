FROM python:3.11-slim

WORKDIR /svitlo-power-grid-reporter

COPY requirements.txt /svitlo-power-grid-reporter/
COPY --from=shared ./python /shared/python

RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

COPY . /svitlo-power-grid-reporter/

CMD ["python", "/svitlo-power-grid-reporter/run.py"]