class EventGeneratorWrapper:
    def __init__(self, generator, sse_manager, wallet, topic, populate_task):
        self.generator = generator
        self.sse_manager = sse_manager
        self.wallet = wallet
        self.topic = topic
        self.populate_task = populate_task

    async def __aenter__(self):
        return self.generator

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.generator.aclose()  # Close the async generator
        await self.sse_manager.cleanup(
            self.wallet, self.topic, self.populate_task
        )  # Call the cleanup method on the SseManager instance
