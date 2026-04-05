"""Terminal output helpers — colors and formatted printing."""


class Colors:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    CYAN = '\033[0;36m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    NC = '\033[0m'


BANNER = (
    " \u2588\u2588\u2588\u2588\u2588\u2588\u2588 \u2588\u2588\u2588\u2588\u2588\u2588\u2588 \u2588\u2588\u2588    \u2588\u2588\u2588 \u2588\u2588\u2588\u2588\u2588\u2588\n"
    " \u2588\u2588      \u2588\u2588      \u2588\u2588\u2588\u2588  \u2588\u2588\u2588\u2588 \u2588\u2588   \u2588\u2588\n"
    " \u2588\u2588\u2588\u2588\u2588\u2588\u2588 \u2588\u2588\u2588\u2588\u2588\u2588\u2588 \u2588\u2588 \u2588\u2588\u2588\u2588 \u2588\u2588 \u2588\u2588   \u2588\u2588\n"
    "      \u2588\u2588      \u2588\u2588 \u2588\u2588  \u2588\u2588  \u2588\u2588 \u2588\u2588   \u2588\u2588\n"
    " \u2588\u2588\u2588\u2588\u2588\u2588\u2588 \u2588\u2588\u2588\u2588\u2588\u2588\u2588 \u2588\u2588      \u2588\u2588 \u2588\u2588\u2588\u2588\u2588\u2588\n"
    " Spawn \u00b7 Scope \u00b7 Migrate \u00b7 Destroy\n"
)


def print_colored(text, color):
    print(f"{color}{text}{Colors.NC}")


def print_banner():
    print(f"{Colors.CYAN}{BANNER}{Colors.NC}")


def print_header(text):
    print("\n" + "=" * 50)
    print_colored(text, Colors.BLUE)
    print("=" * 50 + "\n")
