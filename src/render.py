import re
import argparse
from pathlib import Path
import markdown
from jinja2 import Environment, FileSystemLoader

def parse_markdown(md_text):
    html = re.sub(
        r'\[source:\s*(.+?)\]', 
        r'<div class="sync-marker" data-img="\1"></div>', 
        md_text
    )
    html = re.sub(
        r'\[ref:\s*(.+?)\]', 
        r'<div class="sync-marker ref-marker" data-ref="\1"></div>', 
        html
    )
    return markdown.markdown(html, extensions=['fenced_code', 'tables'])

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input_file", type=str, help="Markdown file to render")
    args = parser.parse_args()

    input_path = Path(args.input_file)
    with open(input_path, "r", encoding="utf-8") as f:
        md_text = f.read()

    html_content = parse_markdown(md_text)

    env = Environment(loader=FileSystemLoader('templates'))
    template = env.get_template('layout.html')
    
    final_html = template.render(html_content=html_content)
    
    output_path = Path("output") / f"{input_path.stem}.html"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(final_html)
        
    print(f"Rendered HTML saved to {output_path}")

if __name__ == "__main__":
    main()
