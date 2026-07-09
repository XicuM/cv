# CV Compiler CLI (`cv-cli`)

`cv-cli` is a Python command-line compiler and SCons build system wrapper designed to build LaTeX CVs and letters from YAML files using Pandoc and pdflatex.

By separating the compilation tool from your resume data, you can maintain your private resume files in a separate repository (`cv-private`) while keeping the build engine open-source and reusable.

---

## Key Features

- **Direct CLI Compiler**: Build your CV in a single command. All intermediate compiler files are isolated and automatically cleaned.
- **SCons Integration**: Exposes custom builders (`BuildTex` and `BuildPdf`) to automatically track dependencies and handle translations.
- **Packaged Templates & i18n**: Ships standard templates and translation files (`en`, `es`, `ca`) natively.

---

## Installation

### Prerequisites

Ensure you have the system dependencies installed:
- **Pandoc**
- **LaTeX** (e.g., TeX Live)
- **Python 3.7+**

### Local Package Installation

Clone this repository and install it in editable mode:
```bash
pip install --user --break-system-packages -e .
```

---

## Usage

### 1. CLI Usage (Direct Build)

To build a PDF directly from your YAML content file:
```bash
cv-cli content.yaml --output build/resume.pdf
```

#### Options:
- `-o, --output PATH`: Output path for the generated PDF. If not specified, defaults to `<content_filename>.pdf` in the current working directory.
- `-t, --template TEXT`: Specify a custom LaTeX template file or path (defaults to `template-cv.tex` or `template-letter.tex`).
- `-l, --lang TEXT`: Language code (e.g. `en`, `es`, `ca`). If omitted, it is automatically inferred from the input filename (e.g. `template-en.yaml` -> `en`).

*Note: CLI builds perform all compilation steps inside a standard system temporary directory, ensuring your workspace remains completely clean.*

---

## SCons Integration

If you prefer a build automation system that resolves multi-language configurations and tracks dependencies, you can use `cv-cli` directly in your SCons `SConstruct` configuration:

```python
import os
import cv_cli
from cv_cli.scons_helpers import setup_cv_env

# Set up SCons environment using builders provided by the cv-cli package
env = Environment(ENV=os.environ)
setup_cv_env(env)

# Use packaged translations
i18n_file = cv_cli.get_resource_path('i18n', 'en.yaml')

# Define targets
combined_target = env.Command(
    'build/cv.yaml', 
    ['content.yaml', i18n_file],
    lambda target, source, env: 0 if cv_cli.combine_yaml_files(str(source[0]), str(source[1]), str(target[0])) else 1
)

tex_target = env.BuildTex('build/cv.tex', combined_target)
pdf_target = env.BuildPdf('build/cv.pdf', tex_target)
```
