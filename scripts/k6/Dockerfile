# Use the official Go image as the base image
FROM golang:1.22 AS builder

# Set the working directory inside the container
WORKDIR /app

# Install xk6 and build with specified extensions in a single step to reduce layers
RUN go install go.k6.io/xk6/cmd/xk6@latest && \
    xk6 build --output /usr/local/bin/xk6 \
    --with github.com/avitalique/xk6-file@latest \
    --with github.com/phymbert/xk6-sse

# Use a minimal base image for the final stage
FROM alpine:latest

# Copy the built xk6 binary from the builder stage
COPY --from=builder /usr/local/bin/xk6 /usr/local/bin/xk6

# Install Tini
RUN apk add --no-cache tini

# Set the entrypoint to Tini
ENTRYPOINT ["/sbin/tini", "--"]

# Run your program under Tini
CMD ["/usr/local/bin/xk6"]

# # Set the entrypoint to xk6
# ENTRYPOINT ["/usr/local/bin/xk6"]
