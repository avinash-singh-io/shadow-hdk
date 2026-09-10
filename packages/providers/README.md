# shadow-hdk-providers

Which model or agent this machine can reach, and whether it is ready to be used.

Two seams (D39): an **inference** provider you hold a key for, and an **agent** provider you already
have a subscription to. This package finds them, asks them about themselves, and hands back the
right port — and it imports no adapter to do it.

It never reads a credential and it never installs anything (D41).
