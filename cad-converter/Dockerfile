# Use a lightweight Python base image
FROM python:3.11-slim

# Install system dependencies needed to build LibreDWG
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    autoconf \
    libtool \
    swig \
    texinfo \
    build-essential \
    gcc \
    pkg-config \
    make \
    && rm -rf /var/lib/apt/lists/*

# Clone and build GNU LibreDWG
WORKDIR /tmp
RUN git clone --depth 1 https://github.com/LibreDWG/libredwg.git && \
    cd libredwg && \
    sh autogen.sh && \
    ./configure --prefix=/usr/local --disable-shared && \
    make -j$(nproc) && \
    make install && \
    cd .. && \
    rm -rf libredwg

# Set working directory for the application
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn

# Copy the rest of the application files
COPY . .

# Expose port (Render/Railway will provide $PORT)
EXPOSE 5000

# Run with gunicorn
CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:${PORT:-5000} server:app"]
