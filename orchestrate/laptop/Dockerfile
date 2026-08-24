FROM alpine:3.24

WORKDIR /app

# Install required runtimes
RUN apk add --no-cache \
    go \
    python3 \
    py3-pip

# Install Go dependencies first for Docker layer caching
COPY benchmark/go.mod benchmark/go.sum ./benchmark/

RUN cd benchmark && go mod download

# Install Python dependencies
COPY requirements.txt ./requirements.txt

RUN python3 -m pip install \
    --no-cache-dir \
    --break-system-packages \
    -r requirements.txt

# Copy project using the real repository layout
COPY benchmark/ ./benchmark/
COPY environment/ ./environment/
COPY orchestrate/ ./orchestrate/
COPY report/ ./report/

# Runtime directories used by the orchestrators
RUN mkdir -p ./bin ./results