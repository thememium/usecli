# Reporting a Vulnerability

To report a security vulnerability, please email boswell.labs@gmail.com.

We take security seriously and will respond to security reports within 48 hours. Please include as much detail as possible about the vulnerability, including:

- A description of the vulnerability
- Steps to reproduce the issue
- Potential impact
- Suggested fix (if any)

While the discovery of new vulnerabilities is rare, we also recommend always using the latest version of useCli to ensure your application remains as secure as possible.

## Security Considerations for useCli

As useCli is a CLI tool that generates code and executes commands, please be aware of the following security practices:

- **Code Generation**: useCli generates files and code based on templates. Always review generated code before committing it to your repository.
- **Command Execution**: Some useCli features may execute system commands. Ensure you trust the source of any useCli commands you run.
- **File System Access**: useCli reads from and writes to the file system. Be cautious when running useCli in directories with sensitive files.

## Security Hall of Fame

We would like to thank the following security researchers for responsibly disclosing security issues to us.

*No security researchers have been added to the hall of fame yet. Will you be the first?*
