# OpenAPI AsyncAPI Tools

Tooling to assist with exchange of information between API Portal and Event Portal

## Installation

Install Python 3.x first, then clone this repo then install the package locally with:

```bash
$ pip install .
```

## Usage

You MUST [Obtain an API token from Solace Cloud](https://docs.solace.com/Solace-Cloud/ght_use_rest_api_client_profiles.htm) using your account before launching this tool.

```bash
$ sep
Usage: sep [OPTIONS] COMMAND [ARGS]...

Options:
  --version  Show the version and exit.
  --help     Show this message and exit.

Commands:
  createQueue       Generate a queue based on the specified OpenAPI 3.0...
  generateAsyncAPI  Generate an AsyncAPI spec for the specified Application
  generateOpenAPI   Generate a OpenAPI spec for the specified Domain that...
  importOpenAPI     Generate an Application based on the specified OpenAPI...

$ sep --version
sep, version 0.0.4
```

## Known Issues

If you encountered below issue like :

> RuntimeError: Click will abort further execution because Python 3 was configured to use ASCII as encoding for the environment. Consult https://click.palletsprojects.com/python3/ for mitigation steps.

Please run `export LC_ALL=en_US.UTF-8` to fix it.
