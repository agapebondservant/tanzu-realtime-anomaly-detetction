FROM python:3.10-slim
ENV PYTHONUNBUFFERED=1
ENV PYTHONIOENCODING=UTF-8

WORKDIR /parent
COPY requirements.txt ./requirements.txt

RUN apt-get update \
    && apt-get install g++ -y \
    && apt-get install gcc -y \
    && apt-get install -y default-libmysqlclient-dev \
    && apt-get install -y git \
    && apt-get clean && \
    pip3 install --no-cache-dir  -r requirements.txt && \
    mkdir -p /root/.streamlit

COPY app ./app
# COPY rabbitmq ./rabbitmq
COPY data ./data
COPY assets ./assets
EXPOSE 8501

ENV PYTHONPATH /parent

ENTRYPOINT ["streamlit", "run"]
CMD ["app/main/python/ui/dashboard.py"]