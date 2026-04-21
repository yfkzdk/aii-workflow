#!/usr/bin/env python3
"""
Report Fixer - Fix garbled characters in analysis reports
"""

import os
import re
import sys
from pathlib import Path

def fix_garbled_report(input_path):
    """Fix garbled characters in a report file"""

    if not os.path.exists(input_path):
        print(f"Error: File not found: {input_path}")
        return False

    try:
        # Read the file
        with open(input_path, 'r', encoding='utf-8') as f:
            content = f.read()

        print(f"Original file: {input_path}")
        print(f"File size: {len(content)} bytes")

        # Fix common garbled characters
        fixes = {
            '鉁\\?': '✓',      # Checkmark symbol
            '鈥?': '-',        # Dash
            '鈥?|': '|',       # Pipe
            '鈥?`"': '"',      # Quote
            '聽': ' ',         # Non-breaking space
            '鈥橢': "'",       # Apostrophe
            '鈥?': "'",        # Another apostrophe
        }

        # Apply fixes
        original_content = content
        for bad, good in fixes.items():
            content = content.replace(bad, good)

        # Also fix checkmark with regex
        content = re.sub(r'鉁\?', '✓', content)

        # Create output filename
        output_path = input_path.replace('.md', '_fixed.md')

        # Save fixed content
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)

        print(f"Fixed file saved: {output_path}")

        # Show diff
        original_lines = original_content.split('\n')
        fixed_lines = content.split('\n')

        print("\n=== Fixed Content Preview ===")
        for i, (orig, fixed) in enumerate(zip(original_lines[:10], fixed_lines[:10])):
            if orig != fixed:
                print(f"Line {i+1}:")
                print(f"  Before: {repr(orig)}")
                print(f"  After:  {repr(fixed)}")
                print()

        print("\n=== Full Fixed Content ===")
        print(content)

        return True

    except Exception as e:
        print(f"Error fixing file: {e}")
        return False

def find_latest_report(reports_dir):
    """Find the latest report file"""

    if not os.path.exists(reports_dir):
        print(f"Reports directory not found: {reports_dir}")
        return None

    md_files = list(Path(reports_dir).glob("*.md"))
    if not md_files:
        print("No .md files found in reports directory")
        return None

    # Sort by modification time
    latest = max(md_files, key=lambda x: x.stat().st_mtime)
    return str(latest)

def show_all_reports(reports_dir):
    """Show all available reports"""

    if not os.path.exists(reports_dir):
        print(f"Reports directory not found: {reports_dir}")
        return

    md_files = list(Path(reports_dir).glob("*.md"))
    if not md_files:
        print("No reports found")
        return

    print("=== Available Reports ===")
    for i, file in enumerate(sorted(md_files, key=lambda x: x.stat().st_mtime, reverse=True), 1):
        size = file.stat().st_size
        mtime = file.stat().st_mtime
        from datetime import datetime
        mtime_str = datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S')

        status = "[Fixed]" if "_fixed" in file.name else "[Original]"
        print(f"{i}. {status} {file.name}")
        print(f"   Size: {size} bytes | Modified: {mtime_str}")
        print(f"   Path: {file}")
        print()

def main():
    """Main function"""

    reports_dir = "./output/reports"

    if not os.path.exists(reports_dir):
        print("Creating reports directory...")
        os.makedirs(reports_dir, exist_ok=True)

    print("=== Report Fixer Tool ===")
    print("Fixes garbled characters in analysis reports")
    print()

    # Show available reports
    show_all_reports(reports_dir)

    # Ask user what to do
    print("Options:")
    print("  1. Fix the latest report")
    print("  2. Fix all reports")
    print("  3. Show a specific report")
    print("  4. Exit")

    try:
        choice = input("\nEnter choice (1-4): ").strip()

        if choice == "1":
            # Fix latest report
            latest = find_latest_report(reports_dir)
            if latest:
                print(f"\nFixing latest report: {os.path.basename(latest)}")
                fix_garbled_report(latest)
            else:
                print("No reports found to fix")

        elif choice == "2":
            # Fix all reports
            md_files = list(Path(reports_dir).glob("*.md"))
            fixed_files = [f for f in md_files if "_fixed" not in f.name]

            if not fixed_files:
                print("No unfixed reports found")
                return

            print(f"\nFixing {len(fixed_files)} reports...")
            for i, file in enumerate(fixed_files, 1):
                print(f"\n[{i}/{len(fixed_files)}] Fixing: {file.name}")
                fix_garbled_report(str(file))

        elif choice == "3":
            # Show specific report
            md_files = list(Path(reports_dir).glob("*.md"))
            if not md_files:
                print("No reports found")
                return

            print("\nSelect a report to view:")
            for i, file in enumerate(sorted(md_files, key=lambda x: x.stat().st_mtime, reverse=True), 1):
                print(f"{i}. {file.name}")

            try:
                file_choice = int(input("\nEnter report number: ").strip())
                if 1 <= file_choice <= len(md_files):
                    selected = sorted(md_files, key=lambda x: x.stat().st_mtime, reverse=True)[file_choice - 1]
                    print(f"\n=== Content of {selected.name} ===")
                    with open(selected, 'r', encoding='utf-8') as f:
                        print(f.read())
                else:
                    print("Invalid selection")
            except ValueError:
                print("Invalid input")

        elif choice == "4":
            print("Exiting...")
            return

        else:
            print("Invalid choice")

    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()