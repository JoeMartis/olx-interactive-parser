# OLX Interactive Parser

An interactive Python tool for parsing edX OLX course structures and generating searchable HTML visualizations.

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.6+-blue.svg)
![Platform](https://img.shields.io/badge/platform-cross--platform-green.svg)

## 🎯 Features

- 📦 **Multiple Format Support**: Handles directories, `.zip`, `.tar.gz`, and `.tgz` files
- 🔍 **Interactive Search**: Real-time search through component names, types, and URLs
- 🌳 **Expandable Tree View**: Collapsible/expandable course structure visualization
- 📊 **Component Summary**: Visual statistics of course components
- 💻 **No Dependencies**: Uses only Python standard library
- 🌐 **Self-contained Output**: Generates portable HTML files that work offline

## 🚀 Quick Start

### Installation

Clone the repository:
\`\`\`bash
git clone https://github.com/JoeMartis/olx-interactive-parser.git
cd olx-interactive-parser
\`\`\`

### Basic Usage

\`\`\`bash
# Parse a course directory
python olx_parser.py /path/to/course

# Parse a compressed file
python olx_parser.py course_export.zip

# Parse with verbose output
python olx_parser.py -v course_backup.tar.gz

# Specify custom output filename
python olx_parser.py -o my_report.html ./course/
\`\`\`

## 📁 Supported Input Formats

| Format | Example | Description |
|--------|---------|-------------|
| Directory | \`./my_course/\` | Raw OLX course directory |
| ZIP File | \`course_export.zip\` | Compressed course export |
| TAR.GZ | \`course_backup.tar.gz\` | Gzipped tar archive |
| TGZ | \`course_data.tgz\` | Alternative gzip format |

## 🎛️ Command Line Options

\`\`\`
usage: olx_parser.py [-h] [-v] [-o OUTPUT] olx_path

Generate interactive OLX course structure with search

positional arguments:
  olx_path              Path to the OLX course directory, zip file, tar.gz file, or tgz file

optional arguments:
  -h, --help            show this help message and exit
  -v, --verbose         Enable verbose debug output
  -o OUTPUT, --output OUTPUT
                        Output HTML file name (default: <source_name>_structure.html)
\`\`\`

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (\`git checkout -b feature/amazing-feature\`)
3. Commit your changes (\`git commit -m 'Add some amazing feature'\`)
4. Push to the branch (\`git push origin feature/amazing-feature\`)
5. Open a Pull Request

---

**Made with ❤️ for the edX community**
