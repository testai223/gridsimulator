#!/usr/bin/env python3
"""
A simple Hello World application template following Python best practices.

This module serves as a template for Python projects, demonstrating proper
structure, type hints, docstrings, and PEP8 compliance.
"""

from typing import Optional


def greet(name: Optional[str] = None) -> str:
    """
    Generate a greeting message.

    Args:
        name: The name to greet. If None, greets the world.

    Returns:
        A greeting message string.

    Examples:
        >>> greet()
        'Hello, World!'
        >>> greet("Alice")
        'Hello, Alice!'
    """
    if name is None:
        return "Hello, World!"
    return f"Hello, {name}!"


def main() -> None:
    """
    Main entry point of the application.
    
    This function orchestrates the program execution and handles
    any necessary setup or cleanup.
    """
    # Print the default greeting
    print(greet())
    
    # Example of greeting with a name
    print(greet("Python Developer"))


if __name__ == "__main__":
    main()