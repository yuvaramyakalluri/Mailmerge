import os
from certificate_agent.main import main

if __name__ == "__main__":
    # 1. Run the certificate generation agent
    main()

    # 2. Ensure the output folder exists
    output_dir = "certificates"
    os.makedirs(output_dir, exist_ok=True)

    # 3. Generate index.html so GitHub Pages can display the files
    pdf_files = [f for f in os.listdir(output_dir) if f.endswith(".pdf")]

    html_content = """<!DOCTYPE html>
<html>
<head>
    <title>Generated Certificates</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; background-color: #f6f8fa; }
        h1 { color: #24292e; }
        ul { list-style-type: none; padding: 0; }
        li { margin: 12px 0; padding: 12px; background: white; border-radius: 6px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
        a { text-decoration: none; color: #0366d6; font-size: 18px; font-weight: bold; }
        a:hover { text-decoration: underline; }
    </style>
</head>
<body>
    <h1>Generated Certificates</h1>
    <ul>
"""
    for pdf in pdf_files:
        html_content += f'        <li>📄 <a href="{pdf}" target="_blank">{pdf}</a></li>\n'

    html_content += """    </ul>
</body>
</html>
"""

    with open(os.path.join(output_dir, "index.html"), "w", encoding="utf-8") as f:
        f.write(html_content)
