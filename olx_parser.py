#!/usr/bin/env python3
"""
Interactive OLX Directory Parser with Search
Parses edX OLX course structure and generates an interactive HTML tree view with search functionality
Supports .zip, .tar.gz, and .tgz files
"""

import os
import json
import xml.etree.ElementTree as ET
import zipfile
import tarfile
import tempfile
import shutil
from pathlib import Path
from typing import Dict, List, Tuple, Optional

class InteractiveOLXParser:
    def __init__(self, olx_path: str, verbose: bool = False):
        self.original_path = Path(olx_path)
        self.temp_dir = None  # Will hold temporary directory if we extract a compressed file
        self.verbose = verbose  # Control debug output
        
        # Handle compressed files vs directories
        if self.original_path.is_file():
            if self.original_path.suffix.lower() == '.zip':
                if self.verbose:
                    print(f"📦 Extracting zip file: {self.original_path}")
                self.olx_dir = self._extract_zip(self.original_path)
            elif self.original_path.suffix.lower() in ['.gz', '.tgz'] or '.tar.gz' in str(self.original_path).lower():
                if self.verbose:
                    print(f"📦 Extracting tar.gz/tgz file: {self.original_path}")
                self.olx_dir = self._extract_tar(self.original_path)
            else:
                raise ValueError(f"Unsupported file type. Path must be a directory, .zip, .tar.gz, or .tgz file: {olx_path}")
        elif self.original_path.is_dir():
            self.olx_dir = self.original_path
        else:
            raise ValueError(f"Path must be a directory, .zip, .tar.gz, or .tgz file: {olx_path}")
            
        self.components = {}  # Cache for parsed components
    
    def _extract_zip(self, zip_path: Path) -> Path:
        """Extract zip file to temporary directory and return the OLX root directory"""
        # Create temporary directory
        self.temp_dir = Path(tempfile.mkdtemp(prefix="olx_parser_"))
        
        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(self.temp_dir)
            
            if self.verbose:
                print(f"   📁 Extracted to: {self.temp_dir}")
            
            return self._find_olx_root(self.temp_dir)
            
        except zipfile.BadZipFile:
            raise ValueError(f"Invalid zip file: {zip_path}")
    
    def _extract_tar(self, tar_path: Path) -> Path:
        """Extract tar.gz/tgz file to temporary directory and return the OLX root directory"""
        # Create temporary directory
        self.temp_dir = Path(tempfile.mkdtemp(prefix="olx_parser_"))
        
        try:
            with tarfile.open(tar_path, 'r:gz') as tar_ref:
                # Extract all files
                tar_ref.extractall(self.temp_dir)
            
            if self.verbose:
                print(f"   📁 Extracted to: {self.temp_dir}")
            
            return self._find_olx_root(self.temp_dir)
            
        except (tarfile.TarError, tarfile.ReadError) as e:
            raise ValueError(f"Invalid tar.gz file: {tar_path}. Error: {e}")
    
    def _find_olx_root(self, extraction_dir: Path) -> Path:
        """Find the OLX root directory within the extracted content"""
        # Find the OLX root directory within the extracted content
        # Sometimes the archive contains a single folder, sometimes it's at the root
        extracted_items = list(extraction_dir.iterdir())
        
        # If there's only one directory, check if it looks like an OLX structure
        if len(extracted_items) == 1 and extracted_items[0].is_dir():
            potential_olx_dir = extracted_items[0]
            if (potential_olx_dir / "course.xml").exists():
                if self.verbose:
                    print(f"   🎯 Found OLX structure in: {potential_olx_dir.name}")
                return potential_olx_dir
        
        # Otherwise, check if the extraction directory itself has the OLX structure
        if (extraction_dir / "course.xml").exists():
            if self.verbose:
                print(f"   🎯 Found OLX structure at extraction root")
            return extraction_dir
        
        # If we can't find a clear OLX structure, list what we found
        if self.verbose:
            print(f"   ⚠️  Contents of extracted archive:")
            for item in extracted_items:
                print(f"      - {item.name} ({'dir' if item.is_dir() else 'file'})")
        
        # Try to find any directory with a 'course.xml' file (not just 'course' subdirectory)
        for item in extraction_dir.rglob("course.xml"):
            if item.is_file():
                olx_root = item.parent
                if self.verbose:
                    print(f"   🎯 Found course.xml in: {olx_root}")
                return olx_root
        
        raise ValueError("Could not find OLX course structure in the extracted archive")
    
    def cleanup(self):
        """Clean up temporary directory if it was created"""
        if self.temp_dir and self.temp_dir.exists():
            if self.verbose:
                print(f"🧹 Cleaning up temporary directory: {self.temp_dir}")
            shutil.rmtree(self.temp_dir)
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with cleanup"""
        self.cleanup()
        
    def parse_xml_file(self, file_path: Path) -> Optional[ET.Element]:
        """Parse an XML file and return the root element"""
        try:
            tree = ET.parse(file_path)
            return tree.getroot()
        except (ET.ParseError, FileNotFoundError) as e:
            if self.verbose:
                print(f"Error parsing {file_path}: {e}")
            return None
    
    def get_component_info(self, component_type: str, url_name: str) -> Tuple[str, str, List[str]]:
        """Get component information including display name and children"""
        file_path = self.olx_dir / component_type / f"{url_name}.xml"
        
        if not file_path.exists():
            if self.verbose:
                print(f"File not found: {file_path}")
            return f"Missing {component_type}", url_name, []
        
        root = self.parse_xml_file(file_path)
        if root is None:
            return f"Invalid {component_type}", url_name, []
        
        # Get display name
        display_name = root.get('display_name', url_name)
        
        # Get children references - handle different attribute names
        children = []
        for child in root:
            url_name_attr = child.get('url_name') or child.get('url_name_ref')
            if url_name_attr:
                children.append((child.tag, url_name_attr))
        
        return display_name, url_name, children
    
    def find_course_file(self) -> Tuple[Path, str]:
        """Find the root course.xml file and get the course url_name"""
        # Look for course.xml in the root OLX directory
        course_xml = self.olx_dir / "course.xml"
        
        if not course_xml.exists():
            raise FileNotFoundError(f"Root course.xml not found: {course_xml}")
        
        # Parse course.xml to get the url_name that points to the actual course file
        root = self.parse_xml_file(course_xml)
        if root is None:
            raise ValueError(f"Could not parse {course_xml}")
        
        course_url_name = root.get('url_name')
        if not course_url_name:
            raise ValueError(f"No url_name found in {course_xml}")
        
        # The actual course file should be in /course/{url_name}.xml
        actual_course_file = self.olx_dir / "course" / f"{course_url_name}.xml"
        
        if not actual_course_file.exists():
            raise FileNotFoundError(f"Course file not found: {actual_course_file}")
        
        return actual_course_file, course_url_name

    def parse_course_structure(self) -> Dict:
        """Parse the entire course structure starting from the root course.xml file"""
        # Find the course file automatically
        course_file, course_url_name = self.find_course_file()
        
        if self.verbose:
            print(f"📚 Starting from root course.xml")
            print(f"📚 Course url_name: {course_url_name}")
            print(f"📚 Actual course file: {course_file.name}")
        
        # Parse the actual course file
        course_root = self.parse_xml_file(course_file)
        if course_root is None:
            raise ValueError(f"Could not parse {course_file}")
        
        course_name = course_root.get('display_name', 'Untitled Course')
        if self.verbose:
            print(f"🎓 Course: {course_name}")
        
        # Build course structure recursively
        structure = {
            'type': 'course',
            'display_name': course_name,
            'url_name': course_url_name,
            'children': []
        }
        
        # Process course children - handle different OLX formats
        for child in course_root:
            # Handle different ways children can be referenced
            url_name = child.get('url_name') or child.get('url_name_ref')
            
            if url_name:
                child_structure = self.parse_component_recursive(
                    child.tag, url_name, level=1
                )
                if child_structure:
                    structure['children'].append(child_structure)
            else:
                # Some OLX files embed content directly without url_name
                # Try to process as inline content
                display_name = child.get('display_name', f'Inline {child.tag}')
                
                inline_structure = {
                    'type': child.tag,
                    'display_name': display_name,
                    'url_name': child.get('url_name', f'inline_{child.tag}'),
                    'children': []
                }
                
                # Process any nested children
                for nested_child in child:
                    nested_url_name = nested_child.get('url_name') or nested_child.get('url_name_ref')
                    if nested_url_name:
                        nested_structure = self.parse_component_recursive(
                            nested_child.tag, nested_url_name, level=2
                        )
                        if nested_structure:
                            inline_structure['children'].append(nested_structure)
                
                if inline_structure['children'] or child.tag in ['chapter', 'sequential', 'vertical']:
                    structure['children'].append(inline_structure)
        
        return structure
    
    def parse_component_recursive(self, component_type: str, url_name: str, level: int = 0) -> Optional[Dict]:
        """Recursively parse a component and its children, and include its XML structure as a string"""
        if self.verbose:
            indent = "  " * level
            print(f"{indent}🔍 Following: {component_type}/{url_name}")
        
        display_name, actual_url_name, children = self.get_component_info(component_type, url_name)
        
        # Get XML structure as string
        file_path = self.olx_dir / component_type / f"{url_name}.xml"
        xml_string = ''
        if file_path.exists():
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    xml_string = f.read()
            except Exception:
                xml_string = ''
        
        if self.verbose:
            indent = "  " * level
            print(f"{indent}   📋 Parsing: {display_name}")
            if children:
                print(f"{indent}   ✅ Found {len(children)} child components")
        
        component_structure = {
            'type': component_type,
            'display_name': display_name,
            'url_name': actual_url_name,
            'xml_string': xml_string,
            'children': []
        }
        
        # Process children recursively
        for child_type, child_url_name in children:
            child_structure = self.parse_component_recursive(
                child_type, child_url_name, level + 1
            )
            if child_structure:
                component_structure['children'].append(child_structure)
        
        return component_structure
    
    def count_components(self, node, counts=None):
        """Count components recursively"""
        if counts is None:
            counts = {}
        
        comp_type = node['type']
        counts[comp_type] = counts.get(comp_type, 0) + 1
        
        for child in node.get('children', []):
            self.count_components(child, counts)
        
        return counts
    
    def generate_interactive_html(self, structure: Dict, output_file: str = None):
        """Generate an interactive HTML file with expandable/collapsible tree and search"""
        
        # Auto-generate output filename from source path if not provided
        if output_file is None:
            # Use original path name (whether zip, tar.gz, or directory)
            source_name = self.original_path.stem
            # Handle .tar.gz files where stem only gives us .tar
            if source_name.endswith('.tar'):
                source_name = source_name[:-4]  # Remove .tar to get the actual base name
            output_file = f"{source_name}_structure.html"
        
        # Get component counts
        counts = self.count_components(structure)
        
        html_template = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{course_title}</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 20px;
            background-color: #f5f5f5;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        .header {
            text-align: center;
            margin-bottom: 30px;
            padding-bottom: 20px;
            border-bottom: 2px solid #e0e0e0;
        }
        .header h1 {
            color: #333;
            margin-bottom: 10px;
        }
        .search-container {
            background: #f8f9fa;
            padding: 20px;
            border-radius: 5px;
            margin-bottom: 20px;
            border: 1px solid #dee2e6;
        }
        .search-box {
            width: 100%;
            padding: 12px;
            font-size: 16px;
            border: 2px solid #007bff;
            border-radius: 5px;
            box-sizing: border-box;
        }
        .search-box:focus {
            outline: none;
            border-color: #0056b3;
            box-shadow: 0 0 5px rgba(0,123,255,0.3);
        }
        .search-info {
            margin-top: 10px;
            color: #666;
            font-size: 14px;
        }
        .search-results {
            margin-top: 10px;
            font-weight: bold;
            color: #007bff;
        }
        .summary {
            background: #f8f9fa;
            padding: 20px;
            border-radius: 5px;
            margin-bottom: 30px;
        }
        .summary h3 {
            margin-top: 0;
            color: #495057;
        }
        .summary-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 10px;
            margin-top: 15px;
        }
        .summary-item {
            background: white;
            padding: 10px;
            border-radius: 5px;
            text-align: center;
            border: 1px solid #dee2e6;
        }
        .tree {
            font-family: 'Courier New', monospace;
            line-height: 1.6;
        }
        .tree-node {
            margin: 2px 0;
            position: relative;
        }
        .tree-node.hidden {
            display: none;
        }
        .tree-node.search-highlight {
            background-color: #fff3cd;
            border-left: 4px solid #ffc107;
            padding-left: 10px;
            margin-left: -14px;
        }
        .tree-toggle {
            cursor: pointer;
            user-select: none;
            display: inline-block;
            width: 20px;
            text-align: center;
            color: #666;
            font-weight: bold;
        }
        .tree-toggle:hover {
            color: #007bff;
        }
        .tree-content {
            display: inline-block;
            padding: 4px 8px;
            border-radius: 4px;
            margin-left: 5px;
        }
        .tree-content:hover {
            background-color: #e9ecef;
        }
        .tree-children {
            margin-left: 25px;
            border-left: 1px dotted #ccc;
            padding-left: 15px;
        }
        .tree-children.collapsed {
            display: none;
        }
        .component-type {
            color: #666;
            font-size: 0.9em;
            font-weight: normal;
        }
        .component-name {
            font-weight: bold;
            color: #333;
        }
        .component-url {
            color: #888;
            font-size: 0.85em;
            font-style: italic;
        }
        .search-match {
            background-color: #ffeb3b;
            padding: 1px 2px;
            border-radius: 2px;
        }
        .controls {
            margin-bottom: 20px;
            text-align: center;
        }
        .btn {
            background: #007bff;
            color: white;
            border: none;
            padding: 8px 16px;
            margin: 0 5px;
            border-radius: 4px;
            cursor: pointer;
            font-size: 14px;
        }
        .btn:hover {
            background: #0056b3;
        }
        .btn-secondary {
            background: #6c757d;
        }
        .btn-secondary:hover {
            background: #545b62;
        }
        .clear-search {
            background: #dc3545;
            color: white;
            border: none;
            padding: 8px 16px;
            margin: 0 5px;
            border-radius: 4px;
            cursor: pointer;
            font-size: 14px;
        }
        .clear-search:hover {
            background: #c82333;
        }
        .xml-toggle {
            cursor: pointer;
            user-select: none;
            display: inline-block;
            width: auto;
            text-align: center;
            color: #666;
            font-weight: bold;
            margin-left: 8px;
        }
        .xml-toggle:hover, .xml-toggle:focus {
            color: #007bff;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📋 {course_title}</h1>
            <p>Search through components or click on [+] and [-] to expand/collapse sections</p>
        </div>
        
        <div class="search-container">
            <input type="text" class="search-box" id="searchBox" placeholder="🔍 Search components by name, type, or URL..." />
            <div class="search-info">
                Search across component names, types (e.g., "video", "problem"), and URL names
            </div>
            <div class="search-results" id="searchResults"></div>
        </div>
        
        <div class="summary">
            <h3>📊 Component Summary</h3>
            <div class="summary-grid">
                {summary_items}
            </div>
        </div>
        
        <div class="controls">
            <button class="btn" onclick="expandAll()">Expand All</button>
            <button class="btn btn-secondary" onclick="collapseAll()">Collapse All</button>
            <button class="clear-search" onclick="clearSearch()">Clear Search</button>
        </div>
        
        <div class="tree" id="tree-container">
            {tree_html}
        </div>
    </div>

    <script>
        let allNodes = [];
        let searchTimeout;
        
        // Initialize after DOM loads
        document.addEventListener('DOMContentLoaded', function() {
            // Cache all tree nodes for search
            allNodes = Array.from(document.querySelectorAll('.tree-node'));
            
            // Set up search functionality
            const searchBox = document.getElementById('searchBox');
            searchBox.addEventListener('input', function() {
                clearTimeout(searchTimeout);
                searchTimeout = setTimeout(() => performSearch(this.value.trim()), 300);
            });
            
            collapseAll()
            // Initialize with first level expanded
            const firstLevelToggles = document.querySelectorAll('.tree > .tree-node > .tree-toggle');
            firstLevelToggles.forEach(toggle => {
                // Only expand if this node actually has children
                if (toggle.parentElement.querySelector('.tree-children')) {
                    toggleNode(toggle);
                }
            });
        });
        
        function performSearch(query) {
            const resultsDiv = document.getElementById('searchResults');
            
            if (!query) {
                clearSearch();
                return;
            }
            
            const lowerQuery = query.toLowerCase();
            let matchCount = 0;
            let visibleNodes = new Set();
            
            // Reset all nodes
            allNodes.forEach(node => {
                node.classList.remove('hidden', 'search-highlight');
                // Remove previous search highlights
                const content = node.querySelector('.tree-content');
                if (content) {
                    content.innerHTML = content.innerHTML.replace(/<span class="search-match">(.*?)<\/span>/g, '$1');
                }
            });
            
            // Find matches
            allNodes.forEach(node => {
                const content = node.querySelector('.tree-content');
                if (!content) return;
                
                const nameElement = content.querySelector('.component-name');
                const typeElement = content.querySelector('.component-type');
                const urlElement = content.querySelector('.component-url');
                
                const name = nameElement ? nameElement.textContent.toLowerCase() : '';
                const type = typeElement ? typeElement.textContent.toLowerCase() : '';
                const url = urlElement ? urlElement.textContent.toLowerCase() : '';
                
                if (name.includes(lowerQuery) || type.includes(lowerQuery) || url.includes(lowerQuery)) {
                    matchCount++;
                    node.classList.add('search-highlight');
                    visibleNodes.add(node);
                    
                    // Highlight matching text
                    highlightText(nameElement, lowerQuery);
                    highlightText(typeElement, lowerQuery);
                    highlightText(urlElement, lowerQuery);
                    
                    // Make sure all parents are visible
                    let parent = node.parentElement;
                    while (parent && parent !== document.body) {
                        if (parent.classList && parent.classList.contains('tree-node')) {
                            visibleNodes.add(parent);
                        }
                        parent = parent.parentElement;
                    }

                    // Also make all children visible
                    function addChildrenToVisible(n) {
                        const childrenContainer = n.querySelector('.tree-children');
                        if (childrenContainer) {
                            Array.from(childrenContainer.children).forEach(child => {
                                if (child.classList && child.classList.contains('tree-node')) {
                                    visibleNodes.add(child);
                                    addChildrenToVisible(child);
                                }
                            });
                        }
                    }
                    addChildrenToVisible(node);
                }
            });
            
            // Hide non-matching nodes
            allNodes.forEach(node => {
                if (!visibleNodes.has(node)) {
                    node.classList.add('hidden');
                }
            });
            
            // Expand all visible parent nodes to show matches
            visibleNodes.forEach(node => {
                const children = node.querySelector('.tree-children');
                if (children) {
                    children.classList.remove('collapsed');
                    const toggle = node.querySelector('.tree-toggle');
                    if (toggle && children.children.length > 0) {
                        toggle.textContent = '[-]';
                    }
                }
            });
            
            // Update results
            resultsDiv.textContent = matchCount > 0 ? 
                `Found ${matchCount} matching component${matchCount !== 1 ? 's' : ''}` :
                'No matches found';
        }
        
        function highlightText(element, query) {
            if (!element || !query) return;
            
            const text = element.textContent;
            const lowerText = text.toLowerCase();
            const lowerQuery = query.toLowerCase();
            
            if (lowerText.includes(lowerQuery)) {
                const index = lowerText.indexOf(lowerQuery);
                const before = text.substring(0, index);
                const match = text.substring(index, index + query.length);
                const after = text.substring(index + query.length);
                
                element.innerHTML = before + '<span class="search-match">' + match + '</span>' + after;
            }
        }
        
        function clearSearch() {
            const searchBox = document.getElementById('searchBox');
            const resultsDiv = document.getElementById('searchResults');
            
            searchBox.value = '';
            resultsDiv.textContent = '';
            
            // Show all nodes and remove highlights
            allNodes.forEach(node => {
                node.classList.remove('hidden', 'search-highlight');
                const content = node.querySelector('.tree-content');
                if (content) {
                    content.innerHTML = content.innerHTML.replace(/<span class="search-match">(.*?)<\/span>/g, '$1');
                }
            });
            
            // Reset to default collapsed state
            collapseAll();
            const firstLevelChildren = document.querySelectorAll('.tree > .tree-node > .tree-children');
            firstLevelChildren.forEach(child => child.classList.remove('collapsed'));
        }
        
        function toggleNode(element) {
            const children = element.parentElement.querySelector('.tree-children');
            const toggle = element;
            
            if (children) {
                if (children.classList.contains('collapsed')) {
                    children.classList.remove('collapsed');
                    toggle.textContent = '[-]';
                } else {
                    children.classList.add('collapsed');
                    toggle.textContent = '[+]';
                }
            }
        }
        
        function expandAll() {
            const allChildren = document.querySelectorAll('.tree-children:not(.hidden)');
            const allToggles = document.querySelectorAll('.tree-toggle');
            
            allChildren.forEach(child => child.classList.remove('collapsed'));
            allToggles.forEach(toggle => {
                const parentNode = toggle.parentElement;
                if (parentNode && !parentNode.classList.contains('hidden') && 
                    toggle.parentElement.querySelector('.tree-children')) {
                    toggle.textContent = '[-]';
                }
            });
        }
        
        function collapseAll() {
            const allChildren = document.querySelectorAll('.tree-children');
            const allToggles = document.querySelectorAll('.tree-toggle');
            
            allChildren.forEach(child => child.classList.add('collapsed'));
            allToggles.forEach(toggle => {
                if (toggle.parentElement.querySelector('.tree-children')) {
                    toggle.textContent = '[+]';
                }
            });
        }

        // Add this JS function for XML toggle
        function toggleXml(xmlId, btn) {
            const xmlBlock = document.getElementById(xmlId);
            if (!xmlBlock) return;
            if (xmlBlock.style.display === 'none') {
                xmlBlock.style.display = 'block';
                btn.textContent = '[hide xml]';
            } else {
                xmlBlock.style.display = 'none';
                btn.textContent = '[show xml]';
            }
        }
    </script>
</body>
</html>
        """
        
        # Generate summary items HTML
        summary_html = ""
        icon_map = {
            'course': '🎓', 'chapter': '📚', 'sequential': '📄', 
            'vertical': '📝', 'problem': '❓', 'video': '🎥', 
            'html': '📋', 'discussion': '💬'
        }
        
        for comp_type, count in sorted(counts.items()):
            icon = icon_map.get(comp_type, '📦')
            summary_html += f'<div class="summary-item">{icon} <strong>{count}</strong><br>{comp_type}</div>'
        
        # Generate tree HTML
        tree_html = self.generate_tree_html(structure)
        
        # Get course name for title
        course_title = structure.get('display_name', 'Course') + ' Structure'
        
        # Fill in the template - escape any remaining braces
        final_html = html_template.replace('{summary_items}', summary_html).replace('{tree_html}', tree_html).replace('{course_title}', course_title)
        
        # Write to file
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(final_html)
        
        print(f"✅ Interactive HTML with search generated: {output_file}")
        print(f"   Open this file in your web browser to view the searchable expandable tree!")
    
    def generate_tree_html(self, node, is_root=True, level=0, node_id_prefix=''):
        """Generate HTML for tree structure, including collapsible XML string as a sibling to component-url"""
        icon_map = {
            'course': '🎓', 'chapter': '📚', 'sequential': '📄', 
            'vertical': '📝', 'problem': '❓', 'video': '🎥', 
            'html': '📋', 'discussion': '💬'
        }
        
        icon = icon_map.get(node['type'], '📦')
        children = node.get('children', [])
        
        # Unique id for XML block
        import uuid
        xml_block_id = f"xmlblock_{uuid.uuid4().hex}"
        
        # Determine if children should be collapsed or expanded by default
        if level == 0:
            if children:
                toggle_html = '<span class="tree-toggle" onclick="toggleNode(this)">[-]</span>'
            else:
                toggle_html = ''
            children_collapsed = False
        elif level == 1:
            toggle_html = '<span class="tree-toggle" onclick="toggleNode(this)">[-]</span>'
            children_collapsed = False
        else:
            toggle_html = '<span class="tree-toggle" onclick="toggleNode(this)">[+]</span>'
            children_collapsed = True
        
        # Escape XML for HTML display
        import html
        xml_string_escaped = html.escape(node.get('xml_string', ''))
        
        # Show XML toggle as a span, not a button
        show_xml_btn = f'<span class="xml-toggle" onclick="toggleXml(\'{xml_block_id}\', this)">[show xml]</span>'
        
        # Create the node content
        content_html = f'''
        <div class="tree-node">
            {toggle_html}{show_xml_btn}
            <span class="tree-content">
                {icon} 
                <span class="component-type">[{node['type']}]</span> 
                <span class="component-name">{node['display_name']}</span> 
                <span class="component-url">({node['url_name']})</span>
            </span>
            <span class="component-xml" id="{xml_block_id}" style="display:none; margin-top:4px;">
                <pre style="white-space:pre-wrap; background:#f8f8f8; border:1px solid #ccc; padding:6px; border-radius:4px;">{xml_string_escaped}</pre>
            </span>
        '''
        
        if children:
            children_class = 'tree-children'
            if children_collapsed:
                children_class += ' collapsed'
            content_html += f'<div class="{children_class}">'
            for child in children:
                content_html += self.generate_tree_html(child, False, level+1)
            content_html += '</div>'
        
        content_html += '</div>'
        
        return content_html

def main():
    """Main function to demonstrate the interactive OLX parser"""
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate interactive OLX course structure with search')
    parser.add_argument('olx_path', help='Path to the OLX course directory, zip file, tar.gz file, or tgz file')
    parser.add_argument('-v', '--verbose', action='store_true', help='Enable verbose debug output')
    parser.add_argument('-o', '--output', default=None, help='Output HTML file name (default: <source_name>_structure.html)')
    
    args = parser.parse_args()
    
    try:
        # Use context manager to ensure cleanup
        with InteractiveOLXParser(args.olx_path, verbose=args.verbose) as olx_parser:
            structure = olx_parser.parse_course_structure()
            olx_parser.generate_interactive_html(structure, args.output)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()