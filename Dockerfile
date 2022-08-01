FROM python:3.10
ENV PYTHONUNBUFFERED=1
ENV PYTHONIOENCODING=UTF-8
WORKDIR /app
COPY requirements.txt ./requirements.txt
COPY Pipfile ./Pipfile
#RUN pip3 install -r requirements.txt
EXPOSE 8501
COPY app .
RUN pip3 install -r requirements.txt && \
pip3 install --upgrade pip && \
pip3 install pipenv && \
pipenv install --deploy --system --ignore-pipfile

ENTRYPOINT ["streamlit", "run"]
CMD ["app/main/tracker.py"]