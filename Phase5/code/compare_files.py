from pathlib import Path
import sys

def same_file(a, b):
    return Path(a).read_bytes() == Path(b).read_bytes()

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python code/compare_files.py input_file output_file")
        raise SystemExit(1)
    if same_file(sys.argv[1], sys.argv[2]):
        print("PASS: files match byte-for-byte")
    else:
        print("FAIL: files do not match")
        raise SystemExit(2)
