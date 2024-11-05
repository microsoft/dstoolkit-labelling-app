FROM python:3.11-slim-buster

RUN pip install -U pip

RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install --no-install-recommends -y \
    ca-certificates \
    g++ \
    ffmpeg libsm6 libxext6 git ninja-build libglib2.0-0 libsm6 libxrender-dev libxext6 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY ./src/requirements.txt /src/requirements.txt
RUN pip install -r /src/requirements.txt

RUN useradd -m appuser
USER appuser

COPY ./src /app/src

EXPOSE 80

ENV PYTHONPATH=/app/src


CMD streamlit run /app/src/webpage/main.py --server.port 80 --server.fileWatcherType none --browser.gatherUsageStats false
