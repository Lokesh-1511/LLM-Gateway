import asyncio
from compression_service import compress_prompt

async def test_compression():
    print("Testing Prompt Compression...")
    
    test_prompts = [
        "Please can you tell me what the capital of France is? I was wondering if you could also list some of its famous landmarks.",
        "    Would you mind   writing a simple python   script for me?   ",
        "Explain quantum computing."
    ]
    
    for prompt in test_prompts:
        print(f"\nOriginal ({len(prompt)} chars): {prompt}")
        compressed, ratio = compress_prompt(prompt)
        print(f"Compressed ({len(compressed)} chars): {compressed}")
        print(f"Compression Ratio: {ratio:.2f}x")

if __name__ == "__main__":
    asyncio.run(test_compression())
