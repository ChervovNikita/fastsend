# fastsend

Fast file transfer over direct TCP. A lightweight croc alternative built for RunPod symmetric ports.

Supports single files, multiple files, and entire folders.

## Install

```bash
curl -fsSL https://raw.githubusercontent.com/ChervovNikita/fastsend/main/install.sh | bash
```

## Usage

### Receive (on the target machine)

```bash
fastsend receive
```

On RunPod this auto-discovers a symmetric port. On other machines, pass one explicitly:

```bash
fastsend receive --port 9000
```

Output:

```
Listening on 52.10.1.4:12001

Run this on the sender:

  fastsend send 52.10.1.4:12001 --token F3K9A1 FILE [FILE ...]
```

### Send a single file

```bash
fastsend send 52.10.1.4:12001 --token F3K9A1 model.pt
```

### Send multiple files

```bash
fastsend send 52.10.1.4:12001 --token F3K9A1 model.pt config.yaml weights.bin
```

### Send a folder

The directory structure is preserved on the receiver side:

```bash
fastsend send 52.10.1.4:12001 --token F3K9A1 checkpoints/
```

## How it works

1. **Receiver** binds a TCP port (auto-detected from RunPod env vars or manually specified) and generates a one-time auth token.
2. **Sender** connects, authenticates with the token, then streams files sequentially over the same connection.
3. Folders are walked recursively; the receiver recreates the directory structure.

No relay servers, no encryption overhead — just raw TCP for maximum throughput between machines on the same network or with direct connectivity.
