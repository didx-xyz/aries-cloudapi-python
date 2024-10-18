# NATS

**NATS** is an open-source messaging system designed for high-performance, lightweight, and reliable communication between
distributed applications. It supports **pub-sub** (publish-subscribe), **request-reply**, and **message queue** patterns,
allowing for flexible communication between microservices, IoT devices, and cloud-native systems.

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

## Consuming our NATS

Please contact us for help with connecting/authenticating to our nats service
