FROM rust:latest as builder
WORKDIR /app
COPY . .
# Cache dependencies later if needed, for now straight build
RUN cargo build --release

FROM debian:bookworm-slim
WORKDIR /app
RUN apt-get update && apt-get install -y openssl ca-certificates && rm -rf /var/lib/apt/lists/*
COPY --from=builder /app/target/release/entry_proxy /usr/local/bin/entry_proxy
COPY --from=builder /app/target/release/exit_proxy /usr/local/bin/exit_proxy
