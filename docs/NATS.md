# NATS

NATS is a lightweight, high-performance messaging system designed for cloud native applications, IoT messaging, and microservices
architectures.

## Key Features

- Simple: Text-based protocol with straightforward publish-subscribe semantics
- Fast: Written in Go, capable of millions of messages per second
- Lightweight: Small footprint, minimal dependencies
- Cloud Native: Built for modern distributed systems

## Core Concepts

- Publishers: Send messages to subjects
- Subscribers: Receive messages from subjects
- Subjects: Named channels for message routing
- Queue Groups: Load balance messages across subscribers

## Message Patterns

- Publish/Subscribe: One-to-many message distribution
- Request/Reply: Synchronous communication
- Queue Groups: Load balanced message processing
- Stream Processing: Persistent message streams (via NATS Streaming/JetStream)
