FROM docker.io/golang:1.23 AS builder

WORKDIR /app

# xk6-sse doesn't support k6>=0.53
# https://github.com/phymbert/xk6-sse/issues/19
RUN go install go.k6.io/xk6/cmd/xk6@v0.13.0
RUN xk6 build v0.52.0 --output /app/xk6 \
    --with github.com/avitalique/xk6-file@v1.4.0 \
    --with github.com/phymbert/xk6-sse@v0.1.2

FROM docker.io/alpine:3

COPY --from=builder /app/xk6 /usr/local/bin/xk6

ENTRYPOINT ["/usr/local/bin/xk6"]
