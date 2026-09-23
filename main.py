import os
# ... your existing imports and script execution ...

if __name__ == "__main__":
    main()

    # Create certificates directory if not exists
    output_dir = "certificates"
    os.makedirs(output_dir, exist_ok=True)

    # Generate an index.html file to serve on GitHub Pages
    pdf_files = [f for f in os.listdir(output_dir) if f.endswith(".pdf")]
    
    html_content = """<!DOCTYPE html>
<html>
<head>
    <title>Generated Certificates</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        h1 { color: #333; }
        ul { list-style-type: none; padding: 0; }
        li { margin: 10px 0; }
        a { text-decoration: none; color: #0366d6; font-size: 18px; }
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
