import shutil
import subprocess
import tempfile
from pathlib import Path
import importlib.resources

import yaml


def _resource(category: str, filename: str) -> Path:
    '''Look up a packaged resource shipped with cv-cli.'''
    path = Path(filename)
    if path.is_file():
        return path.resolve()
    ref = importlib.resources.files(f'cv_cli.{category.replace('/', '.')}') / filename
    if not ref.is_file():
        raise FileNotFoundError(f'Packaged resource not found: {category}/{filename}')
    return Path(ref)


def combine_yaml_files(content: Path, i18n: Path, output: Path) -> bool:
    '''Concatenate content + i18n YAML into a single Pandoc metadata file.'''
    try:
        output.write_text(content.read_text() + '\n' + i18n.read_text())
        return True
    except OSError as e:
        print(f'Error combining YAML files: {e}')
        return False


TEMPLATE_MAP: dict[str, str] = {
    'cv': 'template-cv.tex',
    'letter': 'template-letter.tex',
    'personal-info': 'template-personal-info.tex',
}


def _read_meta(path: Path) -> tuple[str | None, str | None]:
    data = yaml.safe_load(path.read_text()) or {}
    return data.get('type'), data.get('language')


def _infer_from_filename(path: Path) -> tuple[str | None, str | None]:
    parts = path.stem.rsplit('-', 1)
    return (parts[0], parts[1]) if len(parts) == 2 else (None, None)


def _discover_docs(person_dir: Path) -> list[dict]:
    '''Find all buildable YAML documents in a person directory.'''
    docs: list[dict] = []
    for yf in sorted(person_dir.glob('*.yaml')):
        dt, lg = _read_meta(yf)
        dt = dt or _infer_from_filename(yf)[0] or 'cv'
        lg = lg or 'en'
        docs.append({'path': yf, 'type': dt, 'lang': lg})

    letters_dir = person_dir / 'letters'
    if letters_dir.is_dir():
        for yf in sorted(letters_dir.glob('*.yaml')):
            dt, lg = _read_meta(yf)
            docs.append({
                'path': yf,
                'type': dt or 'letter',
                'lang': lg or 'en',
            })

    return docs


def discover_persons(base_dir: Path | None = None) -> dict[str, dict]:
    '''Scan for person directories (flat or nested) containing YAML docs.'''
    root = base_dir or Path.cwd()
    docs = _discover_docs(root)
    if docs:
        return {root.name: {'dir': root, 'docs': docs}}
    return {
        d.name: {'dir': d, 'docs': d_docs}
        for d in sorted(root.iterdir())
        if d.is_dir()
        and not d.name.startswith('.')
        and d.name != 'output'
        and (d_docs := _discover_docs(d))
    }


def build_document(
    content: Path,
    person_dir: Path,
    output_path: Path,
    lang: str,
    progress: bool = True,
) -> bool:
    '''Compile a single YAML document to PDF via Pandoc + pdflatex.'''
    dt = _read_meta(content)[0] or _infer_from_filename(content)[0] or 'cv'
    template_name = TEMPLATE_MAP.get(dt, 'template-cv.tex')
    i18n = _resource('i18n', f'{lang}.yaml')
    if not (tex_template := _resource('templates', template_name)):
        return False

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        assets = tmp / 'assets'
        assets.mkdir()
        for f in person_dir.iterdir():
            if f.suffix.lower() in ('.png', '.jpg', '.jpeg', '.pdf'):
                shutil.copy2(f, assets / f.name)
        shared = Path('assets')
        if shared.is_dir():
            shutil.copytree(shared, assets, dirs_exist_ok=True)

        combined = tmp / 'combined.yaml'
        tex_file = tmp / 'output.tex'
        pdf_file = tmp / 'output.pdf'
        if not combine_yaml_files(content, i18n, combined):
            return False
        if progress:
            print(f'  pandoc {content.name} ...', flush=True)
        try:
            subprocess.run(
                [
                    'pandoc',
                    f'--metadata-file={combined.name}',
                    f'--template={tex_template}',
                    '-o', tex_file.name,
                ],
                cwd=str(tmp), input='', check=True,
                capture_output=True, text=True,
            )
        except subprocess.CalledProcessError as e:
            print(f'  pandoc failed: {e.stderr}', flush=True)
            return False

        for pass_num in (1, 2):
            if progress:
                print(f'  pdflatex (pass {pass_num}) ...', flush=True)
            subprocess.run(
                ['pdflatex', '-interaction=nonstopmode', tex_file.name],
                cwd=str(tmp), check=False,
                capture_output=True, text=True,
            )

        if pdf_file.is_file():
            output_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(pdf_file, output_path)
            if progress:
                print(f'  -> {output_path}', flush=True)
            return True

        print(f'  Error: PDF not generated for {content.name}', flush=True)
        log_file = tmp / 'output.log'
        if log_file.is_file():
            for line in log_file.read_text().splitlines()[-20:]:
                print(f'    {line}', flush=True)
        return False
