import sys
import os
from pathlib import Path

# Add backend/ to path
sys.path.insert(0, str(Path(__file__).resolve().parent))

print(f"sys.path[0]: {sys.path[0]}")

try:
    import ingestion.loader
    print(f"ingestion.loader file: {ingestion.loader.__file__}")
    print(f"Attributes in ingestion.loader: {[a for a in dir(ingestion.loader) if not a.startswith('__')]}")
    
    from ingestion.loader import load_csv_to_sqlite
    print("Import successful!")
except ImportError as e:
    print(f"Import failed: {e}")
except Exception as e:
    print(f"An error occurred: {e}")
