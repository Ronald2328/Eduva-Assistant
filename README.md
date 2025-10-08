# Getting Started

## Requirements

Install [uv](https://github.com/astral-sh/uv) with the following command:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

## Install project dependencies

```bash
uv sync
```

## Configure environment variables

Create a `.env` file in the root of the project. You can start with the `.env.example` file.

```bash
cp .env.example .env
```

## Run the project

```bash
uv run fastapi dev
```

or

```bash
uv run langgraph dev
```
