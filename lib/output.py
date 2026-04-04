"""Terminal output helpers — colors and formatted printing."""


class Colors:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    NC = '\033[0m'


def print_colored(text, color):
    print(f"{color}{text}{Colors.NC}")


def print_header(text):
    print("\n" + "=" * 50)
    print_colored(text, Colors.BLUE)
    print("=" * 50 + "\n")
