#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test the new conversation-aware dataset to verify it preserves boundaries.
"""

import os
import sys

# Add the project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_conversation_dataset():
    """Test that the new dataset preserves conversation boundaries."""
    print("=== Conversation Dataset Test ===")

    try:
        from transformers import GPT2Tokenizer
        from brain.sara_slm import _ConversationDataset

        # Create test conversations
        test_conversations = [
            "<|system|>\nYou are Sara.\n</s>\n<|user|>\nHello\n</s>\n<|assistant|>\nHi there!\n</s>",
            "<|system|>\nYou are helpful.\n</s>\n<|user|>\nWhat's 2+2?\n</s>\n<|assistant|>\n2+2 equals 4.\n</s>",
            "<|system|>\nYou are Sara.\n</s>\n<|user|>\nTell me a joke\n</s>\n<|assistant|>\nWhy did the chicken cross the road?\n</s>",
        ]

        # Initialize tokenizer
        tokenizer = GPT2Tokenizer.from_pretrained("gpt2")
        tokenizer.pad_token = tokenizer.eos_token

        # Create dataset
        seq_len = 256
        dataset = _ConversationDataset(test_conversations, tokenizer, seq_len)

        print(f"Created dataset with {len(dataset)} samples")

        # Test first few samples
        for i in range(min(3, len(dataset))):
            x, y = dataset[i]

            print(f"\nSample {i+1}:")
            print(f"  Input length: {len(x)}")
            print(f"  Target length: {len(y)}")

            # Decode to check content
            decoded_input = tokenizer.decode(x, skip_special_tokens=False)
            print(f"  Content preview: {repr(decoded_input[:100])}...")

            # Check that it's a complete conversation (not a fragment)
            if "<|system|>" in decoded_input and "<|user|>" in decoded_input:
                print(f"  [OK] Contains proper conversation structure")
            else:
                print(f"  [X] Missing conversation structure")

    except Exception as e:
        print(f"Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_conversation_dataset()