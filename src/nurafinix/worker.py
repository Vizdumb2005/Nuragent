"""Worker entry point for the Nurafinix Prospect Engine."""

from mistralai.workflows import workflow

# Import workflows to register them
from .workflows.prospecting import ProspectingWorkflow


if __name__ == "__main__":
    import asyncio
    import sys
    
    async def main():
        """Start the worker."""
        # Import and start the workflow worker
        from mistralai.workflows.worker import Worker
        
        worker = Worker()
        await worker.run()
    
    asyncio.run(main())
