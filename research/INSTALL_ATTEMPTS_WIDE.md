# mutmut and Alive2 attempts

Date: 2026-10-12. Neither tool installed. There is no killed, survived, timeout, or excluded count. There is no Alive2 score and no Alive2 command output.

## Debian CloudFront, which answered

`https://dpvctowv9b08b.cloudfront.net/debian/dists/trixie/main/binary-amd64/Packages.gz` returned HTTP 200. Bookworm returned HTTP 200. Sid returned HTTP 200. A case-insensitive search of each package list for `mutmut` or `alive2` found zero packages. Names that merely contained `alive` were `keepalived`, `libkeepalive0`, `libpoe-component-client-keepalive-perl`, and `python3-keepalive`.

## Hosts that did not answer

Each URL was requested once.

| URL | Error |
| --- | --- |
| `https://pypi.org/pypi/mutmut/json` | `OpenSSL SSL_connect: SSL_ERROR_SYSCALL` to pypi.org:443, HTTP 000 |
| `https://github.com/boxed/mutmut/archive/refs/heads/main.tar.gz` | `SSL_ERROR_SYSCALL` to github.com:443 |
| `https://github.com/AliveToolkit/alive2/archive/refs/heads/master.tar.gz` | `SSL_ERROR_SYSCALL` to github.com:443 |
| `https://files.pythonhosted.org/packages/source/m/mutmut/mutmut-3.2.0.tar.gz` | `SSL_ERROR_SYSCALL` to files.pythonhosted.org:443 |
| `https://cloudfront.cdn.aws.ubuntu.com/ubuntu/dists/noble/main/binary-amd64/Packages.gz` | `Could not resolve host: cloudfront.cdn.aws.ubuntu.com` |

Alive2 was not run. The checker language is `+` `-` `*` at one unsigned width. Alive2's language is LLVM IR. No subset was executed, because the tool is not on this machine.
