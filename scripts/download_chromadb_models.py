#!/usr/bin/env python3
"""
Download ChromaDB embedding models for offline bundling.

This script pre-downloads the ONNX embedding models used by ChromaDB
so they can be bundled with the PyInstaller executable.

Usage:
    python scripts/download_chromadb_models.py

After running, the models will be in ~/.cache/chroma/onnx_models/
and the build script will bundle them with the executable.
"""


import sys
from pathlib import Path

def download_models():
    """Download ChromaDB's default ONNX embedding model."""
    print("=" * 60)
    print("ChromaDB ONNX Model Download Script")
    print("=" * 60)
    
    # Check if chromadb is installed
    try:
        import chromadb
        from chromadb.utils.embedding_functions import ONNXMiniLM_L6_V2
        print(f"ChromaDB version: {chromadb.__version__}")
    except ImportError:
        print("Error: chromadb not installed. Run: pip install chromadb")
        sys.exit(1)
    
    # Get the cache directory where models will be stored
    cache_dir = Path.home() / ".cache" / "chroma" / "onnx_models"
    print(f"Model cache directory: {cache_dir}")
    
    # Create the embedding function - this triggers download if not cached
    print("\nDownloading/loading ONNX embedding model...")
    print("(This may take a few minutes on first run)")
    
    try:
        # Initialize the embedding function
        ef = ONNXMiniLM_L6_V2(preferred_providers=["CPUExecutionProvider"])
        
        # Test it with a sample text to ensure it's fully loaded
        test_result = ef(["Test embedding"])
        print(f"Model loaded successfully! Embedding dimension: {len(test_result[0])}")
        
    except Exception as e:
        print(f"Error loading embedding model: {e}")
        sys.exit(1)
    
    # Find the downloaded model files
    if cache_dir.exists():
        model_files = list(cache_dir.rglob("*"))
        total_size = sum(f.stat().st_size for f in model_files if f.is_file())
        print("\nModel files downloaded:")
        print(f"  Location: {cache_dir}")
        print(f"  Files: {len([f for f in model_files if f.is_file()])}")
        print(f"  Total size: {total_size / (1024*1024):.1f} MB")
    else:
        print(f"\nWarning: Expected cache directory not found: {cache_dir}")
        print("Models may be stored in a different location.")
    
    print("\n" + "=" * 60)
    print("Model download complete!")
    print("Run 'python scripts/build_backend.py' to build with bundled models.")
    print("=" * 60)


if __name__ == "__main__":
    download_models()
