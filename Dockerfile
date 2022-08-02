FROM python:3.10-slim
ENV PYTHONUNBUFFERED=1
ENV PYTHONIOENCODING=UTF-8

#PIPENV_IGNORE_VIRTUALENVS=1
#ENV VIRTUAL_ENV=/opt/venv
#RUN python3 -m venv $VIRTUAL_ENV
#ENV PATH="$VIRTUAL_ENV/bin:$PATH"


RUN apt-get update \
    && apt-get install g++ -y \
    && apt-get install gcc -y \
    && apt-get install -y default-libmysqlclient-dev \
    && apt-get clean

WORKDIR /parent
COPY requirements.txt ./requirements.txt
COPY Pipfile ./Pipfile
COPY Pipfile.lock ./Pipfile.lock
COPY app ./app
COPY artifacts ./artifacts
COPY data ./data
EXPOSE 8501

RUN pip3 install -r requirements.txt && \
mkdir -p /root/.streamlit && \
mkdir -p /root/.streamlit && \
bash -c 'echo -e "\
[general]\n\
email = \"\"\n\
headless = true\n\
" > /root/.streamlit/credentials.toml'

ENV PYTHONPATH /parent

#ENTRYPOINT ["streamlit", "run", "--server.headless", "true", "--server.enableXsrfProtection", "false"]
ENTRYPOINT ["streamlit", "run"]
CMD ["app/main/python/dashboard.py"]