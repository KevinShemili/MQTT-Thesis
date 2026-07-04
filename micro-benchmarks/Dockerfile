FROM golang:1.25-alpine

RUN apk add --no-cache python3 py3-pip

WORKDIR /app

COPY python/requirements.txt .
RUN pip install --no-cache-dir --break-system-packages -r requirements.txt

COPY golang/go.mod golang/go.sum ./
RUN go mod download

COPY golang/ .
COPY python/ .
COPY script/ .

RUN go test -c -o benchmark-binary ./benchmark