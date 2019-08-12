ARG TENSORFLOW_VERSION=1.14.0-gpu-py3
FROM tensorflow/tensorflow:${TENSORFLOW_VERSION}

WORKDIR /

RUN apt-get -y update && apt-get -y upgrade && \
    apt-get install -y --no-install-recommends curl

COPY . /galois
WORKDIR /galois
RUN curl -SL https://github.com/iedmrc/galois-autocompleter/releases/latest/download/model.tar.xz \
    | tar -xJC . && \
    pip --no-cache-dir install --upgrade pip && \
    pip --no-cache-dir install -r requirements.txt && \
    apt purge -y git curl && \
    apt autoremove --purge -y && \
    apt clean && \
    rm -rf /var/lib/apt/lists/*

CMD [ "python", "main.py" ]