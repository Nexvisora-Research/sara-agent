#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Debug script to test Sara SLM generation and confidence gate.
"""

import os
import sys

# Add the project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Test user ID - let's find which user actually has a trained model
USER_ID = None

def find_trained_users():
    """Find users who have trained SLM models."""
    from brain.sara_slm import DATA_DIR, SLM_DIR_NAME, WEIGHTS_FILE

    trained_users = []
    if os.path.exists(DATA_DIR):
        for user_id in os.listdir(DATA_DIR):
            user_slm_dir = os.path.join(DATA_DIR, user_id, SLM_DIR_NAME)
            weights_path = os.path.join(user_slm_dir, WEIGHTS_FILE)
            if os.path.exists(weights_path):
                trained_users.append(user_id)
    return trained_users

def test_slm_generation():
    """Test what Sara SLM is actually generating."""
    print("=== Sara SLM Debug Test ===")

    # Import the required modules
    from brain.sara_slm import is_trained, generate
    from brain.personal_llm import _is_confident

    # Find users with trained models
    print("1. Finding users with trained SLM models...")
    trained_users = find_trained_users()
    print(f"   Found trained users: {trained_users}")

    if not trained_users:
        print("   [X] No users have trained SLM models yet! Run /train_slm first!")
        return

    # Use the first trained user
    user_id = trained_users[0]
    print(f"   Using user: {user_id}")

    print(f"2. Verifying SLM is trained for user {user_id}...")
    trained = is_trained(user_id)
    print(f"   Trained: {trained}")

    if not trained:
        print("   [X] SLM training check failed!")
        return

    # Test prompts
    test_prompts = [
        "Hello, how are you?",
        "What is your name?",
        "Tell me a joke",
        "What's 2+2?",
        "How's the weather?"
    ]

    for i, prompt in enumerate(test_prompts, 1):
        print(f"\n{i}. Testing prompt: '{prompt}'")

        # Get raw SLM output
        raw_output = generate(user_id, prompt)
        print(f"   Raw output: {repr(raw_output)}")

        if raw_output:
            print(f"   Length: {len(raw_output)} chars")
            print(f"   Content: '{raw_output[:200]}...' " if len(raw_output) > 200 else f"   Content: '{raw_output}'")

            # Check confidence gate
            confident = _is_confident(raw_output, min_len=10)  # SLM uses min_len=10
            print(f"   Passes confidence gate: {confident}")

            if not confident:
                print("   [X] Response rejected by confidence gate!")
                # Detailed confidence checks
                t = raw_output.strip()
                print(f"      - Length check (>= 10): {len(t) >= 10}")
                print(f"      - Contains letters: {any(c.isalpha() for c in t)}")

                # Repetition check
                words = t.lower().split()
                if len(words) > 4:
                    unique_ratio = len(set(words)) / len(words)
                    print(f"      - Word uniqueness ratio: {unique_ratio:.2f} (need >= 0.40)")
                else:
                    print(f"      - Too few words for repetition check: {len(words)}")

            else:
                print("   [OK] Response would be accepted!")
        else:
            print("   [X] No output generated")

def test_confidence_gate():
    """Test the confidence gate with various inputs."""
    print("\n=== Confidence Gate Test ===")

    from brain.personal_llm import _is_confident

    test_cases = [
        ("Hello! How can I help you?", True),
        ("I don't know.", False),
        ("Hi", False),  # Too short
        ("???", False),  # No letters
        ("Hello hello hello hello hello hello", False),  # Too repetitive
        ("<|system|>Hello", False),  # Special tokens
        ("I can help you with various tasks and questions.", True),
    ]

    for text, expected in test_cases:
        result = _is_confident(text, min_len=10)
        status = "[OK]" if result == expected else "[X]"
        print(f"{status} '{text}' -> {result} (expected {expected})")

if __name__ == "__main__":
    test_slm_generation()
    test_confidence_gate()