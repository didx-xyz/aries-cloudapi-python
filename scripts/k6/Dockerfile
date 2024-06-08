# Use the official Go image as the base image
FROM golang:1.22

# Set the working directory inside the container
WORKDIR /app

# Install xk6
RUN go install go.k6.io/xk6/cmd/xk6@latest

# Build xk6 with the specified extensions
RUN xk6 build --output /usr/local/bin/xk6 \
  --with github.com/avitalique/xk6-file@latest \
  --with github.com/phymbert/xk6-sse

# Set the entrypoint to xk6
ENTRYPOINT ["/usr/local/bin/xk6"]
