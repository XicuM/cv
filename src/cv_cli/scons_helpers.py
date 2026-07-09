import os
import subprocess
from pathlib import Path
import importlib.resources
from SCons.Script import Builder, Glob

def get_resource_path(package_subfolder, filename):
    """Finds a packaged resource (like templates or i18n files)."""
    if os.path.exists(filename):
        return os.path.abspath(filename)

    try:
        ref = importlib.resources.files(f"cv_cli.{package_subfolder}") / filename
        if ref.exists():
            return str(ref)
    except Exception as e:
        print(f"Error finding resource {filename} in packaged {package_subfolder}: {e}")

    return filename

def combine_yaml_files(content_file, i18n_file, output_file):
    """ Combine content YAML with i18n YAML """
    try:
        with open(output_file, 'w', encoding='utf-8') as outf:
            with open(content_file, 'r', encoding='utf-8') as inf:
                outf.write(inf.read())
            outf.write('\n')
            with open(i18n_file, 'r', encoding='utf-8') as inf:
                outf.write(inf.read())
        return True
    except Exception as e:
        print(f"Error combining YAML files: {e}")
        return False

def tex_from_yaml(target, source, env):
    """ Build LaTeX from YAML using pandoc """
    template = env.get('CV_TEMPLATE', 'template-cv.tex')
    template_path = get_resource_path('templates', template)

    try:
        subprocess.run(
            args=[
                'pandoc',
                f'--metadata-file={Path(str(source[0]))}',
                f'--template={Path(template_path)}',
                f'-o', str(Path(str(target[0])))
            ],
            input='', text=True, check=True, capture_output=True
        )
        return 0
    except subprocess.CalledProcessError as e:
        print(f"Pandoc failed: {e}")
        if e.stderr: print(f"Error output: {e.stderr}")
        if e.stdout: print(f"Output: {e.stdout}")
        return 1

def pdf_from_tex(target, source, env):
    """ Build PDF from LaTeX using pdflatex """
    build_path = Path(str(target[0])).parent.absolute()
    tex_file = Path(str(source[0]))
    tex_filename = tex_file.name

    try:
        print(f"Building PDF from {tex_filename} in {build_path}")

        result = subprocess.run(
            ['pdflatex', '-interaction=nonstopmode', tex_filename],
            cwd=str(build_path),
            text=True,
            capture_output=True
        )
        print(result.stdout)
        print(result.stderr)

        result = subprocess.run(
            args=['pdflatex', '-interaction=nonstopmode', tex_filename],
            cwd=str(build_path),
            text=True,
            capture_output=True
        )
        print(result.stdout)
        print(result.stderr)

        pdf_path = build_path / f"{tex_file.stem}.pdf"
        if pdf_path.exists():
            print(f"Successfully generated {pdf_path}")
            return 0
        else:
            print(f"PDF file was not created: {pdf_path}")
            return 1

    except subprocess.CalledProcessError as e:
        print(f"pdflatex failed: {e}")
        if e.stdout: print(f"stdout: {e.stdout}")
        if e.stderr: print(f"stderr: {e.stderr}")

        log_file = build_path / f"{tex_file.stem}.log"
        if log_file.exists():
            print(f"\nLast 20 lines of {log_file}:")
            with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
                for line in lines[-20:]:
                    print(line.rstrip())
        return 1

def setup_cv_env(env):
    """Appends CV compilation builders to the SCons environment."""
    env.Append(BUILDERS={
        'BuildTex': Builder(action=tex_from_yaml, suffix='.tex', src_suffix='.yaml'),
        'BuildPdf': Builder(action=pdf_from_tex, suffix='.pdf', src_suffix='.tex')
    })

def configure_cv_build(env, content_dir='content/cv', build_dir='build'):
    """Discover CV content files and register SCons build targets.

    Scans ``content_dir`` for ``*.yaml`` files, resolves per-language
    overrides against the i18n files shipped with cv-cli, and creates
    the full build graph (combine → tex → pdf) for every
    ``(base, language)`` pair found.

    Returns ``(all_pdf_targets, lang_codes)``.
    """
    setup_cv_env(env)

    # Discover available language codes from the i18n directory
    try:
        i18n_dir = os.path.dirname(get_resource_path('i18n', 'en.yaml'))
        lang_codes = [
            f.replace('.yaml', '')
            for f in os.listdir(i18n_dir)
            if f.endswith('.yaml')
        ]
    except Exception as e:
        print(f"Warning: Failed to load language codes, using fallbacks. {e}")
        lang_codes = ['en', 'es', 'ca']

    # Collect content YAML files and resolve per-language overrides
    content_files = Glob(f'{content_dir}/*.yaml')

    generic_files = {}
    overrides = {}
    bases = set()

    for yaml_file in content_files:
        stem = Path(str(yaml_file)).stem
        parts = stem.rsplit('-', 1)
        if len(parts) == 2 and parts[1] in lang_codes:
            overrides[(parts[0], parts[1])] = yaml_file
            bases.add(parts[0])
        else:
            generic_files[stem] = yaml_file
            bases.add(stem)

    # Build targets for each (base, language) pair
    all_pdfs = []
    template_path = get_resource_path('templates', 'template-cv.tex')

    for base in sorted(bases):
        base_targets = []

        for lang_code in lang_codes:
            content_yaml = overrides.get((base, lang_code), generic_files.get(base))
            if not content_yaml:
                continue

            lang_build_dir = f'{build_dir}/{base}/{lang_code}'
            combined_yaml = f'{lang_build_dir}/cv.yaml'
            i18n_file = get_resource_path('i18n', f'{lang_code}.yaml')

            def _combine_action(content, i18n):
                return lambda target, source, env: (
                    0 if combine_yaml_files(content, i18n, str(target[0])) else 1
                )

            combined_target = env.Command(
                combined_yaml,
                [content_yaml, i18n_file],
                _combine_action(str(content_yaml), i18n_file)
            )

            tex_target = env.BuildTex(f'{lang_build_dir}/cv.tex', combined_target)
            pdf_target = env.BuildPdf(f'{lang_build_dir}/cv.pdf', tex_target)

            env.Alias(f'{base}-{lang_code}', pdf_target)
            env.Depends(tex_target, template_path)
            env.Depends(combined_target, content_yaml)
            env.Depends(combined_target, i18n_file)
            env.Clean(pdf_target, [
                f'{lang_build_dir}/cv.aux',
                f'{lang_build_dir}/cv.log',
                f'{lang_build_dir}/cv.out',
                combined_yaml,
            ])

            all_pdfs.append(pdf_target)
            base_targets.append(pdf_target)

        env.Alias(base, base_targets)

    return all_pdfs, lang_codes
