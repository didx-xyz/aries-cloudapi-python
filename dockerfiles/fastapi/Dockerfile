FROM tiangolo/uvicorn-gunicorn-fastapi:python3.8

COPY app /app

WORKDIR /app

RUN cd /app && pip install -r requirements.txt --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/
# RUN cd /app && pip install -r requirements.txt

EXPOSE 8000

CMD ["uvicorn", "main:app", "--reload", "--host", "0.0.0.0", "--port", "8000"]
