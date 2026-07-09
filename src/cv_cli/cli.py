import click
import os
import shutil
import tempfile
import subprocess
from pathlib import Path
from cv_cli.scons_helpers import get_resource_path, combine_yaml_files

@click.command()
@click.argument('content', type=click.Path(exists=True))
@click.option('--output', '-o', default=None, type=click.Path(), help='Path to output PDF. Defaults to <content_filename>.pdf in CWD.')
@click.option('--template', '-t', default='template-cv.tex', help='LaTeX template filename or path.')
@click.option('--lang', '-l', default=None, help='Language code (e.g. en, es, ca). Inferred from filename if not specified.')
def main(content, output, template, lang):
    """Builds a PDF from YAML content and localization files."""
    content_path = Path(content).absolute()
    if output:
        output_path = Path(output).absolute()
    else:
        output_path = Path.cwd() / f"{content_path.stem}.pdf"
    
    # 1. Infer language if not specified
    if not lang:
        # Try to infer from filename e.g. template-en.yaml
        stem = content_path.stem
        parts = stem.rsplit('-', 1)
        if len(parts) == 2 and parts[1] in ['en', 'es', 'ca']:
            lang = parts[1]
        else:
            lang = 'en' # Default fallback
            
    # Locate i18n file in package
    i18n_file = get_resource_path('i18n', f'{lang}.yaml')
    if not os.path.exists(i18n_file):
        click.echo(f"Warning: translation file for '{lang}' not found, using default 'en'.", err=True)
        i18n_file = get_resource_path('i18n', 'en.yaml')
        
    template_path = get_resource_path('templates', template)
    if not os.path.exists(template_path):
        click.echo(f"Error: LaTeX template '{template}' not found.", err=True)
        return 1
        
    # 2. Setup temporary compilation environment mimicking SCons path structure
    # template-cv.tex references: ../../../assets/
    # template-letter.tex references: ../assets/
    # So we structure the temp directory to support both relative references:
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        
        # Copy assets directory if it exists locally
        # Look in the folder of the content file, or the current working directory
        assets_src = None
        for p in [content_path.parent / 'assets', Path('assets'), content_path.parent.parent / 'assets']:
            if p.exists() and p.is_dir():
                assets_src = p
                break
                
        if assets_src:
            # 1. For CV: ../../../assets/ (from build/cv/en/)
            shutil.copytree(assets_src, tmp_path / 'assets')
            # 2. For intermediate levels (e.g., ../../assets/)
            (tmp_path / 'build').mkdir(parents=True, exist_ok=True)
            shutil.copytree(assets_src, tmp_path / 'build' / 'assets')
            # 3. For Letter: ../assets/ (from build/cv/en/)
            (tmp_path / 'build' / 'cv').mkdir(parents=True, exist_ok=True)
            shutil.copytree(assets_src, tmp_path / 'build' / 'cv' / 'assets')
            
        build_dir = tmp_path / 'build' / 'cv' / lang
        build_dir.mkdir(parents=True, exist_ok=True)
        
        combined_yaml = build_dir / 'cv.yaml'
        tex_file = build_dir / 'cv.tex'
        pdf_file = build_dir / 'cv.pdf'
        
        # Combine content and i18n
        if not combine_yaml_files(str(content_path), i18n_file, str(combined_yaml)):
            click.echo("Error combining YAML files.", err=True)
            return 1
            
        # Run pandoc
        click.echo("Running pandoc...")
        try:
            subprocess.run(
                args=[
                    'pandoc',
                    f'--metadata-file={combined_yaml.name}',
                    f'--template={template_path}',
                    f'-o', tex_file.name
                ],
                cwd=str(build_dir),
                input='',
                check=True,
                capture_output=True,
                text=True
            )
        except subprocess.CalledProcessError as e:
            click.echo(f"Pandoc failed: {e.stderr}", err=True)
            return 1
            
        # Run pdflatex (Pass 1)
        click.echo("Running pdflatex (Pass 1)...")
        try:
            subprocess.run(
                ['pdflatex', '-interaction=nonstopmode', tex_file.name],
                cwd=str(build_dir),
                check=False,
                capture_output=True,
                text=True
            )
        except Exception as e:
            click.echo(f"pdflatex error: {e}", err=True)
            
        # Run pdflatex (Pass 2 for cross-references)
        click.echo("Running pdflatex (Pass 2)...")
        try:
            subprocess.run(
                ['pdflatex', '-interaction=nonstopmode', tex_file.name],
                cwd=str(build_dir),
                check=False,
                capture_output=True,
                text=True
            )
        except Exception as e:
            pass
            
        if pdf_file.exists():
            # Copy PDF to target output
            output_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(pdf_file, output_path)
            click.echo(f"Successfully generated {output_path}")
            return 0
        else:
            click.echo("Error: PDF was not generated. Check pdflatex log.", err=True)
            log_file = build_dir / 'cv.log'
            if log_file.exists():
                with open(log_file, 'r', encoding='utf-8', errors='ignore') as lf:
                    lines = lf.readlines()
                    click.echo("\n".join(lines[-20:]))
            return 1
