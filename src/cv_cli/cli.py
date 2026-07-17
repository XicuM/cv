import shutil
import struct
import zlib
from pathlib import Path

import click
import yaml

from cv_cli.builder import (
    _read_meta,
    _infer_from_filename,
    _resource,
    build_document,
    discover_persons,
)


_FONT5X7: dict[str, tuple[int, ...]] = {
    ' ': (0b00000, 0b00000, 0b00000, 0b00000, 0b00000, 0b00000, 0b00000),
    'P': (0b11110, 0b10001, 0b10001, 0b11110, 0b10000, 0b10000, 0b10000),
    'S': (0b01110, 0b10001, 0b10000, 0b01110, 0b00001, 0b10001, 0b01110),
    'a': (0b00000, 0b00000, 0b01110, 0b00001, 0b01111, 0b10001, 0b01111),
    'c': (0b00000, 0b00000, 0b01110, 0b10001, 0b10000, 0b10001, 0b01110),
    'd': (0b00001, 0b00001, 0b01111, 0b10001, 0b10001, 0b10001, 0b01111),
    'e': (0b00000, 0b00000, 0b01110, 0b10001, 0b11111, 0b10000, 0b01110),
    'g': (0b00000, 0b00000, 0b01111, 0b10001, 0b10001, 0b01111, 0b00001),
    'h': (0b10000, 0b10000, 0b11110, 0b10001, 0b10001, 0b10001, 0b10001),
    'i': (0b00100, 0b00000, 0b00100, 0b00100, 0b00100, 0b00100, 0b00100),
    'l': (0b10000, 0b10000, 0b10000, 0b10000, 0b10000, 0b10000, 0b10000),
    'n': (0b00000, 0b00000, 0b10110, 0b11001, 0b10001, 0b10001, 0b10001),
    'o': (0b00000, 0b00000, 0b01110, 0b10001, 0b10001, 0b10001, 0b01110),
    'p': (0b00000, 0b00000, 0b11110, 0b10001, 0b10001, 0b11110, 0b10000),
    'r': (0b00000, 0b00000, 0b10110, 0b11001, 0b10000, 0b10000, 0b10000),
    's': (0b00000, 0b00000, 0b01110, 0b10000, 0b01110, 0b00001, 0b11110),
    't': (0b00000, 0b01000, 0b11110, 0b01000, 0b01000, 0b01000, 0b00110),
    'u': (0b00000, 0b00000, 0b10001, 0b10001, 0b10001, 0b10001, 0b01111),
}


def _placeholder_png(path: Path, w: int, h: int, r: int, g: int, b: int, text: str = '') -> None:
    '''Write a placeholder PNG with optional centered text (no external deps).'''
    def _chunk(tag: bytes, data: bytes) -> bytes:
        payload = tag + data
        return struct.pack('>I', len(data)) + payload + struct.pack('>I', zlib.crc32(payload) & 0xFFFFFFFF)

    bg = bytes([r, g, b])
    fg = bytes([max(r - 60, 20), max(g - 60, 20), max(b - 60, 20)])
    rows: list[bytearray] = [bytearray(b'\x00') + bg * w for _ in range(h)]

    if text:
        CW, CH, SP = 5, 7, 1
        chars = [ch for ch in text if ch in _FONT5X7]
        if chars:
            tw = sum((CW + SP) for _ in chars) - SP
            ox = max((w - tw) // 2, 0)
            oy = max((h - CH) // 2, 0)
            x = ox
            for ch in chars:
                glyph = _FONT5X7[ch]
                for row_i in range(CH):
                    bits = glyph[row_i]
                    for col_i in range(CW):
                        if bits & (0b10000 >> col_i):
                            px, py = x + col_i, oy + row_i
                            if 0 <= px < w and 0 <= py < h:
                                offset = py * (1 + w * 3) + 1 + px * 3
                                rows[py][offset:offset+3] = fg
                x += CW + SP

    raw = b''.join(bytes(row) for row in rows)
    with open(path, 'wb') as f:
        f.write(b'\x89PNG\r\n\x1a\n'
                + _chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0))
                + _chunk(b'IDAT', zlib.compress(raw))
                + _chunk(b'IEND', b''))


def _resolve_single_file(target: Path, doc_type: str | None, lang: str | None):
    '''Build a single .yaml file, auto-detecting person dir and metadata.'''
    content = target.resolve()
    person_dir = content.parent
    while person_dir != person_dir.parent:
        if any(person_dir.glob('*.yaml')) or (person_dir / 'letters').is_dir():
            break
        person_dir = person_dir.parent
    dt = doc_type or _read_meta(content)[0] or _infer_from_filename(content)[0] or 'cv'
    lg = lang or _read_meta(content)[1] or _infer_from_filename(content)[1] or 'en'
    rel = content.relative_to(person_dir)
    out = Path.cwd() / 'output' / rel.with_suffix('.pdf')
    click.echo(f'Building {content.name} ({dt}/{lg})')
    if not build_document(content, person_dir, out, lg):
        raise SystemExit(1)


@click.group(help='''
Multi-language CV and cover letter builder.

\b
Quick start:
  cv init              scaffold templates in current directory
  cv cv -l en          create a new English CV
  cv letter acme -l es create a new Spanish cover letter for "acme"
  cv build             build all documents
  cv build -t cv -l en build only English CVs
  cv clean             remove output/
''')
def cli():
    pass


@cli.command(short_help='Initialize a new project with default templates.')
def init():
    '''Scaffold templates and placeholder images in the current directory.'''
    cwd = Path.cwd()
    if (cwd / 'cv-en.yaml').exists():
        click.echo('cv-en.yaml already exists.', err=True)
        raise SystemExit(1)

    letters_dir = cwd / 'letters'
    letters_dir.mkdir(exist_ok=True)
    for name, dest in [('cv-en.yaml', cwd / 'cv-en.yaml'), ('letter-en.yaml', letters_dir / 'template-en.yaml')]:
        shutil.copy2(_resource('resources/templates', name), dest)
    _placeholder_png(cwd / 'photo.png', 200, 200, 204, 204, 204, 'Placeholder Photo')
    _placeholder_png(cwd / 'signature.png', 300, 80, 204, 204, 204, 'Placeholder Signature')
    click.echo(f'Initialised {cwd}/')
    click.echo('  cv-en.yaml\n  letters/template-en.yaml')
    click.echo('  photo.png          (placeholder — replace)')
    click.echo('  signature.png      (placeholder — replace)')
    click.echo('\nEdit the YAML files, replace the images, then run cv build.')


@cli.command(name='cv', short_help='Create a new CV YAML file.')
@click.option('--lang', '-l', default='en', help='Language code (en, es, ca)')
def create_cv(lang):
    '''Create a new CV YAML file in the current directory.'''
    dest = Path.cwd() / f'cv-{lang}.yaml'
    if dest.exists():
        click.echo(f'{dest.name} already exists.', err=True)
        raise SystemExit(1)
    data = yaml.safe_load(_resource('resources/templates', 'cv-en.yaml').read_text())
    data['language'] = lang
    dest.write_text(yaml.dump(data, default_flow_style=False, allow_unicode=True, sort_keys=False))
    click.echo(f'Created {dest.name}')


@cli.command(short_help='Create a new cover letter YAML file.')
@click.argument('company')
@click.option('--lang', '-l', default='en', help='Language code (en, es, ca)')
def letter(company, lang):
    '''Create a new cover letter for COMPANY in the specified language.'''
    letters_dir = Path.cwd() / 'letters'
    letters_dir.mkdir(exist_ok=True)
    dest = letters_dir / f'{company}-{lang}.yaml'
    if dest.exists():
        click.echo(f'{dest.name} already exists.', err=True)
        raise SystemExit(1)
    data = yaml.safe_load(_resource('resources/templates', 'letter-en.yaml').read_text())
    data['language'] = lang
    data['company'] = company
    dest.write_text(yaml.dump(data, default_flow_style=False, allow_unicode=True, sort_keys=False))
    click.echo(f'Created letters/{dest.name}')


@cli.command(short_help='Open a LaTeX template in the default editor.')
@click.argument('template_name', type=click.Choice(['cv', 'letter']))
def template(template_name):
    '''Open a packaged LaTeX template in the default editor ($EDITOR).'''
    filename = f'template-{template_name}.tex'
    click.edit(filename=str(_resource('templates', filename)))


@cli.command(short_help='Build documents from YAML files.')
@click.argument('target', required=False)
@click.option('--type', '-t', 'doc_type', help='Document type: cv, letter')
@click.option('--lang', '-l', help='Language code: en, es, ca')
def build(target: str | None, doc_type: str | None, lang: str | None):
    '''Build documents from YAML content files.

    Run from a project root (multiple person dirs) or inside a
    single person directory.  Pass a .yaml file to build just that file.
    '''
    if target and (p := Path(target)).suffix == '.yaml' and p.is_file():
        _resolve_single_file(p, doc_type, lang)
        return

    persons = discover_persons()
    if not persons:
        click.echo('No person directories found.  Run cv init in an empty directory.', err=True)
        raise SystemExit(1)

    if target:
        if target not in persons:
            click.echo(f"Person '{target}' not found.  Available: {', '.join(persons)}", err=True)
            raise SystemExit(1)
        persons = {target: persons[target]}

    cwd = Path.cwd().resolve()
    jobs: list[tuple[str, dict, Path, Path]] = []
    for name, data in persons.items():
        for doc in data['docs']:
            if doc_type and doc['type'] != doc_type:
                continue
            if lang and doc['lang'] != lang:
                continue
            rel = doc['path'].relative_to(data['dir'])
            prefix = name if data['dir'].resolve() != cwd else ''
            out = cwd / 'output' / prefix / rel.with_suffix('.pdf')
            jobs.append((name, doc, out, data['dir']))

    if not jobs:
        click.echo('No documents match the filters.')
        return

    succeeded = 0
    failed = 0
    for person_name, doc, out, person_dir in jobs:
        click.echo(f"[{person_name}] {doc['path'].name} ({doc['type']}/{doc['lang']})")
        if build_document(doc['path'], person_dir, out, doc['lang']):
            succeeded += 1
        else:
            failed += 1

    click.echo(f'\nDone: {succeeded} succeeded, {failed} failed')
    if failed:
        raise SystemExit(1)


@cli.command(short_help='Remove output/ from the current directory.')
def clean():
    '''Remove output/ from the current directory.'''
    out = Path.cwd() / 'output'
    if out.exists():
        shutil.rmtree(out)
        click.echo(f'Removed {out}')
    else:
        click.echo('Nothing to clean.')


def main(): cli()
