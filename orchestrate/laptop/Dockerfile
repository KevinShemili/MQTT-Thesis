FROM golang:1.25.11-alpine3.24

RUN apk add --no-cache python3=3.14.5-r0 py3-pip=26.1.2-r0 pv=1.10.5-r0

WORKDIR /app

COPY python/requirements.txt .
RUN pip install --no-cache-dir --break-system-packages -r requirements.txt

COPY golang/go.mod golang/go.sum ./
RUN go mod download

COPY golang/ .

RUN go test -c -o benchmark-binary ./benchmark
RUN go build -o provision-binary ./cmd/provision

COPY python/ .
COPY script/ .
COPY orchestration/ ./orchestration/