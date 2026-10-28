FROM python:3-alpine
RUN pip3 install pika nltk
RUN python -c "import nltk; nltk.download('stopwords', download_dir='/usr/local/share/nltk_data', raise_on_error=True)"
WORKDIR /app
COPY src/common common
COPY src/preprocess preprocess
ENTRYPOINT ["python", "-m", "preprocess.main"]
