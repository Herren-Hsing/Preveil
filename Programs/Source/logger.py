import logging
import os

log_directory = "run-log"
os.makedirs(log_directory, exist_ok=True)

log_file_path = os.path.join(log_directory, "output.log")

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s', handlers=[
    logging.FileHandler(log_file_path),
    logging.StreamHandler()
])

def print_to_log(*args, **kwargs):
    message = ' '.join(map(str, args))
    logging.info(message)
    print(*args, **kwargs)

if __name__ == "__main__":
    print_to_log("This is a test message with multiple", "arguments:", 123, {"key": "value"})
