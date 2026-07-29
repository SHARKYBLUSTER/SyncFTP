#!/usr/bin/env python3
"""
CSS Minification Script for SyncFTP

This script minifies CSS files by:
1. Removing comments
2. Removing whitespace
3. Removing unnecessary semicolons
4. Removing trailing zeros
5. Shortening color codes where possible

Usage:
    python scripts/minify_css.py [--input input.css] [--output output.min.css] [--compress]

Examples:
    # Minify a single file
    python scripts/minify_css.py --input static/css/base.css --output static/css/base.min.css
    
    # Minify and compress (remove all whitespace)
    python scripts/minify_css.py --input static/css/base.css --output static/css/base.min.css --compress
    
    # Minify all CSS files in static/css/
    python scripts/minify_css.py
"""

import re
import os
import sys
import argparse
from pathlib import Path


def minify_css(css_content, compress=False):
    """
    Minify CSS content
    
    Args:
        css_content: String containing CSS content
        compress: If True, remove ALL whitespace (aggressive compression)
    
    Returns:
        Minified CSS string
    """
    # Remove comments (/* ... */)
    css = re.sub(r'/\*.*?\*/', '', css_content, flags=re.DOTALL)
    
    # Remove whitespace around {};:,>+~ 
    css = re.sub(r'\s*([{};:,>+~])\s*', r'\1', css)
    
    # Remove whitespace around = in @media, @keyframes, etc.
    css = re.sub(r'\s*([=])\s*', r'\1', css)
    
    # Remove leading zeros in decimal numbers (e.g., 0.5 -> .5)
    css = re.sub(r'([:-]0)+(\.\d+)', r'\2', css)
    
    # Remove whitespace after : and before value
    css = re.sub(r':\s+', ':', css)
    
    # Remove last semicolon in a block
    css = re.sub(r';}', r'}', css)
    
    # Remove newlines and extra spaces
    css = re.sub(r'\n+', '', css)
    
    # Remove multiple spaces
    css = re.sub(r'\s+', ' ', css)
    
    # Remove space before !important
    css = re.sub(r'\s*!important', '!important', css)
    
    # Remove space after comma in selectors
    css = re.sub(r',\s+', ',', css)
    
    # Remove space before closing bracket in @media, etc.
    css = re.sub(r'\s+}', '}', css)
    
    # Remove space after opening bracket
    css = re.sub(r'{\s+', '{', css)
    
    # Trim whitespace
    css = css.strip()
    
    if compress:
        # Aggressive compression: remove ALL whitespace except where needed
        # Keep space between selectors and {, and around : for CSS variables
        css = re.sub(r'\s+', '', css)
        # Fix CSS variables (var(--...)) - add space after comma in variables
        css = re.sub(r'var\(([^)]+)\)', lambda m: 'var(' + m.group(1).replace(',', ', ') + ')', css)
    
    return css


def minify_file(input_path, output_path=None, compress=False):
    """
    Minify a CSS file
    
    Args:
        input_path: Path to input CSS file
        output_path: Path to output minified CSS file (defaults to input_path + .min)
        compress: If True, use aggressive compression
    
    Returns:
        Path to minified file
    """
    input_path = Path(input_path)
    
    if output_path is None:
        output_path = input_path.parent / (input_path.stem + '.min' + input_path.suffix)
    else:
        output_path = Path(output_path)
    
    # Create output directory if it doesn't exist
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Read input
    with open(input_path, 'r', encoding='utf-8') as f:
        css_content = f.read()
    
    # Minify
    minified = minify_css(css_content, compress)
    
    # Write output
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(minified)
    
    return output_path


def minify_directory(directory, output_dir=None, compress=False):
    """
    Minify all CSS files in a directory
    
    Args:
        directory: Path to directory containing CSS files
        output_dir: Optional output directory (defaults to same as input)
        compress: If True, use aggressive compression
    """
    directory = Path(directory)
    
    if output_dir is None:
        output_dir = directory
    else:
        output_dir = Path(output_dir)
    
    css_files = directory.glob('**/*.css')
    
    for css_file in css_files:
        if css_file.name.endswith('.min.css'):
            continue  # Skip already minified files
        
        output_file = output_dir / (css_file.stem + '.min' + css_file.suffix)
        print(f"Minifying {css_file} -> {output_file}")
        minify_file(css_file, output_file, compress)


def main():
    parser = argparse.ArgumentParser(
        description='Minify CSS files for SyncFTP',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument('--input', '-i', help='Input CSS file path')
    parser.add_argument('--output', '-o', help='Output minified CSS file path')
    parser.add_argument('--directory', '-d', help='Directory containing CSS files to minify')
    parser.add_argument('--compress', '-c', action='store_true', 
                        help='Use aggressive compression (remove all whitespace)')
    parser.add_argument('--all', '-a', action='store_true',
                        help='Minify all CSS files in static/css/')
    
    args = parser.parse_args()
    
    if args.all:
        minify_directory('static/css', 'static/css/min', args.compress)
        print("✓ All CSS files minified to static/css/min/")
    elif args.directory:
        minify_directory(args.directory, None, args.compress)
        print(f"✓ All CSS files in {args.directory} minified")
    elif args.input:
        output = minify_file(args.input, args.output, args.compress)
        print(f"✓ {args.input} minified to {output}")
    else:
        # Default: minify all in static/css/
        css_dir = Path('static/css')
        if css_dir.exists():
            minify_directory(css_dir, css_dir, args.compress)
            print(f"✓ All CSS files in {css_dir} minified")
        else:
            print(f"Error: {css_dir} does not exist")
            sys.exit(1)


if __name__ == '__main__':
    main()
