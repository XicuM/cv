import os
import subprocess
from pathlib import Path

def combine_yaml_files(content_file, i18n_file, output_file):
    ''' Combine content YAML with i18n YAML '''
    try:
        with open(output_file, 'w', encoding='utf-8') as outf:
            # First, write the content file
            with open(content_file, 'r', encoding='utf-8') as inf:
                outf.write(inf.read())
            outf.write('\n') # Ensure newline between files
            # Then, append the i18n file
            with open(i18n_file, 'r', encoding='utf-8') as inf:
                outf.write(inf.read())
        return True
    except Exception as e:
        print(f"Error combining YAML files: {e}")
        return False

def tex_from_yaml(target, source, env):
    """ Build LaTeX from YAML using pandoc """
    try:
        subprocess.run(
            args=[
                'pandoc',
                f'--metadata-file={Path(str(source[0]))}',
                f'--template={Path('template-cv.tex')}',
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
    ''' Build PDF from LaTeX using pdflatex '''

    build_path = Path(str(target[0])).parent.absolute()
    tex_file = Path(str(source[0]))
    tex_filename = tex_file.name
    
    try:
        print(f"Building PDF from {tex_filename} in {build_path}")
        
        # First pass
        result = subprocess.run(
            ['pdflatex', '-interaction=nonstopmode', tex_filename],
            cwd=str(build_path),
            text=True,
            capture_output=True
        )
        print(result.stdout)
        print(result.stderr)

        # Second pass for cross-references
        result = subprocess.run(
            args=['pdflatex', '-interaction=nonstopmode', tex_filename],
            cwd=str(build_path),
            text=True,
            capture_output=True
        )
        print(result.stdout)
        print(result.stderr)
        
        # Check if PDF was actually created
        pdf_path = build_path/f"{tex_file.stem}.pdf"
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

def clean_build_files(target, source, env):
    """Clean all generated build files including auxiliary files"""
    build_dir = Path('build')
    if build_dir.exists():
        print(f"Cleaning build directory: {build_dir}")
        import shutil
        shutil.rmtree(build_dir)
        print("Build directory cleaned")
    else:
        print("Build directory doesn't exist, nothing to clean")
    return 0

# Define builders
env = Environment(ENV=os.environ)
env.Append(BUILDERS={
    'BuildTex': Builder(action=tex_from_yaml, suffix='.tex', src_suffix='.yaml'),
    'BuildPdf': Builder(action=pdf_from_tex, suffix='.pdf', src_suffix='.tex'),
    'CleanBuild': Builder(action=clean_build_files)
})

# Save all PDF targets
all_pdfs = []

# Get available language codes
i18n_files = Glob('i18n/*.yaml')
language_codes = [os.path.splitext(os.path.basename(str(f)))[0] for f in i18n_files]

# For each YAML file in 'content' directory
for yaml_file in Glob('content/cv/*.yaml'):

    # Get base name without extension
    base_name = os.path.splitext(os.path.basename(str(yaml_file)))[0]

    # Build default version (no language suffix) - original behavior
    tex_target = env.BuildTex(f'build/cv-{base_name}.tex', yaml_file)
    pdf_target = env.BuildPdf(f'build/cv-{base_name}.pdf', tex_target)
    
    # Create an alias for easy building
    env.Alias(base_name, pdf_target)
    all_pdfs.append(pdf_target)

    # Define dependencies
    env.Depends(tex_target, 'template-cv.tex')
    env.Depends(tex_target, yaml_file)
    
    # Add auxiliary files to clean list for scons -c
    aux_files = [
        f'build/cv-{base_name}.aux',
        f'build/cv-{base_name}.log', 
        f'build/cv-{base_name}.out'
    ]
    env.Clean(pdf_target, aux_files)

    # Build language variants
    for lang_code in language_codes:
        # Create combined YAML file in build directory
        combined_yaml = f'build/cv-{base_name}-{lang_code}.yaml'
        i18n_file = f'i18n/{lang_code}.yaml'
        
        # Create a custom command to combine YAML files
        def create_combine_action(content_file, i18n_file, output_file):
            def combine_action(target, source, env):
                return 0 if combine_yaml_files(content_file, i18n_file, str(target[0])) else 1
            return combine_action
        
        # Build the combined YAML file
        combined_target = env.Command(
            combined_yaml, 
            [yaml_file, i18n_file],
            create_combine_action(str(yaml_file), i18n_file, combined_yaml)
        )
        
        # Build LaTeX and PDF from combined YAML
        tex_target_lang = env.BuildTex(f'build/cv-{base_name}-{lang_code}.tex', combined_target)
        pdf_target_lang = env.BuildPdf(f'build/cv-{base_name}-{lang_code}.pdf', tex_target_lang)
        
        # Create alias for language variant
        env.Alias(f'{base_name}-{lang_code}', pdf_target_lang)
        all_pdfs.append(pdf_target_lang)
        
        # Define dependencies
        env.Depends(tex_target_lang, 'template-cv.tex')
        env.Depends(combined_target, yaml_file)
        env.Depends(combined_target, i18n_file)
        
        # Add auxiliary files to clean list
        aux_files_lang = [
            f'build/cv-{base_name}-{lang_code}.aux',
            f'build/cv-{base_name}-{lang_code}.log',
            f'build/cv-{base_name}-{lang_code}.out',
            combined_yaml
        ]
        env.Clean(pdf_target_lang, aux_files_lang)

# Also add the build directory itself to be cleaned by scons -c
env.Clean('.', 'build/')

# Default target builds all CVs
env.Default(all_pdfs)

# Help text
Help(f"""
CV Build System with Language Support using SCons

Targets:
  scons                   - Build all CVs (all content files, all languages)
  scons *                 - Build CV from content/cv/*.yaml (default language)
  scons *-<lang>          - Build CV with specific language (e.g., automotive-es)
  scons -c                - Remove all generated build files (SCons clean)

Available languages: {', '.join(language_codes) if language_codes else 'none'}

Input files:
  content/cv/*.yaml       - CV content files
  i18n/*.yaml             - Language/localization files  
  template-cv.tex         - LaTeX template for CVs

Output:
  build/cv-*.pdf          - Generated PDFs
  build/cv-*.tex          - Generated LaTeX files
  build/cv-*.yaml         - Combined YAML files (for language variants)
  build/cv-*.aux          - Auxiliary LaTeX files
  build/cv-*.log          - LaTeX log files
  build/cv-*.out          - LaTeX outline files
""")
