# Heredoc (Here Document) Syntax Guide

## Overview

`cat << 'EOF'` is a **heredoc** (here document) syntax in Bash/shell scripting. It's a way to pass multi-line text input to a command without using separate quoted strings or files.

## Basic Syntax

```bash
cat << 'EOF'
multiple
lines
of text
EOF
```

**Output:**

```
multiple
lines
of text
```

## How It Works

1. `cat` - The command that reads and outputs content
2. `<<` - Redirects input from a here document
3. `'EOF'` - A **delimiter** marking the start of the text
4. Text content - Multiple lines
5. `EOF` - A **delimiter** marking the end of the text (must be at the start of a line)

## Quoted vs Unquoted Delimiters

### 1. Quoted Delimiter (Prevents Variable Expansion)

```bash
cat << 'EOF'
This is $USER (literal)
EOF
```

**Output:**

```
This is $USER (literal)
```

Variables and special characters are treated literally.

### 2. Unquoted Delimiter (Allows Variable Expansion)

```bash
cat << EOF
This is $USER (expanded to your username)
EOF
```

**Output:**

```
This is sibamaharana (expanded to your username)
```

Variables and backticks are interpreted.

### 3. Escaped Delimiter (Mixed Behavior)

```bash
cat << \EOF
This is $USER (literal, backslash escapes the delimiter)
EOF
```

**Output:**

```
This is $USER (literal)
```

## Common Use Cases

### 1. Write Multi-line Text to a File

```bash
cat << 'EOF' > /tmp/config.txt
[database]
host=localhost
port=5432
username=admin
EOF
```

### 2. Append to a File

```bash
cat << 'EOF' >> /tmp/config.txt
[logging]
level=debug
EOF
```

### 3. Pipe to Another Command

```bash
cat << 'EOF' | grep "error"
Processing started
error: file not found
Processing completed
EOF
```

**Output:**

```
error: file not found
```

### 4. Create Environment Variables

```bash
export MY_CONFIG=$(cat << 'EOF'
line1
line2
line3
EOF
)
echo "$MY_CONFIG"
```

### 5. Generate Configuration Files with Variables

```bash
USERNAME="sibamaharana"
cat << EOF > /tmp/user_config.txt
User: $USERNAME
Home: $HOME
Shell: $SHELL
EOF
```

### 6. Multi-line Comments in Scripts

```bash
: << 'EOF'
This is a comment block
that spans multiple lines
and doesn't execute any code
EOF
```

### 7. Pass Multi-line Arguments to Commands

```bash
mysql -u root << 'EOF'
CREATE DATABASE test;
USE test;
CREATE TABLE users (id INT, name VARCHAR(100));
EOF
```

## Advanced Examples

### With Indentation (using `-` prefix)

```bash
function setup() {
    cat <<- 'EOF'
 This text is indented
 but leading tabs are removed
 (useful for readability in scripts)
    EOF
}
```

The `-` allows the closing delimiter to be indented.

### Heredoc with Command Substitution

```bash
cat << EOF
Current directory: $(pwd)
User: $(whoami)
Date: $(date)
EOF
```

**Output:**

```
Current directory: /home/sibamaharana/workspace/project-durango/orangescrum-next/project-durango
User: sibamaharana
Date: Wed Jan 15 12:00:00 UTC 2026
```

### Heredoc in Docker/Configuration Files

In the project's Dockerfiles, heredoc is used for creating multi-line configurations:

```dockerfile
RUN cat << 'EOF' > /etc/php/php.ini
[PHP]
memory_limit = 512M
max_execution_time = 300
EOF
```

## Variants and Options

| Syntax | Effect |
|--------|--------|
| `<< 'EOF'` | Literal text (no variable expansion) |
| `<< EOF` | Variable expansion enabled |
| `<< \EOF` | Escape delimiter (same as quoted) |
| `<<- 'EOF'` | Allow indentation of closing delimiter |
| `<<~ 'EOF'` | Remove leading whitespace (bash 5.3+) |

## Common Mistakes

### ❌ Closing Delimiter Not at Start of Line

```bash
# WRONG - will fail
cat << 'EOF'
some text
    EOF  # indented - not recognized as delimiter
```

### ❌ Closing Delimiter with Extra Characters

```bash
# WRONG - will fail
cat << 'EOF'
some text
EOF; # semicolon breaks it
```

### ✅ Correct Way

```bash
# RIGHT
cat << 'EOF'
some text
EOF
```

## In This Project

Look for heredoc usage in:

- **Dockerfiles**: Creating configuration files during image build
- **Shell scripts**: Generating complex configurations or SQL scripts
- **setup-*.sh scripts**: Multi-line environment configuration

Example from project:

```bash
# In setup.sh or similar
cat << 'EOF' > config.env
DEBUG=true
APP_NAME=OrangeScrum
EOF
```

## Summary

| Feature | Syntax |
|---------|--------|
| What | Multi-line text input to commands |
| Start | `<< 'DELIMITER'` |
| End | `DELIMITER` at start of line |
| Variables | Quoted delimiter = literal; Unquoted = expanded |
| Use | Files, pipes, variables, configuration |
| Advantage | Clean, readable multi-line input |
| Alternative | Echo multiple lines, `-e` flag, or separate files |

---

**References:**

- [GNU Bash Manual - Here Documents](https://www.gnu.org/software/bash/manual/html_node/Redirections.html#Here-Documents)
- [Bash Scripting Guide](https://www.gnu.org/software/bash/manual/bash.html)
