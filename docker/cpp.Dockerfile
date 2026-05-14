FROM debian:bookworm-slim

RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    nlohmann-json3-dev \
    --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

    
COPY docker/cpp_support.hpp /opt/cpp_support.hpp

# Precompile the stable wrapper support once at image-build time so each
# submission only compiles the user code plus the thin generated wrapper.
RUN g++ -std=c++20 -O0 -pipe -x c++-header /opt/cpp_support.hpp -o /opt/cpp_support.hpp.gch

RUN useradd -m -u 1001 runner
WORKDIR /app
