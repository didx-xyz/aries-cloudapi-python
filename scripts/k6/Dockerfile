FROM docker.io/golang:1.23 AS builder

WORKDIR /app

RUN go install go.k6.io/xk6/cmd/xk6@v0.13.4
RUN xk6 build v0.56.0 --output /app/xk6 \
    --with github.com/avitalique/xk6-file@v1.4.2 \
    --with github.com/phymbert/xk6-sse@v0.1.8

FROM docker.io/alpine:3

COPY --from=builder /app/xk6 /usr/local/bin/xk6

USER nobody

ENTRYPOINT ["/usr/local/bin/xk6"]
