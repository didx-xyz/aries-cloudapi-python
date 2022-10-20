FROM tiangolo/uvicorn-gunicorn-fastapi:python3.8

COPY app /app/
# COPY aries-cloudcontroller-python /aries-cloudcontroller-python/

WORKDIR /app

# If needing to download from test pypi
# RUN cd /app && pip install -r requirements.txt --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/
RUN cd /app && pip install -r requirements.txt

# RUN cd && pip install -e /aries-cloudcontroller-python

EXPOSE 8000

CMD ["uvicorn", "main:app", "--reload", "--host", "0.0.0.0", "--port", "8000"]
