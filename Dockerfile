FROM python:3.12-slim-bookworm

RUN groupadd --gid 998 container && \
    useradd \
      --uid 998 \
      --gid 998 \
      --create-home \
      --home-dir /home/container \
      --shell /bin/bash \
      container

RUN mkdir -p /home/container && \
    chown 998:998 /home/container

ENV USER=container
ENV HOME=/home/container

WORKDIR /home/container

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        openssh-client \
        ca-certificates && \
    rm -rf /var/lib/apt/lists/*

COPY --chown=998:998 requirements.txt /home/container/requirements.txt

RUN python -m pip install --no-cache-dir \
    -r /home/container/requirements.txt

COPY --chown=998:998 app.py /home/container/app.py

USER container

CMD ["python", "/home/container/app.py"]
