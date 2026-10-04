# Security policy

This repository ships code that runs inside people's Claude Code sessions: hooks that inspect every `Bash` call, scripts that read agent configuration, and an MCP server. We treat its security seriously and we want to hear about problems.

## Supported versions

Only the latest release on `main` is supported. Pin a tag if you need stability, and update when a security fix is announced in [CHANGELOG.md](CHANGELOG.md).

## Reporting a vulnerability

Please do not open a public issue for a security problem.

1. Use GitHub's private vulnerability reporting on this repository ("Security" tab, "Report a vulnerability").
2. If that is unavailable, open an issue titled "Security contact request" with no details, and the maintainer will reply with a private channel.

Include what you found, how to reproduce it, and what you think the impact is. You will get an acknowledgement within 5 working days and a fix or a mitigation plan within 30 days for confirmed issues.

## What counts

Things we consider in scope:

- A hook that can be bypassed in a way that defeats its documented purpose (for example, a secret-printing command the `block-secret-exposure` hook misses by design rather than by omission in its pattern list).
- A hook, skill, command or script that could be made to execute untrusted input, write outside the project, or send data anywhere.
- The MCP server reading files outside its bundled data, binding to a network interface, or executing anything.
- The config audit script producing a false "no findings" result on a clearly dangerous configuration.
- Prompt-injection-style instructions hidden in any file of this repository.

Pattern-list gaps in the hooks (a new way to print a secret we do not catch yet) are welcome as ordinary issues or pull requests; they are detection improvements rather than vulnerabilities, unless they reveal a design flaw.

## What this plugin does and does not do

- No telemetry. Nothing in this repository phones home.
- The only network call is the documented, opt-in fetch of the incident dataset in `incident-lookup`, which falls back to a bundled copy and can be disabled with `--offline`.
- Hooks read the tool-call JSON on stdin and write a decision to stdout or stderr. They never modify files or run the command themselves.
- The MCP server uses stdio only and reads one JSON file that ships with the plugin.

See the "Security of the plugin itself" section of [README.md](README.md) for the full list of what each component can touch.
