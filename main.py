import sys

print("\n==========================================================")
print("ERROR: You are in the wrong folder!")
print("Please type 'cd backend' first, then run 'uvicorn main:app --reload'")
print("==========================================================\n")
sys.exit(1)

app = None  # Just in case uvicorn expects an app object
