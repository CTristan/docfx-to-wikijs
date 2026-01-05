# DocFX to Wiki.js Converter

This project is a documentation site generator designed to create API references for Unity games (such as [*Lobotomy Corporation*](https://store.steampowered.com/app/568220/Lobotomy_Corporation__Monster_Management_Simulation/)), converting them into a format compatible with **Wiki.js**.

It utilizes **DocFX** to extract metadata from managed assemblies (DLLs) and a custom Python toolchain to transform that metadata into clean, Wiki.js-ready Markdown.

## Features

*   **Metadata Extraction**: Uses DocFX to generate structured YAML metadata from C# assemblies.
*   **Wiki.js Conversion**: Converts DocFX YAML into Markdown files optimized for Wiki.js.
    *   Handles cross-references (`<xref>`) and links.
    *   Generates namespace landing pages.
    *   Includes full member details (constructors, methods, properties, fields).
    *   Sanitizes filenames for web compatibility.

## Prerequisites

*   **Game Assemblies (DLLs)**: The project requires the game's managed assemblies (specifically `Assembly-CSharp.dll` and relevant Unity libraries) to be placed in the `assemblies/` directory.
    *   *Hint:* These are typically found in the game's installation folder under `{GameName}_Data\Managed\`.
    *   *Example (Lobotomy Corporation):* `C:\Program Files (x86)\Steam\steamapps\common\LobotomyCorp\LobotomyCorp_Data\Managed\`
*   **Python 3.12+**
*   **[uv](https://github.com/astral-sh/uv)** (for Python dependency management)
*   **[DocFX](https://dotnet.github.io/docfx/)**
    *   Install via .NET CLI: `dotnet tool install -g docfx`

## Installation

1.  Clone the repository.
2.  Install Python dependencies using `uv`:

    ```bash
    uv sync
    ```

## Usage

> [!IMPORTANT]
> Before running any build commands, ensure you have copied the necessary game assemblies (DLLs) into the `assemblies/` directory (see [Prerequisites](#prerequisites)).

### One-Step Build (Recommended)

To run the full pipeline (generate metadata + convert to Markdown), execute the orchestration script:

```bash
uv run python main.py
```

This will:
1.  Run `docfx metadata` to generate YAML files in the `api/` directory from the DLLs in `assemblies/`.
2.  Run the conversion script to generate Markdown files in `wikijs_out/`.

### Manual Steps

You can also run the steps individually.

#### 1. Generate Metadata

Generate the DocFX metadata from the source assemblies:

```bash
docfx docfx.json
```

This populates the `api/` directory with `.yml` files.

#### 2. Convert to Wiki.js Markdown

Run the conversion script to transform the YAML metadata into Markdown:

```bash
uv run python src/docfx_yml_to_wikijs.py api wikijs_out --include-namespace-pages --include-member-details --home-page
```

*   `api`: Input directory containing DocFX YAML files.
*   `wikijs_out`: Output directory for generated Markdown.
*   `--include-namespace-pages`: Generates index pages for each namespace.
*   `--include-member-details`: Includes inline details for methods, properties, etc., on the class page.
*   `--home-page`: Generates a basic `home.md`.

## Project Structure

*   **`assemblies/`**: Input directory for game assemblies (DLLs).
*   **`api/`**: Intermediate output directory for DocFX YAML metadata.
*   **`wikijs_out/`**: Final output directory containing Wiki.js-compatible Markdown.
*   **`src/`**: Contains the conversion logic (`docfx_yml_to_wikijs.py`).
*   **`main.py`**: Orchestration script to run the full build process.
*   **`docfx.json`**: Configuration file for DocFX.

## Development

This project uses `ruff` for linting and formatting, `mypy` for static type checking, and `pytest` for unit testing. A convenience script `dev.py` is provided to run the full pipeline in sequence.

```bash
# Run Development Pipeline (Format -> Lint -> Type Check -> Test -> Main Build)
uv run python dev.py
```

To run only the checks and tests (useful for CI):

```bash
# Run CI Checks (Format -> Lint -> Type Check -> Test)
uv run python dev.py --ci
```

Or run tools individually:

```bash
# Run formatter
uv run ruff format .

# Run linter
uv run ruff check .

# Run type checker
uv run mypy .

# Run unit tests
uv run pytest
```
