FROM python:3.11-slim

WORKDIR /app

# Install build tools for compiling C and C++ shared modules
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    clang \
    g++ \
    make \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Compile C and C++ native libraries
RUN make -C c_modules clean && make -C c_modules
RUN make -C cpp_modules clean && make -C cpp_modules

EXPOSE 8000

CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
