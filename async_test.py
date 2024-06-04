import asyncio
import random


async def access_shared_resource(task_id, semaphore):
    async with semaphore:
        print(f"Task {task_id} is accessing the shared resource")
        # Simulate some I/O-bound operation
        await asyncio.sleep(random.uniform(0.1, 1.0))
        result = f"Result from task {task_id}"
        print(f"Task {task_id} has finished accessing the shared resource")
        return result


async def main():
    # Create a semaphore that allows up to 3 concurrent accesses
    semaphore = asyncio.Semaphore(3)

    # Create multiple tasks
    tasks = [access_shared_resource(i, semaphore) for i in range(10)]

    # Run tasks concurrently and gather their results
    results = await asyncio.gather(*tasks)

    # Print all results
    for result in results:
        print(result)


# Run the main function
if __name__ == "__main__":
    asyncio.run(main())
