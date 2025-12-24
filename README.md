# CV Generation System

A CV generation system that uses SCons, Pandoc, and LaTeX to convert YAML-based CV content into formatted PDF documents with multi-language support.

## Features

- **YAML-based Content**: Store CV content in easy-to-edit YAML files
- **Multi-language Support**: Generate CVs in multiple languages (English, Spanish, Catalan, etc.)
- **Pandoc Templating**: Use Pandoc to convert YAML metadata to LaTeX
- **Letter Generation**: Create cover letters based on templates
- **SCons Automation**: Efficient build system with dependency tracking

## Project Structure

```
cv/
├── SConstruct                   # SCons build configuration
├── README.md                    # This file
├── template-cv.tex              # LaTeX template for CVs
├── template-letter.tex          # LaTeX template for cover letters
├── assets/                      # Images and logos
│   ├── logos/
│   ├── template_photo.yaml
│   └── template_signature.yaml
├── build/                       # Generated files (created during build)
├── content/                     # Source content files
│   ├── cv/                      # CV content files (.yaml)
│   │   └── template.yaml
│   ├── letters/                 # Cover letter templates
│   │   └── template.yaml
│   └── personal_info/           # Personal information files
│       └── template.yaml
└── i18n/
    ├── en.yaml                  # English translations
    ├── es.yaml                  # Spanish translations
    └── ca.yaml                  # Catalan translations
```

## Requirements

### System Dependencies

- **Python 3.7+**: Required by SCons
- **SCons**: Build automation tool (`pip install scons`)
- **Pandoc**: Document converter (https://pandoc.org)
- **LaTeX/MiKTeX**: For PDF generation (https://miktex.org for Windows)

### Installation on Windows

1. **Install Python** (if not already installed):
   - Download from https://www.python.org
   - Ensure Python is added to PATH

2. **Install SCons**:
   ```powershell
   pip install scons
   ```

3. **Install Pandoc**:
   - Download from https://pandoc.org/installing.html
   - Add to PATH during installation

4. **Install MiKTeX**:
   - Download from https://miktex.org/download
   - Run installer with default options
   - Ensure `pdflatex` is added to PATH
   - Add MiKTeX bin directory to PATH: `C:\Users\<username>\AppData\Local\MikTeX\miktex\bin\x64`

### Installation on Linux/macOS

1. **Install Python and dependencies**:
   ```bash
   sudo apt-get install python3 python3-pip pandoc texlive-full
   ```

2. **Install SCons**:
   ```bash
   pip3 install scons
   ```

## Usage

### Basic Commands

Generate all CVs in all languages:
```powershell
scons
```

Generate a specific CV (e.g., template):
```powershell
scons template
```

Generate a specific CV in a specific language:
```powershell
scons template-es
```

Clean all generated build files:
```powershell
scons -c
```

### Creating a New CV

1. Create a new YAML file in `content/cv/` directory:
   ```bash
   cp content/cv/template.yaml content/cv/mycv.yaml
   ```

2. Edit `content/cv/mycv.yaml` with your information:
   - Replace placeholder values with your details
   - Maintain YAML structure and formatting
   - Add skills, experience, and education sections

3. Build your CV:
   ```powershell
   scons mycv
   ```

4. For a specific language variant:
   ```powershell
   scons mycv-en    # English
   scons mycv-es    # Spanish
   scons mycv-ca    # Catalan
   ```

### Creating a New Cover Letter

1. Create a new YAML file in `content/letters/` directory:
   ```bash
   cp content/letters/template.yaml content/letters/mycompany.yaml
   ```

2. Edit with your letter details:
   - Set company name, position, and language
   - Write the letter body
   - Reference the company logo if available

3. Build (requires personal_info file):
   ```powershell
   scons mycompany
   ```

## Customization

### Colors

Modify the color values in your CV YAML file:
- `primary`: Main accent color (used for headers and highlights)
- `secondary`: Secondary accent color (used for details and supporting text)

Colors should be 6-digit hex values without the `#` prefix (e.g., `"2E5090"`).

### LaTeX Template

Edit `template-cv.tex` to customize the visual appearance:
- Layout and spacing
- Font sizes and styles
- Section formatting
- Color application

The template uses Pandoc's templating syntax with `$variable$` placeholders for dynamic content injection.

### Fonts and Styling

Common LaTeX customizations in `template-cv.tex`:
- `\documentclass` options: Font size, paper size
- `\usepackage`: Control included packages and styles
- `\definecolor`: Add new color definitions
- Custom commands: Modify section styling, bullet points, etc.

## Available Languages

The system supports multiple languages through `i18n/` YAML files:
- **en.yaml**: English
- **es.yaml**: Spanish (Español)
- **ca.yaml**: Catalan (Català)

Add new languages by creating new YAML files in the `i18n/` directory and running the build.

## Build Output

Generated files are created in the `build/` directory:

```
build/
├── cv-template.tex         # Compiled LaTeX source (default language)
├── cv-template.pdf         # Generated PDF
├── cv-template-en.tex      # English variant
├── cv-template-en.pdf
├── cv-template-es.tex      # Spanish variant
├── cv-template-es.pdf
├── cv-*.aux                # LaTeX auxiliary files
├── cv-*.log                # LaTeX log files
└── cv-*.out                # LaTeX outline files
```
