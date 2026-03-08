import sys
import os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from main import initialize

svc = initialize()
print("\n--- Summary ---")
print(svc.get_market_summary())

print("\n--- Insights ---")
print(svc.get_insights())

print("\n--- Chain (1st row) ---")
chain = svc.get_options_chain()
if not chain.empty:
    print(chain.iloc[0].to_dict())
else:
    print("Chain is empty")
