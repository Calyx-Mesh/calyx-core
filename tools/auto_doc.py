import os
import ast

def generate_docs():
    """
    Parses the codebase and generates a Markdown API Reference.
    Professional DX (Developer Experience) tool.
    """
    core_dir = os.path.dirname(os.path.dirname(__file__))
    docs_dir = os.path.join(os.path.dirname(core_dir), "Docs")
    output_file = os.path.join(docs_dir, "API_REFERENCE.md")
    
    print(f"--- 📚 GENERATING API REFERENCE ---")
    
    doc_content = "# INGRVM API Reference\n\nGenerated automatically from the source code.\n\n"
    
    for filename in os.listdir(core_dir):
        if filename.endswith(".py") and not filename.startswith("__"):
            path = os.path.join(core_dir, filename)
            with open(path, "r") as f:
                try:
                    tree = ast.parse(f.read())
                    doc_content += f"## `{filename}`\n"
                    
                    # Extract Classes
                    for node in tree.body:
                        if isinstance(node, ast.ClassDef):
                            doc_content += f"### Class: `{node.name}`\n"
                            doc_content += f"{ast.get_docstring(node) or 'No description.'}\n\n"
                            
                            # Extract Methods
                            for subnode in node.body:
                                if isinstance(subnode, ast.FunctionDef):
                                    doc_content += f"- **Method:** `{subnode.name}()`\n"
                        
                        elif isinstance(node, ast.FunctionDef):
                            doc_content += f"### Function: `{node.name}()`\n"
                            doc_content += f"{ast.get_docstring(node) or 'No description.'}\n\n"
                    
                    doc_content += "---\n\n"
                except Exception as e:
                    print(f"  [!] Failed to parse {filename}: {e}")

    with open(output_file, "w") as f:
        f.write(doc_content)
    
    print(f"SUCCESS: API Reference generated at {output_file}")

if __name__ == "__main__":
    generate_docs()

